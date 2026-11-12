"""无头量前滚翻策略：站 2 s → 触发 → 看 6 s，记累计前翻角、腾空、前移、是否站回。不开窗口、不跑 robotd。
动作窗口 1 s（robotd 默认）/ 2 s（infer_policy 默认）× 电压 6.5 / 7.4 / 8.2 V（训练随机范围的两端和标称）各跑一次。
用法（microduck_rl 根目录）：uv run python roll_eval.py <walk.onnx> <roulade.onnx> [<roulade.onnx> ...]
第一行是不触发的阴性对照；每份策略每种组合打印一行 RESULT JSON。ok = 翻过 300° 且最后站直。
N=50 uv run python roll_eval.py ...：改成随机抽样比成功率。这里是确定性仿真但对初值敏感，每种组合只跑一次不足以比好坏
（11-05：官方 onnx 6 格过 5 格，看着差不多，随机 50 次 1 s 窗口才露出只过 36 次）。每次抽电压 6.5–8.2、触发时刻 1.5–2.5 s、关节初值 ±0.02 rad。
"""
import json, math, os, sys

import mujoco
import numpy as np

sys.path.insert(0, "scripts")
import infer_policy as ip   # 官方 CPU 推理脚本：BAM 执行器与训练一致

DT, DECIM = 0.005, 4
CTRL_DT = DT * DECIM


def run(walk, roll, dur, vin, trigger=True, t0=2.0, rng=None):
    bam = ip.load_bam_model(ip.BAM_KP_FW, vin, 0.0)
    model, data, ctrl, _ = ip.load_mujoco_with_bam(ip.MICRODUCK_XML, bam, DT, 0.1, ip.BAM_VIN_MIN)
    pol = ip.PolicyInference(model, data, bam_ctrl=ctrl, walking_onnx_path=walk, use_projected_gravity=True,
                             roulade_onnx_path=roll, roulade_duration=dur, new_cmd_obs=True)   # 61D 观测
    pol.set_vel_cmd(0.0, 0.0, 0.0)
    fj = model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "trunk_base_freejoint")]
    data.qpos[fj:fj + 3] = [0, 0, 0.125]; data.qpos[fj + 3:fj + 7] = [1, 0, 0, 0]
    for i, q in enumerate(pol.joint_qpos_indices): data.qpos[q] = pol.default_pose[i] + (rng.uniform(-.02, .02) if rng else 0)
    ctrl.reset(data.qpos); pol.set_position_targets(pol.default_pose); mujoco.mj_forward(model, data)

    start = int(t0 / CTRL_DT)
    ang, ups, zs, air, wmax, x0 = [], [], [], 0, 0., 0.
    for step in range(start + int(6.0 / CTRL_DT)):
        if step == start:
            x0 = data.qpos[fj]
            if trigger: pol.trigger_behavior("roulade")
        pol.update_behavior(CTRL_DT)
        pol.apply_action(pol.infer())
        for _ in range(DECIM): ctrl.update(); mujoco.mj_step(model, data)
        w, x, y, z = data.qpos[fj + 3:fj + 7]
        upx, upz = 2 * (x * z + w * y), 1 - 2 * (x * x + y * y)   # 躯干上方向在世界 xz 平面的分量
        if step >= start:
            ang.append(math.atan2(upx, upz)); ups.append(upz); zs.append(data.qpos[fj + 2])
            air += data.ncon == 0
            wmax = max(wmax, abs(data.qvel[model.jnt_dofadr[0] + 4]))
    a = np.unwrap(ang)
    rot = math.degrees(a[-1] - a[0]); peak = math.degrees(np.abs(a - a[0]).max())
    return {"onnx": roll.split("/")[-1], "dur": dur, "vin": vin, "trigger": trigger, "ok": bool(peak > 300 and ups[-1] > 0.9),
            "rot_deg": round(rot), "max_rot_deg": round(peak), "air_s": round(air * CTRL_DT, 2), "max_w_rad_s": round(float(wmax), 1),
            "min_z": round(min(zs), 3), "end_z": round(zs[-1], 3), "end_upright": round(ups[-1], 3), "dx_m": round(float(data.qpos[fj] - x0), 3)}


if __name__ == "__main__":
    walk, rolls = sys.argv[1], sys.argv[2:]
    r = run(walk, rolls[0], 2.0, 7.4, trigger=False)
    assert abs(r["max_rot_deg"]) < 10, r              # 不触发还转了 = 量法或站立策略坏了，后面的数都不算
    print("RESULT", json.dumps(r), flush=True)
    n = int(os.environ.get("N", "0"))
    for roll in rolls:
        for dur in (1.0, 2.0):
            if not n:
                for vin in (6.5, 7.4, 8.2):
                    print("RESULT", json.dumps(run(walk, roll, dur, vin)), flush=True)
                continue
            rng = np.random.default_rng(0)                # 每份策略抽到同一批条件
            rs = [run(walk, roll, dur, rng.uniform(6.5, 8.2), t0=rng.uniform(1.5, 2.5), rng=rng) for _ in range(n)]
            print("RESULT", json.dumps({"onnx": roll.split("/")[-1], "dur": dur, "n": n, "ok": sum(r["ok"] for r in rs),
                                        "fail_peak": [r["max_rot_deg"] for r in rs if not r["ok"]][:12],
                                        "air_s_mean": round(float(np.mean([r["air_s"] for r in rs])), 3),
                                        "w_max": max(r["max_w_rad_s"] for r in rs), "dx_mean": round(float(np.mean([r["dx_m"] for r in rs])), 3)}), flush=True)

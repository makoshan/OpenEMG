"""在 Spark 上无头量 ground_pick 槽策略（鞠躬）：复用官方 scripts/infer_policy.py 的模型加载和推理类，
不开窗口、不跑 robotd。站 2 s → 触发 ground_pick（周期 4 s）→ 再看 3 s，记嘴尖高度、躯干高度/前倾、膝髋。
用法（仓库根目录）：uv run python bow_eval.py <walk.onnx> <ground_pick.onnx> [<ground_pick.onnx> ...]
每份打印一行 RESULT JSON。和 Mac 仿真（robotd，phase 0.7 切走）不同：这里放满整个周期。
"""
import json, math, os, sys

import mujoco
import numpy as np

sys.path.insert(0, "scripts")
import infer_policy as ip   # 官方 CPU 推理脚本：BAM 执行器与训练一致

DT, DECIM = 0.005, 4
CTRL_DT = DT * DECIM
CUT = float(os.environ.get("CUT", "1.0"))   # robotd 在 phase 0.7 切回 velstand；CUT=0.7 模拟它，默认放满整个周期


def run(walk, gp):
    bam = ip.load_bam_model(ip.BAM_KP_FW, 7.4, 0.0)
    model, data, ctrl, _ = ip.load_mujoco_with_bam(ip.MICRODUCK_XML, bam, DT, 0.1, ip.BAM_VIN_MIN)
    pol = ip.PolicyInference(model, data, bam_ctrl=ctrl, walking_onnx_path=walk, use_projected_gravity=True,
                             ground_pick_onnx_path=gp, ground_pick_period=4.0, new_cmd_obs=True)   # 61D 观测 = 3+3+14×3+13
    pol.set_vel_cmd(0.0, 0.0, 0.0)
    fj = model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "trunk_base_freejoint")]
    data.qpos[fj:fj + 3] = [0, 0, 0.125]; data.qpos[fj + 3:fj + 7] = [1, 0, 0, 0]
    for i, q in enumerate(pol.joint_qpos_indices): data.qpos[q] = pol.default_pose[i]
    ctrl.reset(data.qpos); pol.set_position_targets(pol.default_pose); mujoco.mj_forward(model, data)
    names = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, model.jnt_qposadr.tolist().index(q)) if q in model.jnt_qposadr else "?" for q in pol.joint_qpos_indices]
    pick = {k: names.index(k) for k in ("left_hip_pitch", "right_hip_pitch", "left_knee", "right_knee", "neck_pitch") if k in names}

    def sample():
        w, x, y, z = data.qpos[fj + 3:fj + 7]
        lean = math.degrees(math.asin(max(-1., min(1., 2 * (w * y - z * x)))))
        j = [data.qpos[pol.joint_qpos_indices[i]] for i in pick.values()]
        return [data.site("mouth_tip").xpos[2], data.qpos[fj + 2], lean, 1 - 2 * (x * x + y * y)] + j

    trace, t = [], 0.0
    for step in range(int(9.0 / CTRL_DT)):
        if step == int(2.0 / CTRL_DT): s0 = sample(); pol.trigger_ground_pick()
        pol.update_ground_pick_phase(CTRL_DT); pol.update_behavior(CTRL_DT)
        if pol.ground_pick_mode and pol.ground_pick_phase >= CUT: pol._end_ground_pick()
        pol.apply_action(pol.infer())
        for _ in range(DECIM): ctrl.update(); mujoco.mj_step(model, data)
        if step >= int(2.0 / CTRL_DT): trace.append(sample())
    a = np.array(trace)
    k = int(np.argmin(a[:, 0]))                       # 嘴尖最低那一刻
    joints = {n: round(float(a[k, 4 + i] - s0[4 + i]), 2) for i, n in enumerate(pick)}
    return {"onnx": gp.split("/")[-1], "cut": CUT, "stand_mouth_z": round(s0[0], 3), "min_mouth_z": round(float(a[:, 0].min()), 3),
            "stand_trunk_z": round(s0[1], 3), "trunk_z_at_min": round(float(a[k, 1]), 3),
            "lean_deg_at_min": round(float(a[k, 2] - s0[2]), 1), "t_min_s": round(k * CTRL_DT, 2),
            "joints_at_min_rad": joints, "end_mouth_z": round(float(a[-1, 0]), 3), "end_trunk_z": round(float(a[-1, 1]), 3),
            "fell": bool(a[:, 3].min() < 0.5)}


if __name__ == "__main__":
    for gp in sys.argv[2:]:
        print("RESULT", json.dumps(run(sys.argv[1], gp), ensure_ascii=False), flush=True)

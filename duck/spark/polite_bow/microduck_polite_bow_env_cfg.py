"""Microduck 鞠躬（PoliteBow）：在 GroundPick 上改，只改「低到哪、腿弯不弯」。

GroundPick：嘴尖贴地（target 0）再站回。鞠躬：嘴尖从站立的 0.225 m（STAND 关键帧实测）降到
BOW_MOUTH_Z，腿全程尽量保持站姿，再站回。相位、周期 4 s、61D 观测 / 14D 动作都与 GroundPick
一样，所以运行时直接放进 ground_pick 槽（netpad B 键），--ground-pick-period 不用改。

从官方 GroundPick 检查点热启动（它已经会「弯下去再站回」，只需改目标）：
    MICRODUCK_WARM_START=1 uv run train Mjlab-PoliteBow-Flat-MicroDuck --env.scene.num-envs 4096 \\
        --init-checkpoint hf://pollen-robotics/microduck-training/bundles/ground_pick/4ly1pcxj_2750
文件由 原力手环/duck/spark/polite_bow/install.sh 装进 Spark 上的 microduck_rl 检出（上游没有这个任务）。
"""

from copy import deepcopy

from mjlab.managers import RewardTermCfg

from mjlab_microduck.tasks import mdp as microduck_mdp
from mjlab_microduck.tasks.microduck_ground_pick_env_cfg import (
    DESCENT_END,
    HOLD_END,
    RISE_END,
    MicroduckGroundPickRlCfg,
    make_microduck_ground_pick_env_cfg,
)

BOW_MOUTH_Z = 0.13      # 嘴尖目标高度 (m)：站立 0.225，降约 10 cm，离地很远
BOW_MOUTH_STD = 0.08    # v1 用 0.05：热启动策略嘴贴地时奖励≈0.003，没梯度
BOW_LEAN = 0.45         # 躯干前倾目标，projected_gravity_b.x（≈sin 27°，正 = 前倾）
KNEE_ANKLE = [3, 4, 12, 13]   # 左膝、左踝、右膝、右踝（14 关节布局：0-4 左腿，5-8 脖子/头，9-13 右腿）
# 鸭子没有腰，弯腰就是 hip_pitch（2、11），所以只锁膝踝防蹲，髋放开（v1 锁全腿，弯腰和蹲一起罚，分不出）。


def make_microduck_polite_bow_env_cfg(play: bool = False, rough: bool = False):
    cfg = make_microduck_ground_pick_env_cfg(play=play, rough=rough)

    # 嘴尖目标从「贴地」改成「半高」
    near = cfg.rewards["mouth_ground_proximity"].params
    near["target_height"], near["std"] = BOW_MOUTH_Z, BOW_MOUTH_STD

    # 鞠躬时头朝下即可，不必像捡东西那样嘴垂直对地：权重 2.0 → 1.0
    cfg.rewards["mouth_perpendicular_to_ground"].weight = 1.0

    # 不叼东西：去掉往嘴上挂重物的钩子和对应事件
    del cfg.rewards["mouth_payload_force"]
    del cfg.events["sample_mouth_payload"]

    # 膝踝全程保持站姿（不蹲）。借 GroundPick 的「回站姿」奖励，hold_end=0、rise_end 极小
    # → 上升门在整个周期都等于 1（phase_rise_gate 的定义；phase 恰为 0 那一点是 0，可忽略）。
    cfg.rewards["bow_knees_straight"] = RewardTermCfg(
        func=microduck_mdp.ground_pick_return_pose_phased,
        weight=2.0,
        params={"std": 0.15, "command_name": "twist", "joint_indices": KNEE_ANKLE,
                "hold_end": 0.0, "rise_end": 1e-6},
    )

    # 弯腰本身：下降+停顿阶段奖励躯干前倾到 BOW_LEAN（现成项，roller_crouch 在用），相位切分同 GroundPick。
    cfg.rewards["bow_forward_lean"] = RewardTermCfg(
        func=microduck_mdp.crouch_forward_lean,
        weight=3.0,
        params={"command_name": "twist", "target_pitch": BOW_LEAN, "std": 0.15,
                "descent_end": DESCENT_END, "hold_end": HOLD_END, "rise_end": RISE_END},
    )
    return cfg


MicroduckPoliteBowRlCfg = deepcopy(MicroduckGroundPickRlCfg)
MicroduckPoliteBowRlCfg.experiment_name = "polite_bow"
MicroduckPoliteBowRlCfg.run_name = "polite_bow"

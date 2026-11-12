#!/bin/sh
# 把鞠躬任务装进 Spark 上的 microduck_rl 检出：拷配置文件 + 在 tasks/__init__.py 末尾注册（已注册就跳过）。
set -eu
HOST="${SPARK_HOST:-gpu-host}"; T='microduck_rl-20261103/src/mjlab_microduck/tasks'
/usr/bin/scp -q "$(dirname "$0")/microduck_polite_bow_env_cfg.py" "$HOST:$T/"
/usr/bin/ssh "$HOST" "cd $T && grep -q 'Mjlab-PoliteBow-Flat-MicroDuck' __init__.py && echo 已注册过 || { cat >> __init__.py <<'EOF'

# 鞠躬 — Mircoduck 本地加的任务（上游没有），见 microduck_polite_bow_env_cfg.py
from .microduck_polite_bow_env_cfg import make_microduck_polite_bow_env_cfg, MicroduckPoliteBowRlCfg
register_mjlab_task(
    task_id=\"Mjlab-PoliteBow-Flat-MicroDuck\",
    env_cfg=make_microduck_polite_bow_env_cfg(),
    play_env_cfg=make_microduck_polite_bow_env_cfg(play=True),
    rl_cfg=MicroduckPoliteBowRlCfg,
    runner_cls=MicroduckOnPolicyRunner,
)
EOF
echo 已注册; }"

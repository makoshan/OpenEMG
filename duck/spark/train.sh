#!/bin/sh
# 在 Spark 上训练 / 导出 Microduck 策略，结果拉回本机，再用 spark/sim_eval.sh 装进仿真比。
#   spark/train.sh start <名字> <任务> <轮数> [train 额外参数...]   后台开训；GPU 被别人占着就不开
#   spark/train.sh status <名字>          进度：最新检查点、最后几行日志、是否结束
#   spark/train.sh fetch <名字> [轮]      导出最新（或指定轮）检查点 → policies-trained/<名字>_<轮>.onnx
#   spark/train.sh stop <名字>
# 接着官方检查点微调：额外参数加 --init-checkpoint hf://pollen-robotics/microduck-training/bundles/velstand/0045i2si_2749
# （官方训练包公开，不用 wandb；--agent.max_iterations 在续训时是「再训多少轮」）。
# 热启动到别的任务：SPARK_ENV='MICRODUCK_WARM_START=1' spark/train.sh start ...（课程从 0 重来，。
# 连 gpu-host（Tailscale）：11-03 局域网地址 <gpu-lan-ip> 不通。任务目录 Spark:~/duck-jobs/<名字>/。
set -eu
HOST="${SPARK_HOST:-gpu-host}"; R='~/microduck_rl-20261103'; OUT="${MICRODUCK_DIR:-./microduck}/policies-trained"
cmd="${1:?start|status|fetch|stop}"; name="${2:?名字}"; shift 2
case "$name" in *[!A-Za-z0-9_.-]*) echo "名字只用字母数字 _ . -" >&2; exit 2;; esac
for a in "$@"; do case "$a" in *[\'\"\$\`\\]*) echo "参数里不能有引号、\$、反引号、反斜杠：$a" >&2; exit 2;; esac; done   # 参数要穿过两层 shell，这几个字符会断或被执行
ENVS="${SPARK_ENV:-}"; case "$ENVS" in *[!A-Za-z0-9_=\ ]*) echo "SPARK_ENV 只能是 名字=值（字母数字下划线）" >&2; exit 2;; esac
J="~/duck-jobs/$name"
rsh() { /usr/bin/ssh -o ConnectTimeout=10 "$HOST" "$@"; }

case "$cmd" in
start)
  task="${1:?任务}"; iters="${2:?轮数}"; shift 2
  extra=""; for a in "$@"; do extra="$extra '$a'"; done
  rsh "set -e
    [ ! -e $J ] || { echo '$name 用过了（日志和 onnx 会被盖掉），换个名字' >&2; exit 1; }
    apps=\$(nvidia-smi --query-compute-apps=pid,process_name --format=csv,noheader) || { echo 'nvidia-smi 失败，不开' >&2; exit 1; }
    [ -z \"\$apps\" ] || { echo \"GPU 上已有进程在跑，不抢：\$apps\" >&2; exit 1; }
    ! pgrep -f '[r]un train Mjlab' >/dev/null || { echo '有别的训练刚起（还没上 GPU），不抢' >&2; exit 1; }
    mkdir -p $J && rm -f $J/exit && echo '$task' > $J/task
    cd $R
    echo '$ENVS' > $J/env
    $ENVS WANDB_MODE=disabled nohup setsid sh -c \"~/.local/bin/uv run train '$task' --env.scene.num-envs 4096 --agent.max_iterations '$iters' --agent.logger tensorboard $extra; echo \\\$? > $J/exit\" > $J/train.log 2>&1 < /dev/null &
    echo \$! > $J/pid; echo \"已开训 $name：pid \$(cat $J/pid)，日志 $J/train.log\""
  ;;
status)
  rsh "d=\$(grep -o 'Logging experiment in directory: .*' $J/train.log | tail -1 | cut -d' ' -f5)
    echo \"目录 \$d\"; ls $R/\$d 2>/dev/null | grep -o 'model_[0-9]*' | sort -t_ -k2 -n | tail -1
    grep -E 'Learning iteration|Mean reward|Mean episode length|ETA' $J/train.log | tail -4
    [ -f $J/exit ] && echo \"已结束，退出码 \$(cat $J/exit)\" || { kill -0 \$(cat $J/pid) 2>/dev/null && echo 训练中 || echo '进程不在、也没写退出码（被杀了？）'; }"
  ;;
fetch)
  it="${1:-}"; case "$it" in *[!0-9]*) echo "轮数只能是数字" >&2; exit 2;; esac; mkdir -p "$OUT"
  f=$(rsh "set -e; cd $R; d=\$(grep -o 'Logging experiment in directory: .*' $J/train.log | tail -1 | cut -d' ' -f5)
    ck=\$d/model_${it:-*}.pt; ck=\$(ls -v \$ck | tail -1)    # 不指定轮就取最大那个；ls -v 按数字排（整条路径带 _，sort -t_ 会退化成字典序）
    n=\$(basename \$ck .pt | cut -d_ -f2)
    ~/.local/bin/uv run scripts/export.py \$(cat $J/task) --checkpoint-file \$ck --onnx-file $J/${name}_\$n.onnx > $J/export_\$n.log 2>&1 || { tail -5 $J/export_\$n.log >&2; exit 1; }
    echo $J/${name}_\$n.onnx")
  /usr/bin/scp -q "$HOST:$f" "$OUT/" && echo "拉回 $OUT/$(basename "$f")"
  ;;
stop) rsh "p=\$(cat $J/pid 2>/dev/null)
    [ -n \"\$p\" ] && [ ! -f $J/exit ] && grep -qa 'duck-jobs/$name/exit' /proc/\$p/cmdline 2>/dev/null || { echo '$name 没在跑'; exit 0; }   # pid 会被复用，核对是不是自己那个 sh -c 再杀整组
    kill -TERM -\$p && echo 已停 $name" ;;
*) echo "用法见文件头" >&2; exit 2 ;;
esac

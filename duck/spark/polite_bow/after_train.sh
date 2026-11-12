#!/bin/sh
# 在 Spark 上跑（Mac 关机也继续）：等 <任务名> 训完 → 导出每个检查点为 onnx → 无头量 → 写 ~/duck-jobs/<任务名>/eval.jsonl。
# 先量官方基线，之后按轮数从小到大。全部做完写 eval.done。默认量鞠躬；量别的动作传测量脚本和 seed/ 下的基线。
#   Mac：spark/polite_bow/after_train.sh launch bow-v2     # 拷到 Spark 并后台挂起
#   Mac：spark/polite_bow/after_train.sh launch roll-v1 spark/roulade/roll_eval.py roulade.onnx
#   Spark：sh ~/duck-jobs/after_train.sh bow-v2            # launch 实际调用的
# 连哪台看 SPARK_HOST，和 train.sh 一样。
set -eu
if [ "${1:-}" = launch ]; then
  name="${2:?任务名}"; case "$name" in *[!A-Za-z0-9_.-]*) exit 2;; esac
  # 下面 ssh 那行用 ; 不用 &&：「cd && nohup … &」会把整串放后台，ssh 要等它跑完才返回
  HOST="${SPARK_HOST:-gpu-host}"; ev="${3:-$(dirname "$0")/bow_eval.py}"; base="${4:-alpha_ground_pick.onnx}"
  case "$base" in *[!A-Za-z0-9_.-]*) exit 2;; esac
  /usr/bin/scp -q "$0" "$ev" "$HOST:duck-jobs/"
  /usr/bin/ssh "$HOST" "cd ~/duck-jobs; nohup setsid sh after_train.sh '$name' '$(basename "$ev")' '$base' > '$name/after.log' 2>&1 < /dev/null & echo 已挂起：训完自动导出并测量，日志 ~/duck-jobs/$name/after.log"
  exit
fi
name="$1"; EV="${2:-bow_eval.py}"; BASE="${3:-alpha_ground_pick.onnx}"; J="$HOME/duck-jobs/$name"; R="$HOME/microduck_rl-20261103"; UV="$HOME/.local/bin/uv"
while [ ! -f "$J/exit" ]; do sleep 60; done
echo "训练结束，退出码 $(cat "$J/exit")  $(date)"
cd "$R"; command cp -f "$HOME/duck-jobs/$EV" .
d=$(grep -o 'Logging experiment in directory: .*' "$J/train.log" | tail -1 | cut -d' ' -f5)
list="$HOME/duck-jobs/seed/$BASE"
for ck in $(ls -v "$d"/model_*.pt); do
  n=$(basename "$ck" .pt | cut -d_ -f2); out="$J/${name}_$n.onnx"
  [ "$n" = 0 ] && continue                                   # 第 0 轮就是热启动的官方权重，基线已经有了
  "$UV" run scripts/export.py "$(cat "$J/task")" --checkpoint-file "$ck" --onnx-file "$out" > "$J/export_$n.log" 2>&1 && list="$list $out" || echo "导出 $n 失败"
done
"$UV" run python "$EV" "$HOME/duck-jobs/seed/velstand.onnx" $list 2>&1 | grep '^RESULT' | cut -c8- > "$J/eval.jsonl"
date > "$J/eval.done"; echo "量完 $(wc -l < "$J/eval.jsonl") 份  $(date)"

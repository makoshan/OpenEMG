#!/bin/sh
# 把一份走路策略装进 Mac 仿真，用 m1/dkpd_walk.py 量前进和右转，打印一行 RESULT JSON。
#   spark/sim_eval.sh official                          # 官方 velstand（policies/current）
#   spark/sim_eval.sh policies-trained/<名字>_<轮>.onnx  # 自己训的，换掉 walk 那一格，别的策略照旧
#   spark/sim_eval.sh <onnx|official> ground_pick         # 换 B 键那一格（鞠躬放这里），用 spark/bow_probe.py 量
# 做法：duck-sim 发现 upstream/microduck/policies/ 有 velstand.onnx 就用它（README 说的「自己的策略集」）。
# 这里临时建这个目录（软链官方集 + 换 velstand），退出时删掉；目录已存在说明有人在用，直接退出。
set -eu
# D = 代码（cd -P：从 Mircoduck 软链进来也落到仓库），M = 上游克隆
D="$(cd -P "$(dirname "$0")/.." && pwd)"; M="${MICRODUCK_DIR:-./microduck}"; U="$M/upstream/microduck"; SEED="$HOME/.cache/duck-sim/policies/current"; S="$HOME/.cache/duck-sim"
pol="${1:?official 或 onnx 路径}"; slot="${2:-walk}"; NP=; MADE=; onnx=
case "$slot" in
  walk) file=velstand.onnx; probe="$D/m1/dkpd_walk.py" ;;
  ground_pick) file=alpha_ground_pick.onnx; probe="$D/spark/bow_probe.py" ;;
  *) echo "槽只支持 walk / ground_pick" >&2; exit 2 ;;
esac
[ -e "$U/policies" ] && { echo "$U/policies 已存在，不动别人的策略集" >&2; exit 1; }
lsof -nP -iTCP:7801 -sTCP:LISTEN >/dev/null 2>&1 && { echo "已有仿真在跑（7801 有人在听），不动别人的" >&2; exit 1; }   # duck-sim up/down 按共享 pidfile 停，会停掉别人的仿真
stop() { set +e; [ -n "$NP" ] && kill "$NP" 2>/dev/null; (cd "$U" && scripts/duck-sim down >/dev/null 2>&1); [ -n "$MADE" ] && /bin/rm -rf "${U:?}/policies"; NP=; MADE=; }
trap stop EXIT
trap 'exit 130' INT TERM
trap 'exit 129' HUP                                # 关终端也要清理，否则留下的 policies/ 会让之后的「官方」仿真用上待测策略

if [ "$pol" != official ]; then
  onnx="$(cd "$(dirname "$pol")" && pwd)/$(basename "$pol")"; [ -f "$onnx" ] || { echo "没有 $pol" >&2; exit 1; }
  mkdir "$U/policies"; MADE=1
  for f in "$SEED"/*; do ln -s "$f" "$U/policies/"; done
  ln -sf "$onnx" "$U/policies/$file"
fi
cd "$U"
DUCK_SIM_VIEWER=0 DUCK_SIM_RL="$U/../microduck_rl" scripts/duck-sim >/dev/null
want="${onnx:-$SEED/$file}"; got=$(grep -o "^$slot = \"[^\"]*\"" "$S/robotd-duck-a.toml" | cut -d'"' -f2)
[ "$(readlink -f "$got")" = "$(readlink -f "$want")" ] || { echo "仿真用的是 $got，不是 $want" >&2; exit 1; }
echo "$slot = $(readlink -f "$got")" >&2
target/debug/netpadd --socket "$S/duck-a.sock" --config "$D/m1/netpad.toml" >"$S/netpadd.log" 2>&1 & NP=$!
sleep 2
n0=$(wc -l < "$S/robotd.log")
python3 "$probe" | grep '^RESULT'
# 本机太忙时 robotd 会和仿真本体断连（11-03 负载 83 时一次测量断 5 次），这种结果不能当策略好坏
drops=$(tail -n +$((n0 + 1)) "$S/robotd.log" | grep -c 'no simulated body' || true)
[ "$drops" = 0 ] || echo "仿真本体断连 $drops 次（本机负载 $(uptime | sed 's/.*averages*: //')），这次结果不可信" >&2

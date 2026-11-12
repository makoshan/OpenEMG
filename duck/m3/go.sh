#!/bin/sh
# M3 一键开测：起无头仿真鸭 + netpadd → 跑 trial.py（念口令、算分）→ 退出时把这三样都停掉。
#   m3/go.sh                          # 真手环：先开 OpenEMG App 的六类实时识别
#   m3/go.sh --dry --reps 2 --rest-s 5   # 不用手环：自动起 gesture_sim --api 代按
# 参数原样传给 trial.py。仿真无头（带窗口会丢拍打转，见 M0）。
# 唤起 = B 键 = ground_pick 槽：这里临时把鞠躬策略放进那一格（DUCK_BOW= 置空则用官方捡东西）。
set -eu
# D = 代码（原力手环/duck，cd -P 穿过 Mircoduck 里的软链），M = 上游克隆和证据
D="$(cd -P "$(dirname "$0")/.." && pwd)"; M="${MICRODUCK_DIR:-./microduck}"; U="$M/upstream/microduck"; H="$D/../host"; PY="$H/.venv-emg/bin/python"
SEED="$HOME/.cache/duck-sim/policies/current"; BOW="${DUCK_BOW-$M/policies-trained/bow-v2_999.onnx}"
NP=; GS=; MADE=
[ -z "$BOW" ] || [ -f "$SEED/velstand.onnx" ] || { echo "没有官方策略集 $SEED（先跑一次 duck-sim 拉取）" >&2; exit 1; }
[ -z "$BOW" ] || [ -f "$BOW" ] || { echo "没有鞠躬策略 $BOW（spark/train.sh fetch bow-v2，或 DUCK_BOW= 用官方捡东西）" >&2; exit 1; }
[ -z "$BOW" ] || [ ! -e "$U/policies" ] || { echo "$U/policies 已存在，不动别人的策略集" >&2; exit 1; }
lsof -nP -iTCP:7801 -sTCP:LISTEN >/dev/null 2>&1 && { echo "已有仿真在跑（7801 有人在听），不动别人的" >&2; exit 1; }   # duck-sim up/down 按共享 pidfile 停，会停掉别人的仿真
stop() { set +e; [ -n "$GS" ] && kill "$GS" 2>/dev/null; [ -n "$NP" ] && kill "$NP" 2>/dev/null; (cd "$U" && scripts/duck-sim down >/dev/null 2>&1); [ -n "$MADE" ] && /bin/rm -rf "${U:?}/policies"; GS=; NP=; MADE=; }   # 进程先崩了 kill 会失败，不能让 set -e 打断清理
trap stop EXIT
trap 'exit 129' HUP
trap 'exit 130' INT TERM                           # Ctrl-C：trial.py 先写半截结果（completed=false），再由 EXIT 清理

if [ -n "$BOW" ]; then                            # 同 spark/sim_eval.sh：软链官方集，只换 ground_pick 那一格
  mkdir "$U/policies"; MADE=1; for f in "$SEED"/*; do ln -s "$f" "$U/policies/"; done
  ln -sf "$(cd "$(dirname "$BOW")" && pwd)/$(basename "$BOW")" "$U/policies/alpha_ground_pick.onnx"
fi
cd "$U"
DUCK_SIM_VIEWER=0 DUCK_SIM_RL="$U/../microduck_rl" scripts/duck-sim >/dev/null   # 起来后会自己 robot.enable 站好
gp=$(grep -o '^ground_pick = "[^"]*"' "$HOME/.cache/duck-sim/robotd-duck-a.toml" | cut -d'"' -f2); echo "B 键（唤起）= $(readlink -f "$gp")" >&2   # 实际用的哪份
target/debug/netpadd --socket "$HOME/.cache/duck-sim/duck-a.sock" --config "$D/m1/netpad.toml" >"$HOME/.cache/duck-sim/netpadd.log" 2>&1 & NP=$!
case " $* " in *" --dry "*)
  "$PY" -B "$H/gesture_sim.py" --api >"$HOME/.cache/duck-sim/gesture_sim.log" 2>&1 & GS=$!
  sleep 1 ;;                                       # 等它把地址写进 service.url
esac
sleep 2                                            # 等鸭子站稳、netpadd 连上 robotd
"$PY" -B -u "$D/m3/trial.py" "$@"

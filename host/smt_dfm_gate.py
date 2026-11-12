#!/usr/bin/env python3
"""贴片可制造性门：给 check_fab.py 调用，也可以单独跑。

两项都要过：
  1. courtyard 每边比焊盘外沿大 ≥ margin（防导入封装框太小，DRC 假通过）
  2. CPL 同面 0201–0805 阻容本体间隙 ≥ min_gap（防工厂判「相互干涉」）
来由：PCB-BATCH 2026-11-08 被嘉立创判 48 颗 0201 干涉，C08A/V4 封装 courtyard 比焊盘还小。
阈值 0.10 mm 置信低（这单 ≥0.07 都能复现）；margin 0.05 是自定的最低线。
用法：python3 smt_dfm_gate.py board.kicad_pcb CPL.csv BOM.csv   退出码：通过 0，不过 1
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cpl_spacing_check as SP  # noqa: E402
import kicad_courtyard_check as CY  # noqa: E402


def errors(pcb, cpl, bom, min_gap=0.10, margin=0.05):
    """返回 (问题列表, 摘要字典)。问题列表为空才算过。"""
    bad = []
    n, cy_bad, nocy = CY.check(pcb, margin)
    if n == 0:
        bad.append("courtyard：一个带 SMD 焊盘的封装都没解析到，检查无效")
    if cy_bad:
        w = cy_bad[0]
        bad.append(f"courtyard 没包住焊盘 {len(cy_bad)} 个（最差 {w[1]} 框 {w[2]}×{w[3]}，焊盘 {w[4]}×{w[5]}）")
    if nocy:
        bad.append(f"没有 courtyard {len(nocy)} 个：{'、'.join(nocy[:8])}")
    pairs, names, checked, skipped = SP.check(cpl, bom, min_gap)
    if checked == 0:
        bad.append("间距：一颗阻容都没认出来，检查无效")
    if pairs:
        g = pairs[0]
        bad.append(f"本体间隙 < {min_gap} mm {len(pairs)} 对、{len(names)} 颗（最差 {g[1]}/{g[2]} {g[0]:+.3f} mm）")
    info = {"courtyard_bad": len(cy_bad), "no_courtyard": len(nocy), "spacing_pairs": len(pairs),
            "spacing_parts": len(names), "checked": checked, "skipped": skipped}
    return bad, info


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    bad, info = errors(*sys.argv[1:4])
    print("贴片门", "通过" if not bad else "不通过", info)
    for b in bad:
        print("  " + b)
    sys.exit(1 if bad else 0)

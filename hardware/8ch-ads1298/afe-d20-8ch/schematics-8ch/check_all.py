"""C08B 四页汇总核对：每件只画一次、期望网表里的脚全到齐；跨页同名网每段都有名字（否则跨页断开）；与期望网表逐脚一致。
期望网表 = C08A 真源叠 C08B PCB 覆盖层（sch.py），即逐脚对 C08B 采集板 PCB。J_AFE 由第 4 页补进期望表。"""
import json, sys
from collections import defaultdict
from pathlib import Path

P = Path(__file__).resolve().parent
import sch
EXPECT = {f'{r}.{p}': n for (r, p), n in sch.EXPECT.items()}
EXPECT.update({f'J_AFE.{p["pin"]}': p['net'] for p in sch.PCB['pins'] if p['ref'] == 'J_AFE' and p['net'] and not p['net'].startswith('unconnected')})
ON_PCB = {p['ref'] for p in sch.PCB['pins']}
EXPECT = {k: v for k, v in EXPECT.items() if k.split('.')[0] in ON_PCB}   # 只核 C08B 板上有的件
err, seen, net_groups, rows = [], defaultdict(list), defaultdict(list), []
for page in range(1, 5):
    chk = json.loads((P / f'page{page}-check.json').read_text())
    rows.append({k: chk[k] for k in ('页', '元件', '脚', '只靠标签占比', '错误')} | {'文字互压': len(chk['文字互压'])})
    err += [f'第{page}页：{e}' for e in chk['错误']] + [f'第{page}页文字互压 {o}' for o in chk['文字互压']]
    for g in json.loads((P / f'page{page}-groups.json').read_text()):
        for p in g['脚']: seen[p].append(page)
        nets = {EXPECT[p] for p in g['脚'] if EXPECT.get(p)}
        for n in nets: net_groups[n].append((page, bool(g['名'])))
dup = {p: v for p, v in seen.items() if len(v) > 1}
miss = sorted(set(EXPECT) - set(seen))
if dup: err.append(f'重复画的脚 {list(dup)[:10]}')
if miss: err.append(f'漏画的脚 {miss[:10]}')
# 反方向：图上画了、板上没有的件（D20 复核：板上删一颗电容，原来只有 470pF 名单拦得住）
extra = sorted({p.split('.')[0] for p in seen} - ON_PCB)
if extra: err.append(f'图上画了板上没有的件 {extra[:10]}')
for n, gs in net_groups.items():
    if len(gs) > 1 and not all(named for _, named in gs): err.append(f'跨页断开 {n}：{gs}')
refs = {p.split('.')[0] for p in seen}
out = {'页': rows, '元件合计': len(refs), '脚合计': len(seen), '真源脚': len(EXPECT), '错误': err}
(P / 'check-all.json').write_text(json.dumps(out, ensure_ascii=False, indent=2))
print(json.dumps(out, ensure_ascii=False, indent=1)[:3000])
sys.exit(1 if err else 0)

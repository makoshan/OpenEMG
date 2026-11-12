"""C08B 主控板五页汇总核对：每件只画一次、板上每只脚都画到；跨页同名网每段都有名字（否则跨页断开）；与 BA 板逐脚一致（sch.EXPECT）。"""
import json, sys
from collections import defaultdict
from pathlib import Path

P = Path(__file__).resolve().parent
import sch
EXPECT = {f'{r}.{p}': n for (r, p), n in sch.EXPECT.items()}
err, seen, net_groups, rows = [], defaultdict(list), defaultdict(list), []
for page in range(1, 6):
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
for n, gs in net_groups.items():
    if len(gs) > 1 and not all(named for _, named in gs): err.append(f'跨页断开 {n}：{gs}')
refs = {p.split('.')[0] for p in seen}
out = {'页': rows, '元件合计': len(refs), '脚合计': len(seen), '真源脚': len(EXPECT), '错误': err}
(P / 'check-all.json').write_text(json.dumps(out, ensure_ascii=False, indent=2))
print(json.dumps(out, ensure_ascii=False, indent=1)[:3000])
sys.exit(1 if err else 0)

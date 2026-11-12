"""F04 嘉立创工程核对：在 EDA 里读焊盘网络、走线、飞线、DRC，和 KiCad 源板比。
用法：python3 verify_f04.py <工程.eprj3> <K9板.kicad_pcb> <输出.json>"""
import json, math, re, sys, time
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'c08-eprj3-20261102'))
from jlccli import close, js, open_ready

eprj3, k9, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]), Path(sys.argv[3])
t = k9.read_text(encoding='utf8')
names = dict((int(a), b) for a, b in re.findall(r'^\t\(net (\d+) "([^"]*)"\)', t, re.M))

# 源板：每个封装的焊盘网络、每网走线总长
src_pads, src_len, src_seg = {}, defaultdict(float), Counter()
for blk in re.split(r'(?m)^(?=\t\(footprint )', t)[1:]:
    ref = re.search(r'\(property "Reference" "([^"]*)"', blk).group(1)
    for num, net in re.findall(r'\(pad "([^"]*)" [\s\S]*?\(net (\d+) "', blk):
        src_pads.setdefault((ref, num), set()).add(names[int(net)])
for x1, y1, x2, y2, net in re.findall(r'\(segment\s+\(start ([-\d.]+) ([-\d.]+)\)\s+\(end ([-\d.]+) ([-\d.]+)\)\s+\(width [\d.]+\)\s+\(layer "F.Cu"\)\s+\(net (\d+)\)', t):
    n = names[int(net)]
    src_len[n] += math.dist((float(x1), float(y1)), (float(x2), float(y2)))
    src_seg[n] += 1

sid, info = open_ready(eprj3)
try:
    for _ in range(60):
        pcbs = js(sid, 'return await eda.dmt_Pcb.getAllPcbsInfo();')
        if pcbs:
            break
        time.sleep(1)
    assert len(pcbs) == 1
    js(sid, 'await eda.dmt_EditorControl.openDocument(' + json.dumps(pcbs[0]['uuid']) + ');await new Promise(s=>setTimeout(s,3000));return 1;')
    r = js(sid, '''
const cs = await eda.pcb_PrimitiveComponent.getAll();
const pads = [];
for (const c of cs) {
  const ps = await eda.pcb_PrimitiveComponent.getAllPinsByPrimitiveId(c.getState_PrimitiveId());
  for (const p of ps || []) pads.push([c.getState_Designator(), p.getState_PadNumber(), p.getState_Net()]);
}
const ls = await eda.pcb_PrimitiveLine.getAll();
const lines = ls.map(l => [l.getState_Net(), l.getState_Layer(), l.getState_StartX(), l.getState_StartY(), l.getState_EndX(), l.getState_EndY(), l.getState_LineWidth()]);
const rat = await eda.pcb_Document.getRatlines?.();
return {n: cs.length, pads, lines, rat: rat ? (rat.total ?? rat.length ?? rat) : null};''', 120000)
finally:
    close(sid)

eda_pads = defaultdict(set)
for ref, num, net in r['pads']:
    eda_pads[(ref, str(num))].add(net)
miss = [k for k in src_pads if k not in eda_pads]
diff = [(k, sorted(src_pads[k]), sorted(eda_pads[k])) for k in src_pads if k in eda_pads and src_pads[k] != eda_pads[k]]
extra = [k for k in eda_pads if k not in src_pads]
elen, eseg, width = defaultdict(float), Counter(), Counter()
for net, lay, x1, y1, x2, y2, w in r['lines']:
    elen[net] += math.dist((x1, y1), (x2, y2)) * 0.0254
    eseg[net] += 1
    width[round(w * 0.0254, 3)] += 1
ld = {n: round(elen[n] - src_len[n], 4) for n in set(src_len) | set(elen)}
res = dict(源封装=len(re.findall(r'(?m)^\t\(footprint ', t)), 导入器件=r['n'], 源焊盘键=len(src_pads), 导入焊盘键=len(eda_pads),
           缺焊盘=[list(k) for k in miss], 多焊盘=[list(k) for k in extra], 网不符=[[list(k), a, b] for k, a, b in diff],
           源走线=sum(src_seg.values()), 导入走线=sum(eseg.values()), 线宽=dict(width), 网长差mm=ld, 飞线=r['rat'])
out.write_text(json.dumps(res, ensure_ascii=False, indent=1))
print(json.dumps({k: (v if k != '网长差mm' else {'最大绝对差': max(abs(x) for x in v.values()), '网数': len(v)}) for k, v in res.items()}, ensure_ascii=False)[:1500])

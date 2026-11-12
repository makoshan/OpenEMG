"""从 C08B 主控板 thru3 PCB 导出逐脚网名与料值（KiCad python），作原理图期望网表的唯一真源（sch.py 读）。
悬空脚（unconnected-…）写成空网。用法：KiCad python pcb_pins.py [板]"""
import sys, json, hashlib
from pathlib import Path
import pcbnew as k
P = Path(__file__).resolve().parent
src = Path(sys.argv[1])
b = k.LoadBoard(str(src))
net = lambda p: '' if p.GetNetname().startswith('unconnected') else p.GetNetname()
pins = sorted(({'ref': f.GetReference(), 'pin': p.GetNumber(), 'net': net(p)} for f in b.GetFootprints() for p in f.Pads() if p.GetNumber()),
              key=lambda d: (d['ref'], d['pin']))
comps = {f.GetReference(): {'value': f.GetValue(), 'dnp': bool(f.IsDNP())} for f in b.GetFootprints()}
out = {'source': src.name, 'sha256': hashlib.sha256(src.read_bytes()).hexdigest(), 'pins': pins, 'comps': comps}
(P / 'ba-pcb-pins.json').write_text(json.dumps(out, ensure_ascii=False, indent=0))
print('导出', len(pins), '脚', len(comps), '件，来源', out['source'], out['sha256'][:12])

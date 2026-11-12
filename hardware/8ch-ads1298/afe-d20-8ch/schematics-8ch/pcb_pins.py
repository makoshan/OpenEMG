"""从 C08B 单面 8 通道采集板 PCB 导出逐脚网名（KiCad python），作原理图期望网表的 C08B 覆盖层（sch.py 读）。
用法：python3 pcb_pins.py [板]，默认 ../afe-d20-8ch.kicad_pcb"""
import sys, json, hashlib
from pathlib import Path
import pcbnew as k
P = Path(__file__).resolve().parent
src = Path(sys.argv[1]) if len(sys.argv) > 1 else P.parent / 'afe-d20-8ch.kicad_pcb'
b = k.LoadBoard(str(src))
pins = sorted(({'ref': f.GetReference(), 'pin': p.GetNumber(), 'net': p.GetNetname()} for f in b.GetFootprints() for p in f.Pads() if p.GetNumber()),
              key=lambda d: (d['ref'], d['pin']))
out = {'source': str(src.relative_to(P.parent.parent)), 'sha256': hashlib.sha256(src.read_bytes()).hexdigest(), 'pins': pins}
(P / 'c08b-pcb-pins.json').write_text(json.dumps(out, ensure_ascii=False, indent=0))
print('导出', len(pins), '脚，来源', out['source'], out['sha256'][:12])

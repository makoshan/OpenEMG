"""P44e 出制造包（不下单）：Gerber（含 B.Paste 钢网层）、Excellon 钻孔、BOM、贴片坐标，打 zip。
自焊用：BOM 里 XIAO 标“手焊”；钢网只开背面（J1、阻容在背面），正面 XIAO 焊盘不开。用系统 python3 跑，调用 kicad-cli。"""
import csv, json, shutil, subprocess, zipfile, hashlib
from pathlib import Path
P = Path(__file__).parent
PCB = P / 'p44e.kicad_pcb'
OUT = P / 'fab-20261106'
if OUT.exists(): shutil.rmtree(OUT)
G = OUT / 'gerber'; G.mkdir(parents=True)
run = lambda *a: subprocess.run(['kicad-cli', *a], check=True, capture_output=True)
run('pcb', 'export', 'gerbers', '--layers', 'F.Cu,B.Cu,B.Paste,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts',
    '--no-protel-ext', '--subtract-soldermask', '-o', str(G), str(PCB))
run('pcb', 'export', 'drill', '--format', 'excellon', '--excellon-separate-th',
    '-o', str(G) + '/', str(PCB))
# 嘉立创上传只放 Gerber/钻孔
z = OUT / 'P44e-gerber.zip'
with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as f:
    for p in sorted(G.iterdir()): f.write(p, p.name)
# BOM：嘉立创格式列 + 自焊备注
BOM = [('10kΩ 0402 1%', 'R1,R2,R3,R4,R5', 'R_0402_1005Metric', 'C25744', '加热台回流'),
       ('10uF 10V 0603 X5R', 'C1', 'C_0603_1608Metric', 'C19702', '加热台回流'),
       ('FH34SRJ-20S-0.5SH(50)', 'J1', 'Hirose_FH34SRJ-20S-0.5SH', 'C2802370', '加热台回流；翻盖别烫'),
       ('Seeed XIAO nRF52840 Sense', 'U1', 'XIAO-nRF52840-SMD', 'C17401557', '最后烙铁手焊邮票孔；普通版 C17209540 也可')]
with open(OUT / 'BOM.csv', 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.writer(fh, lineterminator='\n'); w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #', '焊法'])
    w.writerows(BOM)
# 坐标：kicad-cli 导出后改成嘉立创列名（自焊用不上，备着）
raw = OUT / 'pos-raw.csv'
run('pcb', 'export', 'pos', '--format', 'csv', '--units', 'mm', '--side', 'both', '-o', str(raw), str(PCB))
rows = list(csv.DictReader(open(raw, encoding='utf-8')))
with open(OUT / 'CPL.csv', 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.writer(fh, lineterminator='\n'); w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
    for r in rows:
        w.writerow([r['Ref'], r['PosX'] + 'mm', r['PosY'] + 'mm', 'Top' if r['Side'] == 'top' else 'Bottom', r['Rot']])
raw.unlink()
files = sorted(p.name for p in G.iterdir())
assert any(n.endswith('B_Paste.gbr') for n in files) and any(n.endswith('.drl') for n in files), files
refs_bom = {d for _, ds, *_ in BOM for d in ds.split(',')}
refs_pcb = {r['Ref'] for r in rows}
assert refs_bom == refs_pcb, (refs_bom ^ refs_pcb)
man = {'pcb_sha256': hashlib.sha256(PCB.read_bytes()).hexdigest(), 'gerber_zip_sha256': hashlib.sha256(z.read_bytes()).hexdigest(),
       'files': files, 'board_mm': [17.78, 21], 'layers': 2, 'stencil': '只开 B.Paste（背面：J1 与阻容）；正面 XIAO 手焊不开'}
(OUT / 'manifest.json').write_text(json.dumps(man, ensure_ascii=False, indent=1))
print(json.dumps(man, ensure_ascii=False, indent=1))

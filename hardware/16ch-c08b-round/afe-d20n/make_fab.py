"""D20N 四角缺口版制造包：源板 ../d20-notch/afe-d20n.kicad_pcb（= D20 补丝印版删 H901–H904、方缺口板框），BOM/CPL 用 ../d20-dfm/ 的（安装孔不进 BOM）。KiCad 自带 Python：python3 -B make_fab.py
D20 只比 D18 少 32 颗 470 pF、C54/C92 下移 0.005 mm、加丝印点；转角沿用 D18 包（已核），自检见 check_fab.py。"""
import hashlib, json, os, shutil, subprocess, zipfile

HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
CLI = os.environ.get('KICAD_CLI', 'kicad-cli')
REL = 'hardware/16ch-c08b-round/afe-d20n'
BASE = 'afe-d20n'; SRC = f'source/{BASE}.kicad_pcb'; ZP = 'c08b-afe-d20n.zip'
SRC_HASH = 'e37f97340f85ed9715cbae572220c9d819f1a2d29e1882eb2de4b455b3691985'
SOURCES = {f'{REL}/d20-notch/{BASE}.{e}': f'source/{BASE}.{e}' for e in ('kicad_pcb', 'kicad_pro', 'kicad_dru')}
SOURCES |= {f'{REL}/d20-dfm/{n}': n for n in ('jlc_smt_bom.csv', 'jlc_smt_cpl.csv')}

files = {}
for rel, dst in SOURCES.items():
    shutil.copyfile(os.path.join(HERE, '..', rel.split('/', 2)[2]), dst); body = open(dst, 'rb').read()
    files[rel] = dict(blob=hashlib.sha1(b'blob %d\0' % len(body) + body).hexdigest(), sha256=hashlib.sha256(body).hexdigest(), bytes=len(body))
assert files[f'{REL}/d20-notch/{BASE}.kicad_pcb']['sha256'] == SRC_HASH, '源板变了，重核 BOM/CPL 再出包'

shutil.rmtree('gerber', ignore_errors=True); os.makedirs('gerber')
LAYERS = 'F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts'
subprocess.run([CLI, 'pcb', 'export', 'gerbers', '--layers', LAYERS, '--subtract-soldermask', '-o', 'gerber/', SRC], check=True, capture_output=True)
subprocess.run([CLI, 'pcb', 'export', 'drill', '--format', 'excellon', '-u', 'mm', '--excellon-separate-th',
                '--generate-map', '--map-format', 'pdf', '-o', 'gerber/', SRC], check=True, capture_output=True)
with zipfile.ZipFile(ZP, 'w', zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir('gerber')):
        if not f.endswith('.pdf'): z.write(f'gerber/{f}', f)   # 平铺
json.dump(dict(file=f'{REL}/d20-notch/{BASE}.kicad_pcb', holes_removed=['H901', 'H902', 'H903', 'H904'], sha256=SRC_HASH, files=files,
               kicad=subprocess.run([CLI, 'version'], capture_output=True, text=True).stdout.strip(),
               production_released=False, platform_verified=False), open('SOURCE.json', 'w'), ensure_ascii=False, indent=1)
print('出包完成', ZP)

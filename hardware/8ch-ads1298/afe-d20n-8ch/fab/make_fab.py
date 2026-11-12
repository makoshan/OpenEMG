"""afe-d20n-8ch 纯单面 8 通道版制造包：源板 ../d20n-8ch/afe-d20n-8ch.kicad_pcb，BOM/CPL 为单面正面 76 颗贴片件。KiCad 自带 Python：python3 -B make_fab.py"""
import hashlib, json, os, shutil, subprocess, zipfile

HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
CLI = os.environ.get('KICAD_CLI', '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')
REL = 'hardware/8ch-ads1298'
BASE = 'afe-d20n-8ch'; SRC = f'source/{BASE}.kicad_pcb'; ZP = 'c08b-afe-d20n-8ch.zip'
SRC_HASH = '1d5dd19ae77378b8bb4e1ebcf8e4ea27b224799f766247868c5bf966470d44e3'
SOURCES = {f'{REL}/afe-d20n-8ch/{BASE}.{e}': f'source/{BASE}.{e}' for e in ('kicad_pcb', 'kicad_pro', 'kicad_dru')}
SOURCES |= {f'{REL}/afe-d20n-8ch/{n}': n for n in ('jlc_smt_bom.csv', 'jlc_smt_cpl.csv')}

files = {}
for rel, dst in SOURCES.items():
    shutil.copyfile(os.path.join(HERE, '..', os.path.basename(rel)), dst); body = open(dst, 'rb').read()
    files[rel] = dict(blob=hashlib.sha1(b'blob %d\0' % len(body) + body).hexdigest(), sha256=hashlib.sha256(body).hexdigest(), bytes=len(body))
assert files[f'{REL}/afe-d20n-8ch/{BASE}.kicad_pcb']['sha256'] == SRC_HASH, '源板变了，重核 BOM/CPL 再出包'

shutil.rmtree('gerber', ignore_errors=True); os.makedirs('gerber')
LAYERS = 'F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts'
subprocess.run([CLI, 'pcb', 'export', 'gerbers', '--layers', LAYERS, '--subtract-soldermask', '-o', 'gerber/', SRC], check=True, capture_output=True)
subprocess.run([CLI, 'pcb', 'export', 'drill', '--format', 'excellon', '-u', 'mm', '--excellon-separate-th',
                '--generate-map', '--map-format', 'pdf', '-o', 'gerber/', SRC], check=True, capture_output=True)
with zipfile.ZipFile(ZP, 'w', zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir('gerber')):
        if not f.endswith('.pdf'): z.write(f'gerber/{f}', f)   # 平铺
json.dump(dict(file=f'{REL}/afe-d20n-8ch/{BASE}.kicad_pcb', holes_removed=['H901', 'H902', 'H903', 'H904'], single_sided=True, sha256=SRC_HASH, files=files,
               kicad=subprocess.run([CLI, 'version'], capture_output=True, text=True).stdout.strip(),
               production_released=False, platform_verified=False), open('SOURCE.json', 'w'), ensure_ascii=False, indent=1)
print('出包完成', ZP)

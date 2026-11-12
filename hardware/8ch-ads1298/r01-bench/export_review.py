"""仅在原生连通/DRC通过后导出；打包后解压复跑，制造放行仍由独立门决定。"""
from pathlib import Path
import csv, hashlib, json, subprocess, tempfile, zipfile
P=Path(__file__).resolve().parent
CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
KIPY='/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3'
def run(*args):subprocess.run(list(map(str,args)),check=True,capture_output=True)
run(CLI,'sch','erc','--format','json','--severity-all','--exit-code-violations','--output',P/'erc.json',P/'v12-r01.kicad_sch')
run(CLI,'sch','export','netlist','--format','kicadxml','--output',P/'v12-r01.net.xml',P/'v12-r01.kicad_sch')
run(CLI,'sch','export','pdf','--output',P/'schematic-review.pdf',P/'v12-r01.kicad_sch')
run('python3',P/'check_candidate.py')
run(KIPY,P/'check_board.py')
b=P/'v12-r01.kicad_pcb';out=P/'gerber-review';out.mkdir(exist_ok=True)
run(CLI,'pcb','export','gerbers','--layers','F.Cu,In1.Cu,In2.Cu,B.Cu,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,F.Paste,B.Paste,Edge.Cuts','--output',str(out)+'/',b)
run(CLI,'pcb','export','drill','--excellon-separate-th','--output',str(out)+'/',b)
run(CLI,'pcb','export','pos','--format','csv','--units','mm','--side','both','--smd-only','--exclude-dnp','--output',P/'placement-SMD.csv',b)
# 测试点是裸铜，不能当作待贴器件送入坐标表。
with (P/'placement-SMD.csv').open(newline='') as f:
 reader=csv.DictReader(f);fields=reader.fieldnames;rows=[r for r in reader if not r['Ref'].startswith('TP')]
assert len(rows)==195 and len({r['Ref'] for r in rows})==195
with (P/'placement-SMD.csv').open('w',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
for side in ['F','B']:
 run(CLI,'pcb','export','svg','--layers',side+'.Cu,'+side+'.Silkscreen,Edge.Cuts','--mode-single','--fit-page-to-board','--exclude-drawing-sheet','--output',P/(side+'-copper.svg'),b)
 run(CLI,'pcb','export','svg','--layers',side+'.Fab,Edge.Cuts','--mode-single','--fit-page-to-board','--exclude-drawing-sheet','--sketch-pads-on-fab-layers','--output',P/(side+'-assembly.svg'),b)
run(CLI,'pcb','export','svg','--layers','F.Paste,Edge.Cuts','--mode-single','--fit-page-to-board','--exclude-drawing-sheet','--output',P/'F-stencil.svg',b)
files=list(out.iterdir());assert len(files)>=13
for p in files:
 assert p.stat().st_size>50,p
 if p.suffix!='.gbrjob':
  txt=p.read_text();assert 'M02' in txt or 'M30' in txt,p
D=json.loads((P/'design.json').read_text());groups={}
for p in D['parts']:
 if p['ref'].startswith('TP'):continue
 key=(p.get('mpn') or p['value'],p.get('lcsc',''),p['footprint'])
 groups.setdefault(key,[]).append(p['ref'])
with (P/'BOM-grouped-S.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['MPN_or_value','LCSC','Footprint','Quantity','Designators','Mounting'])
 for (mpn,lcsc,fp),refs in groups.items():w.writerow([mpn,lcsc,fp,len(refs),','.join(refs),'THT' if all(r.startswith('J') for r in refs) else 'SMD'])
# Gerber单独包只放实际制板层和钻孔，名称明确为审阅候选。
with zipfile.ZipFile(P/'V12-R01-GERBER-REVIEW-NOT-RELEASED.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in files:z.write(f,f.name)
include=[]
for f in P.rglob('*'):
 if not f.is_file() or any(part in ('__pycache__','.pio','artifacts') for part in f.relative_to(P).parts) or f.name.startswith('.') or f.suffix in ['.zip','.png','.kicad_prl'] or f.name in ['package-check.json','package-manifest.json']:continue
 if f.name.startswith('placement-') and f.suffix=='.svg':continue
 if f.suffix in ('.dsn','.ses') or f.name in ('review-narrow-escapes.json','ground-keepouts.json','v12-r01-placement.kicad_pcb','v12-r01-placement.kicad_pro'):continue
 include.append(f)
manifest={str(f.relative_to(P)):hashlib.sha256(f.read_bytes()).hexdigest() for f in include}
(P/'package-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
package=P/'V12-R01-REVIEW.zip'
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
 for f in include+[P/'package-manifest.json']:z.write(f,f.relative_to(P))
with tempfile.TemporaryDirectory(prefix='v12-package-check-') as temp:
 root=Path(temp)
 with zipfile.ZipFile(package) as z:assert z.testzip() is None;z.extractall(root)
 for name,sha in manifest.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,name
 run('python3',root/'check_candidate.py')
 run(CLI,'pcb','drc','--format','json','--schematic-parity','--severity-all','--exit-code-violations','--output',root/'v12-r01.drc.json',root/'v12-r01.kicad_pcb')
 run(KIPY,root/'check_board.py')
result={'archive':package.name,'files':len(include)+1,'sha256':hashlib.sha256(package.read_bytes()).hexdigest(),'crc_verified':True,'extracted_netlist_check':True,'extracted_native_drc':True,'manufacturing_ready':False,'human_test_ready':False}
(P/'package-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))

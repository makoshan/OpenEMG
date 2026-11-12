"""逐条补连，原生DRC拒绝回归；只改本候选并保留每步恢复点。"""
from pathlib import Path
import json,shutil,subprocess
P=Path(__file__).resolve().parent;E=P/'evidence-summary'
# r01-bench在emg/v12下，仓库根目录是parents[2]。
E.mkdir(parents=True,exist_ok=True)
K='/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3'
CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli';board=P/'v12-r01.kicad_pcb';report=P/'v12-r01.drc.json'
def drc():
 subprocess.run([CLI,'pcb','drc','--format','json','--output',str(report),str(board)],check=True,capture_output=True)
 return json.loads(report.read_text())
def signals(r):
 return sum(not all('[GND]' in i['description'] for i in u['items']) for u in r['unconnected_items'])
steps=json.loads((E/'closure-progress.json').read_text()) if (E/'closure-progress.json').exists() else [];offset=len(steps)
for n in range(40):
 r=drc();assert not [v for v in r['violations'] if v['type'] not in ('via_dangling','track_dangling')],r['violations'];count=len(r['unconnected_items'])
 print('补连前',n,count,flush=True)
 if not signals(r):break
 backup=E/f'closure-{n+offset:02}-before.kicad_pcb';shutil.copy2(board,backup);before=report.read_bytes();success=False
 for i in range(count):
  log=E/f'closure-{n+offset:02}-try-{i:02}.log'
  with log.open('w') as f:
   try:result=subprocess.run([K,str(P/'close_connection.py'),str(i)],stdout=f,stderr=f,timeout=100)
   except subprocess.TimeoutExpired:result=None
  if result and result.returncode==0:
   after=drc()
   if not [v for v in after['violations'] if v['type'] not in ('via_dangling','track_dangling')] and signals(after)<signals(r):
    success=True;steps.append({'step':n+offset,'selected':i,'before':count,'after':len(after['unconnected_items']),'log':log.name});print('通过',steps[-1],flush=True);break
   (E/f'closure-{n+offset:02}-try-{i:02}-rejected.json').write_bytes(report.read_bytes())
  shutil.copy2(backup,board);report.write_bytes(before)
 if not success:raise RuntimeError(f'仍有{count}处连接不能自动补通，已恢复本步原板')
 (E/'closure-progress.json').write_text(json.dumps(steps,ensure_ascii=False,indent=2)+'\n')
else:raise RuntimeError('超过40步，未宣称完成')
print('信号补连结束；地铜未连必须另行归零，尚不代表原生DRC通过',flush=True)

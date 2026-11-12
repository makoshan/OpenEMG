"""只删除新原生DRC认定的无连接残线，每轮重填铜并重验。"""
from pathlib import Path
import json,subprocess,sys
P=Path(__file__).resolve().parent;B=P/'v12-r01.kicad_pcb';R=P/'v12-r01.drc.json';CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli';K='/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3'
if len(sys.argv)==1:
 for n in range(12):
  subprocess.run([CLI,'pcb','drc','--format','json','--output',str(R),str(B)],check=True,capture_output=True)
  r=json.loads(R.read_text());ids=[i['uuid'] for v in r['violations'] if v['type'] in ('track_dangling','via_dangling') for i in v['items']]
  if not ids:break
  print('移除原生确认残线',n,len(ids),flush=True)
  subprocess.run([K,__file__,'--drop',*ids],check=True,capture_output=True);subprocess.run([K,__file__,'--fill'],check=True,capture_output=True)
 else:raise RuntimeError('残线清理未收敛')
 print('违规',len(r['violations']),'未连',len(r['unconnected_items']));sys.exit()
import wx
app=wx.App(False)
import pcbnew as k
b=k.LoadBoard(str(B))
if sys.argv[1]=='--drop':
 for t in list(b.GetTracks()):
  if t.m_Uuid.AsString() in sys.argv[2:]:b.Remove(t)
else:k.ZONE_FILLER(b).Fill(b.Zones())
k.SaveBoard(str(B),b)

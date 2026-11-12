"""移除冗余地孔/引线后重铺铜；只有原生地连通仍为零才接受。"""
from pathlib import Path
import sys,subprocess
if '--fill' not in sys.argv and '--drop' not in sys.argv:
 for flag in ('--drop','--fill'):subprocess.run([sys.executable,__file__,*sys.argv[1:],flag],check=True)
 sys.exit()
import wx
app=wx.App(False)
import pcbnew as k
P=Path(__file__).resolve().parent;b=k.LoadBoard(str(P/'v12-r01.kicad_pcb'));x,y=map(float,sys.argv[1:3]);point=k.VECTOR2I(k.FromMM(x),k.FromMM(y))
if '--drop' in sys.argv:
 hits=[]
 for t in b.GetTracks():
  if t.GetNetname()!='GND':continue
  if type(t).__name__=='PCB_VIA' and (t.GetPosition()-point).EuclideanNorm()<k.FromMM(.001):hits.append(t)
  elif type(t).__name__=='PCB_TRACK' and (t.GetStart()==point or t.GetEnd()==point):hits.append(t)
 assert hits
 for t in hits:b.Remove(t)
else:k.ZONE_FILLER(b).Fill(b.Zones())
k.SaveBoard(str(P/'v12-r01.kicad_pcb'),b)

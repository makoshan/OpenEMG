"""移动妨碍相邻信号脚出口的地孔与其引线；保存后必须用原生DRC复核。"""
from pathlib import Path
import sys
import wx
app=wx.App(False)
import pcbnew as k
P=Path(__file__).resolve().parent
b=k.LoadBoard(str(P/'v12-r01.kicad_pcb'));ox,oy,nx,ny=map(float,sys.argv[1:5]);old=k.VECTOR2I(k.FromMM(ox),k.FromMM(oy));new=k.VECTOR2I(k.FromMM(nx),k.FromMM(ny));moved=0
extra=list(map(float,sys.argv[5:]));bends=[k.VECTOR2I(k.FromMM(x),k.FromMM(y)) for x,y in zip(extra[::2],extra[1::2])]
added=[]
for t in b.GetTracks():
 if t.GetNetname()!='GND':continue
 if type(t).__name__=='PCB_VIA' and (t.GetPosition()-old).EuclideanNorm()<k.FromMM(.001):t.SetPosition(new);moved+=1
 elif type(t).__name__=='PCB_TRACK':
  if (t.GetStart()-old).EuclideanNorm()<k.FromMM(.001):t.SetStart(new)
  if (t.GetEnd()-old).EuclideanNorm()<k.FromMM(.001):
   t.SetEnd(bends[0] if bends else new)
   for a,c in zip(bends,bends[1:]+[new]):
    n=k.PCB_TRACK(b);n.SetStart(a);n.SetEnd(c);n.SetWidth(t.GetWidth());n.SetLayer(t.GetLayer());n.SetNet(t.GetNet());added.append(n)
assert moved==1,moved
for t in added:b.Add(t)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(P/'v12-r01.kicad_pcb'),b)

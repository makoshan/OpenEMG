"""按独立几何复核的两段短线，将U1.41接回现有地孔。"""
from pathlib import Path
import wx
app=wx.App(False)
import pcbnew as k
P=Path(__file__).resolve().parent;b=k.LoadBoard(str(P/'v12-r01.kicad_pcb'));V=lambda x,y:k.VECTOR2I(k.FromMM(x),k.FromMM(y))
points=[(137.6625,129.75),(138.40,129.80),(139.49,130.199998)]
for a,c in zip(points,points[1:]):
 t=k.PCB_TRACK(b);t.SetStart(V(*a));t.SetEnd(V(*c));t.SetWidth(k.FromMM(.2));t.SetLayer(k.F_Cu);t.SetNet(b.FindNet('GND'));t.SetLocked(True);b.Add(t)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(P/'v12-r01.kicad_pcb'),b)

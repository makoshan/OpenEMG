"""锁定独立复核后的地孔，并为最后GPIO下拉预留本地出口。"""
from pathlib import Path
import sys
import wx
app=wx.App(False)
import pcbnew as k
P=Path(__file__).resolve().parent;b=k.LoadBoard(str(P/'v12-r01.kicad_pcb'));V=lambda x,y:k.VECTOR2I(k.FromMM(x),k.FromMM(y))
if '--drop' in sys.argv:
 drop=[t for t in b.GetTracks() if t.GetNetname() in ('ADS_GPIO2','ADS_GPIO3','ADS_GPIO4')]
 for t in drop:b.Remove(t)
else:
 for net,a,c,width,diam,hole in [('ADS_GPIO2',(137.6625,128.25),(138.65,128.25),.15,.45,.2)]:
  t=k.PCB_TRACK(b);t.SetStart(V(*a));t.SetEnd(V(*c));t.SetWidth(k.FromMM(width));t.SetLayer(k.F_Cu);t.SetNet(b.FindNet(net));t.SetLocked(True);b.Add(t)
  v=k.PCB_VIA(b);v.SetPosition(V(*c));v.SetWidth(k.FromMM(diam));v.SetDrill(k.FromMM(hole));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(b.FindNet(net));v.SetLocked(True);b.Add(v)
 k.ZONE_FILLER(b).Fill(b.Zones())
k.SaveBoard(str(P/'v12-r01.kicad_pcb'),b)

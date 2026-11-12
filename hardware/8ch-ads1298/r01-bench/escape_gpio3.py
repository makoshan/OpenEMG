"""仅拆RESET阻塞段，固定独立复核通过的GPIO3短出口。"""
from pathlib import Path
import wx,sys
app=wx.App(False)
import pcbnew as k
P=Path(__file__).resolve().parent;b=k.LoadBoard(str(P/'v12-r01.kicad_pcb'));V=lambda x,y:k.VECTOR2I(k.FromMM(x),k.FromMM(y))
if '--drop' in sys.argv:
 hits=[t for t in b.GetTracks() if type(t).__name__=='PCB_TRACK' and t.GetNetname()=='ADS_RESET' and (t.GetStart()-V(135.216,128.972)).EuclideanNorm()<k.FromMM(.001) and (t.GetEnd()-V(138.608,125.58)).EuclideanNorm()<k.FromMM(.001)];assert len(hits)==1
 b.Remove(hits[0])
else:
 t=k.PCB_TRACK(b);t.SetStart(V(137.6625,127.75));t.SetEnd(V(136.45,127.85));t.SetWidth(k.FromMM(.15));t.SetLayer(k.F_Cu)
 v=k.PCB_VIA(b);v.SetPosition(V(136.45,127.85));v.SetWidth(k.FromMM(.45));v.SetDrill(k.FromMM(.2));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu)
 for o in [t,v]:o.SetNet(b.FindNet('ADS_GPIO3'));o.SetLocked(True);b.Add(o)
 k.ZONE_FILLER(b).Fill(b.Zones())
k.SaveBoard(str(P/'v12-r01.kicad_pcb'),b)

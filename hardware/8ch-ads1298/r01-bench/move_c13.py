"""100nF去耦移到ADC同面并直连对应AVDD脚，保留独立近地孔。"""
from pathlib import Path
import wx
app=wx.App(False)
import pcbnew as k
P=Path(__file__).resolve().parent;b=k.LoadBoard(str(P/'v12-r01.kicad_pcb'));fps={f.GetReference():f for f in b.GetFootprints()};f=fps['C13']
V=lambda x,y:k.VECTOR2I(k.FromMM(x),k.FromMM(y))
if f.IsFlipped():f.Flip(f.GetPosition(),False)
f.SetPosition(V(130.75,121.8));f.SetOrientationDegrees(90);f.Reference().SetLayer(k.F_Fab)
def pad(ref,num):return next(p for p in fps[ref].Pads() if p.GetNumber()==str(num))
for net,a,c in [('AVDD',pad('C13',1).GetPosition(),pad('U1',59).GetPosition()),('GND',pad('C13',2).GetPosition(),V(130.75,120.5))]:
 t=k.PCB_TRACK(b);t.SetStart(a);t.SetEnd(c);t.SetWidth(k.FromMM(.2));t.SetLayer(k.F_Cu);t.SetNet(b.FindNet(net));t.SetLocked(True);b.Add(t)
v=k.PCB_VIA(b);v.SetPosition(V(130.75,120.5));v.SetWidth(k.FromMM(.6));v.SetDrill(k.FromMM(.3));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(b.FindNet('GND'));b.Add(v)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(P/'v12-r01.kicad_pcb'),b)

"""把相邻输出的过孔交错到各自空闲方向，再补其余连线。"""
from pathlib import Path
import subprocess,sys
if '--drop' not in sys.argv and '--apply' not in sys.argv:
 for flag in ('--drop','--apply'):subprocess.run([sys.executable,__file__,flag],check=True)
 sys.exit()
import wx
app=wx.App(False)
import pcbnew as k
P=Path(__file__).resolve().parent;b=k.LoadBoard(str(P/'v12-r01.kicad_pcb'));V=lambda x,y:k.VECTOR2I(k.FromMM(x),k.FromMM(y))
if '--drop' in sys.argv:
 for t in list(b.GetTracks()):
  if t.GetNetname() in ('ADS_DRDY','DOUT_B','ADS_GPIO1','ADS_GPIO2'):b.Remove(t)
 k.SaveBoard(str(P/'v12-r01.kicad_pcb'),b);sys.exit()
fps={f.GetReference():f for f in b.GetFootprints()}
for net,ref,num,path in [('ADS_DRDY','U3','20',[(147.2,137.25),(147.6,137.6)]),('DOUT_B','U3','21',[(148.1,136.75)]),('ADS_GPIO1','U1','42',[(138.65,129.25)])]:
 pad=next(p for p in fps[ref].Pads() if p.GetNumber()==num);points=[pad.GetPosition()]+[V(*x) for x in path]
 for a,c in zip(points,points[1:]):
  t=k.PCB_TRACK(b);t.SetStart(a);t.SetEnd(c);t.SetWidth(k.FromMM(.15));t.SetLayer(k.F_Cu);t.SetNet(b.FindNet(net));t.SetLocked(True);b.Add(t)
 v=k.PCB_VIA(b);v.SetPosition(points[-1]);v.SetWidth(k.FromMM(.45));v.SetDrill(k.FromMM(.2));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(b.FindNet(net));v.SetLocked(True);b.Add(v)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(P/'v12-r01.kicad_pcb'),b)

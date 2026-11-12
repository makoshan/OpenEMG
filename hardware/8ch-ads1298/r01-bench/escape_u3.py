"""为U3相邻数字脚预留交错过孔，避免先连的信号把后一个出口封死。"""
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
  if t.GetNetname() in ('XIAO_MISO','XIAO_DRDY','ADS_DRDY','DOUT_B'):b.Remove(t)
 k.SaveBoard(str(P/'v12-r01.kicad_pcb'),b);sys.exit()
fp=next(f for f in b.GetFootprints() if f.GetReference()=='U3')
for net,num,path in [('XIAO_MISO','3',[(142.9,136.25),(142.35,135.95)]),('XIAO_DRDY','4',[(142.4,136.75),(142.4,137.6)]),('ADS_DRDY','20',[(147.2,137.25),(147.6,136.65)])]:
 pad=next(p for p in fp.Pads() if p.GetNumber()==num);points=[pad.GetPosition()]+[V(*x) for x in path]
 for a,c in zip(points,points[1:]):
  t=k.PCB_TRACK(b);t.SetStart(a);t.SetEnd(c);t.SetWidth(k.FromMM(.2));t.SetLayer(k.F_Cu);t.SetNet(b.FindNet(net));t.SetLocked(True);b.Add(t)
 v=k.PCB_VIA(b);v.SetPosition(points[-1]);v.SetWidth(k.FromMM(.5));v.SetDrill(k.FromMM(.2));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(b.FindNet(net));v.SetLocked(True);b.Add(v)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(P/'v12-r01.kicad_pcb'),b)

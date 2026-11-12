"""在真实铜和钻孔约束内重新安放一个地孔，给相邻细脚留出内侧出口。"""
from pathlib import Path
import math,sys
import wx
app=wx.App(False)
import pcbnew as k
P=Path(__file__).resolve().parent;b=k.LoadBoard(str(P/'v12-r01.kicad_pcb'))
V=lambda x,y:k.VECTOR2I(k.FromMM(x),k.FromMM(y))
ox,oy,tx,ty=map(float,sys.argv[1:]);old=V(ox,oy)
tracks=list(b.GetTracks());v=next(t for t in tracks if type(t).__name__=='PCB_VIA' and t.GetNetname()=='GND' and (t.GetPosition()-old).EuclideanNorm()<k.FromMM(.001))
stubs=[t for t in tracks if type(t).__name__=='PCB_TRACK' and t.GetNetname()=='GND' and (t.GetStart()==old or t.GetEnd()==old)]
obstacles=[p for f in b.GetFootprints() for p in f.Pads()]+[t for t in tracks if t.m_Uuid!=v.m_Uuid and all(t.m_Uuid!=s.m_Uuid for s in stubs)]
probe=k.PCB_VIA(b);probe.SetWidth(k.FromMM(.6));probe.SetDrill(k.FromMM(.3));probe.SetViaType(k.VIATYPE_THROUGH);probe.SetLayerPair(k.F_Cu,k.B_Cu)
line=k.PCB_TRACK(b);line.SetWidth(k.FromMM(.2))
candidates=[(tx+dx/10,ty+dy/10) for dx in range(-5,6) for dy in range(0,21)];candidates.sort(key=lambda p:math.dist(p,(tx,ty)))
for pos in candidates:
 point=V(*pos);probe.SetPosition(point);blocked=False
 for o in obstacles:
  if type(o).__name__=='PCB_VIA' and (o.GetPosition()-point).EuclideanNorm()<k.FromMM(.551):blocked=True;break
  if o.GetNetname()!='GND' and any(o.IsOnLayer(l) and o.GetEffectiveShape(l).Collide(probe.GetEffectiveShape(l),k.FromMM(.201)) for l in (k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu)):blocked=True;break
 if blocked:continue
 for s in stubs:
  line.SetLayer(s.GetLayer());line.SetStart(s.GetStart() if s.GetEnd()==old else s.GetEnd());line.SetEnd(point)
  if any(o.GetNetname()!='GND' and o.IsOnLayer(s.GetLayer()) and o.GetEffectiveShape(s.GetLayer()).Collide(line.GetEffectiveShape(s.GetLayer()),k.FromMM(.201)) for o in obstacles):blocked=True;break
 if blocked:continue
 v.SetPosition(point)
 for s in stubs:
  if s.GetStart()==old:s.SetStart(point)
  if s.GetEnd()==old:s.SetEnd(point)
 print('地孔重排',ox,oy,'->',pos);break
else:raise RuntimeError('没有无碰撞地孔位置')
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(P/'v12-r01.kicad_pcb'),b)

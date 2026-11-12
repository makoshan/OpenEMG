"""把剩余数字下拉放到其真实出口旁；以实际铜间距筛选并保留原生DRC终审。"""
from pathlib import Path
import sys,math
import wx
app=wx.App(False)
import pcbnew as k
P=Path(__file__).resolve().parent;b=k.LoadBoard(str(P/'v12-r01.kicad_pcb'));V=lambda x,y:k.VECTOR2I(k.FromMM(x),k.FromMM(y));refs=sys.argv[1:]
fps={f.GetReference():f for f in b.GetFootprints()}
for ref in refs:
 f=fps[ref];pad=next(p for p in f.Pads() if p.GetNumber()=='1');net=pad.GetNetname();old=f.GetPosition();angle=f.GetOrientationDegrees()
 anchors=[t.GetPosition() for t in b.GetTracks() if type(t).__name__=='PCB_VIA' and t.GetNetname()==net]
 if ref=='R12':anchors=[p.GetPosition() for p in fps['R8'].Pads() if p.GetNumber()=='2']
 if not anchors:raise RuntimeError('没有已保留出口:'+ref)
 obs=[p for other in b.GetFootprints() if other.m_Uuid!=f.m_Uuid for p in other.Pads()]+list(b.GetTracks());obs=[o for o in obs if any((o.GetPosition()-a).EuclideanNorm()<k.FromMM(20) for a in anchors)]
 t=k.PCB_TRACK(b);t.SetWidth(k.FromMM(.15));t.SetLayer(k.B_Cu)
 candidates=[]
 for a in anchors:
  for dx in range(-30,31):
   for dy in range(-30,31):
    if .9<math.hypot(dx,dy)/5<6:candidates.append((math.hypot(dx,dy),a,dx/5,dy/5))
 candidates.sort(key=lambda q:q[0]);done=False
 for _,a,dx,dy in candidates:
  if done:break
  f.SetPosition(a+V(dx,dy))
  for rot in (0,90,180,270):
   f.SetOrientationDegrees(rot);pads=list(f.Pads());pad=next(p for p in pads if p.GetNumber()=='1');t.SetStart(a);t.SetEnd(pad.GetPosition())
   if any(p.GetNetname()!=net and p.GetEffectiveShape(k.B_Cu).Collide(t.GetEffectiveShape(k.B_Cu),k.FromMM(.201)) for p in pads):continue
   if any(o.GetNetname()!=net and o.IsOnLayer(k.B_Cu) and o.GetEffectiveShape(k.B_Cu).Collide(t.GetEffectiveShape(k.B_Cu),k.FromMM(.201)) for o in obs):continue
   if any(o.IsOnLayer(k.B_Cu) and o.GetNetname()!=p.GetNetname() and o.GetEffectiveShape(k.B_Cu).Collide(p.GetEffectiveShape(k.B_Cu),k.FromMM(.201)) for p in pads for o in obs):continue
   # 下拉的主体和焊盘必须与其它封装留出装配空间。
   bb=f.GetBoundingBox(False,False)
   if any(other.m_Uuid!=f.m_Uuid and other.GetLayer()==k.B_Cu and bb.Intersects(other.GetBoundingBox(False,False)) for other in b.GetFootprints()):continue
   line=k.PCB_TRACK(b);line.SetStart(a);line.SetEnd(pad.GetPosition());line.SetWidth(k.FromMM(.15));line.SetLayer(k.B_Cu);line.SetNet(b.FindNet(net));line.SetLocked(True);b.Add(line)
   print(ref,'->',k.ToMM(f.GetPosition().x),k.ToMM(f.GetPosition().y),rot,'出口',k.ToMM(a.x),k.ToMM(a.y),flush=True);done=True;break
 if not done:f.SetPosition(old);f.SetOrientationDegrees(angle);raise RuntimeError('找不到局部下拉位置:'+ref)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(P/'v12-r01.kicad_pcb'),b)

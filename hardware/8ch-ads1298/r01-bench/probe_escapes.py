"""只读搜索实际铜允许的局部出口，供引出重排使用。"""
from pathlib import Path
import math
import wx
app=wx.App(False)
import pcbnew as k
P=Path(__file__).resolve().parent;b=k.LoadBoard(str(P/'v12-r01.kicad_pcb'));V=lambda x,y:k.VECTOR2I(k.FromMM(x),k.FromMM(y));layers=(k.F_Cu,k.In2_Cu,k.B_Cu)
obs=[p for f in b.GetFootprints() for p in f.Pads()]+list(b.GetTracks());u=next(f for f in b.GetFootprints() if f.GetReference()=='U1')
v=k.PCB_VIA(b);v.SetWidth(k.FromMM(.45));v.SetDrill(k.FromMM(.2));v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetViaType(k.VIATYPE_THROUGH);t=k.PCB_TRACK(b);t.SetLayer(k.F_Cu);t.SetWidth(k.FromMM(.15))
for num in ['40','45']:
 p=next(p for p in u.Pads() if p.GetNumber()==num);start=p.GetPosition();net=p.GetNetname();res=[]
 near=[o for o in obs if (o.GetPosition()-start).EuclideanNorm()<k.FromMM(20)]
 for dx in range(-15,41):
  for dy in range(-25,26):
   point=V(k.ToMM(start.x)+dx/10,k.ToMM(start.y)+dy/10);v.SetPosition(point);t.SetStart(start);t.SetEnd(point)
   if any(o.GetNetname()!=net and ((o.IsOnLayer(k.F_Cu) and o.GetEffectiveShape(k.F_Cu).Collide(t.GetEffectiveShape(k.F_Cu),k.FromMM(.2))) or any(o.IsOnLayer(l) and o.GetEffectiveShape(l).Collide(v.GetEffectiveShape(l),k.FromMM(.2)) for l in layers)) for o in near):continue
   if any(type(o).__name__=='PAD' and o.GetAttribute()==k.PAD_ATTRIB_SMD and any(o.IsOnLayer(l) and o.GetEffectiveShape(l).Collide(k.SHAPE_CIRCLE(point,k.FromMM(.1)),0) for l in layers) for o in near):continue
   res.append((math.hypot(dx,dy),k.ToMM(point.x),k.ToMM(point.y)))
 print(net,sorted(res)[:12],flush=True)

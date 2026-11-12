"""给指定地焊盘搜索短接地孔；按真实铜、钻孔及SMD禁入约束筛选。"""
from pathlib import Path
import math,sys
import wx
app=wx.App(False)
import pcbnew as k
P=Path(__file__).resolve().parent;b=k.LoadBoard(str(P/'v12-r01.kicad_pcb'));V=lambda x,y:k.VECTOR2I(k.FromMM(x),k.FromMM(y));layers=(k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu)
for spec in sys.argv[1:]:
 ref,num=spec.split('.');f=next(f for f in b.GetFootprints() if f.GetReference()==ref);p=next(p for p in f.Pads() if p.GetNumber()==num);assert p.GetNetname()=='GND';a=p.GetPosition();l=f.GetLayer()
 obs=[p for f in b.GetFootprints() for p in f.Pads()]+list(b.GetTracks());v=k.PCB_VIA(b);v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);t=k.PCB_TRACK(b);t.SetLayer(l);t.SetStart(a)
 candidates=sorted([(math.hypot(dx,dy),dx/10,dy/10) for dx in range(-50,51) for dy in range(-50,51) if math.hypot(dx,dy)>=6]);done=False
 for diam,hole,width in [(.6,.3,.2),(.45,.2,.15)]:
  if done:break
  v.SetWidth(k.FromMM(diam));v.SetDrill(k.FromMM(hole));t.SetWidth(k.FromMM(width))
  for _,dx,dy in candidates:
   point=a+V(dx,dy);v.SetPosition(point);t.SetEnd(point)
   if any(o.GetNetname()!='GND' and ((o.IsOnLayer(l) and o.GetEffectiveShape(l).Collide(t.GetEffectiveShape(l),k.FromMM(.201))) or any(o.IsOnLayer(ll) and o.GetEffectiveShape(ll).Collide(v.GetEffectiveShape(ll),k.FromMM(.201)) for ll in layers)) for o in obs):continue
   if any(type(o).__name__=='PCB_VIA' and (o.GetPosition()-point).EuclideanNorm()<k.FromMM((k.ToMM(o.GetDrillValue())+hole)/2+.251) for o in obs):continue
   if any(type(o).__name__=='PAD' and o.GetAttribute()==k.PAD_ATTRIB_SMD and any(o.IsOnLayer(ll) and o.GetEffectiveShape(ll).Collide(k.SHAPE_CIRCLE(point,k.FromMM(hole/2+.05)),0) for ll in layers) for o in obs):continue
   for item in [v,t]:item.SetNet(b.FindNet('GND'));item.SetLocked(True);b.Add(item)
   print(spec,'->',k.ToMM(point.x),k.ToMM(point.y),diam,hole,width,flush=True);done=True;break
 if not done:print(spec,'没有直接补孔位置',flush=True)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(P/'v12-r01.kicad_pcb'),b)

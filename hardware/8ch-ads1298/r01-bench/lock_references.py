"""固定基准/VCAP3与VCAP1探测支路，避免自动布线把局部去耦绕远。"""
from pathlib import Path
import sys,subprocess
if '--drop' not in sys.argv and '--apply' not in sys.argv:
 for stage in ('--drop','--apply'):subprocess.run([sys.executable,__file__,*sys.argv[1:],stage],check=True)
 sys.exit()
import wx
app=wx.App(False)
import pcbnew as k
P=Path(__file__).resolve().parent
path=P/('v12-r01-placement.kicad_pcb' if '--placement' in sys.argv else 'v12-r01.kicad_pcb')
b=k.LoadBoard(str(path));f={x.GetReference():x for x in b.GetFootprints()}
V=lambda x,y:k.VECTOR2I(k.FromMM(x),k.FromMM(y))
def pad(ref,num):return next(p for p in f[ref].Pads() if p.GetNumber()==str(num))
netnames={'VCAP1','VCAP3','VREFP'}
if '--drop' in sys.argv:
 for t in list(b.GetTracks()):
  if t.GetNetname() in netnames:b.Remove(t)
 k.SaveBoard(str(path),b);sys.exit()
tp=f['TP8']
if tp.IsFlipped():tp.Flip(tp.GetPosition(),False)
tp.SetPosition(V(135.7,140));tp.Reference().SetLayer(k.F_Fab)
def line(net,points,layer=k.F_Cu):
 for a,c in zip(points,points[1:]):
  t=k.PCB_TRACK(b);t.SetNet(b.FindNet(net));t.SetLayer(layer);t.SetWidth(k.FromMM(.2));t.SetStart(a if isinstance(a,k.VECTOR2I) else V(*a));t.SetEnd(c if isinstance(c,k.VECTOR2I) else V(*c));t.SetLocked(True);b.Add(t)
def via(net,point):
 v=k.PCB_VIA(b);v.SetPosition(V(*point));v.SetWidth(k.FromMM(.6));v.SetDrill(k.FromMM(.3));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(b.FindNet(net));v.SetLocked(True);b.Add(v)
line('VCAP1',[pad('U1',28).GetPosition(),(133.75,136.7),pad('C3',1).GetPosition(),pad('TP8',1).GetPosition()])
# 依据当前真实铜寻找短过孔位置；固定几何不能撞上已布的地与去耦。
def clear_path(net,points,layer):
 for a,c in zip(points,points[1:]):
  t=k.PCB_TRACK(b);t.SetStart(a if isinstance(a,k.VECTOR2I) else V(*a));t.SetEnd(c if isinstance(c,k.VECTOR2I) else V(*c));t.SetWidth(k.FromMM(.2));t.SetLayer(layer)
  shape=t.GetEffectiveShape(layer)
  for item in obstacles:
   if item.GetNetname()!=net and item.IsOnLayer(layer) and item.GetEffectiveShape(layer).Collide(shape,k.FromMM(.201)):return False
 return True
def clear_via(net,pos):
 t=k.PCB_VIA(b);t.SetPosition(V(*pos));t.SetWidth(k.FromMM(.6));t.SetDrill(k.FromMM(.3));t.SetViaType(k.VIATYPE_THROUGH);t.SetLayerPair(k.F_Cu,k.B_Cu)
 for item in obstacles:
  if item.GetNetname()==net:
   if type(item).__name__=='PAD':
    t.SetWidth(k.FromMM(.5))
    hit=any(item.IsOnLayer(l) and item.GetEffectiveShape(l).Collide(t.GetEffectiveShape(l),0) for l in (k.F_Cu,k.B_Cu))
    t.SetWidth(k.FromMM(.6))
    if hit:return False
   continue
  for layer in (k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu):
   if item.IsOnLayer(layer) and item.GetEffectiveShape(layer).Collide(t.GetEffectiveShape(layer),k.FromMM(.251 if type(item).__name__=='PCB_VIA' else .201)):return False
 return True
obstacles=[p for fp in b.GetFootprints() for p in fp.Pads()]+list(b.GetTracks())
line('VREFP',[pad('U1',24).GetPosition(),(131.75,136.8)]);via('VREFP',(131.75,136.8))
line('VREFP',[(131.75,136.8),pad('C1',1).GetPosition(),pad('C2',1).GetPosition()],k.B_Cu)
candidates=[(x/10,y/10) for x in range(1300,1361) for y in range(1200,1233)]
candidates.sort(key=lambda v:(v[0]-133.4)**2+(v[1]-123.0)**2)
for pos in candidates:
 front=[pad('U1',55).GetPosition(),(132.75,123.2),pos]
 back=[pos,pad('C5',1).GetPosition(),pad('C6',1).GetPosition()]
 if clear_via('VCAP3',pos) and clear_path('VCAP3',front,k.F_Cu) and clear_path('VCAP3',back,k.B_Cu):
  line('VCAP3',front);via('VCAP3',pos);line('VCAP3',back,k.B_Cu);print('VCAP3过孔',pos);break
else:raise RuntimeError('基准区域没有可用短过孔，需调整局部布局')
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(path),b)
print('基准与局部去耦固定',path.name)

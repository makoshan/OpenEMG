"""按原生未连报告补一条连接；真实铜碰撞搜索，不放宽间距；完成后仍须新跑DRC。"""
from pathlib import Path
import collections,heapq,json,math,sys
import wx
app=wx.App(False)
import pcbnew as k
P=Path(__file__).resolve().parent
b=k.LoadBoard(str(P/'v12-r01.kicad_pcb'));layers=(k.F_Cu,k.In2_Cu,k.B_Cu)
V=lambda x,y:k.VECTOR2I(k.FromMM(x),k.FromMM(y));step=.1;origin=.05
objs=[p for f in b.GetFootprints() for p in f.Pads()]+list(b.GetTracks())
byid={o.m_Uuid.AsString():o for o in objs}
r=json.loads((P/'v12-r01.drc.json').read_text());pair=r['unconnected_items'][int(sys.argv[1])]['items']
a,c=[byid[i['uuid']] for i in pair];net=a.GetNetname();assert net==c.GetNetname()
width=.15 if net.startswith(('ADS_','XIAO_')) or net in ('DOUT_B','DIN_B','SCLK_B') else .2
start=(pair[0]['pos']['x'],pair[0]['pos']['y']);goal=(pair[1]['pos']['x'],pair[1]['pos']['y'])
index=collections.defaultdict(list)
for o in objs:
 box=o.GetBoundingBox()
 for x in range(math.floor(k.ToMM(box.GetLeft())-.7),math.ceil(k.ToMM(box.GetRight())+.7)+1):
  for y in range(math.floor(k.ToMM(box.GetTop())-.7),math.ceil(k.ToMM(box.GetBottom())+.7)+1):index[x,y].append(o)
track=k.PCB_TRACK(b);track.SetWidth(k.FromMM(width))
via=k.PCB_VIA(b);via.SetWidth(k.FromMM(.45));via.SetDrill(k.FromMM(.2));via.SetLayerPair(k.F_Cu,k.B_Cu);via.SetViaType(k.VIATYPE_THROUGH)
def nearby(p,q=None):
 q=q or p;seen=set()
 for x in range(math.floor(min(p[0],q[0])),math.floor(max(p[0],q[0]))+1):
  for y in range(math.floor(min(p[1],q[1])),math.floor(max(p[1],q[1]))+1):
   for o in index[x,y]:
    u=o.m_Uuid.AsString()
    if u not in seen:seen.add(u);yield o
def line_clear(p,q,l):
 track.SetStart(V(*p));track.SetEnd(V(*q));track.SetLayer(l);shape=track.GetEffectiveShape(l)
 return not any(o.GetNetname()!=net and o.IsOnLayer(l) and o.GetEffectiveShape(l).Collide(shape,k.FromMM(.201)) for o in nearby(p,q))
vcache={}
def via_clear(p):
 if p in vcache:return vcache[p]
 via.SetPosition(V(*p));ok=True
 for o in nearby(p):
  if type(o).__name__=='PCB_VIA' and (o.GetPosition()-V(*p)).EuclideanNorm()<k.FromMM(.501):ok=False;break
  if type(o).__name__=='PAD' and o.GetAttribute()==k.PAD_ATTRIB_SMD:
   via.SetWidth(k.FromMM(.4))
   bad=any(o.IsOnLayer(l) and o.GetEffectiveShape(l).Collide(via.GetEffectiveShape(l),0) for l in layers)
   via.SetWidth(k.FromMM(.45))
   if bad:ok=False;break
  if o.GetNetname()!=net and any(o.IsOnLayer(l) and o.GetEffectiveShape(l).Collide(via.GetEffectiveShape(l),k.FromMM(.201)) for l in layers):ok=False;break
 vcache[p]=ok;return ok
def seeds(obj,pos):
 x,y=[round((v-origin)/step) for v in pos]
 for dx in range(-2,3):
  for dy in range(-2,3):
   p=((x+dx)*step+origin,(y+dy)*step+origin)
   for li,l in enumerate(layers):
    if obj.IsOnLayer(l) and line_clear(pos,p,l):yield (x+dx,y+dy,li),math.dist(pos,p)/step
# 从实际已连通铜岛的所有出口搜索，不能把已有细脚引线当成不存在。
own=[o for o in objs if o.GetNetname()==net];groups=list(range(len(own)))
def root(i):
 while groups[i]!=i:groups[i]=groups[groups[i]];i=groups[i]
 return i
for i,o in enumerate(own):
 for j in range(i):
  q=own[j]
  if root(i)!=root(j) and any(o.IsOnLayer(l) and q.IsOnLayer(l) and o.GetEffectiveShape(l).Collide(q.GetEffectiveShape(l),0) for l in layers):groups[root(i)]=root(j)
def component(obj):
 ri=root(next(i for i,o in enumerate(own) if o.m_Uuid==obj.m_Uuid));return [o for i,o in enumerate(own) if root(i)==ri]
def exits(items):
 for o in items:
  if type(o).__name__=='PCB_TRACK':
   aa,cc=o.GetStart(),o.GetEnd();count=max(1,math.ceil(k.ToMM(o.GetLength())/2))
   for i in range(count+1):yield o,(k.ToMM(aa.x+(cc.x-aa.x)*i/count),k.ToMM(aa.y+(cc.y-aa.y)*i/count))
  else:yield o,(k.ToMM(o.GetPosition().x),k.ToMM(o.GetPosition().y))
ends={};goals=[]
for obj,pos in exits(component(c)):
 goals.append(((pos[0]-origin)/step,(pos[1]-origin)/step))
 for n,cost in seeds(obj,pos):
  if n not in ends or cost<ends[n][0]:ends[n]=(cost,pos)
assert ends,'目标没有可用引出点'
def h(n):return min(math.hypot(n[0]-x,n[1]-y) for x,y in goals)
dist={};prev={};heap=[];starts={}
for obj,pos in exits(component(a)):
 for n,cost in seeds(obj,pos):
  if cost<dist.get(n,1e20):dist[n]=cost;prev[n]=None;starts[n]=pos;heapq.heappush(heap,(cost+h(n),cost,n))
visited=0;found=None
while heap:
 _,cost,n=heapq.heappop(heap)
 if cost!=dist.get(n):continue
 visited+=1
 if n in ends:found=n;break
 if visited>250000:break
 x,y,li=n;p=(x*step+origin,y*step+origin)
 candidates=[((x+dx,y+dy,li),math.hypot(dx,dy)) for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1))]
 if via_clear(p):candidates.extend(((x,y,j),8) for j in range(3) if j!=li)
 for nn,delta in candidates:
  xx,yy,j=nn;q=(xx*step+origin,yy*step+origin);nc=cost+delta
  if not(100.75<q[0]<164.25 and 100.75<q[1]<159.25) or nc>=dist.get(nn,1e20):continue
  if j==li and not line_clear(p,q,layers[li]):continue
  dist[nn]=nc;prev[nn]=n;heapq.heappush(heap,(nc+h(nn),nc,nn))
assert found,('无法补通',net,visited)
goal=ends[found][1]
path=[]
while found is not None:path.append(found);found=prev[found]
path.reverse();start=starts[path[0]];nodes=[(start[0],start[1],path[0][2])]+[(x*step+origin,y*step+origin,l) for x,y,l in path]+[(goal[0],goal[1],path[-1][2])]
# 同一直线合并，避免逐格小线段污染实际板。
simple=[]
for n in nodes:
 while len(simple)>1 and simple[-2][2]==simple[-1][2]==n[2] and abs((simple[-1][0]-simple[-2][0])*(n[1]-simple[-1][1])-(simple[-1][1]-simple[-2][1])*(n[0]-simple[-1][0]))<1e-8:simple.pop()
 simple.append(n)
# 同层采用可见直线缩短网格折线，每次仍检查真实铜间距。
smooth=[simple[0]];cursor=0
while cursor<len(simple)-1:
 if simple[cursor][2]!=simple[cursor+1][2]:cursor+=1;smooth.append(simple[cursor]);continue
 end=cursor+1
 while end+1<len(simple) and simple[end+1][2]==simple[cursor][2]:end+=1
 while end>cursor+1 and not line_clear(simple[cursor][:2],simple[end][:2],layers[simple[cursor][2]]):end-=1
 smooth.append(simple[end]);cursor=end
simple=smooth
for p,q in zip(simple,simple[1:]):
 if p[2]!=q[2]:
  t=k.PCB_VIA(b);t.SetPosition(V(*p[:2]));t.SetWidth(k.FromMM(.45));t.SetDrill(k.FromMM(.2));t.SetViaType(k.VIATYPE_THROUGH);t.SetLayerPair(k.F_Cu,k.B_Cu)
 elif math.dist(p[:2],q[:2])>1e-8:
  t=k.PCB_TRACK(b);t.SetStart(V(*p[:2]));t.SetEnd(V(*q[:2]));t.SetWidth(k.FromMM(width));t.SetLayer(layers[p[2]])
 else:continue
 t.SetNet(b.FindNet(net));b.Add(t)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(P/'v12-r01.kicad_pcb'),b)
print(json.dumps({'net':net,'visited':visited,'segments':len(simple)-1,'start':start,'goal':goal}))

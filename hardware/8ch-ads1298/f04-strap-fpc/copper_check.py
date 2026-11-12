"""独立按物理铜几何连通，不利用同脚号被器件内部连接的假设。"""
from pathlib import Path
import json,math,collections,copy
P=Path(__file__).resolve().parent
g=json.loads((P/'native-geometry.json').read_text())
def pointseg(p,a,b):
 v=(b[0]-a[0],b[1]-a[1]);l=v[0]**2+v[1]**2
 t=max(0,min(1,((p[0]-a[0])*v[0]+(p[1]-a[1])*v[1])/l)) if l else 0
 return math.dist(p,(a[0]+t*v[0],a[1]+t*v[1]))
def segdist(a,b,c,d):
 cross=lambda p,q,r:(q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
 if cross(a,b,c)*cross(a,b,d)<=0 and cross(c,d,a)*cross(c,d,b)<=0 and max(min(a[0],b[0]),min(c[0],d[0]))<=min(max(a[0],b[0]),max(c[0],d[0])) and max(min(a[1],b[1]),min(c[1],d[1]))<=min(max(a[1],b[1]),max(c[1],d[1])):return 0
 return min(pointseg(a,c,d),pointseg(b,c,d),pointseg(c,a,b),pointseg(d,a,b))
def rect(p):
 x,y=p['xy'];w,h=p['size'];return [(x-w/2,y-h/2),(x+w/2,y-h/2),(x+w/2,y+h/2),(x-w/2,y+h/2)]
def connected(a,b):
 if 'start' in a and 'start' in b:return segdist(a['start'],a['end'],b['start'],b['end']) <= (a['width']+b['width'])/2+1e-6
 if 'start' in a:a,b=b,a
 pa=rect(a)
 if 'start' in b:
  if any(pa[0][0]<=p[0]<=pa[2][0] and pa[0][1]<=p[1]<=pa[2][1] for p in [b['start'],b['end']]):return True
  return min(segdist(c,d,b['start'],b['end']) for c,d in zip(pa,pa[1:]+pa[:1]))<=b['width']/2+1e-6
 pb=rect(b);return all(max(pa[0][j],pb[0][j])<=min(pa[2][j],pb[2][j])+1e-6 for j in [0,1])
def components(items):
 left=set(range(len(items)));n=0
 while left:
  n+=1;todo=[left.pop()]
  while todo:
   i=todo.pop();found={j for j in left if connected(items[i],items[j])};left-=found;todo.extend(found)
 return n
counts={}
for net in sorted({p['net'] for p in g['pads']}):
 items=[p for p in g['pads']+g['tracks'] if p['net']==net];counts[net]=components(items);assert counts[net]==1,(net,counts[net])
# 删掉接入J1左焊区的线，该区必须独立，不可被重复脚号掩盖。
items=[p for p in g['pads']+g['tracks'] if p['net']=='E1P' and not ('start' in p and math.dist(p['start'],[-1.05,6.5])<1e-6)]
assert components(items)>1
(P/'copper-check.json').write_text(json.dumps({'physical_lands':len(g['pads']),'net_connected_components':counts,'duplicate_pin_disconnection_negative':'PASS'},indent=2))
print('物理铜几何17网各1连通体；重复脚号断线反例通过')

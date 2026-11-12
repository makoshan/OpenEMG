"""背开口一体TPU候选；F04冻结，弹片仍为名义包络。"""
from pathlib import Path
import importlib.util, copy, json
from build123d import *
R=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('fixed',R/'sources/row_fixed_model.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
f=m.f;d=json.loads((R.parent/'f04-strap-fpc/design.json').read_text())
# 局部0.2绝缘补强+0.05胶；不是整片底盖。整体较最初叠层下降0.8。
DROP=.8; TOP=m.COVER_TOP-DROP; SEAT=m.SEAT_TOP-DROP; BOARD=.25; PATCH=.2

def shell(rld=False):
 q=f.plate(15.6,28,TOP)-f.plate(10.8,23.8,SEAT-.4+.01,-.01)
 for y in ([-6.5] if rld else [-6.5,6.5]):
  q-=f.cyl(7,5,y,-1)
  q-=f.cyl(9.4,3,y,SEAT)
 # 背侧桥出口贯通到底，整板从背面放入；正面保留连续皮层。
 for x in (-6.5,6.5):q-=f.box(6,8,.61,x=x,z=-.01)
 return f.named(q,'TPU ONE PIECE OPEN BACK',(.23,.35,.34))

def row(rld=False):
 old=m.parts();p=[shell(rld),f.named(f.plate(6,23,PATCH),'LOCAL insulating stiffener0.2 ASSUMED',(.55,.58,.58)),Pos(0,0,-DROP)*old[4]]
 for j in ([7,8,9,10] if rld else [7,8,9,10,11,12,13,14]):p.append(Pos(0,0,-DROP)*copy.deepcopy(old[j]))
 p.append(Pos(0,0,-DROP)*copy.deepcopy(old[3]))
 # 织带粘接分别在外缘和局部补强背面；中央空腔没有整片底盖。
 glue=(f.plate(15.6,28,.15,-.15)-f.plate(10.8,23.8,.17,-.16)).fuse(f.plate(6,23,.15,-.15))
 for x in (-6.5,6.5):glue-=f.box(6,8,.2,x=x,z=-.17)
 p.insert(-1,f.named(glue,'TEXTILE ADHESIVE0.15 ASSUMED',(.3,.6,.6)))
 return p

def liner():
 q=copy.deepcopy(shell())
 for i in range(1,9):
  x=19.6*i
  # 仅用0.4厚正面桥连接各排，背面FPC通道保持开放。
  q=q.fuse(f.box(4.4,28,.4,x=x-9.8,z=TOP-.4),Pos(x,0,0)*shell(i==8))
 q.label='TPU continuous liner OPEN BACK';return q

def assembly(loading=False):
 p=[liner()]
 for i,x in enumerate(d['row_centers_mm']):
  for q in row(i==8)[1:-1]:
   if loading and 'TEXTILE ADHESIVE' in q.label:continue
   dz=-7 if loading and not ('METAL' in q.label or 'ANNULAR' in q.label) else 0
   p.append(Pos(x,0,dz)*copy.deepcopy(q))
 board=Pos(0,0,BOARD-(7 if loading else 0))*extrude(Polygon(*map(tuple,d['outline']),align=None),amount=.106,dir=(0,0,1))
 p.append(f.named(f.box(7,22,.225,x=-23,z=BOARD-.225-(7 if loading else 0)),'TAIL stiffener nominal',(.54,.46,.3)))
 p+=[f.named(board,'F04 whole unchanged XY',(.72,.44,.16)),f.named(f.box(370,29,1.2,x=87,z=-1.35),'TEXTILE1.2 ASSUMED assembly after PCB',(.2,.22,.22))] if not loading else [f.named(board,'F04 whole BACK INSERTION',(.72,.44,.16))]
 return Compound(children=p)

def save(name,q):
 export_step(q,R/(name+'.step'));b=import_step(R/(name+'.step'));assert b.is_valid and len(q.solids())==len(b.solids()) and abs(q.volume-b.volume)<.01

def build():
 for rld in (False,True):
  p=row(rld);assert p[0].is_valid and len(p[0].solids())==1
  for i,a in enumerate(p):
   for b in p[i+1:]:assert m.vol(a.intersect(b))<1e-6
  # 背面连续扫掠：软板/补强的宽岛只到板顶，弹片单独细长包络到圆片背面。
  sweep=f.box(6,23,8+.106,z=BOARD-8)+f.box(19.6,5,8+.106,z=BOARD-8)
  for y in ([-6.5] if rld else [-6.5,6.5]):sweep=sweep.fuse(f.box(2.5,1,8+1.406,y=y,z=BOARD-8))
  assert m.vol(sweep.intersect(p[0]))<1e-6
  bad=p[0].fuse(f.plate(15.6,28,.7,-.7));assert m.vol(sweep.intersect(bad))>.01
  disc=Pos(0,0,-DROP)*f.disc(-6.5)
  for dz in (0,.5,2,5):assert m.vol((Pos(0,0,dz)*disc).intersect(p[0]))<1e-6
  assert m.vol((Pos(0,0,-.1)*disc).intersect(p[0]))>.01
  assert abs(disc.bounding_box().max.Z-TOP-.5)<1e-6
 q=liner();assert q.is_valid and len(q.solids())==1
 for name,obj in [('assembled',assembly()),('loading',assembly(True)),('row',Compound(children=row())),('liner',q),('shell',shell()),('rld-shell',shell(True))]:save(name,obj)
 # 贴肤平面朝平台，背口向上；金属与电路在打印完成后安装。
 for name,obj in [('shell-print',shell()),('liner-print',q)]:
  obj=Rot(180,0,0)*copy.deepcopy(obj);obj=Pos(0,0,-obj.bounding_box().min.Z)*obj;export_stl(obj,R/(name+'.stl'))
 report={'state':'已实现未实物验收','shell_mm':TOP,'metal_top_mm':TOP+.5,'with_glue_without_strap_mm':TOP+.65,'with_assumed_strap_mm':TOP+1.85,'local_patch_mm':PATCH,'continuous_liner_mm':[172.4,28,TOP],'contacts':17,'tests':['两种单排无交叠','背装连续扫掠及封底碰撞反例','触点从正面装入及下穿反例','连续TPU单实体','6STEP有效回读'],'unverified':['BW焊脚与压缩力，现为S7231包络','TPU刚度、胶粘保持、0.2补强效果','打印公差、切片和实打','弯曲/扣具/尾线/佩戴舒适']}
 (R/'check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(report)
if __name__=='__main__':build()

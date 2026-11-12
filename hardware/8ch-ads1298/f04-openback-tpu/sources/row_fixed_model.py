"""原F04单排局部改盖：固定圆片环台承托；粘接/BW兼容未验。"""
from pathlib import Path
import importlib.util,copy,json
from build123d import *
R=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('f04',R.parents[1]/'f04-strap-fpc/assembly.py');f=importlib.util.module_from_spec(s);s.loader.exec_module(f)
# 沿用原基座/软板XYZ；名义焊高来自原模型，绝非BW允许压缩证明。
DISC_BACK=2.456; DISC_TOP=3.656; COVER_TOP=3.156
BOND=.05; SEAT_TOP=DISC_BACK-BOND

def vol(q):return 0 if not q else (q.volume if hasattr(q,"volume") else sum(x.volume for x in q))

def parts():
 old=f.fixed(False)
 carrier=copy.deepcopy(old[0])
 # 固定圆片由新盖台阶承托，去掉旧活动行程柱，保留底板与软板坐标。
 base=f.named(f.plate(12,25,.4,.6),"PETG base old stop posts removed",(.36,.43,.44))
 guide=f.plate(12,25,COVER_TOP-1.1,1.1)-f.plate(10.8,23.8,SEAT_TOP-.4-1.1,1.1)
 for y in (-6.5,6.5):
  # Φ7通窗供弹片接触；圆片外围1mm宽台阶承托，胶仅在环上。
  guide-=f.cyl(7,5,y,0)
  guide-=f.cyl(9.4,3,y,SEAT_TOP)
 guide=f.passage(guide)
 p=[carrier,base,f.named(guide,'PETG fixed-disc seat cover NO front lip',(.22,.29,.28)),*copy.deepcopy(old[3:])]
 for y in (-6.5,6.5):
  glue=f.cyl(8.9,BOND,y,SEAT_TOP)-f.cyl(7.1,BOND+.02,y,SEAT_TOP-.01)
  p += [f.named(glue,'ANNULAR ADHESIVE assumed needs peel test',(.32,.66,.65)),f.disc(y),f.named(f.box(2.5,1,.1,y=y,z=1.156),'SOLDER assumption',(.7,.7,.7)),f.named(f.box(2.5,1,1.2,y=y,z=1.256),'S7231 nominal envelope NOT BW',(.7,.7,.7))]
 return p

def build():
 p=parts();a=Compound(children=p)
 assert a.is_valid and all(x.is_valid for x in p)
 assert len(p[2].solids())==1
 # 参考盖确实高于旧圆片；新盖低0.5，复现用户看到的旧问题。
 assert f.DISC_FRONT+.4>DISC_TOP and abs(DISC_TOP-COVER_TOP-.5)<1e-7
 for y in (-6.5,6.5):
  h=f.disc(y)
  for dz in (0,.5,1,2,4):
   q=(Pos(0,0,dz)*h).intersect(p[2]);assert not q or vol(q)<1e-7
  q=(Pos(0,0,-.1)*h).intersect(p[2]);assert q and vol(q)>.01
 # 基座与盖避开真实6x23软板岛；两侧通道仍留给连接桥。
 for k in (1,2):
  q=p[k].intersect(p[3]);assert not q or vol(q)<1e-7
 for i in range(len(p)):
  for j in range(i+1,len(p)):
   q=p[i].intersect(p[j]);assert not q or vol(q)<1e-6,(i,j,vol(q))
 for n,obj in [('assembly',a),('exploded',Compound(children=[Pos(0,0,(12 if i==2 else 7 if i>=7 else 0))*q for i,q in enumerate(p)])),('guide',Compound(children=[copy.deepcopy(p[2])]))]:
  export_step(obj,R/(n+'.step'));b=import_step(R/(n+'.step'));assert b.is_valid and abs(b.volume-obj.volume)<.002
 report={'status':'单排固定圆片候选，未实物验收','disc_mm':[9,1.2],'pitch_pair_mm':13,'metal_proud_mm':.5,'seat_window_mm':7,'bond_mm':BOND,'kept':'原F04底板/软板岛/胶层/桥通道；旧行程柱移除','tests':['旧盖高于触点反例','新盖低于圆片0.5','单实体盖','上方5装入位置无碰撞','下压穿台阶反例','盖/底座不撞软板岛','STEP回读'],'unverified':['胶粘耐汗/剥离/防脱','固定圆片无弹簧行程','BW焊位和真实压缩','打印公差','贴肤/安全']}
 (R/'check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':build()

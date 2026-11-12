"""F04：复用触头，承力柱移到6毫米软板岛两侧，不让按压载荷穿过焊点。"""
from pathlib import Path
import importlib.util, json, copy
from functools import lru_cache
from build123d import *
ROOT=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('e23',ROOT/'sources/row_primitives.py')
e=importlib.util.module_from_spec(s);s.loader.exec_module(e)
box,plate,cyl,named=e.box,e.plate,e.cyl,e.named
d=json.loads((ROOT/'design.json').read_text())
e.BOARD_T=.106;e.SPRING_H=1.20;e.SPRING_Z=1.256;e.HEAD_Z=2.456
e.GUIDE_Z=1.10;e.GUIDE_BOTTOM_LIP=2.756;e.GUIDE_TOP=3.356;e.BODY=3.706
# 现成 304 无孔圆片 Φ9×1.2。背面仍在旧法兰底面，皮肤侧 Ø8 边厚 0.4 挡住，掉不出去。
DISC_D,DISC_T,POCKET_D,APERTURE_D,LIP_T,BOSS_D=9.0,1.2,9.4,8.0,0.4,11.0
DISC_FRONT=e.HEAD_Z+DISC_T
def prism(points,z,h):return Pos(0,0,z)*extrude(Polygon(*(tuple(p) for p in points),align=None),amount=h,dir=(0,0,1))
def passage(shape):
    for x in [-6.5,6.5]:shape-=box(6,8,.8,x=x,z=.85)
    return shape
@lru_cache(None)
def fixed(rld=False):
    frame=passage(plate(15.6,28,3.006)-plate(12.4,25.4,6,.6))
    support=plate(12,25,.4,.6)
    for y in [-6.5] if rld else [-6.5,6.5]:
        for x in [-3.9,3.9]:support+=e.circle(x,y,1,.5,e.HEAD_Z-e.TRAVEL-1)
    guide=plate(12,25,2.256,1.1)-plate(10.8,23.8,1.656,1.1)
    for y in [-6.5] if rld else [-6.5,6.5]:
        guide-=cyl(POCKET_D,.64,y,2.736)
        cap=cyl(BOSS_D,DISC_FRONT+LIP_T-e.GUIDE_TOP,y,e.GUIDE_TOP)
        cap-=cyl(POCKET_D,DISC_FRONT-(e.GUIDE_TOP-.01),y,e.GUIDE_TOP-.01)
        cap-=cyl(APERTURE_D,LIP_T+.04,y,DISC_FRONT)
        guide+=cap
    guide=passage(guide)
    glue=passage(plate(12,25,.1,1)-plate(10.8,23.8,.12,.99))
    return [named(frame,'TPU carrier28 floor0.6',(.09,.11,.12)),named(support,'PETG support OUTSIDE FPC stops',(.36,.43,.44)),named(guide,'PETG guide discD9 pocket9.4 aperture8'+(' RLD' if rld else ''),(.17,.2,.22)),named(plate(6,23,.106,1.05),'FPC island6x23 no slots',(.62,.39,.12)),named(plate(6,23,.05,1),'ADHESIVE island0.05 assumed',(.24,.56,.66)),named(glue,'ADHESIVE guide0.1 assumed',(.24,.56,.66)),named(plate(15.6,28,.15,-.15),'ADHESIVE textile0.15 assumed',(.24,.56,.66))]
def disc(y,stroke=0):
    return named(cyl(DISC_D,DISC_T,y,e.HEAD_Z-stroke),'METAL D9x1.2 disc 304 STOCK',(.75,.61,.3))
def row(rld=False,stroke=0):
    assert 0<=stroke<=.22
    p=[copy.deepcopy(q) for q in fixed(rld)]
    for y in [-6.5] if rld else [-6.5,6.5]:
        p.extend([named(box(2.5,1,.1,y=y,z=1.156),'SOLDER allowance0.1 assumed',(.7,.72,.74)),named(box(2.5,1,1.2-stroke,y=y,z=1.256),'S7231 envelope NOT actual deformation',(.74,.77,.79)),disc(y,stroke)])
    return p
def flat():
    p=[named(box(370,29,1.2,x=185,z=-1.35),'TEXTILE29x370 thickness ASSUMED',(.055,.063,.071))]
    for i in range(9):
        for q in row(i==8):
            if 'FPC island' not in q.label:p.append(Pos(98+19.6*i,0,0)*q)
    p.append(named(Pos(98,0,0)*prism(d['outline'],1.05,.106),'F04 native outline186.8x23 no slots',(.62,.39,.12)))
    p.append(named(box(7,22,.225,x=75,z=.825),'TAIL PI0.2 adhesive0.025 single',(.6,.52,.3)))
    return Compound(children=p,label='F04 flat assembly NOT RELEASED')
def bent():
    # shortcut: 连续桥的拉伸和弯曲余量未闭合；此图仅展示局部排列，不替代弯曲制造样板。
    p=[]
    for i in range(9):
        for q in row(i==8)+[named(box(15.6,29,1.2,z=-1.35),'TEXTILE segment ASSUMED',(.055,.063,.071))]:p.append(e.pose(i,20)*q)
        if i<8:
            p.append(Pos(98,0,0)*e.bridge(i,20,-14.5,29,-1.35,1.2,'TEXTILE bend concept',(.055,.063,.071)))
            for j,x in [(i,5.4),(i+1,-5.4)]:p.append(named(e.pose(j,20)*box(4.8,5,.106,x=x,z=1.05),'FPC exit local flat',(.62,.39,.12)))
            pts=[(e.pose(j,20)*Vertex(x,0,z)).center() for j,x,z in [(i,7.8,1.05),(i+1,-7.8,1.05),(i+1,-7.8,1.156),(i,7.8,1.156)]]
            face=Pos(0,2.5,0)*(Plane.XZ*Polygon(*[(v.X,v.Z) for v in pts],align=None))
            p.append(named(extrude(face,amount=5,dir=(0,-1,0)),'FPC bridge CHORD concept NOT bend strain',(.62,.39,.12)))
    return Compound(children=p,label='F04 curved placement concept continuous FPC bend NOT VERIFIED')
def exploded():
    p=[]
    for i,q in enumerate(row()):
        lift=[0,3,12,6,5.5,11.5,-1][i] if i<7 else {'SOLDER':7.5,'S7231':9,'METAL':15}[q.label.split()[0]]
        p.append(Pos(0,0,lift)*q)
    return Compound(children=p,label='F04 exploded row')
def gen_step():return flat()
def check():
    for stroke in [0,.055,.11,.165,.22]:
        for rld in [False,True]:e.clear(row(rld,stroke))
    seat=disc(0).bounding_box()
    assert abs(seat.size.X-DISC_D)<1e-6 and abs(seat.size.Z-DISC_T)<1e-6 and abs(seat.min.Z-e.HEAD_Z)<1e-6
    assert e.overlap(disc(-6.5,.32),fixed()[1])>.01
    assert e.overlap(disc(-6.5,-.1),fixed()[2])>.01
    for y in [-6.5,6.5]:
        for z in [-5,-3,-1,-.3,0]:assert e.overlap(Pos(0,0,z)*disc(y),fixed()[2])<1e-6,(y,z)
    assert e.overlap(fixed()[1],fixed()[3])<1e-6
    assert e.overlap(fixed()[1],plate(10,23,.106,1.05))>.01
    outline=prism(d['outline'],1.05,.106)
    assert abs(outline.bounding_box().size.X-186.8)<1e-6 and abs(outline.bounding_box().size.Y-23)<1e-6
    for i in range(8):
        bridge=Compound(children=list(outline.intersect(box(.01,30,.2,x=9.8+19.6*i,z=1))))
        assert abs(bridge.bounding_box().size.Y-5)<1e-6
    bend=bent()
    for q in bend.children:
        if q.label.startswith(('FPC bridge','FPC exit')):
            for part in bend.children:
                if 'TPU carrier' in part.label or 'PETG guide' in part.label:assert e.overlap(q,part)<1e-6,(q.label,part.label)
    whole=flat();e.clear(list(whole.children))
    assert len([q for q in whole.children if 'METAL' in q.label])==17
    for name,shape in [('assembly',whole),('module',Compound(children=row())),('exploded',exploded()),('bent-concept',bent()),('metal-head',e.head(0))]:
        export_step(shape,ROOT/(name+'.step'));again=import_step(ROOT/(name+'.step'))
        assert again.is_valid and len(again.solids())==len(shape.solids())
        assert abs(sum(q.volume for q in again.solids())-sum(q.volume for q in shape.solids()))<.01
    for name,index,rld in [('tpu-carrier',0,False),('petg-support',1,False),('petg-guide',2,False),('rld-support',1,True),('rld-guide',2,True)]:
        q=copy.deepcopy(fixed(rld)[index])
        if index==2:q=Rot(180,0,0)*q
        q=Pos(0,0,-q.bounding_box().min.Z)*q
        assert q.is_valid and len(q.solids())==1
        export_step(q,ROOT/(name+'.step'));export_stl(q,ROOT/(name+'.stl'))
    (ROOT/'mechanical-check.json').write_text(json.dumps({'state':'已实现未实物验收','body_mm':3.706,'disc_face_mm':DISC_FRONT,'guide_boss_mm':DISC_FRONT+LIP_T,'with_glue_mm':3.856,'spring':'S7231-45R','disc':'304 Φ9×1.2 stock','pocket_mm':POCKET_D,'aperture_mm':APERTURE_D,'working_height_mm':[1.2,.98],'travel_mm':.22,'contacts':17,'tests':['5行程双触点/RLD干涉','圆片背面在旧法兰底面','超程碰到承力柱','上提0.1被皮肤侧边挡住','从内侧装入路径不撞盖','侧柱避板及旧宽岛碰撞反例','全平直装配干涉','实际板框186.8×23及8处桥宽5','弯曲出口/弦桥对全部底座和导向盖干涉','STEP实体体积回读'],'unverified':['弹片力和真实变形','打印间隙和0.4边是否成形','胶厚焊高公差','连续桥弯曲和织带拉伸','尾部进主机壳路径','胶材耐汗耐久']},ensure_ascii=False,indent=2))
if __name__=='__main__':check()

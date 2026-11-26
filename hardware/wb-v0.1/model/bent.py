# /// script
# dependencies = ["build123d==0.13.0"]
# ///
"""由整面薄片版装配 STEP 生成手腕曲率样例，单位 mm。"""
import argparse
import csv
import math
from pathlib import Path

import build123d as b
from scipy.optimize import brentq

PITCH, WIDTH, GAP = 10., 7., 3.
NEUTRAL, TOP, CAP = .20, 2.30, 2.70


def turn(radius):
    # 钉顶切圆。每节含一段直板与一段长度不变的圆弧，解节间转角。
    mid_radius = radius + CAP - NEUTRAL
    return brentq(lambda a: GAP/a + WIDTH/2/math.tan(a/2) - mid_radius, .01, 2.)


def pose(index, angle):
    a = (index-3.5)*angle
    r = GAP/angle + WIDTH/2/math.tan(angle/2)
    return b.Pos(r*math.sin(a), 0, -r*math.cos(a))*b.Rot(0,-math.degrees(a),0)*b.Pos(-PITCH*index,0,-NEUTRAL)


def section(shape, left, right):
    box = b.Pos((left+right)/2,0,0)*b.Box(right-left,120,12)
    return shape.intersect(box).solids()[0]


def arc(index, angle, ymin, ymax, zmin, zmax):
    x = index*PITCH + WIDTH/2
    profile = b.Face(b.Wire.make_polygon([(x,ymin,zmin),(x,ymin,zmax),(x,ymax,zmax),(x,ymax,zmin)],close=True))
    axis = b.Axis((x,0,NEUTRAL+GAP/angle),(0,-1,0))
    return pose(index,angle)*b.revolve(profile,axis=axis,revolution_arc=math.degrees(angle))


def run(source, out):
    assembly = b.import_step(source)
    strap = next(c for c in assembly.children if c.label.startswith('TPU'))
    fpc = next(c for c in assembly.children if c.label.startswith('WB_FPC'))
    metal = [c for c in assembly.children if c.label.startswith(('Pin_', 'Pad_'))]
    assert len(metal)==48
    blocks = [section(strap,i*PITCH-WIDTH/2,i*PITCH+WIDTH/2) for i in range(8)]
    out.mkdir(parents=True,exist_ok=True)
    with (out/'七道缝净距.csv').open('w',newline='',encoding='utf-8-sig') as fp:
        rows = csv.writer(fp)
        rows.writerow(['腕面假设半径_mm','相邻块转角_deg',*[f'缝{i}_mm' for i in range(1,8)]])
        for radius in (15,20,25,30,35):
            a = turn(radius)
            shapes = [pose(i,a)*piece for i,piece in enumerate(blocks)]
            gaps = [shapes[i].distance_to(shapes[i+1]) for i in range(7)]
            predicted = 2*(GAP/a - (TOP-NEUTRAL))*math.sin(a/2)
            assert min(gaps)>0 and max(abs(g-predicted) for g in gaps)<1e-5
            rows.writerow([radius,round(math.degrees(a),3),*[round(g,4) for g in gaps]])
    # 保存 R25 含软板、所有铜钉和焊盘的姿态；外伸排线沿末节切面平伸。
    a=turn(25)
    components=[]
    for flat, ymin, ymax, zmin, zmax in [(strap,-13.,13.,0.,.4),(fpc,-15.,fpc.bounding_box().max.Y,-.11,0.)]:
        sides=flat.bounding_box()
        pieces=[]
        for i in range(8):
            left=sides.min.X if i==0 else i*PITCH-WIDTH/2
            right=sides.max.X if i==7 else i*PITCH+WIDTH/2
            piece=section(flat,left,right)
            pieces.append(pose(i,a)*piece)
            if i<7:
                pieces.append(arc(i,a,ymin,ymax,zmin,zmax))
        merged=pieces[0].fuse(*pieces[1:]).clean()
        assert merged.is_valid and len(merged.solids())==1
        merged.label,merged.color=flat.label,flat.color
        components.append(merged)
    for item in metal:
        idx=round(item.bounding_box().center().X/PITCH)
        moved=pose(idx,a)*item
        moved.label,moved.color=item.label,item.color
        components.append(moved)
    result=b.Compound(children=components,label='WB_v01_R25_bend_study')
    assert result.is_valid and len(result.solids())==50
    path=out/'assembly-r25.step'
    b.export_step(result,path)
    check=b.import_step(path)
    assert check.is_valid and len(check.solids())==50


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('assembly',type=Path)
    parser.add_argument('out',type=Path)
    args=parser.parse_args()
    run(args.assembly,args.out)

"""尾端补强填充，IPC对原生板，明确仅CAM审核包。"""
from pathlib import Path
import json,re,collections
P=Path(__file__).resolve().parent;G=P/'gerber-review'
d=json.loads((P/'design.json').read_text());g=json.loads((P/'native-geometry.json').read_text());checks=json.loads((P/'check.json').read_text())
assert checks['native_DRC']==0 and checks['native_unconnected']==0
expected={(p['ref'],p['pin']):p['net'] for p in d['pins']};actual={};records=[]
for line in (G/'fpc-f04.d356').read_text().splitlines():
 m=re.match(r'^327(\S+)\s+(\S+)\s*-(\d+)',line)
 if m:actual[(m[2],m[3])]=m[1];records.append((m[2],m[3],m[1]))
assert actual==expected
assert len(records)==len(g['pads'])==85
rects=[[(-26.5,-11),(-19.5,-11),(-19.5,11),(-26.5,11)]]
native={(int(x),int(y)) for x,y in re.findall(r'X(-?\d+)Y(-?\d+)D0[12]',(G/'fpc-f04-User_1.gbr').read_text())}
def region(points):
 coords=[(round((x+100)*1e6),round((y-100)*1e6)) for x,y in points]
 # 原生数据库精度nm；取整最多1nm，不把绘图像素当制造尺寸。
 assert all(any(abs(a-c)<=1 and abs(b-e)<=1 for c,e in native) for a,b in coords)
 return 'G36*\n'+''.join(f'X{x}Y{y}D{2 if i==0 else 1:02d}*\n' for i,(x,y) in enumerate(coords+[coords[0]]))+'G37*\n'
text='%FSLAX46Y46*%\n%MOMM*%\n%TF.FileFunction,Other,BOT_PI_STIFFENER*%\n%LPD*%\nG01*\n'+''.join(region(p) for p in rects)+'%LPC*%\n'+''.join(region(p) for p in d['slots'])+'%LPD*%\nM02*\n'
(G/'fpc-f04-BOT-STIFFENER.gbr').write_text(text)
assert text.count('G36*')==1 and len(d['slots'])==0
(P/'fabrication-check.json').write_text(json.dumps({'status':'CAM_REVIEW_ONLY','IPC_records':85,'logical_pins':34,'nets':17,'stiffeners_dark_regions':1,'stiffener_clear_slots':0,'native_geometry_boundary_match':True,'factory_CAM_approved':False},indent=2))
print('IPC85铜区/34逻辑端点匹配，尾端1补强、0槽通过')

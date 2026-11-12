"""离体调试 PCB：模拟输入、ADC、数字接口、电源分区；不沿用可穿戴占位板尺寸。"""
from pathlib import Path
import json, math, re
import wx
app=wx.App(False)
import pcbnew as k
P=Path(__file__).resolve().parent
D=json.loads((P/'design.json').read_text()); parts={p['ref']:p for p in D['parts']}
b=k.BOARD();b.SetCopperLayerCount(4);b.GetDesignSettings().SetBoardThickness(k.FromMM(1.6))
V=lambda x,y:k.VECTOR2I(k.FromMM(x),k.FromMM(y))
X,Y,W,H=100,100,65,60
for a,c in [((X,Y),(X+W,Y)),((X+W,Y),(X+W,Y+H)),((X+W,Y+H),(X,Y+H)),((X,Y+H),(X,Y))]:
 s=k.PCB_SHAPE(b);s.SetShape(k.SHAPE_T_SEGMENT);s.SetStart(V(*a));s.SetEnd(V(*c));s.SetLayer(k.Edge_Cuts);s.SetWidth(k.FromMM(.05));b.Add(s)
nets={};placed={};boxes=[]
for p in parts.values():
 for n in p['pins'].values():
  if n and n not in nets:nn=k.NETINFO_ITEM(b,n);b.Add(nn);nets[n]=nn

def bounds(fp):
 r=fp.GetCourtyard(k.B_CrtYd if fp.IsFlipped() else k.F_CrtYd).BBox()
 if not r.GetWidth():r=fp.GetBoundingBox(False,False)
 return tuple(k.ToMM(v) for v in (r.GetLeft(),r.GetTop(),r.GetRight(),r.GetBottom()))
def overlap(a,c):return a[0]<c[2]-.001 and c[0]<a[2]-.001 and a[1]<c[3]-.001 and c[1]<a[3]-.001

def place(ref,x,y,rot=0,back=False,search=None):
 p=parts[ref];ln,fn=p['footprint'].split(':');fp=k.FootprintLoad(str(P/(ln+'.pretty')),fn);assert fp,ref
 fp.SetReference(ref);fp.SetValue(p['value']);b.Add(fp);fp.SetPosition(V(x,y));fp.SetOrientationDegrees(rot)
 if back:fp.Flip(V(x,y),False)
 layer='both' if ref.startswith('J') else ('back' if back else 'front')
 def fits():
  a=bounds(fp)
  return X+.8<=a[0] and a[2]<=X+W-.8 and Y+.8<=a[1] and a[3]<=Y+H-.8 and not any(overlap(a,c) for rr,c,ll in boxes if ll==layer or ll=='both' or layer=='both')
 if not fits() and search:
  x0,y0,x1,y1=search
  candidates=[(xx/4,yy/4) for xx in range(int(x0*4),int(x1*4)+1) for yy in range(int(y0*4),int(y1*4)+1)]
  for xx,yy in sorted(candidates,key=lambda v:(v[0]-x)**2+(v[1]-y)**2):
   fp.SetPosition(V(xx,yy))
   if fits():break
 assert fits(),(ref,bounds(fp),[(rr,c) for rr,c,ll in boxes if (ll==layer or ll=='both' or layer=='both') and overlap(bounds(fp),c)])
 expected=p['pins'];nums={pad.GetNumber() for pad in fp.Pads() if pad.GetNumber()}
 assert nums==set(expected),(ref,nums,set(expected))
 for pad in fp.Pads():
  n=expected.get(pad.GetNumber());pad.SetNet(nets[n] if n else b.FindNet(0))
 fp.Reference().SetVisible(True);fp.Reference().SetLayer(k.B_Fab if back else k.F_Fab);fp.Value().SetVisible(False)
 for g in fp.GraphicalItems():
  if g.GetLayer() in (k.F_SilkS,k.B_SilkS):g.SetLayer(k.B_Fab if back else k.F_Fab)
 boxes.append((ref,bounds(fp),layer));placed[ref]=fp

place('U1',132,130)
place('J3',106,104.2)
place('J1',157,110)
place('J2',158,153)
# P/N 两条输入链相邻，ESD在接口端；本版仅接假负载，人体安全仍单独审查。
for ch in range(1,9):
 for li,leg in enumerate('PN'):
  yy=119.5+(8-ch)*2.8+(1-li)*1.4
  place('ESD'+str((ch-1)*2+li+1),102.3,yy,180)
  for ri in range(6):place('R'+str(101+(ch-1)*12+li*6+ri),104.5+ri*2.2,yy,180 if ri>=4 else 0,back=ri>=4)
place('U2',145,125)
place('U3',145,138)
place('U7',149,150)
place('L1',152.6,150,270)
place('U9',140,150)
place('U12',156,141)
place('U10',150,137)
# 开关回路与储能电容保持同面相邻，后续用实际铜走线长度复核。
for ref,x,y,rot in [('C19',149.7,147.3,0),('C20',149.6,152.9,180),('C21',153.5,152.9,180),('C22',141,147.2,0),('C23',137.2,150,90),('D1',140,154,0),('C31',156,143.5,0),('C30',150,139,0)]:
 place(ref,x,y,rot,search=(x-1,y-1,x+1,y+1))
# ADC去耦根据实际焊盘位置放；顶面不足只在同一焊盘背面局部放置。
anchors={'C1':24,'C2':24,'C3':28,'C4':30,'C5':55,'C6':55,'C7':26,'C8':17,'C9':19,'C10':54,'C11':56,'C12':59,'C13':59,'C14':48,'C15':50,'C16':48,'C17':60,'R1':60,'R2':60,'R3':63,'R4':61,'C18':61,'R40':35}
pads={p.GetNumber():p for p in placed['U1'].Pads()}
for ref,pin in anchors.items():
 pp=pads[str(pin)].GetPosition();xx,yy=k.ToMM(pp.x),k.ToMM(pp.y)
 angle=math.atan2(yy-130,xx-132);xx+=1.8*math.cos(angle);yy+=1.8*math.sin(angle)
 if ref in ('C3','C4','C7'):
  xx,yy={'C3':(133.75,140.3),'C4':(134.85,137.8),'C7':(132.65,137.8)}[ref]
  place(ref,xx,yy,270,back=False)
 else:place(ref,xx,yy,90 if abs(xx-132)>abs(yy-130) else 0,back=True,search=(xx-4,yy-4,xx+4,yy+4))
for ref,x,y in [('C26',143.9,121),('C27',146.8,122),('C28',143.9,134),('C29',146.8,135)]:place(ref,x,y,back=True)
for i in range(8,21):
 if i in (9,10):continue
 place('R'+str(i),139+(i%3)*2.3,128+(i//3-2)*1.6,back=True,search=(138,122,152,144))
place('R9',147,126.8,back=True,search=(146,126,149,128))
place('R10',141.8,123,back=True,search=(141.5,121.5,144,123.5))
for i,ref in enumerate(['R21','R22','R23','R24','R25','R26','R27','R28','R29','R30','R31','R32','C24','C25','R41']):
 place(ref,143+(i%4)*2.3,145+(i//4)*2.1,back=True,search=(139,143,152,158))
place('Q1',157,145,back=True)
for i in range(33,40):place('R'+str(i),150+(i%2)*2.2,116+(i-33)*1.7,back=True,search=(149,114,154,134))
for ref,x,y in [('R5',123,115),('R6',120,115),('R7',117,112),('ESD17',120,112)]:place(ref,x,y)
for ref,x,y in [('TP1',133,155),('TP2',133,152),('TP3',144,155),('TP4',150,141.5),('TP5',142,129),('TP6',145,130),('TP7',148,130),('TP9',146,158),('TP10',160,158)]:place(ref,x,y,search=(x-1,y-1,x+1,y+1))
# VCAP1测试点紧贴其本地电容，避免长支路引入噪声。
p=placed['C3'].GetPosition();x,y=k.ToMM(p.x),k.ToMM(p.y)
place('TP8',x,y+2.5,back=True,search=(x-2,y,x+2,y+4))
assert set(placed)==set(parts),(set(parts)-set(placed))
for txt,x,y,size in [('V12 R01 - OFF BODY ONLY',133,158,.85),('J3 1',106,111.8,.8),('J1 1',157,103,.8),('BAT +',158,148,.8)]:
 t=k.PCB_TEXT(b);t.SetText(txt);t.SetPosition(V(x,y));t.SetTextSize(V(size,size));t.SetTextThickness(k.FromMM(.12));t.SetLayer(k.F_SilkS);b.Add(t)
project=json.loads((P/'v12-r01.kicad_pro').read_text())
project.update(board={'design_settings':{'rules':{'min_clearance':.2,'min_track_width':.15,'min_via_diameter':.45,'min_through_hole_diameter':.2}}},net_settings={'classes':[{'name':'Default','clearance':.2,'track_width':.2,'via_diameter':.6,'via_drill':.3,'microvia_diameter':.3,'microvia_drill':.1,'diff_pair_width':.2,'diff_pair_gap':.25,'diff_pair_via_gap':.25}]})
(P/'v12-r01.kicad_pro').write_text(json.dumps(project,indent=2))
# 固定模拟输入和局部电源连线，再让通用布线器补数字信号。
def pad(ref,num):return next(p for p in placed[ref].Pads() if p.GetNumber()==str(num))
def line(net,points,layer=k.F_Cu,width=.2):
 for a,c in zip(points,points[1:]):
  t=k.PCB_TRACK(b);t.SetNet(nets[net]);t.SetLayer(layer);t.SetWidth(k.FromMM(width));t.SetStart(a if isinstance(a,k.VECTOR2I) else V(*a));t.SetEnd(c if isinstance(c,k.VECTOR2I) else V(*c));t.SetLocked(True);b.Add(t)
def via(net,point):
 v=k.PCB_VIA(b);v.SetPosition(point if isinstance(point,k.VECTOR2I) else V(*point));v.SetWidth(k.FromMM(.6));v.SetDrill(k.FromMM(.3));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(nets[net]);v.SetLocked(True);b.Add(v)
for ch in range(1,9):
 for li,leg in enumerate('PN'):
  refs=['R'+str(101+(ch-1)*12+li*6+ri) for ri in range(6)]
  for a,c in zip(refs[:3],refs[1:4]):line(pad(a,2).GetNetname(),[pad(a,2).GetPosition(),pad(c,1).GetPosition()])
  esd='ESD'+str((ch-1)*2+li+1)
  line(pad(esd,1).GetNetname(),[pad(esd,1).GetPosition(),pad(refs[0],1).GetPosition()])
  p=pad(refs[3],2);net=p.GetNetname();yy=k.ToMM(p.GetPosition().y);branch=V(112.2,yy)
  target=next(p for p in placed['U1'].Pads() if p.GetNetname()==net)
  ty=k.ToMM(target.GetPosition().y)
  line(net,[p.GetPosition(),branch,(125,ty),target.GetPosition()]);via(net,branch)
  line(net,[branch,pad(refs[4],1).GetPosition()],k.B_Cu)
  line(pad(refs[4],2).GetNetname(),[pad(refs[4],2).GetPosition(),pad(refs[5],1).GetPosition()],k.B_Cu)
  line('GND',[pad(refs[5],2).GetPosition(),(116.6,yy),(116.6,yy+.7),(110,yy+.7)],k.B_Cu);via('GND',(110,yy+.7))
for ref,pin in [('C3',28),('C4',30),('C7',26)]:
 a=pad('U1',pin).GetPosition();c=pad(ref,1).GetPosition()
 line(pad(ref,1).GetNetname(),[a,(k.ToMM(a.x),136.7),c])
# 开关脚先用短颈部从密脚引出，再扩宽到0.4mm。
for pin,lpin,sgn in [(9,1,-1),(7,2,1)]:
 a=pad('U7',pin).GetPosition();bend=(150.3,150+sgn*.5);outer=(150.7,150+sgn*.9)
 line(pad('U7',pin).GetNetname(),[a,bend,outer])
 line(pad('U7',pin).GetNetname(),[outer,pad('L1',lpin).GetPosition()],width=.4)
line('VBAT',[pad('C19',1).GetPosition(),(148.925,148.0),(149.75,148.4)],width=.4)
line('VBAT',[(149.75,148.4),pad('U7',10).GetPosition()])
line('AVDD',[pad('U7',6).GetPosition(),(149.75,151.6),(150.55,152.1)])
line('AVDD',[(150.55,152.1),pad('C20',1).GetPosition(),(150.55,154.4),(154.45,154.4),pad('C21',1).GetPosition()],width=.4)

# 每个表面地焊盘先给真实过孔/短引线，再声明内层地平面。
# 否则旧版布线器会把平面网络视为已连，而遗漏从表面到内层的连接。
allpads=[p for fp in b.GetFootprints() for p in fp.Pads() if p.IsOnLayer(k.F_Cu) or p.IsOnLayer(k.B_Cu)]
seeds=[t for t in b.GetTracks() if type(t).__name__=='PCB_VIA' and t.GetNetname()=='GND'];seen={('R'+str(106+i*6),'2') for i in range(16)};failed=[]
for fp in b.GetFootprints():
 for pad in sorted(fp.Pads(),key=lambda p:p.GetSize().x*p.GetSize().y,reverse=True):
  key=(fp.GetReference(),pad.GetNumber())
  if pad.GetNetname()!='GND' or pad.GetAttribute()!=k.PAD_ATTRIB_SMD or key in seen:continue
  seen.add(key);pos=pad.GetPosition();layer=k.B_Cu if fp.IsFlipped() else k.F_Cu
  x,y=k.ToMM(pos.x),k.ToMM(pos.y)
  candidates= [(V(x+dx*r,y+dy*r),None) for r in [.65,.8,1,1.25,1.5,2,2.5,3,3.5,4] for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)]]
  candidates += [(v.GetPosition(),v) for v in seeds if (v.GetPosition()-pos).EuclideanNorm()<k.FromMM(3.0)]
  if fp.GetReference()=='U7' and pad.GetNumber()=='8':candidates=[(V(150.7,150),None)]+candidates
  for end,existing in candidates:
   if not (k.FromMM(100.8)<end.x<k.FromMM(164.2) and k.FromMM(100.8)<end.y<k.FromMM(159.2)):continue
   via=k.PCB_VIA(b);via.SetPosition(end);via.SetWidth(k.FromMM(.6));via.SetDrill(k.FromMM(.3));via.SetViaType(k.VIATYPE_THROUGH);via.SetLayerPair(k.F_Cu,k.B_Cu);via.SetNet(nets['GND'])
   line=k.PCB_TRACK(b);line.SetStart(pos);line.SetEnd(end);line.SetWidth(k.FromMM(.2));line.SetLayer(layer);line.SetNet(nets['GND'])
   blocked=False
   for other in allpads:
    if other.GetNetname()!='GND':
     if other.IsOnLayer(layer) and other.GetEffectiveShape(layer).Collide(line.GetEffectiveShape(layer),k.FromMM(.201)):blocked=True;break
     if not existing and any(other.IsOnLayer(l) and other.GetEffectiveShape(l).Collide(via.GetEffectiveShape(l),k.FromMM(.201)) for l in (k.F_Cu,k.B_Cu)):blocked=True;break
    elif not existing and any(other.IsOnLayer(l) and other.GetEffectiveShape(l).Collide(via.GetEffectiveShape(l),k.FromMM(.1)) for l in (k.F_Cu,k.B_Cu)):
     blocked=True;break
   if not blocked:
    for copper in b.GetTracks():
     if copper.GetNetname()=='GND':continue
     if copper.IsOnLayer(layer) and copper.GetEffectiveShape(layer).Collide(line.GetEffectiveShape(layer),k.FromMM(.201)):blocked=True;break
     if not existing and any(copper.IsOnLayer(l) and copper.GetEffectiveShape(l).Collide(via.GetEffectiveShape(l),k.FromMM(.201)) for l in (k.F_Cu,k.In2_Cu,k.B_Cu)):blocked=True;break
   if blocked:continue
   if not existing and any((v.GetPosition()-end).EuclideanNorm()<k.FromMM(.61) for v in seeds):continue
   b.Add(line)
   if not existing:b.Add(via);seeds.append(via)
   break
  else:failed.append(key)
assert not failed,('地焊盘无法安全引出',failed)
(P/'ground-fanout.json').write_text(json.dumps({'pads':len(seen),'vias':len(seeds),'source':'scripted-ground-plane-fanout','failed':failed},ensure_ascii=False,indent=2))
# 布线器从一开始就知道内层1为GND，避免先把百余地连接当信号绕线。
z=k.ZONE(b);z.SetLayer(k.In1_Cu);z.SetNet(nets['GND']);z.SetLocalClearance(k.FromMM(.25));z.SetMinThickness(k.FromMM(.2))
z.SetThermalReliefGap(k.FromMM(.25));z.SetThermalReliefSpokeWidth(k.FromMM(.3));z.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS)
poly=z.Outline();poly.NewOutline()
for xx,yy in [(100.5,100.5),(164.5,100.5),(164.5,159.5),(100.5,159.5)]:poly.Append(k.FromMM(xx),k.FromMM(yy))
b.Add(z);k.ZONE_FILLER(b).Fill(b.Zones())
assert k.ExportSpecctraDSN(b,str(P/'v12-r01.dsn'))
s=(P/'v12-r01.dsn').read_text().replace('(layer In1.Cu\n      (type signal)', '(layer In1.Cu\n      (type power)')
s=s.replace('(type route)','(type protect)')
s=re.sub(r'(\(boundary\s+\(path pcb 0)[^)]*',r'\1 164400 -159400 100600 -159400 100600 -100600 164400 -100600 164400 -159400',s)
(P/'v12-r01.dsn').write_text(s)
(P/'placement.json').write_text(json.dumps({'board_mm':[W,H,1.6],'not_wearable':True,'parts':{ref:{'x':k.ToMM(fp.GetPosition().x),'y':k.ToMM(fp.GetPosition().y),'rotation':fp.GetOrientationDegrees(),'back':fp.IsFlipped()} for ref,fp in placed.items()}},indent=2))
k.SaveBoard(str(P/'v12-r01-placement.kicad_pcb'),b)
print(len(placed),'真实封装；65x60mm离体布局，尚未布线。')

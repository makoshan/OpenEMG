"""F04：真实S7231焊盘，17路单铜层，窄尾与无穿板止挡槽，仅尾补强。"""
from pathlib import Path
import json,uuid,math
import wx
app=wx.App(False)
import pcbnew as k
P=Path(__file__).resolve().parent;NAME='fpc-f04'
q=lambda v:json.dumps(str(v),ensure_ascii=False)
u=lambda v:str(uuid.uuid5(uuid.NAMESPACE_URL,'mako/fpc-f04/'+v))
fx='(effects (font (size 1 1)))'
NETS=[f'E{ch}{leg}' for ch in range(1,9) for leg in 'PN']+['E_RLD']
CENTERS=[19.6*i for i in range(9)]
LANES=[(2-.25*(i//2))*(1 if i%2==0 else -1) if i<16 else 0 for i in range(17)]
ORDER=sorted(range(17),key=lambda i:LANES[i]);TAIL={idx:(rank-8)*1.3 for rank,idx in enumerate(ORDER)}
V=lambda x,y:k.VECTOR2I(k.FromMM(x+100),k.FromMM(100-y))
def layers(*ids):
 s=k.LSET()
 for i in ids:s.AddLayer(i)
 return s
parts=[{'ref':f'J{i+1}','value':'S7231-45R','fp':'S7231','pins':{'1':net}} for i,net in enumerate(NETS)]
parts.append({'ref':'J18','value':'TAIL17_TO_R01_J3','fp':'TAIL17','pins':dict(zip(map(str,range(1,18)),NETS))})
def schematic():
 root=u('root');defs=[];items=[];manifest=[]
 for idx,p in enumerate(parts):
  n=len(p['pins']);lib='FPC:'+p['fp'];x=40.64+(idx%3)*106.68;y=35.56+(idx//3)*55.88;h=(n+1)*2.54
  if lib not in [a[0] for a in defs]:
   d=f'(symbol {q(lib)} (pin_names (offset 1)) (in_bom no) (on_board yes) (property "Reference" "J" (at 0 5.08 0) {fx}) (property "Value" {q(p["fp"])} (at 0 2.54 0) {fx}) (symbol {q(p["fp"]+"_0_1")} (rectangle (start 0 0) (end 38.1 {-h}) (stroke (width 0.2) (type default)) (fill (type background)))) (symbol {q(p["fp"]+"_1_1")} '
   d+=''.join(f'(pin passive line (at -5.08 {-2.54*(j+1)} 0) (length 5.08) (name {q(str(j+1))} {fx}) (number {q(str(j+1))} {fx}))' for j in range(n))+'))';defs.append((lib,d))
  items.append(f'(symbol (lib_id {q(lib)}) (at {x} {y} 0) (unit 1) (in_bom no) (on_board yes) (dnp no) (uuid {u(p["ref"])}) (property "Reference" {q(p["ref"])} (at {x+19} {y-3} 0) {fx}) (property "Value" {q(p["value"])} (at {x+19} {y-1} 0) {fx}) (property "Footprint" {q("FPC:"+p["fp"])} (at {x} {y} 0) (effects (font (size 1 1)) (hide yes))) '+''.join(f'(pin {q(pin)} (uuid {u(p["ref"]+pin)}))' for pin in p['pins'])+f'(instances (project "{NAME}" (path "/{root}" (reference {q(p["ref"])}) (unit 1)))))')
  for j,(pin,net) in enumerate(p['pins'].items()):
   yy=y+2.54*(j+1)
   items.append(f'(wire (pts (xy {x-12.7} {yy}) (xy {x-5.08} {yy})) (stroke (width 0) (type default)) (uuid {u(p["ref"]+pin+"wire")})) (global_label {q(net)} (shape input) (at {x-12.7} {yy} 0) (effects (font (size 1 1)) (justify left)) (uuid {u(p["ref"]+pin+"label")}))');manifest.append({'ref':p['ref'],'pin':pin,'net':net})
 items.append(f'(text "FPC-F04 / 8 CHANNELS + RLD / 17 INDEPENDENT SIGNALS / NOT RELEASED" (at 32 20 0) {fx} (uuid {u("title")}))')
 (P/(NAME+'.kicad_sch')).write_text(f'(kicad_sch (version 20250114) (generator "mako_fpc") (uuid {root}) (paper "A2") (lib_symbols '+''.join(d for _,d in defs)+') '+''.join(items)+f'(sheet_instances (path "/" (page "1"))))')
 (P/'FPC.kicad_sym').write_text('(kicad_symbol_lib (version 20250114) (generator "mako_fpc") '+''.join(d.replace('"FPC:','"',1) for _,d in defs)+')')
 (P/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "FPC") (type "KiCad") (uri "${KIPRJMOD}/FPC.kicad_sym") (options "") (descr "FPC solder interfaces")))')
 return manifest
b=k.BOARD();b.SetCopperLayerCount(2);b.GetDesignSettings().SetBoardThickness(k.FromMM(.106))
nets={}
for net in NETS:
 nn=k.NETINFO_ITEM(b,net);b.Add(nn);nets[net]=nn
lib=P/'FPC.pretty';lib.mkdir(exist_ok=True)
def fp(ref,x,y):
 f=k.FOOTPRINT(b);f.SetReference(ref);f.SetValue('S7231-45R' if ref!='J18' else 'TAIL17_TO_R01_J3');f.SetFPID(k.LIB_ID('FPC','S7231' if ref!='J18' else 'TAIL17'));f.SetAttributes(k.FP_SMD|k.FP_EXCLUDE_FROM_BOM);f.SetPath(k.KIID_PATH('/'+u('root')+'/'+u(ref)));f.SetPosition(V(x,y));f.Reference().SetVisible(False);f.Value().SetVisible(False);b.Add(f);return f

def pad(f,pin,x,y,w,h,net,paste=True):
 p=k.PAD(f);p.SetNumber(str(pin));p.SetAttribute(k.PAD_ATTRIB_SMD);p.SetShape(k.PAD_SHAPE_RECT);p.SetSize(k.VECTOR2I(k.FromMM(w),k.FromMM(h)));p.SetLayerSet(layers(k.F_Cu,k.F_Mask,*([k.F_Paste] if paste else [])));p.SetPosition(V(x,y));p.SetNet(nets[net]);p.SetLocalSolderMaskMargin(k.FromMM(.1));f.Add(p)

positions=[]
for i,net in enumerate(NETS):
 x=CENTERS[i//2] if i<16 else CENTERS[8];y=6.5 if i<16 and i%2==0 else -6.5;positions.append((x,y));f=fp(f'J{i+1}',x,y)
 # 原厂推荐图：左0.4×1，右1.2×1与两0.3×0.2耳；相对器件几何中心。
 for dx,dy,w,h in [(-1.05,0,.4,1),(.05,0,1.2,1),(.05,.6,.3,.2),(.05,-.6,.3,.2)]:pad(f,1,x+dx,y+dy,w,h,net)
f=fp('J18',-22,0)
for i,net in enumerate(NETS):pad(f,i+1,-22,TAIL[i],3,.6,net,False)

def edge(points,layer=k.Edge_Cuts):
 for a,z in zip(points,points[1:]+points[:1]):
  s=k.PCB_SHAPE(b);s.SetShape(k.SHAPE_T_SEGMENT);s.SetStart(V(*a));s.SetEnd(V(*z));s.SetWidth(k.FromMM(.05));s.SetLayer(layer);b.Add(s)
def rounded(points,r=.5):
 out=[]
 for i,p in enumerate(points):
  a=points[i-1];z=points[(i+1)%len(points)];la=math.dist(a,p);lz=math.dist(z,p);trim=min(r,la*.3,lz*.3)
  c=tuple(p[j]+(a[j]-p[j])*trim/la for j in (0,1));d=tuple(p[j]+(z[j]-p[j])*trim/lz for j in (0,1))
  out.extend(tuple((1-t)**2*c[j]+2*(1-t)*t*p[j]+t*t*d[j] for j in (0,1)) for t in [n/6 for n in range(7)])
 return out
outer=[(-27,11.5),(-18,11.5),(-7,2.5)]
for x in CENTERS:outer.extend([(x-3,2.5),(x-3,11.5),(x+3,11.5),(x+3,2.5)])
for x in reversed(CENTERS):outer.extend([(x+3,-2.5),(x+3,-11.5),(x-3,-11.5),(x-3,-2.5)])
outer.extend([(-7,-2.5),(-18,-11.5),(-27,-11.5)])
outline=rounded(outer,.3);edge(outline);slots=[]
paths=[]
def route(net,points,w=.15):
 paths.append({'net':net,'points':points})
 for a,z in zip(points,points[1:]):
  if math.dist(a,z)<1e-8:continue
  t=k.PCB_TRACK(b);t.SetStart(V(*a));t.SetEnd(V(*z));t.SetWidth(k.FromMM(w));t.SetLayer(k.F_Cu);t.SetNet(nets[net]);b.Add(t)
for i,net in enumerate(NETS):
 x,y=positions[i];near=y-1.1 if y>0 else y+1.1;lane=LANES[i]
 fan=[(-7-12*t,lane+(TAIL[i]-lane)*(3*t*t-2*t*t*t)) for t in [j/40 for j in range(41)]]
 route(net,[(x+.05,y),(x+.05,near),(x,near),(x,lane)]+ [(-7,lane)]+fan+[(-22,TAIL[i])])
 route(net,[(x-1.05,y),(x-1.05,near),(x+.05,near)])
# 电极承力交给机械底座，工厂仅做尾端一处PI补强。
edge([(-26.5,-11),(-19.5,-11),(-19.5,11),(-26.5,11)],k.User_1)
for txt,x,y in [(f'CH{i+1}',x,9.7) for i,x in enumerate(CENTERS[:8])]+[('RLD',CENTERS[8],9.7)]+[(str(i+1),-25.1,TAIL[i]) for i in range(17)]:
 t=k.PCB_TEXT(b);t.SetText(txt);t.SetPosition(V(x,y));t.SetTextSize(k.VECTOR2I(k.FromMM(1.0),k.FromMM(1.0)));t.SetTextThickness(k.FromMM(.15));t.SetLayer(k.F_SilkS);b.Add(t)
manifest=schematic()
(P/(NAME+'.kicad_dru')).write_text('(version 1)\n(rule "FPC copper gap" (constraint clearance (min 0.10mm)))\n(rule "FPC edge" (constraint edge_clearance (min 0.30mm)))\n(rule "FPC track" (constraint track_width (min 0.15mm)))\n')
(P/(NAME+'.kicad_pro')).write_text(json.dumps({'board':{'design_settings':{'rules':{'min_clearance':.1,'min_track_width':.15,'min_copper_edge_clearance':.3},'defaults':{'solder_mask_clearance':.1}}},'net_settings':{'classes':[{'name':'Default','clearance':.1,'track_width':.15,'via_diameter':.6,'via_drill':.3}]},'meta':{'filename':NAME+'.kicad_pro','version':1}},indent=2))
k.SaveBoard(str(P/(NAME+'.kicad_pcb')),b)
(P/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "FPC") (type "KiCad") (uri "${KIPRJMOD}/FPC.pretty") (options "") (descr "Harwin recommended lands")))')
for ref in ['J1','J18']:
 f=k.FOOTPRINT(next(f for f in b.GetFootprints() if f.GetReference()==ref));f.SetPosition(k.VECTOR2I(0,0))
 for p in f.Pads():p.SetNetCode(0)
 name=str(f.GetFPID().GetLibItemName());text=f'(footprint "{name}" (version 20241229) (generator "mako_fpc") (layer "F.Cu") (attr smd) '
 for pad in f.Pads():
  xy=pad.GetPosition();sz=pad.GetSize();ls='"F.Cu" "F.Mask"'+(' "F.Paste"' if ref!='J18' else '')
  text+=f'(pad "{pad.GetNumber()}" smd rect (at {k.ToMM(xy.x)} {k.ToMM(xy.y)}) (size {k.ToMM(sz.x)} {k.ToMM(sz.y)}) (layers {ls}) (solder_mask_margin 0.1))'
 (lib/(name+'.kicad_mod')).write_text(text+')')
(P/'design.json').write_text(json.dumps({'board':'FPC-F04','status':'NOT_RELEASED','pins':manifest,'nets':NETS,'positions':positions,'lanes':LANES,'tail_y':TAIL,'outline':outline,'slots':slots,'paths':paths,'row_centers_mm':CENTERS,'thickness_mm':.106,'stiffener_mm':.2,'stiffener_glue_mm':.025,'spine_mm':5,'track_mm':.15,'clearance_mm':.1,'spring_free_height_range_mm':[1.28,1.48],'open_gates':['工厂覆盖膜CAM和钢网确认（S7231焊盘已核）','无穿板槽承力座与实际焊接公差','真实弯曲余量/抗拉/疲劳','薄盖和实物弹片公差','17路尾板进主机与焊接应力释放']},ensure_ascii=False,indent=2))
print('生成F04原生候选')

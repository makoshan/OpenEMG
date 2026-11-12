"""导入布线、清残线、扩宽供电并铺地；每个阶段独立进程，避免保存后复用失效句柄。"""
import json,shutil,subprocess,sys
import xml.etree.ElementTree as ET
from pathlib import Path
P=Path(__file__).resolve().parent
SRC=P/'v12-r01-placement.kicad_pcb';OUT=P/'v12-r01.kicad_pcb';REP=OUT.with_suffix('.drc.json')
IDS=P/'.emg-stage-ids.json'
KIPY='/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3'
POWER={'VBAT','3V3','AVDD','DVDD','GND','U7_L1','U7_L2'}

if len(sys.argv)>1:
 import wx
 app=wx.App(False)
 import pcbnew as k
 name=sys.argv[1];V=lambda x,y:k.VECTOR2I(k.FromMM(x),k.FromMM(y))
 if name=='ses':
  b=k.LoadBoard(str(SRC))
  ground=[t.Duplicate() for t in b.GetTracks() if t.GetNetname()=='GND']
  assert k.ImportSpecctraSES(b,str(P/'v12-r01.ses'))
  for t in list(b.GetTracks()):
   if t.GetNetname()=='GND':b.Remove(t)
  for t in ground:t.SetNet(b.FindNet('GND'));b.Add(t)
  # SES改变铜后先重铺内层地，否则有效接地过孔会被误判为悬空并删掉。
  k.ZONE_FILLER(b).Fill(b.Zones())
 else:
  b=k.LoadBoard(str(OUT))
  if name=='powerids':
   IDS.write_text(json.dumps(sorted(t.m_Uuid.AsString() for t in b.GetTracks() if type(t).__name__=='PCB_TRACK' and t.GetNetname() in POWER)));sys.exit()
  ids=set(json.loads(IDS.read_text())) if IDS.exists() else set()
  if name=='drop':
   for t in [t for t in b.GetTracks() if t.m_Uuid.AsString() in ids]:b.Remove(t)
  elif name=='width':
   for t in b.GetTracks():
    if t.m_Uuid.AsString() in ids:t.SetWidth(k.FromMM(float(sys.argv[2])))
  elif name=='finish':
   components={c.attrib['ref']:c for c in ET.parse(P/'v12-r01.net.xml').getroot().find('components')}
   for fp in b.GetFootprints():
    comp=components[fp.GetReference()];fp.SetPath(k.KIID_PATH(comp.find('sheetpath').attrib['tstamps']+comp.findtext('tstamps')))
    fp.Reference().SetVisible(True);fp.Reference().SetLayer(k.B_Fab if fp.IsFlipped() else k.F_Fab);fp.Reference().SetTextSize(V(.45,.45))
   for text in b.GetDrawings():
    if type(text).__name__=='PCB_TEXT':text.SetTextSize(V(.8,.8))
   # 自定义IC的装配圆点靠近真实1脚，避免正文外形错误遗留。
   for fp in b.GetFootprints():
    if fp.GetReference() in ('U2','U3','U7'):
     mx,my=(-.55,-1.25) if fp.GetReference()=='U7' else (-.75,-2.3)
     for g in fp.GraphicalItems():
      if g.GetLayer()==k.F_Fab and type(g).__name__=='PCB_SHAPE' and g.GetShape()==k.SHAPE_T_CIRCLE:
       g.SetPosition(fp.GetPosition()+V(mx,my))
   # 密集小焊盘与同号EP用实心连接，避免只剩一根散热辐条。
   for fp in b.GetFootprints():
    for pad in fp.Pads():
     if pad.GetNetname()=='GND' and pad.GetAttribute()==k.PAD_ATTRIB_SMD:
      pad.SetLocalZoneConnection(k.ZONE_CONNECTION_FULL)
   gnd=b.FindNet('GND')
   for layer in (k.F_Cu,k.In2_Cu,k.B_Cu):
    z=k.ZONE(b);z.SetLayer(layer);z.SetNet(gnd);z.SetLocalClearance(k.FromMM(.25));z.SetMinThickness(k.FromMM(.2))
    z.SetThermalReliefGap(k.FromMM(.25));z.SetThermalReliefSpokeWidth(k.FromMM(.3));z.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS)
    poly=z.Outline();poly.NewOutline()
    for x,y in [(100.5,100.5),(164.5,100.5),(164.5,159.5),(100.5,159.5)]:poly.Append(int(k.FromMM(x)),int(k.FromMM(y)))
    b.Add(z)
   k.ZONE_FILLER(b).Fill(b.Zones())
  else:raise SystemExit('unknown stage '+name)
 k.SaveBoard(str(OUT),b);sys.exit()

def stage(*args):subprocess.run([KIPY,__file__,*map(str,args)],check=True,capture_output=True)
def drc():
 subprocess.run(['/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli','pcb','drc','--format','json','--output',str(REP),str(OUT)],check=True,capture_output=True)
 return json.loads(REP.read_text())
# 同名项目已由布局脚本写入，无须覆盖规则。
stage('ses')
# 只删除原生DRC确认的悬空残线，不放宽规则。
for _ in range(8):
 bad=sorted({i['uuid'] for v in drc()['violations'] if v['type'].endswith('dangling') for i in v['items']})
 if not bad:break
 IDS.write_text(json.dumps(bad));stage('drop')
stage('powerids');wide=set(json.loads(IDS.read_text()))
IDS.write_text(json.dumps(sorted(wide)));stage('width',0.4)
# 供电优先0.4mm；碰撞段保留0.2mm，逐段记录，间距规则不变。
narrow=set()
for _ in range(12):
 hit={i['uuid'] for v in drc()['violations'] for i in v['items']}&wide-narrow
 if not hit:break
 narrow|=hit;IDS.write_text(json.dumps(sorted(narrow)));stage('width',0.2)
stage('finish');r=drc();IDS.unlink()
(P/'review-narrow-escapes.json').write_text(json.dumps(sorted(narrow)))
print(json.dumps({'widened':len(wide)-len(narrow),'kept_narrow':len(narrow),
 'violations':len(r['violations']),'unconnected':len(r['unconnected_items'])}))
for v in r['violations'][:12]:print('  DRC',v['type'],v['description'][:100])
for u in r['unconnected_items'][:12]:print('  UNCONN',u['description'][:100])

"""直接读取最终 PCB 与原生 DRC；不能以文件存在代替连通验收。"""
from pathlib import Path
import json, collections, subprocess
import wx
app=wx.App(False)
import pcbnew as k
P=Path(__file__).resolve().parent
subprocess.run(['/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli','pcb','drc','--format','json','--schematic-parity','--severity-all','--output',str(P/'v12-r01.drc.json'),str(P/'v12-r01.kicad_pcb')],check=True,capture_output=True)
D=json.loads((P/'design.json').read_text());parts={p['ref']:p for p in D['parts']}
b=k.LoadBoard(str(P/'v12-r01.kicad_pcb'))
fp={f.GetReference():f for f in b.GetFootprints()}
assert len(fp)==len(list(b.GetFootprints())) and set(fp)==set(parts)
checked=0
for ref,f in fp.items():
 expected=parts[ref]['pins']
 assert {p.GetNumber() for p in f.Pads() if p.GetNumber()}==set(expected),ref
 for pad in f.Pads():
  n=pad.GetNumber()
  if n:
   if expected[n] is None:
    assert pad.GetNetname().startswith('unconnected-'),(ref,n,pad.GetNetname())
   else:assert pad.GetNetname()==expected[n],(ref,n,pad.GetNetname(),expected[n])
   checked+=1
tracks=list(b.GetTracks());vias=[t for t in tracks if type(t).__name__=='PCB_VIA'];lines=[t for t in tracks if type(t).__name__=='PCB_TRACK']
assert lines and vias and b.GetCopperLayerCount()==4
assert not any(t.GetLayer()==k.In1_Cu for t in lines),'参考地层被信号线占用'
assert min(k.ToMM(t.GetWidth()) for t in lines)>=.1499
assert min(k.ToMM(t.GetDrillValue()) for t in vias)>=.1999
assert min(k.ToMM(t.GetWidth(k.F_Cu)) for t in vias)>=.4499
assert min((k.ToMM(t.GetWidth(k.F_Cu))-k.ToMM(t.GetDrillValue()))/2 for t in vias)>=.1249
r=json.loads((P/'v12-r01.drc.json').read_text())
assert not r['violations'] and not r['unconnected_items'],('原生DRC未通过',len(r['violations']),len(r['unconnected_items']))
assert not r.get('schematic_parity'),r.get('schematic_parity')
control=json.loads((P/'placement-drc.json').read_text())
assert len(control['unconnected_items'])>100,'未布线反例应报告大量未连接'
metrics={}
for net in ['U7_L1','U7_L2','VCAP1','VCAP2','VCAP3','VCAP4','VREFP','ADS_SCLK','ADS_DIN','ADS_DOUT','ADS_DRDY']:
 ts=[t for t in tracks if t.GetNetname()==net]
 metrics[net]={'length_mm':round(sum(k.ToMM(t.GetLength()) for t in ts if type(t).__name__=='PCB_TRACK'),3),'vias':sum(type(t).__name__=='PCB_VIA' for t in ts)}
result={'status':'ROUTING_ONLY_PASS','footprints':len(fp),'pads_checked_including_split_EP':checked,'tracks':len(lines),'vias':len(vias),'zones':len(list(b.Zones())),'tracks_per_layer':dict(collections.Counter(b.GetLayerName(t.GetLayer()) for t in lines)),'trace_metrics':metrics,'negative_control_unconnected':len(control['unconnected_items']),'manufacturing_ready':False,'human_test_ready':False,'open_gates':D['open_gates']}
for net in ('U7_L1','U7_L2'):
 assert metrics[net]['vias']==0 and metrics[net]['length_mm']<4,(net,metrics[net])
for net,limit in [('VCAP1',6.5),('VCAP2',3),('VCAP4',3)]:
 assert metrics[net]['vias']==0 and metrics[net]['length_mm']<limit,(net,metrics[net])
# 最终输入每对经过相同层，支路只准各有一个背面泄放过孔。
analog={}
for ch in range(1,9):
 for leg in 'PN':
  net=f'ADS_IN{ch}{leg}';ts=[t for t in tracks if t.GetNetname()==net]
  assert not any(t.GetLayer()==k.In2_Cu for t in ts if type(t).__name__=='PCB_TRACK'),net
  assert sum(type(t).__name__=='PCB_VIA' for t in ts)==1,net
  analog[net]=round(sum(k.ToMM(t.GetLength()) for t in ts if type(t).__name__=='PCB_TRACK'),3)
 assert abs(analog[f'ADS_IN{ch}P']-analog[f'ADS_IN{ch}N'])<2,(ch,analog)
result['analog_length_mm']=analog
for net in ('VREFP','VCAP3'):
 assert metrics[net]['vias']==1 and metrics[net]['length_mm']<6,(net,metrics[net])
# 过孔孔壁不能侵入贴片焊盘；否则需要另行确认填孔盖铜工艺。
via_in_pad=[]
for v in vias:
 for f in fp.values():
  for p in f.Pads():
   if p.GetAttribute()!=k.PAD_ATTRIB_SMD or not p.GetNumber():continue
   if (p.GetPosition()-v.GetPosition()).EuclideanNorm()>k.FromMM(3):continue
   probe=k.PCB_VIA(b);probe.SetPosition(v.GetPosition());probe.SetWidth(v.GetDrillValue());probe.SetLayerPair(k.F_Cu,k.B_Cu)
   if any(p.IsOnLayer(l) and p.GetEffectiveShape(l).Collide(probe.GetEffectiveShape(l),0) for l in (k.F_Cu,k.B_Cu)):via_in_pad.append((f.GetReference(),p.GetNumber()))
assert not via_in_pad,('过孔侵入贴片焊盘',via_in_pad)
result['via_hole_intrusions']=via_in_pad
(P/'board-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))

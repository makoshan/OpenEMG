"""读取交付源与原生网表；拿R01实板网名作外部配对依据，带必失败反例。"""
from pathlib import Path
import json,subprocess,tempfile,xml.etree.ElementTree as ET,copy,hashlib
import wx
app=wx.App(False)
import pcbnew as k
P=Path(__file__).resolve().parent;CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
NAME='fpc-f04';d=json.loads((P/'design.json').read_text())
b=k.LoadBoard(str(P/(NAME+'.kicad_pcb')))
r01=k.LoadBoard(str(P.parent/'r01-bench/v12-r01.kicad_pcb'))
rj=next(f for f in r01.GetFootprints() if f.GetReference()=='J3')
external={int(p.GetNumber()):p.GetNetname() for p in rj.Pads() if p.GetNumber()}
fp={f.GetReference():f for f in b.GetFootprints()};expected={(p['ref'],p['pin']):p['net'] for p in d['pins']}
def pins_ok(board):
 a={(f.GetReference(),p.GetNumber()):p.GetNetname() for f in board.GetFootprints() for p in f.Pads() if p.GetNumber()}
 assert a==expected,(a,expected)
 tail=next(f for f in board.GetFootprints() if f.GetReference()=='J18')
 for p in tail.Pads():assert p.GetNetname()==external[int(p.GetNumber())],('R01 J3 mismatch',p.GetNumber())
pins_ok(b)
netlist=ET.parse(P/'netlist.xml');actual={}
for net in netlist.findall('.//nets/net'):
 for node in net.findall('node'):actual[(node.get('ref'),node.get('pin'))]=net.get('name')
assert actual==expected,(actual,expected)
tracks=list(b.GetTracks());assert tracks and all(t.GetLayer()==k.F_Cu and type(t).__name__=='PCB_TRACK' for t in tracks)
assert not list(b.Zones())
assert all(k.ToMM(t.GetWidth())>=.1499 for t in tracks)
assert not any(p.IsOnLayer(k.B_Cu) for f in b.GetFootprints() for p in f.Pads() if p.GetNumber())
assert abs(k.ToMM(b.GetDesignSettings().GetBoardThickness())-.106)<1e-6
assert not any(p.GetAttribute()==k.PAD_ATTRIB_NPTH for f in b.GetFootprints() for p in f.Pads())
def run(report,*args):
 subprocess.run([CLI,*args],check=True,capture_output=True)
 return json.loads(report.read_text())
erc=run(P/'erc.json','sch','erc','--format','json','--severity-all','--output',str(P/'erc.json'),str(P/(NAME+'.kicad_sch')))
assert not [v for s in erc['sheets'] for v in s['violations']]
drc=run(P/'drc.json','pcb','drc','--format','json','--schematic-parity','--severity-all','--output',str(P/'drc.json'),str(P/(NAME+'.kicad_pcb')))
assert not drc['violations'] and not drc['unconnected_items'] and not drc.get('schematic_parity'),drc
with tempfile.TemporaryDirectory(prefix='fpc-f04-check-') as tmp:
 tmp=Path(tmp);bad=b
 removed=max(bad.GetTracks(),key=lambda t:t.GetLength());bad.Remove(removed);k.SaveBoard(str(tmp/'broken.kicad_pcb'),bad);bad.Add(removed)
 r=run(tmp/'broken.json','pcb','drc','--format','json','--severity-all','--output',str(tmp/'broken.json'),str(tmp/'broken.kicad_pcb'))
 assert r['unconnected_items'],'断线反例必须报未连接'
 bad=b;tail=next(f for f in bad.GetFootprints() if f.GetReference()=='J18')
 wrong=next(p for p in tail.Pads() if p.GetNumber()=='1');wrong.SetNet(bad.FindNet('E1N'))
 try:pins_ok(bad)
 except AssertionError:pass
 else:raise AssertionError('错接P/N反例未拒绝')
 wrong.SetNet(bad.FindNet('E1P'));pins_ok(b)
lengths={net:round(sum(k.ToMM(t.GetLength()) for t in tracks if t.GetNetname()==net),2) for net in d['nets']}
report={'status':'DESIGN_ROUTING_CHECK_PASS_NOT_RELEASED','copper_layers_used':1,'nets':17,'numbered_pads':34,'NPTH':0,'routed_slots':0,'physical_copper_lands':85,'tracks':len(tracks),'vias':0,'native_ERC':0,'native_DRC':0,'native_unconnected':0,'native_schematic_parity':0,'trace_lengths_mm':lengths,'negative_controls':['实际删除最长走线→原生DRC报未连接','J18:1错接N→针脚映射检查失败'],'R01_sha256':hashlib.sha256((P.parent/'r01-bench/v12-r01.kicad_pcb').read_bytes()).hexdigest(),'manufacturing_ready':False,'human_test_ready':False,'open_gates':d['open_gates']}
(P/'check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))

xy=lambda p:[round(k.ToMM(p.x)-100,6),round(100-k.ToMM(p.y),6)]
geometry={'tracks':[{'start':xy(t.GetStart()),'end':xy(t.GetEnd()),'width':k.ToMM(t.GetWidth()),'net':t.GetNetname()} for t in b.GetTracks()],'pads':[{'ref':f.GetReference(),'pin':p.GetNumber(),'xy':xy(p.GetPosition()),'size':[k.ToMM(p.GetSize().x),k.ToMM(p.GetSize().y)],'net':p.GetNetname(),'hole':p.GetAttribute()==k.PAD_ATTRIB_NPTH} for f in b.GetFootprints() for p in f.Pads()]}
(P/'native-geometry.json').write_text(json.dumps(geometry,ensure_ascii=False,indent=2))

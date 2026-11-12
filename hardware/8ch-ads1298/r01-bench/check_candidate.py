"""独立检查真实导出网表；破坏供电/极性/默认态的反例必须失败。"""
from pathlib import Path
import copy, hashlib, json, xml.etree.ElementTree as ET
P=Path(__file__).resolve().parent

def electrical(d):
 p={v['ref']:v for v in d['parts']}
 def pin(r,n,net): assert p[r]['pins'][str(n)]==net,(r,n,net)
 for r,n,net in [('U1',35,'ADS_PWDN'),('U2',8,'XIAO_PWDN'),('U2',16,'ADS_PWDN'),('J1',15,'XIAO_PWDN'),('J1',16,'OE_N'),('U1',62,'AVDD'),('U12',1,'U7_EN'),('U12',6,'VBAT'),('U12',5,'3V3'),('D1',1,'AVDD'),('D1',2,'DVDD'),('R41',1,'U7_EN'),('R41',2,'EN_RC'),('C24',1,'EN_RC')]:pin(r,n,net)
 for r,net in [('R39','XIAO_PWDN'),('R40','ADS_PWDN')]:
  assert p[r]['value']=='10k';pin(r,1,net);pin(r,2,'GND')
 assert p['U10']['value']=='SN74AUP1T14DCKR'
 assert p['R41']['value']=='4.7k'
 assert 'U11' not in p
 assert not d['manufacturing_ready'] and not d['human_test_ready']
 assert len(p)==208 and all(x['footprint'] for x in p.values())
 assert len(set(x['source_ref'] for x in p.values()))==208
 return p

def check():
 d=json.loads((P/'design.json').read_text());p=electrical(d)
 x=ET.parse(P/'v12-r01.net.xml').getroot()
 comps={c.attrib['ref']:c for c in x.findall('./components/comp')}
 assert set(comps)==set(p),('元件集合不一致',set(comps)^set(p))
 actual={}
 for net in x.findall('./nets/net'):
  name=net.attrib['name']
  for n in net.findall('node'):
   key=(n.attrib['ref'],n.attrib['pin'])
   assert key not in actual,key
   actual[key]=name
 count=0
 for ref,v in p.items():
  assert comps[ref].findtext('footprint')==v['footprint'],ref
  for pin,net in v['pins'].items():
   got=actual.get((ref,pin))
   if net is not None:assert got==net,(ref,pin,net,got);count+=1
   else: assert got is None or got.startswith('unconnected-'),(ref,pin,got)
 baseline=json.loads((P/'baseline.json').read_text())
 assert hashlib.sha256((P/'baseline-design.json').read_bytes()).hexdigest()==baseline['sha256']
 for name,sha in json.loads((P/'footprint-hashes.json').read_text()).items():
  assert hashlib.sha256((P/name).read_bytes()).hexdigest()==sha,name
 failures=[]
 for ref,pin,net in [('U1','35','PG'),('R40','2','ADS_PWDN'),('D1','1','DVDD'),('U12','6','3V3'),('C24','1','U7_EN'),('J1','16','DVDD')]:
  bad=copy.deepcopy(d);next(v for v in bad['parts'] if v['ref']==ref)['pins'][pin]=net
  try:electrical(bad)
  except AssertionError:failures.append(ref+'.'+pin)
  else:raise AssertionError('反例未被发现:'+ref)
 result={'components':len(p),'connected_pins_verified':count,'negative_controls_rejected':failures,'netlist_matches':True,'scope':'静态电气与原生网表；非上电/人体/制造验收'}
 (P/'check-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':check()

"""与原生网表同步库标识及独立NC网络；不改焊盘位置或实际信号连接。"""
from pathlib import Path
import json,xml.etree.ElementTree as ET
import wx
app=wx.App(False)
import pcbnew as k
P=Path(__file__).resolve().parent;b=k.LoadBoard(str(P/'v12-r01.kicad_pcb'));D=json.loads((P/'design.json').read_text());parts={p['ref']:p for p in D['parts']};nc={}
for net in ET.parse(P/'v12-r01.net.xml').getroot().findall('./nets/net'):
 if net.attrib['name'].startswith('unconnected-'):
  nodes=net.findall('node');assert len(nodes)==1
  n=nodes[0];nc[n.attrib['ref'],n.attrib['pin']]=net.attrib['name']
for f in b.GetFootprints():
 d=parts[f.GetReference()];lib,name=d['footprint'].split(':',1);f.SetFPID(k.LIB_ID(lib,name))
 for p in f.Pads():
  if p.GetNumber() and d['pins'][p.GetNumber()] is None:
   raw=nc[f.GetReference(),p.GetNumber()];name=raw.replace('/','{slash}')
   if not b.FindNet(name):b.Add(k.NETINFO_ITEM(b,name))
   assert p.GetNetname() in ('',raw,name)
   p.SetNet(b.FindNet(name))
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(P/'v12-r01.kicad_pcb'),b)
print('库标识同步',len(parts),'独立NC网络',len(nc))

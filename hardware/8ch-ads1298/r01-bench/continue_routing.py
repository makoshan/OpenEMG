"""以真实DRC未闭合的路由继续求解，保留内层参考地和现有走线，不降低工艺规则。"""
from pathlib import Path
import re
import wx
app=wx.App(False)
import pcbnew as k
P=Path(__file__).resolve().parent
# 地的连接已经由原生检查证明。把固定地引线作为障碍，避开旧路由器的GND归一化递归错误。
import sys,json,subprocess
if len(sys.argv)==1:
 subprocess.run([sys.executable,__file__,'ground'],check=True)
 subprocess.run([sys.executable,__file__,'export'],check=True)
 sys.exit()
if sys.argv[1]=='ground':
 source=k.LoadBoard(str(P/'v12-r01-placement.kicad_pcb'))
 keep=[]
 for t in source.GetTracks():
  if t.GetNetname()!='GND':continue
  if type(t).__name__=='PCB_VIA':
   pos=t.GetPosition()
   for l in (k.F_Cu,k.In2_Cu,k.B_Cu):keep.append(f'(keepout \"GND_FIXED\" (circle {source.GetLayerName(l)} {k.ToMM(t.GetWidth(l))*1000:.3f} {k.ToMM(pos.x)*1000:.3f} {-k.ToMM(pos.y)*1000:.3f}))')
  else:
   a,c=t.GetStart(),t.GetEnd();keep.append(f'(keepout \"GND_FIXED\" (path {source.GetLayerName(t.GetLayer())} {k.ToMM(t.GetWidth())*1000:.3f} {k.ToMM(a.x)*1000:.3f} {-k.ToMM(a.y)*1000:.3f} {k.ToMM(c.x)*1000:.3f} {-k.ToMM(c.y)*1000:.3f}))')
 (P/'ground-keepouts.json').write_text(__import__('json').dumps(keep))
 print('固定地障碍',len(keep))
 sys.exit()
b=k.LoadBoard(str(P/'v12-r01.kicad_pcb'))
keep=json.loads((P/'ground-keepouts.json').read_text())
for t in list(b.GetTracks()):
 if t.GetNetname()=='GND':b.Remove(t)
assert k.ExportSpecctraDSN(b,str(P/'v12-r01-continue.dsn'))
s=(P/'v12-r01-continue.dsn').read_text().replace('(layer In1.Cu\n      (type signal)', '(layer In1.Cu\n      (type power)')
s=s.replace('    (boundary','    '+'\n    '.join(keep)+'\n    (boundary',1)
s=re.sub(r'(\(boundary\s+\(path pcb 0)[^)]*',r'\1 164400 -159400 100600 -159400 100600 -100600 164400 -100600 164400 -159400',s)
# 外层地铜在最终KiCad重铺，路由阶段只保留内层参考面。
pos=0
while True:
 a=s.find('(plane GND',pos)
 if a<0:break
 depth=0
 for i in range(a,len(s)):
  depth+=(s[i]=='(')-(s[i]==')')
  if depth==0:break
 if 'In1.Cu' not in s[a:i+1]:s=s[:a]+s[i+1:];pos=a
 else:pos=i+1
# 继续补线时保留关键模拟主路径；其余短线可由路由器重新整理。
for net in [f'ADS_IN{ch}{leg}' for ch in range(1,9) for leg in 'PN']+['VCAP1','VCAP2','VCAP4','U7_L1','U7_L2']:
 s=s.replace(f'(net {net}) (type route)',f'(net {net}) (type protect)')
assert '(net GND)' not in s and s.count('GND_FIXED')==len(keep)
(P/'v12-r01-continue.dsn').write_text(s)

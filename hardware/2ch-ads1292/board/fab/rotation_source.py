"""将已核过的嘉立创封装拟合绑定到真实板，拒绝旧坐标表随新板混用。"""
import hashlib,json,math
from pathlib import Path
import pcbnew as k

def turn(a,x,y):
 c,s=math.cos(math.radians(a)),math.sin(math.radians(a))
 return x*c+y*s,-x*s+y*c

def signature(f):
 # 撤销板上的旋转/背面镜像，确认复用的是同一封装几何而非只同名。
 x,y=k.ToMM(f.GetPosition().x),k.ToMM(f.GetPosition().y);a=f.GetOrientationDegrees();out=[]
 for p in f.Pads():
  px,py=turn(-a,k.ToMM(p.GetPosition().x)-x,k.ToMM(p.GetPosition().y)-y)
  if f.IsFlipped():px=-px
  out.append((p.GetNumber(),round(px,4),round(py,4),round(k.ToMM(p.GetSize().x),4),round(k.ToMM(p.GetSize().y),4)))
 return sorted(out)

def errors(board,rows):
 bad=[]
 for f in board.GetFootprints():
  ref=f.GetReference()
  if ref not in rows:continue
  r=rows[ref]
  if abs(k.ToMM(f.GetPosition().x)-r['kicad_x'])>.0001 or abs(-k.ToMM(f.GetPosition().y)-r['kicad_y'])>.0001:bad.append(ref+' 旋转表位置过期')
  if abs((f.GetOrientationDegrees()-r['kicad_rot']+180)%360-180)>.001:bad.append(ref+' 旋转表方向过期')
  if ('Bottom' if f.IsFlipped() else 'Top')!=r['side']:bad.append(ref+' 旋转表面别过期')
 return bad

def verify_source(pcb,rotation):
 p=Path(pcb);r=Path(rotation);meta=json.loads(r.with_suffix('.source.json').read_text())
 assert hashlib.sha256(p.read_bytes()).hexdigest()==meta['pcb_sha256'],'旋转表源板哈希过期'
 assert hashlib.sha256(r.read_bytes()).hexdigest()==meta['rotation_sha256'],'旋转表内容与来源记录不一致'
 assert not errors(k.LoadBoard(str(p)),json.loads(r.read_text())),'旋转表位置/方向/面别与板不一致'

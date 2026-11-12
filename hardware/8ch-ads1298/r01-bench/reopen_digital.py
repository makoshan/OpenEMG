"""只撤回冲突的数字全局路由，保留已验证的局部引出；清除冗余输入地扇出。"""
from pathlib import Path
import wx
app=wx.App(False)
import pcbnew as k
P=Path(__file__).resolve().parent;b=k.LoadBoard(str(P/'v12-r01.kicad_pcb'));fp=next(f for f in b.GetFootprints() if f.GetReference()=='U3')
groundpads=[p.GetPosition() for p in fp.Pads() if p.GetNumber() in ('14','15','16','17','18','19')]
tracks=list(b.GetTracks());ends=[];drop=[]
for t in tracks:
 if t.GetNetname() in ('ADS_DRDY','DOUT_B','ADS_GPIO1','ADS_GPIO2','ADS_GPIO3','ADS_GPIO4') or (t.GetNetname()=='XIAO_DRDY' and not t.IsLocked()):drop.append(t);continue
 if t.GetNetname()=='GND' and type(t).__name__=='PCB_TRACK':
  if any(t.GetStart()==p for p in groundpads):ends.append(t.GetEnd());drop.append(t)
  elif any(t.GetEnd()==p for p in groundpads):ends.append(t.GetStart());drop.append(t)
for t in tracks:
 if type(t).__name__=='PCB_VIA' and t.GetNetname()=='GND' and any(t.GetPosition()==p for p in ends):drop.append(t)
for t in drop:b.Remove(t)
k.SaveBoard(str(P/'v12-r01.kicad_pcb'),b)

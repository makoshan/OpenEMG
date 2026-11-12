"""把无法引出的低速控制下拉移到空闲背面区域；原生检查负责拒绝碰撞。"""
from pathlib import Path
import wx
app=wx.App(False)
import pcbnew as k
P=Path(__file__).resolve().parent;b=k.LoadBoard(str(P/'v12-r01.kicad_pcb'))
positions={'R15':(154,129),'R16':(152,131),'R40':(153,133)}
for fp in b.GetFootprints():
 if fp.GetReference() in positions:
  x,y=positions[fp.GetReference()];fp.SetPosition(k.VECTOR2I(k.FromMM(x),k.FromMM(y)))
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(P/'v12-r01.kicad_pcb'),b)

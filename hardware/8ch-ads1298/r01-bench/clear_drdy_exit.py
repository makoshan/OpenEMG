"""先给GPIO保留短出口，再重连DRDY，避免先到的数字线堵住邻脚。"""
from pathlib import Path
import wx
app=wx.App(False)
import pcbnew as k
P=Path(__file__).resolve().parent;b=k.LoadBoard(str(P/'v12-r01.kicad_pcb'))
for t in list(b.GetTracks()):
 if t.GetNetname() in ('ADS_DRDY','ADS_SCLK') and not t.IsLocked():b.Remove(t)
k.SaveBoard(str(P/'v12-r01.kicad_pcb'),b)

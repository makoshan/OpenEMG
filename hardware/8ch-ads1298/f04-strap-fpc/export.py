"""只导出当前候选；工具默认FR4 job隔离，不进入工厂Gerber审核目录。"""
from pathlib import Path
import subprocess
P=Path(__file__).resolve().parent;CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli';B=P/'fpc-f04.kicad_pcb';S=P/'fpc-f04.kicad_sch';G=P/'gerber-review';G.mkdir(exist_ok=True)
def run(*args):subprocess.run([CLI,*map(str,args)],check=True)
run('sch','export','netlist','--format','kicadxml','--output',P/'netlist.xml',S)
run('sch','export','pdf','--output',P/'schematic.pdf',S)
run('pcb','export','gerbers','--layers','F.Cu,F.Mask,F.Paste,F.SilkS,Edge.Cuts,User.1','--output',str(G)+'/',B)
run('pcb','export','drill','--excellon-separate-th','--excellon-units','mm','--output',str(G)+'/',B)
a=P/'audit';a.mkdir(exist_ok=True)
for source,target in [('fpc-f04-job.gbrjob','INVALID-NATIVE-FR4-JOB-DO-NOT-USE.json'),('fpc-f04-PTH.drl','empty-PTH.drl')]:
 
 if (G/source).exists():(G/source).replace(a/target)
run('pcb','export','svg','--layers','F.Cu,Edge.Cuts,User.1','--mode-single','--page-size-mode','2','--output',P/'copper-native.svg',B)
run('pcb','export','step','--force','--no-components','--include-tracks','--include-pads','--user-origin','100x100mm','--output',P/'fpc-f04.step',B)
(P/'fpc-f04.step').replace(a/'DEFAULT-STACK-NOT-MECHANICAL-FPC.step')
assert not list(G.glob('*.gbrjob')) and not list(G.glob('*B_Cu*'))

run('pcb','export','ipcd356','--output',G/'fpc-f04.d356',B)

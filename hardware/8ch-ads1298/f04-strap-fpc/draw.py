"""从原生铜坐标输出软板审核图和1:1纸样。"""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Rectangle
from matplotlib.font_manager import FontProperties
P=Path(__file__).resolve().parent;d=json.loads((P/'design.json').read_text());g=json.loads((P/'native-geometry.json').read_text());F=FontProperties(fname='/System/Library/Fonts/STHeiti Medium.ttc');plt.rcParams['font.family']=F.get_name();plt.rcParams['axes.unicode_minus']=False

def board(ax,back=False):
 ax.set_aspect('equal');ax.set(xlim=(-30,164),ylim=(-13,13));ax.axis('off');ax.add_patch(Polygon(d['outline'],facecolor='#d3d5ce' if back else '#203239',edgecolor='#333333',lw=.6))
 if back:
  ax.add_patch(Rectangle((-26.5,-11),7,22,facecolor='#b4c6da',edgecolor='#718aa7',lw=.5))
 else:
  for t in g['tracks']:
   x,y=t['start'];u,v=t['end'];ax.plot([x,u],[y,v],color='#dfbf73',lw=.35)
  for p in g['pads']:
   x,y=p['xy'];w,h=p['size'];ax.add_patch(Rectangle((x-w/2,y-h/2),w,h,facecolor='#efca77',lw=0))
   if p['ref']=='J18':ax.text(x-3.7,y,p['pin'],color='white',fontsize=4,ha='center',va='center')
  for i,x in enumerate(d['row_centers_mm']):ax.text(x,10,'RLD' if i==8 else f'CH{i+1}',color='white',ha='center',fontsize=6)
 for s in d['slots']:ax.add_patch(Polygon(s,facecolor='white',edgecolor='#888888',lw=.3))
fig=plt.figure(figsize=(16,10),dpi=150,facecolor='white');fig.text(.04,.95,'F04 · 薄弹片腕带软 PCB 制造审核图',fontsize=24)
fig.text(.04,.89,'A 正面铜线｜17路独立网络，0过孔，尾板按丝印针号接R01 J3同号针',fontsize=13)
a=fig.add_axes([.03,.62,.94,.25]);board(a)
fig.text(.04,.58,'B 背面补强｜仅尾部1块PI补强，电极岛由外侧承力柱支撑，无穿板槽',fontsize=13)
a=fig.add_axes([.03,.31,.94,.25]);board(a,True)
fig.text(.04,.26,'C 186.8×23mm最大包络；连接脊5mm；线宽0.15 / 间距≥0.10 / 铜边距≥0.30mm。',fontsize=12)
fig.text(.04,.20,'D 单面PI / RA铜18µm / 柔性区106µm；局部补强0.20+胶0.025mm；均待工厂确认。',fontsize=12)
fig.text(.04,.14,'E 17个S7231-45R焊位；85块实际铜焊区 / 34逻辑端点；覆盖膜开窗须CAM回读。',fontsize=12)
fig.text(.04,.07,'F 当前仅可询价与工程审核：尚未批准投产；不含金属头、弹片、贴片、3D打印和主机。',fontsize=12)
fig.savefig(P/'fabrication-drawing.png');fig.savefig(P/'gerber-review/FAB-DRAWING.pdf');plt.close(fig)
fig=plt.figure(figsize=(297/25.4,210/25.4));a=fig.add_axes([15/297,75/210,186.8/297,23/210]);a.set(xlim=(-27,159.8),ylim=(-11.5,11.5));a.set_aspect('equal');a.axis('off');a.add_patch(Polygon(d['outline'],fill=False,lw=.4))
for s in d['slots']:a.add_patch(Polygon(s,fill=False,lw=.3))
for p in g['pads']:
 x,y=p['xy'];w,h=p['size'];a.add_patch(Rectangle((x-w/2,y-h/2),w,h,fill=False,lw=.3))
fig.text(.05,.83,'F04 1:1纸样 / A4横向 / 100%打印，关闭适应纸张',fontsize=14);fig.text(.05,.24,'打印后实测总长186.8mm。先核侧柱、出口与尾板路径，不凭显示缩放决定下单。',fontsize=11)
fig.savefig(P/'paper-template-1to1.pdf');plt.close(fig)

# 总装图使用真实STEP快照；缺图直接报错，不用示意方块代替生成结果。
fig=plt.figure(figsize=(16,10),dpi=150,facecolor='white')
fig.text(.035,.95,'F04 · 胶粘式弹片腕带｜已实现，未实物验收',fontsize=23)
for x,pattern,title in [(0.03,'bent-final_*.png','A 弯曲排列概念｜桥为弦线，未验应变'),(.515,'exploded-final_*.png','B 单排爆炸｜触头、弹片、软板、承力底座')]:
    files=sorted(P.glob(pattern));assert files,pattern
    ax=fig.add_axes([x,.38,.455,.53]);ax.imshow(plt.imread(files[-1]));ax.axis('off')
    fig.text(x,.365,title,fontsize=12)
for x,y,title,body in [(.035,.28,'C 尺寸','本体3.71 mm；含底胶3.86 mm（未实测）\nFPC 186.8×23 mm；适配29 mm织带'),(.52,.28,'D 连接','16采集触点＋独立RLD → 17路软板\n尾J18:1–17 → R01 J3同号；N不能并地'),(.035,.13,'E 粘贴','胶粘每排底座；软板桥不整面贴死\n尾端1处补强；侧柱避开软板托住触头'),(.52,.13,'F 验收','已验证：17网/名义干涉/独立复核\n待打印、焊接、弯曲拉伸、尾部进壳实测')]:
    fig.text(x,y,title,fontsize=15);fig.text(x,y-.07,body,fontsize=12,linespacing=1.8)
fig.savefig(P/'overview.png');plt.close(fig)

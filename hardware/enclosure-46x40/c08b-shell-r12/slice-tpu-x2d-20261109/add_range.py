# 给切好的 3MF 加「高度范围修改器」：只在床面 Z 0.7..1.3（表带内袋顶那层桥）把桥接角设 180（横跨），其它高度仍自动。
# 用法：python3 add_range.py 输入.3mf 输出.3mf [对象编号…]，默认 1 2。编号按 3MF 里对象顺序（Bambu 认这个，不是 3dmodel 里的 id 2/4）。
import sys, zipfile
RANGE = ('  <range min_z="0.7" max_z="1.3">\n   <option opt_key="layer_height">0.16</option>\n'
         '   <option opt_key="bridge_angle">180</option>\n  </range>\n')
xml = '<?xml version="1.0" encoding="utf-8"?>\n<objects>\n' + "".join(
    f' <object id="{i}">\n{RANGE} </object>\n' for i in (sys.argv[3:] or ("1", "2"))) + '</objects>\n'
src = zipfile.ZipFile(sys.argv[1])
with zipfile.ZipFile(sys.argv[2], "w", zipfile.ZIP_DEFLATED) as z:
    for it in src.infolist():
        if not it.filename.startswith("Metadata/plate_1.gcode"):
            z.writestr(it, src.read(it.filename))
    z.writestr("Metadata/layer_config_ranges.xml", xml)

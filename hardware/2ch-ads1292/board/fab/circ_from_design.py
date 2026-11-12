"""把 ../design.json 转成 rot_check.py 要的 circ 格式：{位号:{lcsc,dnp,pin_names}}，脚名取 pins 键里 '号:名' 的名。"""
import json, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
D = json.load(open('../design.json'))['parts']
out = {r: dict(lcsc=p.get('lcsc'), dnp=bool(p.get('dnp')), pin_names={k.split(':')[0]: k.split(':')[1] for k in p['pins'] if ':' in k}) for r, p in D.items()}
for r in out:
    if r[0] == 'D': out[r]['pin_names'] = {'1': '1', '2': '2'}   # ESD501：TI 与嘉立创都按 1/2 编号，嘉立创符号没有功能名
json.dump(out, open('circ.json', 'w'), ensure_ascii=False, indent=0)

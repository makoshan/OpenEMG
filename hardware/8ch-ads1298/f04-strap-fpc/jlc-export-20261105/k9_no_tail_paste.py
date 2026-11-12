"""K9 板上给尾端 17 个手焊盘加负的钢网余量：KiCad 里它们本来就没有 F.Paste，嘉立创导入后给所有贴片焊盘自动开钢网，要缩没。
0.6 mm 高的焊盘每边缩 0.31，开口就没了。只改给嘉立创用的 K9 中间板，KiCad 源板不动。
用法：python3 k9_no_tail_paste.py <K9板>"""
import re, sys
from pathlib import Path

p = Path(sys.argv[1]); t = p.read_text(encoding='utf8')
i = t.index('(footprint "FPC:TAIL17"')
m = re.search(r'(?m)^\t\(', t[i + 1:]); j = i + 1 + m.start() if m else len(t)
blk, n = re.subn(r'(\(pad "\d+" smd rect[\s\S]*?\(layers "F\.Cu" "F\.Mask"\))', r'\1\n\t\t\t(solder_paste_margin -0.31)', t[i:j])
assert n == 17, n
p.write_text(t[:i] + blk + t[j:], encoding='utf8')
print('尾焊盘加负钢网余量', n)

"""把 KiCad 10 的 .kicad_pcb 改成 KiCad 9 的网络写法，给嘉立创EDA 导入用：python3 tools/kicad10_to_9_nets.py <源板> <输出板>
2026-10-23 实测：KiCad 10（version 20260206）只写网络名 `(net "GND")`、没有网络编号表，嘉立创EDA 专业版按 KiCad 导入后
261 件、437 个过孔都在，但网络全空、走线 0 条；转成下面的写法后导入，226 个网、2853 段走线都在，焊盘网络逐个对上。
KiCad 9（version 20241229）的写法：文件头有编号表 `(net 1 "GND")`；焊盘 `(net 1 "GND")`；走线/过孔/圆弧/图形只写 `(net 1)`；
铺铜写 `(net 1)` 加 `(net_name "GND")`。按网络所在的最内层对象判断写法（封装里的铺铜也按铺铜写），别的不动。
输出只给嘉立创EDA 导入用，不要拿回 KiCad 改：KiCad 10 读这个 9 版文件会提示「Legacy zone fill strategy」，铺铜按旧规则重算。
改完从输出里的编号表反查：每处的编号、行内名字、net_name 都要和编号表一致，每类对象上每个网的次数要和源板一样。"""
import collections, re, sys

NET = re.compile(r'\(net "((?:[^"\\]|\\.)*)"\)')


def owners(lines):
    """每行所属的最内层对象名（按制表符缩进深度记开着的块）。"""
    stack, out = {}, []
    for line in lines:
        d = len(line) - len(line.lstrip('\t'))
        m = re.match(r'^\t*\((\w+)', line)
        out.append(stack.get(d - 1))
        if m:
            stack[d] = m.group(1)
            for k in [k for k in stack if k > d]:
                del stack[k]
    return out


def convert(text):
    assert re.search(r'^\(kicad_pcb\s*\n\s*\(version 2026', text), '不是 KiCad 10 板文件'
    names = list(dict.fromkeys(NET.findall(text)))
    num = {n: i + 1 for i, n in enumerate(names)}
    lines = text.split('\n'); own = owners(lines); before = collections.Counter(); out = []
    for line, o in zip(lines, own):
        hit = NET.search(line)
        if hit:
            n = hit.group(1); before[(o, n)] += 1
            ind = line[:len(line) - len(line.lstrip('\t'))]
            if o == 'pad':
                line = line.replace(hit.group(0), f'(net {num[n]} "{n}")')
            elif o == 'zone':
                line = line.replace(hit.group(0), f'(net {num[n]})') + f'\n{ind}(net_name "{n}")'
            else:
                line = line.replace(hit.group(0), f'(net {num[n]})')
        out.append(line)
    res = re.sub(r'\(version 2026\d+\)', '(version 20241229)', '\n'.join(out), count=1)
    table = '\n'.join(['\t(net 0 "")'] + [f'\t(net {i} "{n}")' for n, i in num.items()])
    i = res.index('\n\t(footprint')
    return res[:i] + '\n' + table + res[i:], before


def verify(res, before):
    """从输出自己的编号表反查（不用转换时内存里的表）。"""
    lines = res.split('\n')
    tab = {int(m.group(1)): m.group(2) for m in (re.match(r'^\t\(net (\d+) "((?:[^"\\]|\\.)*)"\)$', l) for l in lines) if m}
    assert tab.get(0) == '' and len(set(tab.values())) == len(tab), '编号表缺 0 号或有重名'
    back, bad = collections.Counter(), []
    own = owners(lines)
    for k, (line, o) in enumerate(zip(lines, own)):
        if re.match(r'^\t\(net \d+ ', line):
            continue
        for m in re.finditer(r'\(net (\d+)(?: "((?:[^"\\]|\\.)*)")?\)', line):
            n = int(m.group(1))
            if n not in tab:
                bad.append(f'行 {k + 1}：编号 {n} 不在表里'); continue
            if m.group(2) is not None and m.group(2) != tab[n]:
                bad.append(f'行 {k + 1}：名字 {m.group(2)} ≠ 表里 {tab[n]}')
            if o == 'zone':
                nn = re.match(r'^\t*\(net_name "((?:[^"\\]|\\.)*)"\)', lines[k + 1])
                if not nn or nn.group(1) != tab[n]:
                    bad.append(f'行 {k + 2}：铺铜 net_name 与编号 {n} 不符')
            back[(o, tab[n])] += 1
    if back != before:
        bad.append(f'回数不一致：{sorted((back - before).items())[:3]} / {sorted((before - back).items())[:3]}')
    return bad


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    text = open(src, encoding='utf-8').read()
    res, before = convert(text)
    bad = verify(res, before)
    # 阳性对照：输出编号表里 1、2 号互换名字，反查必须报错
    swapped = re.sub(r'^\t\(net 1 "([^"]*)"\)\n\t\(net 2 "([^"]*)"\)', lambda m: f'\t(net 1 "{m.group(2)}")\n\t(net 2 "{m.group(1)}")', res, count=1, flags=re.M)
    ctrl = verify(swapped, before)
    assert not bad, bad[:5]
    assert ctrl, '阳性对照没报错：反查不起作用'
    open(dst, 'w', encoding='utf-8').write(res)
    print(f'网络 {len(set(n for _, n in before))} 个；改写 {sum(before.values())} 处（{dict(collections.Counter(o for o, _ in before.elements()))}）；'
          f'按输出编号表反查一致；对照（表里 1、2 号互换）报 {len(ctrl)} 条')

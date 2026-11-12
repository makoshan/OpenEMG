# coding: utf-8
"""Btai1 小板原理图公共生成器：parts 字典（pins → nets）→ KiCad 原理图 + 网表 + ERC + 逐脚核对。

parts = {'U1': {'value':..., 'fp':..., 'lcsc':..., 'pins': {'1:NAME': 'NET', ...}}}，网络名 'NC' 表示悬空。
写法沿用 v12/compact-c01-8ch/button-clock-c05/button/build.py：方框符号 + 全局标签。
"""
import json, uuid, subprocess, sys, xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import shutil as _sh
CLI = _sh.which('kicad-cli') or '/opt/homebrew/bin/kicad-cli'
FX = '(effects (font (size 1 1)))'
q = lambda x: json.dumps(x, ensure_ascii=False)
pin_num = lambda k: k.split(':')[0]
pin_name = lambda k: k.split(':')[-1]


def write(out_dir, name, parts, extra=None, cols=7, row_pitch=63.5, paper='A3'):
    P = Path(out_dir); u = lambda n: str(uuid.uuid5(uuid.NAMESPACE_URL, f'mako/btai1/{name}/' + n))
    root = u('root'); defs = []; items = []
    for j, (ref, p) in enumerate(parts.items()):
        col, row = j % cols, j // cols
        # 坐标全部落在 1.27mm 格点上，避免 ERC 端点离格警告
        x = round(40.64 + col * 50.8, 2); y = round(30.48 + row * row_pitch, 2); h = (len(p['pins']) + 1) * 2.54
        pins_def = ''.join(f'(pin passive line (at -5.08 {-2.54*(i+1):.2f} 0) (length 5.08) (name {q(pin_name(k))} {FX}) (number "{pin_num(k)}" {FX}))'
                           for i, k in enumerate(p['pins']))
        defs.append(f'(symbol "BTAI1:{ref}" (pin_names (offset 1)) (in_bom yes) (on_board yes) '
                    f'(property "Reference" "{ref}" (at 0 5.08 0) {FX}) (property "Value" {q(p["value"])} (at 0 2.54 0) {FX}) '
                    f'(symbol "{ref}_0_1" (rectangle (start 0 0) (end 17.78 {-h:.2f}) (stroke (width .2) (type default)) (fill (type background)))) '
                    f'(symbol "{ref}_1_1" {pins_def}))')
        props = (f'(property "Reference" "{ref}" (at {x+8.89:.2f} {y-6.35:.2f} 0) {FX}) (property "Value" {q(p["value"])} (at {x+8.89:.2f} {y-3.81:.2f} 0) {FX}) '
                 f'(property "Footprint" {q(p["fp"])} (at {x} {y} 0) (effects (font (size 1 1)) (hide yes))) '
                 f'(property "LCSC" {q(p.get("lcsc") or "")} (at {x} {y} 0) (effects (font (size 1 1)) (hide yes)))')
        items.append(f'(symbol (lib_id "BTAI1:{ref}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {u(ref)}) {props} '
                     + ''.join(f'(pin "{pin_num(k)}" (uuid {u(ref+k)}))' for k in p['pins'])
                     + f'(instances (project "{name}" (path "/{root}" (reference "{ref}") (unit 1)))))')
        for i, (k, net) in enumerate(p['pins'].items()):
            yy = round(y + 2.54 * (i + 1), 2); xx = round(x - 5.08, 2)
            if net == 'NC':   # 悬空脚：打不连接标记
                items.append(f'(no_connect (at {xx} {yy}) (uuid {u(ref+k+"nc")}))')
            else:
                items.append(f'(wire (pts (xy {xx-7.62:.2f} {yy}) (xy {xx} {yy})) (stroke (width 0) (type default)) (uuid {u(ref+k+"w")})) '
                             f'(global_label "{net}" (shape input) (at {xx-7.62:.2f} {yy} 0) (effects (font (size 1 1)) (justify right)) (uuid {u(ref+k+"l")}))')
    (P / f'{name}.kicad_sch').write_text(f'(kicad_sch (version 20250114) (generator "mako") (uuid {root}) (paper "{paper}") (lib_symbols '
                                         + ''.join(defs) + ') ' + ''.join(items) + ' (sheet_instances (path "/" (page "1"))))')
    (P / 'BTAI1.kicad_sym').write_text('(kicad_symbol_lib (version 20250114) (generator "mako") ' + ''.join(d.replace('"BTAI1:', '"', 1) for d in defs) + ')')
    (P / 'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "BTAI1") (type "KiCad") (uri "${KIPRJMOD}/BTAI1.kicad_sym") (options "") (descr "BTAI1")))')
    (P / f'{name}.kicad_pro').write_text(json.dumps({'meta': {'filename': f'{name}.kicad_pro', 'version': 3}}, indent=2))
    (P / 'design.json').write_text(json.dumps({'parts': parts, **(extra or {})}, ensure_ascii=False, indent=1))
    subprocess.run([CLI, 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o', str(P / f'{name}.net.xml'), str(P / f'{name}.kicad_sch')], check=True, capture_output=True)
    subprocess.run([CLI, 'sch', 'erc', '--severity-all', '-o', str(P / 'erc.rpt'), str(P / f'{name}.kicad_sch')], capture_output=True)
    print(f'{name}：{len(parts)} 个器件；' + next(l.strip() for l in (P / 'erc.rpt').read_text().splitlines() if 'ERC messages' in l))


def check(design_json, net_xml):
    """网表逐脚核对：网表必须与 design.json 的 pins→nets 完全一致；NC 脚不能落进真实网络；真实网络至少 2 个脚。"""
    want = {(ref, pin_num(k)): net for ref, p in json.loads(Path(design_json).read_text())['parts'].items() for k, net in p['pins'].items()}
    got = {(node.get('ref'), node.get('pin')): n.get('name').lstrip('/') for n in ET.parse(net_xml).getroot().iter('net') for node in n.iter('node')}
    bad = []
    for key, net in sorted(want.items()):
        g = got.get(key)
        if net == 'NC':
            if g and not g.startswith('unconnected-'): bad.append(f'{key} 应悬空，实际 {g}')
        elif g != net: bad.append(f'{key} 应为 {net}，实际 {g}')
    bad += [f'网表多出 {k}' for k in got if k not in want]
    cnt = Counter(v for v in want.values() if v != 'NC')
    bad += [f'网络 {n} 只有 {c} 个脚' for n, c in cnt.items() if c < 2]
    print(f'核对 {len(want)} 个引脚、{len(cnt)} 个网络：' + ('通过' if not bad else f'{len(bad)} 处不一致'))
    for b in bad[:20]: print('  ', b)
    return not bad


if __name__ == '__main__':   # 用法：kisch.py design.json 网表.xml
    sys.exit(0 if check(sys.argv[1], sys.argv[2]) else 1)

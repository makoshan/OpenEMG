"""复用本机 EMG4 的逐脚分层原理图模式；输出可由原生 KiCad 导出网表的审阅源。"""
from pathlib import Path
import csv
import json
import uuid

P = Path(__file__).resolve().parent
q = lambda v: json.dumps(str(v), ensure_ascii=False)
u = lambda v: str(uuid.uuid5(uuid.NAMESPACE_URL, 'mako/v12/r01/'+v))
fx = '(effects (font (size 1 1)))'


def pin_type(part, n, name):
    ref = part['ref']
    if part['pins'][n] is None:
        return 'no_connect'
    if ref.startswith('#'):
        return 'power_out'
    if not ref.startswith('U'):
        return 'passive'
    if name in ('GND', 'EP', 'AVSS', 'AVSS1', 'DGND'):
        return 'power_in'
    if ref == 'U1':
        if name.startswith(('AVDD', 'DVDD')):
            return 'power_in'
        if n in ('24', '26', '28', '30', '55', '43', '47', '63'):
            return 'output'
        if n == '37':
            return 'tri_state'
        return 'input'
    if ref in ('U2', 'U3'):
        if n in ('1', '23', '24'):
            return 'power_in'
        if n in ('2', '11', '22'):
            return 'input'
        if n in ('12', '13', '25'):
            return 'power_in'
        a = 3 <= int(n) <= 10
        return 'input' if a == (ref == 'U2') else 'tri_state'
    if ref == 'U7':
        return {'10': 'power_in', '6': 'power_out', '3': 'power_in', '8': 'power_in',
                '1': 'input', '2': 'input', '4': 'input', '5': 'open_collector'}.get(n, 'passive')
    if ref == 'U9':
        return {'1': 'power_in', '2': 'power_in', '3': 'input', '5': 'power_out'}[n]
    if ref == 'U10':
        return {'2': 'input', '3': 'power_in', '4': 'output', '5': 'power_in'}[n]
    if ref == 'U12':
        return {'1': 'open_collector', '2': 'power_in', '3': 'input', '5': 'input', '6': 'power_in'}[n]
    raise ValueError((ref, n, name))


def main():
    d = json.loads((P/'design.json').read_text())
    parts = d['parts']
    for i, net in enumerate(['GND', 'VBAT', '3V3'], 1):
        parts.append(dict(ref=f'#FLG{i:02}', value='PWR_FLAG', pins={'1': net},
                          sym='PWR_FLAG', sheet='POWER', footprint='', annotation=True))
    pages = ['ADS', 'POWER', 'IF']+[f'CH{i}' for i in range(1, 9)]
    root = u('root')
    all_defs, root_items = [], []
    pin_manifest = []
    for pn, page in enumerate(pages, 2):
        sheet = u(page)
        path = f'/{root}/{sheet}'
        defs, items = [], []
        for idx, part in enumerate(x for x in parts if x['sheet'] == page):
            ref = part['ref']
            sname = ref.replace('#', '')
            lib = 'V12:'+sname
            if ref == 'U1':
                x, y = 48.26, 35.56
            elif page == 'ADS':
                x, y = 160.02+(idx % 4)*96.52, 35.56+(idx // 4)*30.48
            elif page == 'IF':
                x, y = 48.26+(idx % 5)*105.41, 35.56+(idx // 5)*88.9
            else:
                x, y = 48.26+(idx % 5)*105.41, 35.56+(idx // 5)*40.64
            names = d['pinnames'].get(part['sym'], {})
            pins = [dict(id=n, name=names.get(n, n), net=net,
                         type=pin_type(part, n, names.get(n, n))) for n, net in part['pins'].items()]
            h = (len(pins)+1)*2.54
            assert y+h < 407, (ref, page, y, h)
            annotation = part.get('annotation', False)
            yes = 'no' if annotation else 'yes'
            bom_yes = 'no' if annotation or ref.startswith('TP') else 'yes'
            definition = (f'(symbol {q(lib)} (pin_names (offset 1)) (in_bom {bom_yes}) (on_board {yes}) '
                f'(property "Reference" {q(ref)} (at 0 5.08 0) {fx}) '
                f'(property "Value" {q(part["value"])} (at 0 2.54 0) {fx}) '
                f'(symbol {q(sname+"_0_1")} (rectangle (start 0 0) (end 38.1 {-h:.4f}) '
                '(stroke (width 0.2) (type default)) (fill (type background)))) '
                f'(symbol {q(sname+"_1_1")} '+''.join(
                    f'(pin {v["type"]} line (at -5.08 {-2.54*(j+1):.4f} 0) (length 5.08) '
                    f'(name {q(v["name"])} {fx}) (number {q(v["id"])} {fx}))'
                    for j, v in enumerate(pins))+'))')
            defs.append(definition)
            all_defs.append(definition)
            items.append(f'(symbol (lib_id {q(lib)}) (at {x:.4f} {y:.4f} 0) (unit 1) '
                f'(in_bom {bom_yes}) (on_board {yes}) (dnp no) (uuid {u(ref)}) '
                f'(property "Reference" {q(ref)} (at {x+19.05:.4f} {y-6.35:.4f} 0) {fx}) '
                f'(property "Value" {q(part["value"])} (at {x+19.05:.4f} {y-3.81:.4f} 0) {fx}) '
                f'(property "Footprint" {q(part["footprint"])} (at {x:.4f} {y:.4f} 0) '
                '(effects (font (size 1 1)) (hide yes))) '+''.join(
                    f'(pin {q(v["id"])} (uuid {u(ref+v["id"])}))' for v in pins)+
                f'(instances (project "v12-r01" (path {q(path)} (reference {q(ref)}) (unit 1)))))')
            for j, v in enumerate(pins):
                xx, yy = x-5.08, y+2.54*(j+1)
                key = ref+'/'+v['id']
                if v['net'] is None:
                    items.append(f'(no_connect (at {xx:.4f} {yy:.4f}) (uuid {u(key+"nc")}))')
                else:
                    items.append(f'(wire (pts (xy {xx-7.62:.4f} {yy:.4f}) (xy {xx:.4f} {yy:.4f})) '
                        '(stroke (width 0) (type default)) '+f'(uuid {u(key+"wire")})) '
                        f'(global_label {q(v["net"])} (shape input) (at {xx-7.62:.4f} {yy:.4f} 0) '
                        f'(effects (font (size 1 1)) (justify left)) (uuid {u(key+"label")}))')
                pin_manifest.append(dict(ref=ref, **v))
        (P/f'{page}.kicad_sch').write_text(f'(kicad_sch (version 20250114) (generator "mako_v12") '
            f'(uuid {sheet}) (paper "A2") (title_block (title {q("V12-R01 / "+page)}) '
            '(comment 1 "OFF-BODY CANDIDATE - NOT RELEASED")) (lib_symbols '+''.join(defs)+') '+''.join(items)+')\n')
        x, y = 25+(pn-2) % 4*92, 35+(pn-2)//4*64
        root_items.append(f'(sheet (at {x} {y}) (size 78 40) (stroke (width 0.2) (type default)) '
            f'(fill (color 0 0 0 0)) (uuid {sheet}) (property "Sheetname" {q(page)} (at {x} {y-2} 0) {fx}) '
            f'(property "Sheetfile" {q(page+".kicad_sch")} (at {x} {y+42} 0) {fx}) '
            f'(instances (project "v12-r01" (path "/{root}" (page "{pn}")))))')
    (P/'v12-r01.kicad_sch').write_text(f'(kicad_sch (version 20250114) (generator "mako_v12") '
        f'(uuid {root}) (paper "A3") (title_block (title "MAKO V12-R01 / 8CH ADS1298") '
        '(comment 1 "OFF-BODY CANDIDATE - NOT RELEASED")) (lib_symbols) '+''.join(root_items)+
        f'(sheet_instances (path "/" (page "1"))))\n')
    (P/'V12.kicad_sym').write_text('(kicad_symbol_lib (version 20250114) (generator "mako_v12") '+
        ''.join(s.replace('"V12:', '"', 1) for s in all_defs)+')\n')
    (P/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "V12") (type "KiCad") '
        '(uri "${KIPRJMOD}/V12.kicad_sym") (options "") (descr "V12逐脚审核符号")))\n')
    (P/'schematic-pins.json').write_text(json.dumps(pin_manifest, ensure_ascii=False, indent=2)+'\n')
    for variant in ['S', 'Q']:
        with (P/f'BOM-{variant}.csv').open('w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['Reference', 'Value', 'LCSC', 'Footprint', 'Variant', 'Note'])
            for part in parts:
                if part.get('annotation'):
                    continue
                w.writerow([part['ref'], part.get('value_q', part['value']) if variant == 'Q' else part['value'],
                    part.get('lcsc_q', part['lcsc']) if variant == 'Q' else part['lcsc'],
                    part['footprint'], variant, part['note']])
    if not (P/'v12-r01.kicad_pro').exists():
        (P/'v12-r01.kicad_pro').write_text('{}\n')
    print('已生成11张功能页及总图；必须再运行原生ERC与独立网表比对。')


if __name__ == '__main__':
    main()

"""封装来自已核厂家图与本机 KiCad 库；两种 HotRod/WQFN 不用近似封装替代。"""
from pathlib import Path
import hashlib
import json
import math
import re

P = Path(__file__).resolve().parent
LIB = Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints')
CUSTOM = P/'V12Parts.pretty'


def rect(layer, x, y, w, h):
    return (f'(fp_rect (start {x-w/2:.4f} {y-h/2:.4f}) (end {x+w/2:.4f} {y+h/2:.4f}) '
            f'(stroke (width 0.05) (type default)) (fill none) (layer "{layer}"))')


def pad(n, x, y, w, h, paste=True, radius=.05):
    layers = '"F.Cu" "F.Mask"'+(' "F.Paste"' if paste else '')
    return (f'(pad "{n}" smd roundrect (at {x} {y}) (size {w} {h}) (layers {layers}) '
            f'(roundrect_rratio {min(.5, radius/min(w,h))}))')


def write_fp(name, body, w, h, description, body_size=None):
    CUSTOM.mkdir(exist_ok=True)
    text = (f'(footprint "{name}" (version 20241229) (generator "mako_v12") (layer "F.Cu") '
        f'(descr {json.dumps(description)}) (attr smd) '
        f'(property "Reference" "REF**" (at 0 {-h/2-1.5}) (layer "F.SilkS") (effects (font (size 1 1)(thickness .15)))) '
        f'(property "Value" "{name}" (at 0 {h/2+1.5}) (layer "F.Fab") (effects (font (size 1 1)(thickness .15)))) '
        +rect('F.Fab',0,0,*(body_size or (w,h)))+('' if name=='FTC201610S' else f'(fp_circle (center {(-.75 if name=="TI_RHL0024A" else -.55)} {(-2.3 if name=="TI_RHL0024A" else -1.25)}) (end {(-.60 if name=="TI_RHL0024A" else -.40)} {(-2.3 if name=="TI_RHL0024A" else -1.25)}) (stroke (width 0.08) (type default)) (fill solid) (layer "F.Fab"))')+rect('F.CrtYd',0,0,w+.6,h+.6)+''.join(body)+')\n')
    (CUSTOM/f'{name}.kicad_mod').write_text(text)


def main():
    bindings = {}
    def bind(key, footprint, source):
        bindings[key] = dict(footprint=footprint, source=source)
    for key, value in [('R0402','Resistor_SMD:R_0402_1005Metric'),
                       ('C0402','Capacitor_SMD:C_0402_1005Metric'),
                       ('C0603','Capacitor_SMD:C_0603_1608Metric'),
                       ('TESTPOINT','TestPoint:TestPoint_Pad_D1.0mm')]:
        bind(key, value, '继承原设计尺寸；KiCad10.0.6封装库，物料额定值另验')
    bind('U1','Package_QFP:TQFP-64_10x10mm_P0.5mm','TI ADS1298IPAGR / PAG0064A / ads1298.pdf')
    for n in range(1,18):
        bind(f'ESD{n}','Package_SON:Texas_DPY0002A_0.6x1mm_P0.65mm','TI ESD501DPYR / DPY0002A / esd501.pdf')
    for key in ['C20','C21']:
        bind(key,'Capacitor_SMD:C_0805_2012Metric','C109314 / 0805 / 原设计10V22uF；直流偏压有效电容仍待验证')
    for key in ['U9']:
        bind(key,'Package_TO_SOT_SMD:SOT-23-5','TI TPS7A2018PDBVR / DBV0005A')
    bind('Q1','Package_TO_SOT_SMD:SOT-23','AOS AO3400A / 1G 2S 3D')
    bind('D1','Diode_SMD:D_SOD-323','R+O B5819WS C7420331 / 物理1K2A；候选已转换原逻辑脚号')
    bind('U10','Package_TO_SOT_SMD:SOT-353_SC-70-5','TI SN74AUP1T14DCKR / DCK0005A / SCES802')
    bind('U12','Package_TO_SOT_SMD:SOT-23-6','TI TPS3808G33DBVR / DBV0006A')
    bind('J1','V12Parts:Samtec_TST-108-01-L-D','Samtec tst_c.pdf / 2x8 P2.54 / 键控垂直，配套线束待确认')
    bind('J2','Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical','JST ePH.pdf / B2B-PH-K-S + PHR-2')
    bind('J3','Connector_Molex:Molex_Micro-Fit_3.0_43045-2012_2x10_P3.00mm_Vertical',
         'Molex 43045-2012 + 43025-2000；1–17原逻辑，18–20NC')

    # DLA0010A：右侧开关/电源焊盘不是等宽矩形，也不存在第11脚散热盘。
    pads = [pad(i,-.9,-1+(i-1)*.5,.6,.25) for i in range(1,6)]
    pads += [pad(i,.75,y,.9,.25) for i,y in [(10,-1),(9,-.5),(7,.5),(6,1)]]
    pads += [pad(8,.55,0,1.3,.25)]
    write_fp('TI_DLA0010A',pads,2.4,3.1,'TI TPS63802 DLA0010A 原厂推荐焊盘；无EP', (2.0,3.0))
    bind('U7','V12Parts:TI_DLA0010A','TI tps63802.pdf p36 DLA0010A 4223750/D 03/2019')

    # RHL0024A：25号接地盘包含上下窄舌；四个舌与主体同网且必须保持真实外形。
    pads = [pad(i,x,y,.24,.6) for i,x,y in [(1,-.75,-2.65),(24,.75,-2.65),
                                                   (12,-.75,2.65),(13,.75,2.65)]]
    pads += [pad(i,-1.65,-2.25+(i-2)*.5,.6,.24) for i in range(2,12)]
    pads += [pad(23-i,1.65,-2.25+i*.5,.6,.24) for i in range(10)]
    # 同号矩形内部重叠10微米，外轮廓不变；仅边相切会被KiCad判成断开。
    pads += [pad(25,0,0,2.05,4.05,False)]
    for sign in [-1,1]:
        pads.append(pad(25,0,sign*2.22,.75,.41,False,0))
        for x in [-.275,.275]:
            pads.append(pad(25,x,sign*2.6825,.2,.535,False,0))
    # 复刻TI第38页钢网示例：6个0.92×1.14窗口，加上下U形窗。
    for x in [-.56,.56]:
        for y in [-1.34,0,1.34]:
            pads.append(f'(pad "" smd roundrect (at {x} {y}) (size .92 1.14) (layers "F.Paste") (roundrect_rratio {0.05/.92}))')
    outline=[(-.375,-2.95),(-.175,-2.95),(-.175,-2.425),(.175,-2.425),(.175,-2.95),(.375,-2.95),(.375,-2.11),(-.375,-2.11)]
    rounded=[]
    for i,(x,y) in enumerate(outline):
        a=outline[i-1];c=outline[(i+1)%len(outline)]
        u=((x-a[0])/math.dist(a,(x,y)),(y-a[1])/math.dist(a,(x,y)))
        v=((c[0]-x)/math.dist(c,(x,y)),(c[1]-y)/math.dist(c,(x,y)))
        if u[0]*v[1]-u[1]*v[0]<0:
            rounded.append((x,y));continue
        start=(x-u[0]*.05,y-u[1]*.05);center=(start[0]+v[0]*.05,start[1]+v[1]*.05)
        angle=math.atan2(start[1]-center[1],start[0]-center[0])
        rounded += [(center[0]+.05*math.cos(angle+j*math.pi/16),center[1]+.05*math.sin(angle+j*math.pi/16)) for j in range(9)]
    for sign in [1,-1]:
        pads.append('(fp_poly (pts '+''.join(f'(xy {x:.6f} {sign*y:.6f})' for x,y in rounded)+') (stroke (width 0) (type solid)) (fill solid) (layer "F.Paste"))')
    write_fp('TI_RHL0024A',pads,3.9,5.9,'TI RHL0024A；钢网按第38页0.125mm示例，几何覆盖率约76.9%，生产工艺待确认',(3.5,5.5))
    for key in ['U2','U3']:
        bind(key,'V12Parts:TI_RHL0024A','TI sn74axc8t245.pdf p37 RHL0024A 4225250/C 06/2026')

    write_fp('FTC201610S', [pad(1,-.65,0,.8,1.7),pad(2,.65,0,.8,1.7)],2.1,1.7,
             '长江FTC201610S系列：厂家推荐外宽2.10、内隙0.50、焊盘高1.70',(2.0,1.6))
    bind('L1','V12Parts:FTC201610S','FTC201610SR47MBCA C5832340；厂家FT_Catalouge p5')
    # 用同针距库作为起点，外形按具体 TST-108 原厂尺寸收口；焊盘不凭外形去猜针号。
    src=LIB/'Connector_IDC.pretty/IDC-Header_2x08_P2.54mm_Vertical.kicad_mod'
    text=src.read_text().replace('IDC-Header_2x08_P2.54mm_Vertical','Samtec_TST-108-01-L-D')
    # 原库主体27.98×8.90与原厂27.94×8.89差0.04/0.01；保留略大的机械包络作候选保守检查。
    text=text.replace('(descr ', '(descr "Samtec TST-108-01-L-D 候选；原厂27.94x8.89，库包络略大；孔公差待厂商核。")\n (tags ' ,1)
    (CUSTOM/'Samtec_TST-108-01-L-D.kicad_mod').write_text(text)
    (P/'footprints.json').write_text(json.dumps(bindings,ensure_ascii=False,indent=2)+'\n')
    # 将实际使用的库文件复制到项目，防止另一台电脑换库后悄悄换了焊盘。
    manifest={}
    for entry in bindings.values():
        lib,name=entry['footprint'].split(':')
        target=P/(lib+'.pretty')/(name+'.kicad_mod')
        if lib!='V12Parts':
            source=LIB/(lib+'.pretty')/(name+'.kicad_mod')
            assert source.is_file(),source
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(source.read_bytes())
        target.write_text(target.read_text().replace('(layer "F.SilkS")','(layer "F.Fab")').replace('(layer "B.SilkS")','(layer "B.Fab")'))
        manifest[str(target.relative_to(P))]=hashlib.sha256(target.read_bytes()).hexdigest()
    libs=sorted({entry['footprint'].split(':')[0] for entry in bindings.values()})
    (P/'fp-lib-table').write_text('(fp_lib_table (version 7) '+''.join(
        f'(lib (name "{lib}") (type "KiCad") (uri "${{KIPRJMOD}}/{lib}.pretty") (options "") (descr "V12已钉住封装"))'
        for lib in libs)+')\n')
    (P/'footprint-hashes.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('封装映射及本地库已生成；自定义焊盘仍须独立复核。')


if __name__ == '__main__':
    main()

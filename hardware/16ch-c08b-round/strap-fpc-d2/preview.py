"""D2 PNG 预览：python3 preview.py（系统 python3 即可；要 kicad-cli 和 ImageMagick 的 magick）。
kicad-cli 按整页（板坐标 = 页坐标，mm）导出 SVG，再按板坐标裁切成 PNG（kicad-cli 默认配色：F.Cu 红、B.Cu 蓝、外形灰）。
- preview-a/b.png：全貌（外形 + F/B 面走线）；preview-a-north.png：北支两岛 + 胶囊底；
- preview-island-a-ch5 / b-ch9.png：岛特写（含 F.Mask 开窗、User.2 的 PI 补强片）；
- preview-capsule-a/b/ab.png：胶囊段特写（11-11 胶囊底 6 个 Φ6.5 SMD 焊盘、B 面串阻、A 片 Φ6.9 EB2 让位孔；ab 为两片叠看）；
- preview-slot.png：A、B 两片叠在一起（正片叠底），B 垫在 A 背后；preview-a-gnd.png：A 带根和南岛间的 In1.Cu 网格地。"""
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
KC = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
CU = 'Edge.Cuts,F.Cu,B.Cu'
VIEWS = {                                   # 文件名: (片, 层, (x0, y0, x1, y1) 板坐标 mm, dpi)
    'preview-a.png': ('a', CU, (10.0, 36.0, 118.5, 64.0), 500),
    'preview-b.png': ('b', CU, (31.5, 36.0, 182.5, 64.0), 450),
    'preview-a-north.png': ('a', CU + ',F.Mask', (10.0, 36.0, 76.0, 64.0), 800),
    'preview-island-a-ch5.png': ('a', CU + ',F.Mask,User.2', (85.5, 36.0, 99.0, 64.0), 1500),
    'preview-island-b-ch9.png': ('b', CU + ',F.Mask,User.2', (115.5, 36.0, 131.0, 64.0), 1500),
    'preview-slot.png': ('ab', CU, (72.0, 36.0, 126.0, 64.0), 900),
    'preview-capsule-a.png': ('a', CU + ',F.Mask', (38.0, 36.0, 76.0, 64.0), 1000),
    'preview-capsule-b.png': ('b', CU + ',F.Mask', (38.0, 36.0, 76.0, 64.0), 1000),
    'preview-capsule-ab.png': ('ab', CU, (38.0, 36.0, 76.0, 64.0), 1000),
    'preview-a-gnd.png': ('a', 'Edge.Cuts,In1.Cu', (74.0, 36.0, 104.0, 64.0), 1200),
}


def svg(piece, layers, tmp):
    out = tmp / f'{piece}-{abs(hash(layers))}.svg'
    if not out.exists():
        subprocess.run([KC, 'pcb', 'export', 'svg', '--layers', layers, '--mode-single', '--exclude-drawing-sheet',
                        '--page-size-mode', '1', '-o', str(out), str(HERE / f'strap-{piece}.kicad_pcb')], check=True, capture_output=True)
    return out


def crop(piece, layers, box, dpi, tmp, dst):
    x0, y0, x1, y1 = box
    s = dpi / 25.4
    geo = f'{round((x1 - x0) * s)}x{round((y1 - y0) * s)}+{round(x0 * s)}+{round(y0 * s)}'
    subprocess.run(['magick', '-density', str(dpi), '-background', 'white', str(svg(piece, layers, tmp)), '-flatten', '-crop', geo, '+repage', str(dst)],
                   check=True, capture_output=True)


def main():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        for name, (piece, layers, box, dpi) in VIEWS.items():
            if piece == 'ab':
                crop('a', layers, box, dpi, tmp, tmp / 'sa.png')
                crop('b', layers, box, dpi, tmp, tmp / 'sb.png')
                subprocess.run(['magick', str(tmp / 'sa.png'), str(tmp / 'sb.png'), '-compose', 'multiply', '-composite', str(HERE / name)],
                               check=True, capture_output=True)
            else:
                crop(piece, layers, box, dpi, tmp, HERE / name)
            print(name)
    for prl in HERE.glob('*.kicad_prl'):
        prl.unlink()


if __name__ == '__main__':
    sys.exit(main())

"""R14 PNG 预览：python3 preview.py（系统 python3 即可；要 kicad-cli 和 ImageMagick 的 magick）。
kicad-cli 按整页（板坐标 = 页坐标，mm）导出 SVG，再按板坐标裁切成 PNG（kicad-cli 默认配色：F.Cu 红、B.Cu 蓝、外形灰）。
- preview-a/b.png：全貌（外形 + F/B 面走线）；preview-a-band / b-band / b-islands：并行段与岛的局部放大；
- preview-slot.png：A、B 两片按同一坐标叠在一起（正片叠底），看同一 TPU 槽里两片并排；
- preview-a-stiffener.png：A 南岛 CH5 的 B 面补强外形（User.2）与触点、串阻；preview-a-gnd.png：A 出盒带和 A 桥 1 的 In1.Cu 网格地。"""
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
KC = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
CU = 'Edge.Cuts,F.Cu,B.Cu'
VIEWS = {                                   # 文件名: (片, 层, (x0, y0, x1, y1) 板坐标 mm, dpi)
    'preview-a.png': ('a', CU, (11.5, 36.0, 118.5, 64.0), 600),
    'preview-b.png': ('b', CU, (31.5, 38.5, 182.5, 61.5), 600),
    'preview-a-band.png': ('a', CU, (66.0, 47.0, 100.0, 61.5), 1500),
    'preview-b-band.png': ('b', CU, (62.0, 41.5, 100.0, 55.5), 1500),
    'preview-b-islands.png': ('b', CU, (114.0, 38.5, 150.0, 61.5), 1200),
    'preview-slot.png': ('ab', CU, (72.0, 38.5, 120.0, 61.5), 1000),
    'preview-a-stiffener.png': ('a', 'Edge.Cuts,B.Cu,User.2', (85.5, 38.5, 94.5, 61.5), 1500),
    'preview-a-gnd.png': ('a', 'Edge.Cuts,In1.Cu', (74.0, 38.5, 96.0, 61.5), 1500),
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

"""D2-8CH PNG 预览：python3 preview.py（要 kicad-cli 和 ImageMagick magick）。"""
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
KC = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
PCB = HERE / 'strap-d2-8ch.kicad_pcb'
CU = 'Edge.Cuts,F.Cu,B.Cu'
VIEWS = {
    'preview-d2-8ch.png': (CU, (10.0, 36.0, 118.5, 64.0), 500),
    'preview-capsule-8ch.png': (CU + ',F.Mask', (38.0, 36.0, 76.0, 64.0), 1000),
    'preview-island-ch5.png': (CU + ',F.Mask,User.2', (85.5, 36.0, 99.0, 64.0), 1500),
}


def main():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        for name, (layers, (x0, y0, x1, y1), dpi) in VIEWS.items():
            svg = tmp / f'{abs(hash(layers))}.svg'
            if not svg.exists():
                subprocess.run([KC, 'pcb', 'export', 'svg', '--layers', layers, '--mode-single', '--exclude-drawing-sheet',
                                '--page-size-mode', '1', '-o', str(svg), str(PCB)], check=True, capture_output=True)
            s = dpi / 25.4
            geo = f'{round((x1 - x0) * s)}x{round((y1 - y0) * s)}+{round(x0 * s)}+{round(y0 * s)}'
            subprocess.run(['magick', '-density', str(dpi), '-background', 'white', str(svg), '-flatten', '-crop', geo, '+repage',
                            str(HERE / name)], check=True, capture_output=True)
            print(name)
    for prl in HERE.glob('*.kicad_prl'):
        prl.unlink()


if __name__ == '__main__':
    sys.exit(main())

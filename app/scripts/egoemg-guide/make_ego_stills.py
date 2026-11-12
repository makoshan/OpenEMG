"""EgoEMG 六手势示范静图：external-reference-stills/ 的 codex 生图（已按 EgoEMG 动捕核过）
→ 和现有示范同规格 400×400、白线透明底的 public/images/emg8-meta/ego_*-first.png。唤起复用 middle_pinch-first.png。
运行：python3 app/scripts/egoemg-guide/make_ego_stills.py（需要 Pillow）"""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SRC = ROOT / 'design' / 'egoemg-gestures-20261016' / 'codex'
OUT = ROOT / 'app' / 'public' / 'images' / 'emg8-meta'
NAMES = ['rest', 'thumb_slide', 'index_bow', 'ring_thumb', 'claw5']

spec = importlib.util.spec_from_file_location('seal', HERE.parent / 'seal-anim' / 'make_seal_anims.py')
seal = importlib.util.module_from_spec(spec); spec.loader.exec_module(seal)   # 复用 white_on_clear：亮度当不透明度

for n in NAMES:
    im = seal.white_on_clear(SRC / f'{n}.png')
    assert im.size == (400, 400) and im.getchannel('A').getextrema()[1] > 200, n   # 线条要看得见
    assert im.getchannel('A').getpixel((3, 3)) == 0, n                              # 角落是透明底
    im.save(OUT / f'ego_{n}-first.png')
    print(OUT / f'ego_{n}-first.png')

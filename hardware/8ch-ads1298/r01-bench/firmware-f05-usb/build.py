"""F05-USB 构建：把 F05 的 ADS 驱动（钉哈希）+ 豁免锁头文件 + 本目录的 USB 主程序拼到 .pio/stage 再编译。
firmware-f05 一个字节都不改。用法：python build.py --pio <pio路径> [--toolchain 包规格]"""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess, sys

HERE = Path(__file__).resolve().parent
F05 = HERE.parent / 'firmware-f05'
sys.path.insert(0, str(HERE.parent / 'firmware-f05-waiver'))
import build as waiver  # noqa: E402  复用豁免版的锁头文件与说明，两边口径一致

# 从 F05 借用的文件及其哈希：任何一个变了就停，重新审查后再更新
BORROWED = {
    'src/ads1298.cpp': None, 'src/ads1298.h': None, 'src/capture_guard.h': None,
    'src/timebase_board.h': None, 'src/timebase.h': None,
    'verify_board.py': None, 'sdk_patch.py': None,
}
PINNED_FILE = HERE / 'f05_pins.json'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def stage(toolchain=None):
    pins = json.loads(PINNED_FILE.read_text())
    for rel in BORROWED:
        if sha(F05 / rel) != pins[rel]:
            raise SystemExit(f'firmware-f05/{rel} 已变，先审查再更新 f05_pins.json')
    out = HERE / '.pio' / 'stage'
    shutil.rmtree(out, ignore_errors=True)
    (out / 'src').mkdir(parents=True)
    for rel in BORROWED:
        shutil.copy2(F05 / rel, out / rel)
    for p in (HERE / 'src').iterdir():
        shutil.copy2(p, out / 'src' / p.name)
    (out / 'src/bench_release.h').write_text(waiver.WAIVER_HEADER)
    ini = (HERE / 'platformio.ini').read_text()
    if toolchain:
        if ini.count('platform_packages =\n') != 1:
            raise SystemExit('platformio.ini 结构变了')
        ini = ini.replace('platform_packages =\n', f'platform_packages =\n    {toolchain}\n')
    (out / 'platformio.ini').write_text(ini)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--env', default='usb_2k_spi2')
    ap.add_argument('--pio', default='pio')
    ap.add_argument('--toolchain')
    a = ap.parse_args()
    out = stage(a.toolchain)
    subprocess.run([a.pio, 'run', '-d', str(out), '-e', a.env], check=True)
    build = out / '.pio' / 'build' / a.env
    meta = json.loads((build / 'generated' / 'build-inputs.json').read_text())
    if waiver.BASIS.encode() not in waiver.hex_payload(build / 'firmware.hex'):
        raise SystemExit('烧录镜像里没有豁免标注，停止')
    art = HERE / 'artifacts'
    art.mkdir(exist_ok=True)
    stem = f'f05-usb-{a.env}-{meta["build_id"]}'
    shutil.copy2(build / 'firmware.hex', art / f'{stem}.hex')
    shutil.copy2(build / 'firmware.zip', art / f'{stem}-dfu.zip')
    manifest = dict(profile='F05_USB_BENCH', transport='usb_cdc', off_body_only=True, bench_basis=waiver.BASIS,
                    env=a.env, build_id=meta['build_id'], toolchain=a.toolchain or 'platformio.ini 默认',
                    f05_pins=json.loads(PINNED_FILE.read_text()), hex_sha256=sha(art / f'{stem}.hex'), dfu_sha256=sha(art / f'{stem}-dfu.zip'))
    (art / f'{stem}.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

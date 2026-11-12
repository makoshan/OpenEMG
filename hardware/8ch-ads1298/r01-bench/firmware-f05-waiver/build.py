"""F05 离体台架豁免版构建（2026-10-21 Mako 批准方案 B）。

firmware-f05 一个字节都不改（C05P/F05C 共用它的 src，CI 也禁止改）。本脚本：
1. 把 firmware-f05 的工程文件复制到 .pio/stage；main.cpp、bench_release.h 先核 sha256（F05 一变就停，重新审查）；
2. 在副本里换掉 bench_release.h：解锁，POR 等 5s、参考等 1s（远大于数据手册最小值，均未实测）；
3. 副本 main.cpp 的元数据加 "bench_basis"，如实标注“豁免、未实测”；
4. 编译并把 hex/DFU 包与清单放到 artifacts/（镜像只留本地，不入库）。
仅离体芯片内部测试用，不上人体。用法：python build.py [--env ads_2k] [--pio pio路径] [--toolchain 包规格]
"""
from pathlib import Path
import argparse, hashlib, json, os, shutil, subprocess, sys

HERE = Path(__file__).resolve().parent
F05 = HERE.parent / 'firmware-f05'
# 复制进副本的全部 F05 文件（3 个工程文件 + src/*）合起来的哈希：任何一个变了都停，
# 包括 ads1298.cpp 里的锁门和等待逻辑。算法见 bundle_sha()。
F05_BUNDLE_SHA256 = '80cb9cb2c2837c0ea9dd2d78b0d42b0a7c57e11ec7cb0acdd53cf5793e89037f'
PINNED = {
    'src/main.cpp': '12afcd92fa669c12944071b31a3402b8528c043d0a71754d558ec88da703a9e8',
    'src/bench_release.h': '553302834625dda972486aa7ff38d91040ad7cf04315f9ff2f79d807e32571e3',
}
BASIS = 'waived_by_Mako_2026-10-21_not_measured'
WAIVER_HEADER = f'''#pragma once
// F05 离体台架豁免版（firmware-f05-waiver/build.py 生成，不是 firmware-f05 原文件）。
// 2026-10-21 Mako 批准方案 B：VCAP1 与参考稳定时间未实测，用保守等待放行，仅离体芯片内部测试，不上人体。
#define MAKO_BENCH_MEASURED 1
#define MAKO_BENCH_BASIS "{BASIS}"
#define MAKO_BENCH_POR_US 5000000u
#define MAKO_BENCH_REFERENCE_US 1000000u
'''
META_ANCHOR = ('\\"bench_measured\\":%s,\\"protocol\\":1,', '\\"bench_measured\\":%s,\\"bench_basis\\":\\"%s\\",\\"protocol\\":1,')
ARG_ANCHOR = ('MAKO_BENCH_MEASURED?"true":"false",MAKO_V12_IMU_ENABLED', 'MAKO_BENCH_MEASURED?"true":"false",MAKO_BENCH_BASIS,MAKO_V12_IMU_ENABLED')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def bundle_files():
    return [F05 / n for n in ('platformio.ini', 'verify_board.py', 'sdk_patch.py')] + \
        sorted(p for p in (F05 / 'src').iterdir() if p.is_file())


def bundle_sha():
    # 与 shell 写法一致：每行“哈希  相对路径”，按路径排序后整体再取 sha256
    lines = sorted(f'{sha(p)}  {p.relative_to(F05)}\n' for p in bundle_files())
    lines.sort(key=lambda l: l.split('  ', 1)[1])
    return hashlib.sha256(''.join(lines).encode()).hexdigest()


def hex_payload(path):
    # 解析 Intel HEX，只取会烧进芯片的数据字节，证明标注真的在镜像里
    out = bytearray()
    for line in path.read_text().split():
        b = bytes.fromhex(line[1:])
        if b[3] == 0:
            out += b[4:4 + b[0]]
    return bytes(out)


def stage(toolchain=None):
    if bundle_sha() != F05_BUNDLE_SHA256:
        raise SystemExit('firmware-f05 有文件变了，先重新审查豁免补丁再更新 F05_BUNDLE_SHA256')
    for rel, want in PINNED.items():
        if sha(F05 / rel) != want:
            raise SystemExit(f'firmware-f05/{rel} 已变（{sha(F05 / rel)[:12]}），先重新审查豁免补丁再更新哈希')
    out = HERE / '.pio' / 'stage'
    shutil.rmtree(out, ignore_errors=True)
    (out / 'src').mkdir(parents=True)
    for name in ('platformio.ini', 'verify_board.py', 'sdk_patch.py'):
        shutil.copy2(F05 / name, out / name)
    for p in (F05 / 'src').iterdir():
        if p.is_file():
            shutil.copy2(p, out / 'src' / p.name)
    (out / 'src/bench_release.h').write_text(WAIVER_HEADER)
    main = (out / 'src/main.cpp').read_text()
    for old, new in (META_ANCHOR, ARG_ANCHOR):
        if main.count(old) != 1:
            raise SystemExit('main.cpp 元数据锚点不是正好一处，停止')
        main = main.replace(old, new)
    (out / 'src/main.cpp').write_text(main)
    if toolchain:  # 本机全局工具链是 x86 时，用原生 arm64 工具链覆盖（只影响副本）
        ini = (out / 'platformio.ini').read_text()
        if ini.count('platform_packages =\n') != 1:
            raise SystemExit('platformio.ini 结构变了，停止')
        (out / 'platformio.ini').write_text(ini.replace('platform_packages =\n', f'platform_packages =\n    {toolchain}\n'))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--env', default='ads_2k', choices=['ads_2k', 'ads_4k', 'ads_2k_spi1', 'ads_4k_spi1'])
    ap.add_argument('--pio', default='pio')
    ap.add_argument('--toolchain')
    a = ap.parse_args()
    out = stage(a.toolchain)
    subprocess.run([a.pio, 'run', '-d', str(out), '-e', a.env], check=True)
    build = out / '.pio' / 'build' / a.env
    meta = json.loads((build / 'generated' / 'build-inputs.json').read_text())
    if BASIS.encode() not in hex_payload(build / 'firmware.hex'):
        raise SystemExit('烧录镜像里没有豁免标注，停止')
    art = HERE / 'artifacts'
    art.mkdir(exist_ok=True)
    stem = f'f05-waiver-{a.env}-{meta["build_id"]}'
    shutil.copy2(build / 'firmware.hex', art / f'{stem}.hex')
    shutil.copy2(build / 'firmware.zip', art / f'{stem}-dfu.zip')
    manifest = dict(profile='F05_ADS_BENCH_WAIVED', bench_basis=BASIS, env=a.env, build_id=meta['build_id'],
                    por_wait_us=5000000, reference_wait_us=1000000, toolchain=a.toolchain or 'platformio.ini 默认',
                    f05_pinned=PINNED, f05_bundle_sha256=F05_BUNDLE_SHA256, hex_sha256=sha(art / f'{stem}.hex'), dfu_sha256=sha(art / f'{stem}-dfu.zip'))
    (art / f'{stem}.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

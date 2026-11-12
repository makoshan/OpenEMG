"""R01 一镜像两通道（2026-10-24 Mako：不再为换模式频繁刷机）。

不重写采样代码，把两份已实测过的程序原样拼进同一个镜像：
- firmware-f05-ble-dout 的暂存 main.cpp → src/ble_app.cpp（setup/loop 改名 ble_setup/ble_loop）；
- firmware-f05-usb 的暂存 main.cpp → src/usb_app.cpp（setup/loop 改名 usb_setup/usb_loop）；
- src/main.cpp（本目录 src/dispatch.cpp）开机看 VBUS：插着 USB 走 USB 串口，只接电池走蓝牙；运行中 VBUS 一变就整片复位。
两边各自的命令与安全判据不变：USB 侧只有 TST1/SHT1/PWR1/DIAG 等离体命令；蓝牙侧检测到 USB 拒绝开始。
共享的 ADS 驱动等文件两边必须逐字节相同，否则停。镜像只留本地 artifacts/。
TI 计划 S3+S4 的补丁（bench_patch.py）也在这里打：寄存器快照（蓝牙状态 v3、USB diag:8）、可选的 LOF1。
用法：python build.py --pio <pio路径> [--toolchain 包规格] [--loff]
  --loff：认 LOF1（外部输入 + RLD + 直流导联检测）。只离体：SINGLE-FAULT-R01.md 的前提是导联电流为 0。
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json, os, re, shutil, subprocess, sys

HERE = Path(__file__).resolve().parent
ENV = 'ads_2k'
# 进右腿驱动（RLD）平均的通道：bit0=CH1 … bit7=CH8，同时写 RLD_SENSP/RLD_SENSN。
# R01 人体只接 CH1；F05 原值 0xFF 会把 7 路悬空输入（经 10M+10M 接地）一起平均，把 RLD 拉偏（2026-10-25）。
RLD_SENS = 0x01
RLD_OLD = 'if(rld)regs[0xd]=regs[0xe]=0xff; // 8 路 P/N 都进 RLD 平均；PD_RLD 仍为 0，放大器未开。'  # 蓝牙版的 2 kHz、SPI 2 MHz 档；USB 版 usb_2k_spi2 同为 2 kHz、2 MHz
EXR1_LINE = '      else if (!strcmp(line, "EXR1")) start_req = 5;  // 与 F05 同名：外部输入+RLD：只接信号发生器做频响/串扰（2026-10-22 Mako 要求）；互锁失效时绝不接人体\n'
SHARED = ('ads1298.cpp', 'ads1298.h', 'capture_guard.h', 'timebase_board.h', 'timebase.h', 'bench_release.h')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


bench = load('r01_bench_patch', HERE / 'bench_patch.py')  # TI 计划 S3+S4 的补丁


def rename_entry(text, prefix):
    # 只认行首的 void setup() / void loop()，各必须正好一处
    for fn in ('setup', 'loop'):
        text, n = re.subn(rf'^void {fn}\(\)', f'void {prefix}_{fn}()', text, flags=re.M)
        if n != 1:
            raise SystemExit(f'{prefix} 的 {fn}() 不是正好一处，停止')
    # 两边都有 struct BoardHal：同名类的成员函数是弱符号，链接器会静默只留一份（2026-10-24 复核抓到 USB 模式跑了蓝牙版 HAL）
    return re.sub(r'\bBoardHal\b', f'{prefix.capitalize()}BoardHal', text)


def shared_symbols(nm, build):
    # 两个程序的目标文件里，凡是双方都定义的外部/弱/vtable 符号都会被链接器合并，必须为空
    def syms(name):
        out = subprocess.run([nm, '--defined-only', str(build / 'src' / name)], check=True, capture_output=True, text=True).stdout
        return {f[2] for f in (l.split() for l in out.splitlines()) if len(f) == 3 and f[1].isupper()}
    return sorted(syms('ble_app.cpp.o') & syms('usb_app.cpp.o'))


def stage(toolchain=None, loff=False):
    ble = load('r01_ble_build', HERE.parent / 'firmware-f05-ble-dout' / 'build.py')
    ble_src = ble.stage(toolchain)
    sys.path.insert(0, str(HERE.parent / 'firmware-f05-waiver'))  # USB 版里 import build 指豁免版
    usb = load('r01_usb_build', HERE.parent / 'firmware-f05-usb' / 'build.py')
    usb_src = usb.stage(toolchain)
    for name in SHARED:
        a, b = (ble_src / 'src' / name).read_bytes(), (usb_src / 'src' / name).read_bytes()
        if a != b:
            raise SystemExit(f'两版共享文件 {name} 不一致，停止')
    out = HERE / '.pio' / 'stage'
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(ble_src, out, ignore=shutil.ignore_patterns('.pio'))
    main = out / 'src' / 'main.cpp'
    (out / 'src' / 'ble_app.cpp').write_text(rename_entry(main.read_text(), 'ble'))
    usb_text = rename_entry((usb_src / 'src' / 'main.cpp').read_text(), 'usb')
    # 插 USB 不开任何外部输入：去掉 F05-USB 的 EXR1（J3 外部输入+RLD，原为 10-22 接信号发生器用）；外部输入只走电池+蓝牙
    if usb_text.count(EXR1_LINE) != 1:
        raise SystemExit('USB 程序的 EXR1 命令行变了，停止')
    (out / 'src' / 'usb_app.cpp').write_text(usb_text.replace(EXR1_LINE, ''))
    shutil.copy2(usb_src / 'src' / 'usb_frame.h', out / 'src' / 'usb_frame.h')
    shutil.copy2(HERE / 'src' / 'dispatch.cpp', main)
    # 共享 ADS 驱动只在本镜像的暂存副本里改 RLD 通道，firmware-f05 原文件不动（上面已核两版逐字节相同）
    ads = out / 'src' / 'ads1298.cpp'
    text = ads.read_text()
    if text.count(RLD_OLD) != 1:
        raise SystemExit('ads1298.cpp 的 RLD 通道行变了，停止')
    ads.write_text(text.replace(RLD_OLD, f'if(rld)regs[0xd]=regs[0xe]=0x{RLD_SENS:02x}; // R01 双通道镜像：只让已接电极的通道进 RLD 平均（firmware-r01-dual/build.py 的 RLD_SENS）'))
    # SPI 写死 2 MHz：蓝牙半边默认就是 2 MHz，USB 半边默认 1 MHz，DOUT 代 DRDY 读帧在 1 MHz 下太紧（见 F05-USB README）
    ini = out / 'platformio.ini'
    old = '[env:ads_2k]\nbuild_flags = ${env.build_flags} -DMAKO_V12_FS=2000\n'
    if ini.read_text().count(old) != 1:
        raise SystemExit('蓝牙版 platformio.ini 的 ads_2k 段变了，停止')
    ini.write_text(ini.read_text().replace(old, old.rstrip('\n') + ' -DMAKO_V12_SPI_HZ=2000000\n'))
    bench.apply(out, loff)  # TI 计划 S3+S4
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pio', default='pio')
    ap.add_argument('--toolchain')
    ap.add_argument('--loff', action='store_true', help='认 LOF1（直流导联检测），只离体')
    a = ap.parse_args()
    out = stage(a.toolchain, a.loff)
    subprocess.run([a.pio, 'run', '-d', str(out), '-e', ENV], check=True)
    build = out / '.pio' / 'build' / ENV
    meta = json.loads((build / 'generated' / 'build-inputs.json').read_text())
    core = Path(os.environ.get('PLATFORMIO_CORE_DIR', Path.home() / '.platformio'))
    nm = core / 'packages' / 'toolchain-gccarmnoneeabi' / 'bin' / 'arm-none-eabi-nm'
    if not nm.exists():
        raise SystemExit(f'找不到 {nm}，无法做链接重名检查，停止')
    dup = shared_symbols(str(nm), build)
    if dup:
        raise SystemExit(f'两个程序有同名外部符号会被链接器合并，停止：{dup[:5]}')
    waiver = sys.modules['build']
    payload = waiver.hex_payload(build / 'firmware.hex')
    for tag in (waiver.BASIS, 'dout_isr', 'usb_cdc'):  # 豁免标注、蓝牙 DOUT 版、USB 版都得真在镜像里
        if tag.encode() not in payload:
            raise SystemExit(f'烧录镜像里没有 {tag}，停止')
    bad = bench.usb_has_external((out / 'src' / 'usb_app.cpp').read_text())
    if bad:  # 插 USB 不开任何外部输入：EXT1、EXR1、LOF1 都不许在 USB 半边（蓝牙侧合法处理，故只查 USB 源码）
        raise SystemExit(f'USB 程序里有外部输入模式 {bad}，停止')
    art = HERE / 'artifacts'
    art.mkdir(exist_ok=True)
    stem = f'r01-dual-{ENV}{"-lof1" if a.loff else ""}-{meta["build_id"]}'
    shutil.copy2(build / 'firmware.hex', art / f'{stem}.hex')
    shutil.copy2(build / 'firmware.zip', art / f'{stem}-dfu.zip')
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    manifest = dict(profile='R01_DUAL_BENCH', rld_sens=f'0x{RLD_SENS:02x}', transports=['ble_dout', 'usb_cdc'], off_body_only=True, lof1=a.loff, regs_snapshot='ble_status_v3+usb_diag8', bench_basis=waiver.BASIS,
                    env=ENV, build_id=meta['build_id'], toolchain=a.toolchain or 'platformio.ini 默认',
                    hex_sha256=sha(art / f'{stem}.hex'), dfu_sha256=sha(art / f'{stem}-dfu.zip'))
    (art / f'{stem}.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

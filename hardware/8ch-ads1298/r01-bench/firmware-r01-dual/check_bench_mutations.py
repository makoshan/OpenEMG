"""TI 计划 S3+S4 补丁（bench_patch.py）和主机状态 v3 解码的变异测试：每次改坏一处，对应检查必须失败。

先把仓库里要用的几个目录复制到临时目录（不复制 .venv、.pio、采集数据），只在副本里改，工作区一个字节不动
（这个仓库常有别的会话同时在改）。先跑一遍不改的基线必须通过；导入、语法、缩进错误不算「抓到」。
不挂进 check_all（复制加 24 次检查约 40 s）。改了 bench_patch.py 或 host/v12_status.py 等之后手动跑：
  host/.venv-emg/bin/python hardware/8ch-ads1298/r01-bench/firmware-r01-dual/check_bench_mutations.py
"""
import pathlib, shutil, subprocess, sys, tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
COPY = ('host', 'hardware/8ch-ads1298/r01-bench', 'firmware/offline-f01', 'firmware/dsp-f03')
SKIP = shutil.ignore_patterns('.venv*', '.pio', '__pycache__', 'v12-captures', 'artifacts', '*.pyc', 'node_modules')


def main():
    py = sys.executable
    with tempfile.TemporaryDirectory(prefix='r01-bench-mut-') as tmp:
        ov = pathlib.Path(tmp)
        for rel in COPY:
            shutil.copytree(REPO / rel, ov / rel, ignore=SKIP, symlinks=True)
        dual = ov / 'hardware/8ch-ads1298/r01-bench/firmware-r01-dual'; host = ov / 'host'
        B, S, H = dual / 'bench_patch.py', host / 'v12_status.py', host
        M = [
         (B, "for(uint8_t a=0;a<26;++a)readback[a]=read_reg(a);readback_valid=true;", "readback_valid=true;"),
         (B, "for(uint8_t a=0;a<26;++a)readback[a]=read_reg(a);", "for(uint8_t a=0;a<25;++a)readback[a]=read_reg(a);"),
         (B, "             ' for(uint8_t a=0;a<26;++a)readback[a]=read_reg(a);readback_valid=true;  // TI 计划 S3：读回实际寄存器，随状态上报\\n'\n             ' command(0x10);if(!h.session_valid()){stop(Fault::Cancelled);return false;}\\n'",
             "             ' command(0x10);if(!h.session_valid()){stop(Fault::Cancelled);return false;}\\n'\n             ' for(uint8_t a=0;a<26;++a)readback[a]=read_reg(a);readback_valid=true;\\n'"),
         (B, "stop();readback_valid=false;\\n'", "stop();\\n'"),
         (B, "!(MAKO_R01_LOFF && input==Input::ExternalRldLoff)", "!(input==Input::ExternalRldLoff)"),
         (B, " const bool loff=MAKO_R01_LOFF && input==Input::ExternalRldLoff;", " const bool loff=false;"),
         (B, "regs[0x4]=0x03;", "regs[0x4]=0x02;"),
         (B, "regs[0x17]=0x02;}", "regs[0x17]=0x00;}"),
         (B, "regs[0xf]=regs[0x10]=regs[0xd];", "regs[0xf]=regs[0x10]=0xff;"),
         (B, "regs[0xf]=regs[0x10]=regs[0xd];", "regs[0xf]=regs[0x10]=regs[0x11]=regs[0xd];"),
         (B, "bytes[43]=3;'", "bytes[43]=2;'"),
         (B, "memcpy(bytes+137,ads.readback,26);", "memcpy(bytes+137,ads.readback,25);"),
         (B, "(MAKO_R01_LOFF && request==7)", "(request==7)"),
         (B, "'#if MAKO_R01_LOFF\\n else if", "'#if 1\\n else if"),
         (B, "EXTERNAL_MODES = ('\"EXT1\"', '\"EXR1\"', '\"LOF1\"')", "EXTERNAL_MODES = ('\"EXT1\"', '\"EXR1\"')"),
         (B, "'\\n  send_regs();  // 放最后\\n}\\n\\nstatic void send_status() {'", "'\\n}\\n\\nstatic void send_status() {'"),
         (B, "ads.readback_valid ? 1 : 0", "1"),
         (B, "    if loff:\n        ini = out / 'platformio.ini'", "    if False:\n        ini = out / 'platformio.ini'"),
         (B, "'    if (mode == 1 || mode == 2) ads.start(", "'    if (true) ads.start("),
         (B, 'MAKO_R01_LOFF?"true":"false");', '"false");'),
         (S, "        if data[136] not in (0, 1):", "        if False:"),
         (S, "data[137:163].hex() if data[136] else None", "data[137:163].hex()"),
         (H / 'v12_ble.py', "stopped['status_version'] < 2:", "stopped['status_version'] != 2:"),
         (H / 'v12_dongle.py', "len(res) not in (48, 64, 136, 163):", "len(res) not in (48, 64, 136):"),
        ]

        def run(f):
            cmd = {S: ['check_v12_status.py'], H / 'v12_ble.py': ['check_v12_ble.py'], H / 'v12_dongle.py': ['v12_dongle.py', 'selftest']}.get(f)
            if cmd:
                return subprocess.run([py, '-B', *cmd], cwd=host, capture_output=True, text=True, timeout=600)
            return subprocess.run([py, '-B', 'check.py'], cwd=dual, capture_output=True, text=True, timeout=600)

        for f in (B, S, H / 'v12_ble.py', H / 'v12_dongle.py'):
            r = run(f)
            if r.returncode:
                sys.exit(f'基线就没过（{f.name}），先修环境或代码：\n{r.stderr.strip()[-400:]}')
        miss = 0
        for i, (f, a, b) in enumerate(M, 1):
            orig = f.read_text(encoding='utf-8')
            if orig.count(a) != 1:
                sys.exit(f'变异 {i} 的原文在 {f.name} 里出现 {orig.count(a)} 次，变异表过期了：{a[:60]}')
            f.write_text(orig.replace(a, b), encoding='utf-8')
            try:
                r = run(f)
            finally:
                f.write_text(orig, encoding='utf-8')
            last = (r.stderr.strip().splitlines() or [''])[-1]
            caught = r.returncode != 0 and not last.startswith(('ImportError', 'ModuleNotFoundError', 'SyntaxError', 'IndentationError', 'TabError'))
            miss += not caught
            print(f'{i:2d} {"红" if caught else "**没抓到**"} {f.name}: {a.strip()[:48]}')
        print(f'check_bench_mutations: {len(M) - miss}/{len(M)} 个变异被抓到')
        sys.exit(1 if miss else 0)


if __name__ == '__main__':
    main()

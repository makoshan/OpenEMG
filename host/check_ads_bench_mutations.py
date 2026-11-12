"""ads1298_regs / ads1292_regs / bench_analysis 的变异测试：每次只改一处，跑对应 --check，必须失败。

先跑一遍不改的基线，必须通过（环境缺 numpy/scipy 时直接报错退出，不会把导入失败当成「抓到」）。
变异只有在 --check 报出断言或运行错误时才算抓到；导入错误、语法/缩进错误不算。
用 check_all 的 $PY（本机是 host/.venv-emg/bin/python）跑：python host/check_ads_bench_mutations.py
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile

SRC = pathlib.Path(__file__).resolve().parent
FILES = ('ads1298_regs.py', 'ads1292_regs.py', 'bench_analysis.py')
R, R2, B = FILES
M = [
    # ads1298_regs：保留位、字段表、换算、导联、ID、状态字
    (R, "0x16: (0x20, 0x20)", "0x16: (0x20, 0x00)"),
    (R, "return (w >> 12) & 0xFF", "return (w >> 11) & 0xFF"),
    (R, "    0x03: (0x40, 0x40),", "    0x03: (0x00, 0x00),"),
    (R, "(4 if c1['HR'] else 8)", "(8 if c1['HR'] else 4)"),
    (R, "if regs[0x00] & 0x1F != 0x12", "if regs[0x00] & 0x18 != 0x10"),
    (R, "return 4.0 if c3['VREF_4V'] else 2.4", "return 4.0"),
    (R, "if (regs[0x0F] or regs[0x10]) and flead == 0b00", "if regs[0x0F] and flead == 0b00"),
    (R, "and flead == 0b00:", "and flead != 0b11:"),
    (R, "return full_scale_uv(regs, ch) / (2 ** 23 - 1)", "return full_scale_uv(regs, ch) / (2 ** 23)"),
    (R, "0x01: (0x18, 0x00)", "0x01: (0x08, 0x00)"),
    (R, "0x02: (0xC8, 0x00)", "0x02: (0x48, 0x00)"),
    (R, "0x17: (0x11, 0x00)", "0x17: (0x01, 0x00)"),
    (R, "if regs[0x16] & 0xC0 and", "if regs[0x16] & 0x80 and"),
    (R, " and d['ID']['DEV_ID'] != DEV_ID_R:", ":"),
    (R, "('VREF_4V', 5, 5)", "('VREF_4V', 4, 4)"),
    (R, "_CH = [('PD', 7, 7), ('GAIN', 6, 4)", "_CH = [('PD', 7, 7), ('GAIN', 6, 5)"),
    (R, "('WCTB', 5, 3)", "('WCTB', 5, 4)"),
    (R, "& ((1 << (hi - lo + 1)) - 1)", "& ((1 << (hi - lo)) - 1)"),
    (R, "if type(ch) is not int or not 1 <= ch <= 8:", "if False:"),
    (R, "if c1['HR'] and c1['DR'] == 0:", "if False:"),
    # ads1292_regs：ID、保留位、非 R 版 RESP1/RESP2(0x07 vs 0x03)、2.42V/4.033V、RLD 互斥、状态字映射
    (R2, "if (regs[0x00] & 0xDF) != 0x53:", "if (regs[0x00] & 0xDD) != 0x51:"),
    (R2, "0x02: (0x84, 0x80),", "0x02: (0x04, 0x00),"),
    (R2, "0x03: (0x10, 0x10),", "0x03: (0x00, 0x00),"),
    (R2, "0x09: (0x02, 0x02),", "0x09: (0x02, 0x00),"),
    (R2, "0x0A: (0x79, 0x01),", "0x0A: (0x78, 0x00),"),
    (R2, "if d['RESP2']['RESP_FREQ'] != 1:", "if False:"),
    (R2, "if regs[0x09] != 0x02:", "if False:"),
    (R2, "if d['RLD_SENS']['PDB_RLD'] and d['RLD_SENS']['RLD_LOFF_SENS']:", "if False:"),
    (R2, "return 4.033 if c2['VREF_4V'] else 2.42", "return 4.0 if c2['VREF_4V'] else 2.4"),
    (R2, "return (fclk / 4) / (1 << (10 - c1['DR']))", "return (fclk / 8) / (1 << (10 - c1['DR']))"),
    (R2, "if w & 0x1FFF:", "if False:"),
    (R2, "f01 = 0xC00000 | (statp << 12) | (statn << 4) | gpio", "f01 = 0xC00000 | (statn << 12) | (statp << 4) | gpio"),
    # bench_analysis：谱归一化、噪声补齐、谐波、杂散、ENOB/SINAD、CMRR、相干频率
    (B, "p[1:(n + 1) // 2] *= 2", "p[1:(n + 1) // 2] *= 1"),
    (B, "p[1:(n + 1) // 2] *= 2", "p[1:] *= 2"),
    (B, "/ (n * np.sum(w * w))", "/ (n * n)"),
    (B, "np.fft.rfft((x - x.mean()) * w)", "np.fft.rfft(x * w)"),
    (B, "p[noise].mean() * band.sum()", "p[noise].mean() * noise.sum()"),
    (B, "'enob': (db(pfs, pn + ph) - 1.76) / 6.02", "'enob': (db(pfs, pn + ph)) / 6.02"),
    (B, "'enob': (db(pfs, pn + ph) - 1.76)", "'enob': (db(pfs, pn) - 1.76)"),
    (B, "'sinad_dbc': db(ps, pn + ph)", "'sinad_dbc': db(ps, pn)"),
    (B, "'thd_dbc': db(ph, ps)", "'thd_dbc': db(max(energies), ps)"),
    (B, "kh = n - kh if kh > n // 2 else kh", "kh = kh"),
    (B, "if kh <= 2 * s or abs(kh - k0) <= 2 * s or kh + s >= m:", "if kh <= 2 * s or kh + s >= m:"),
    (B, "if any(abs(kh - kj) <= 2 * s for kj in g[1]):", "if False:"),
    (B, "spur = max(in_band + [float(p[lo_j:hi_j][noise[lo_j:hi_j]].sum())])", "spur = max(in_band + [float(p[j])])"),
    (B, "p[lo_j:hi_j][noise[lo_j:hi_j]].sum()", "p[lo_j:hi_j][~excl[lo_j:hi_j]].sum()"),
    (B, "if k0 <= 2 * s or k0 >= m - 1 - 2 * s:", "if k0 <= 2 * s:"),
    (B, "rest = np.flatnonzero(noise)", "rest = np.flatnonzero(~excl)"),
    (B, "spur = max(in_band + [", "spur = max(energies + ["),
    (B, "b = tone_amplitude(baseline, fs, fr)[0]", "b = tone_amplitude(baseline, fs, f0)[0]"),
    (B, "excl[:s + 1] = True", "excl[:1] = True"),
    (B, "SPREAD = {'blackmanharris': 12,", "SPREAD = {'blackmanharris': 5,"),
    (B, "return float(np.sqrt(p[sel].sum() * (f[1] - f[0])))", "return float(np.sqrt(p[sel].sum() * (f[1] - f[0]) * 0.9))"),
    (B, "detrend='constant')", "detrend=False)"),
    (B, "if k0 in (win.start, win.stop - 1):", "if False:"),
    (B, "if x.size < seg:", "if False:"),
    (B, "if sel.sum() < 2:", "if False:"),
    (B, "20 * math.log10((inject_vpp / 2) / a)", "20 * math.log10(inject_vpp / a)"),
    (B, "    best = fine[int(np.argmax([amp(g) for g in fine]))]", "    pass"),
    (B, "np.ones_like(t)])", "np.zeros_like(t)])"),
    (B, "out['baseline_db'] = 20 * math.log10(b / a) if b > 0 else float('-inf')", "out['baseline_db'] = 0.0"),
    (B, "if math.gcd(k, n) == 1]", "if k % 2]"),
    (B, "range(1, (n - 1) // 2 + 1)", "range(1, n)"),
]


def run(d, fn):
    return subprocess.run([sys.executable, '-B', fn, '--check'], cwd=d, capture_output=True, text=True)


def main():
    with tempfile.TemporaryDirectory() as d:
        for f in FILES:
            shutil.copy(SRC / f, pathlib.Path(d) / f)
        for f in FILES:
            r = run(d, f)
            if r.returncode:
                sys.exit(f'基线就没过（{f}），先修环境或代码：\n{r.stderr.strip()[-400:]}')
    missed = 0
    for i, (fn, a, b) in enumerate(M, 1):
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            for f in FILES:
                shutil.copy(SRC / f, d / f)
            t = (d / fn).read_text(encoding='utf-8')
            if t.count(a) != 1:
                sys.exit(f'变异 {i} 的原文在 {fn} 里出现 {t.count(a)} 次，变异表过期了：{a}')
            (d / fn).write_text(t.replace(a, b), encoding='utf-8')
            r = run(d, fn)
            last = (r.stderr.strip().splitlines() or [''])[-1]
            caught = r.returncode != 0 and not last.startswith(('ImportError', 'ModuleNotFoundError', 'SyntaxError', 'IndentationError', 'TabError'))
            missed += not caught
            print(f'{i:2d} {"红" if caught else "**没抓到**"} {fn}: {a[:48]}')
    print(f'check_ads_bench_mutations: {len(M) - missed}/{len(M)} 个变异被抓到')
    sys.exit(1 if missed else 0)


if __name__ == '__main__':
    main()

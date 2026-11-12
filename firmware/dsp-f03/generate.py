"""生成候选系数；运行时不用 SciPy，参数尚未冻结。"""
from pathlib import Path
import hashlib
import json
import numpy as np
from scipy import signal

ROOT = Path(__file__).resolve().parent


def reference(fs, notch):
    sos = np.vstack([
        signal.butter(2, 15, 'highpass', fs=fs, output='sos'),
        signal.butter(4, 600, 'lowpass', fs=fs, output='sos'),
    ])
    if notch:
        b, a = signal.iirnotch(50, 30, fs=fs)
        sos = np.vstack([sos, signal.tf2sos(b, a)])
    return sos


def main():
    profiles = []
    headers = ['/* 由 generate.py 生成：候选 HP15/LP600/可选50Hz-Q30，禁止手改。 */']
    for fs in (2000, 4000):
        for notch in (False, True):
            sos = reference(fs, notch)
            # 检查实际写入 C 的 float32 系数，恢复段只是极点衰减筛查。
            rounded = sos.astype(np.float32).astype(float)
            assert rounded[0, 1] == -2 * rounded[0, 0] and rounded[0, 2] == rounded[0, 0]
            radius = float(max(abs(signal.sos2zpk(rounded)[1])))
            assert radius < 1
            guard = int(np.ceil(np.log(1e-3) / np.log(radius)))
            name = f'sos_{fs}_{int(notch)}'
            rows = ',\n'.join(' {' + ', '.join(float(v).hex() + 'f' for v in row) + '}' for row in rounded)
            headers.append(f'static const float {name}[{len(sos)}][6] = {{\n{rows}\n}};')
            profiles.append(dict(fs_Hz=fs, notch=notch, hp_Hz=15, lp_Hz=600,
                                 notch_Hz=50 if notch else None, notch_Q=30 if notch else None,
                                 sections=len(sos), sos_float64=sos.tolist(), sos_float32=rounded.tolist(),
                                 max_pole_radius_float32=radius, reset_guard_samples=guard,
                                 reset_guard_ms=1000 * guard / fs))
    headers.append('static int configure(v12_dsp *s, unsigned fs, int notch) {')
    for p in profiles:
        name = f"sos_{p['fs_Hz']}_{int(p['notch'])}"
        headers.append(f" if (fs == {p['fs_Hz']}u && notch == {int(p['notch'])}) {{ s->coeff = {name}; s->sections = {p['sections']}u; s->guard = {p['reset_guard_samples']}u; return 0; }}")
    headers.append(' return -1;\n}')
    content = '\n'.join(headers) + '\n'
    (ROOT / 'coefficients.h').write_text(content)
    report = dict(status='候选，未冻结', profiles=profiles,
                  guard_basis='float32最大极点的自然衰减到0.001；不是所有输入的稳定时间保证',
                  coefficient_sha256=hashlib.sha256(content.encode()).hexdigest())
    (ROOT / 'profiles.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()

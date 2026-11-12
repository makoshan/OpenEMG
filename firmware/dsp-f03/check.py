import os
import shutil
"""合成输入下实际C链路检查，不能给硬件签署验收。"""
from pathlib import Path
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import numpy as np
from scipy import signal
from generate import reference
from runtime import DSP, compile_library, ROOT
from replay import replay
from codec import Packet, encode, SYNTHETIC, SESSION_START


def frame(codes):
    return bytes.fromhex('c00000') + b''.join(int(v).to_bytes(3, 'big', signed=True) for v in codes)


def event(seq, timestamp, raw, flags=SYNTHETIC):
    return dict(packet_hex=encode(Packet(seq, timestamp, flags, tuple(frame(row) for row in raw))).hex(), mtu=247)


def rejected(fn):
    try:
        fn()
    except ValueError:
        return True
    raise AssertionError('错误输入被接受')


def main():
    report = dict(status='主机合成检查通过；独立及实物验收未做', hardware_tested=False,
                  linked_target_firmware=False, profiles=[], checks=[], negative_controls=[])
    profiles = json.loads((ROOT / 'profiles.json').read_text())['profiles']
    rng = np.random.default_rng(1203)
    with tempfile.TemporaryDirectory(prefix='v12-dsp-check-') as tmp:
        tmp = Path(tmp)
        library = compile_library(tmp)
        for fs in (2000, 4000):
            for notch in (False, True):
                n = fs * 3
                t = np.arange(n) / fs
                raw = np.zeros((n, 8), np.int32)
                for ch in range(8):
                    # 不同通道不同频率，并含偏置/运动、噪声及满量程边界。
                    v = 0.25 + 0.04 * np.sin(2 * np.pi * (20 + ch * 60) * t)
                    v += 0.02 * np.sin(2 * np.pi * 50 * t) + rng.normal(0, .001, n)
                    raw[:, ch] = np.rint(v * 8388608).astype(np.int32)
                raw[n // 2:n // 2 + 2, :2] = [[-8388608, 8388607], [8388607, -8388608]]
                original = raw.copy()
                dsp = DSP(library, fs, notch)
                actual, ready = dsp.process(raw)
                assert np.array_equal(raw, original)
                ideal = signal.sosfilt(reference(fs, notch), (raw.astype(float) - raw[0]) / 8388608., axis=0)
                error = float(np.max(abs(actual - ideal)))
                # 满量程比例容差，仅代码一致性；不是肌电噪声预算。
                assert error < 5e-5, (fs, notch, error)
                assert np.isfinite(actual).all()
                chunked = DSP(library, fs, notch)
                pieces, states = [], []
                for chunk in np.array_split(raw, 37):
                    y, valid = chunked.process(chunk)
                    pieces.append(y)
                    states.append(valid)
                assert np.array_equal(np.concatenate(pieces), actual)
                assert np.array_equal(np.concatenate(states), ready)
                config = next(p for p in profiles if (p['fs_Hz'], p['notch']) == (fs, notch))
                guard = config['reset_guard_samples']
                assert not ready[:guard].any() and ready[guard:].all()
                # 只给一路脉冲，其余通道必须为零。
                isolated = np.zeros((100, 8), np.int32)
                isolated[1, 3] = 1000000
                y, _ = DSP(library, fs, notch).process(isolated)
                assert np.any(y[:, 3] != 0) and np.all(y[:, [0, 1, 2, 4, 5, 6, 7]] == 0)
                # 拒绝坏块后下一合法块须与没有坏块的路径完全一致。
                clean = DSP(library, fs, notch)
                clean.process(raw[:100])
                before = bytes(clean.buffer)
                invalid = raw[100:108].copy()
                invalid[-1, -1] = 8388608
                rejected(lambda: clean.process(invalid))
                assert bytes(clean.buffer) == before
                control = DSP(library, fs, notch)
                control.process(raw[:100])
                assert np.array_equal(clean.process(raw[100:108])[0], control.process(raw[100:108])[0])
                # C层直接喂非法最后一帧，确保预检没有只写在Python里。
                out = np.zeros(invalid.shape, np.float32)
                valid = np.zeros(len(invalid), np.uint8)
                before = bytes(clean.buffer)
                assert clean.lib.v12_dsp_block(clean.buffer, invalid.ctypes.data, len(invalid), out.ctypes.data, valid.ctypes.data) == -2
                assert bytes(clean.buffer) == before and np.all(out == 0)
                report['profiles'].append(dict(fs_Hz=fs, notch=notch, frames=n,
                                                max_abs_float32_vs_float64_fs=error,
                                                reset_guard_samples=guard))
                # 大直流+20µV峰值ADC输入（Vref=4/G=6是假设），检查微小信号。
                tt = np.arange(fs * 5) / fs
                micro = np.rint((.25 + 3e-5 * np.sin(2*np.pi*100*tt)) * 8388608).astype(np.int32)
                y, _ = DSP(library, fs, notch).process(np.repeat(micro[:, None], 8, axis=1))
                ref = signal.sosfilt(reference(fs, notch), (micro.astype(float)-micro[0])/8388608.)
                tail = np.arange(len(micro)) >= 2*fs
                rms = float(np.sqrt(np.mean((y[tail, 0]-ref[tail])**2)))
                relative = rms / float(np.sqrt(np.mean(ref[tail]**2)))
                assert relative < .005, (fs, notch, relative)
                report['profiles'][-1].update(small_signal_relative_rms_error=relative,
                                               small_signal_error_fs_rms=rms,
                                               small_signal_error_ADC_uVrms_assumed_Vref4_G6=rms*4/6*1e6)
                # 运动等效偏置在1秒后跃迁，随后恢复的小信号也必须保留。
                tt = np.arange(fs*6)/fs
                step = np.rint((.25 + .05*(tt>=1) + 3e-5*np.sin(2*np.pi*100*tt))*8388608).astype(np.int32)
                y, _ = DSP(library, fs, notch).process(np.repeat(step[:, None], 8, axis=1))
                ref = signal.sosfilt(reference(fs, notch), (step.astype(float)-step[0])/8388608.)
                tail = tt >= 4
                relative = float(np.sqrt(np.mean((y[tail, 0]-ref[tail])**2))/np.sqrt(np.mean(ref[tail]**2)))
                assert relative < .005, (fs, notch, relative)
                report['profiles'][-1]['post_bias_step_small_signal_relative_rms_error'] = relative
        report['checks'] += ['4配置逐点对照SciPy', '37块与整段逐位一致', '8路隔离',
                             '24位极值/原始码不改写', '坏块不推进状态（含直接C调用）', '恢复段标记']
        rejected(lambda: DSP(library, 1000, False))
        rejected(lambda: DSP(library, 2000, False).process(np.full((1, 8), np.nan)))
        rejected(lambda: DSP(library, 2000, False).process(np.full((1, 8), 2**40, dtype=np.int64)))
        report['checks'].append('错误配置、NaN和64位溢出拒绝')

        # 回放真实字节契约，含包丢失、重复、坏包、时间跳变和明确重连。
        a = np.full((8, 8), 1000000, np.int32)
        b = np.full((8, 8), 2000000, np.int32)
        events = [event(0, 0, a, 3), event(16, 8000, b), event(16, 8500, b),
                  {'packet_hex': '00', 'mtu': 247}, event(24, 13000, a),
                  {'disconnect': True}, event(0, 0, b, 3), event(8, 4000, a)]
        result = replay(events, tmp / 'replay', library, 2000)
        assert result['accepted_samples'] == 40 and result['missing_samples'] == 8
        assert result['sessions'] == 2 and len(result['rejected_events']) == 2
        assert [r['reason'] for r in result['resets']] == ['session', 'gap', 'timestamp', 'session']
        assert result['timestamp_discontinuities'] == 1
        rows = list(csv.DictReader((tmp / 'replay/samples.csv').open()))
        assert len(rows) == 40 and not any(int(r['dsp_ready']) for r in rows)
        clean_b = DSP(library, 2000, False).process(b)[0]
        assert np.allclose([float(rows[8][f'filtered_fs{i}']) for i in range(1, 9)], clean_b[0], atol=0, rtol=0)
        assert [int(r['raw1']) for r in rows] == [1000000]*8 + [2000000]*8 + [1000000]*8 + [2000000]*8 + [1000000]*8
        assert rows[8]['sequence'] == '16' and rows[0]['synthetic'] == '1'
        report['checks'].append('F01字节回放/原始码、缺口不补造、重复坏包拒绝、时间跳变和重连恢复')
        # 有真实标签但未授权的文件不能被混入合成会话。
        denied = replay([event(0, 0, a, SESSION_START)], tmp / 'denied', library, 2000)
        assert denied['accepted_samples'] == 0 and len(denied['rejected_events']) == 1
        enabled = replay([event(0, 0, a, SESSION_START)], tmp / 'enabled', library, 2000, allow_real=True)
        assert enabled['real_label_sessions'] == 1 and not enabled['hardware_tested']
        report['checks'].append('真实标签显式开关，始终不冒充实测')

        # 实际CLI阳性/空输入/错包/错采样率对照，不能只测内部函数。
        positive = [event(0, 0, a, 3), event(8, 4000, b)]
        for name, data, rate, exit_code in [('good', positive, 2000, 0), ('empty', [], 2000, 2),
                                            ('bad', events, 2000, 2), ('wrong-rate', positive, 4000, 2)]:
            path=tmp/(name+'.jsonl')
            content=''.join(json.dumps(e)+'\n' for e in data).encode()
            path.write_bytes(content)
            p=subprocess.run([sys.executable, str(ROOT/'replay.py'), str(path), str(tmp/(name+'-cli')),
                              '--fs', str(rate)], capture_output=True, text=True, timeout=30)
            assert p.returncode==exit_code, (name, p.stderr)
            assert (tmp/(name+'-cli/events.jsonl')).read_bytes()==content
        report['checks'].append('真实CLI阳性/空记录/坏包/错误采样率及输入原文件保留')
        for name, period, expected_code in [('single-good', 500, 0), ('single-wrong', 250, 2),
                                             ('single-clock-budget', 490, 0)]:
            data=[event(i, i*period, a[:1], 3 if i==0 else 1) for i in range(256)]
            path=tmp/(name+'.jsonl')
            path.write_text(''.join(json.dumps(e)+'\n' for e in data))
            p=subprocess.run([sys.executable, str(ROOT/'replay.py'), str(path), str(tmp/(name+'-cli')),
                              '--fs', '2000'], capture_output=True, text=True, timeout=30)
            assert p.returncode==expected_code, (name, p.stderr)
            observed=json.loads((tmp/(name+'-cli/result.json')).read_text())
            assert (observed['timestamp_discontinuities']>0) == (expected_code==2)
            # 实测采样率：500µs→2000Hz/0ppm；490µs→约+20408ppm；时间跳变被切段后各段单独拟合。
            if name != 'single-wrong':
                rate = observed['measured_sample_rate']
                assert len(rate) == 1 and rate[0]['packets'] == 256, rate
                assert abs(rate[0]['deviation_ppm'] - (500/period-1)*1e6) < 1, rate
        one = replay([event(0, 0, a, 3)], tmp / 'one-packet', library, 2000)
        assert one['measured_sample_rate'] == [dict(segment=1, packets=1, sample_span=0,
                                                    measured_fs_Hz=None, deviation_ppm=None)]
        report['checks'].append('独立复核反例：单帧包4k伪作2k被拦；正确率及2%频差阳性通过')
        report['checks'].append('实测采样率：0/+20408ppm拟合正确，单包段留空不填标称值')
        data=[event(i*8, i*4000, a, 3 if i==0 else 1) for i in range(2500)]
        data.append(event(20000, 10100000, a))
        path=tmp/'late-jump.jsonl'
        path.write_text(''.join(json.dumps(e)+'\n' for e in data))
        p=subprocess.run([sys.executable, str(ROOT/'replay.py'), str(path), str(tmp/'late-jump-cli'),
                          '--fs', '2000'], capture_output=True, text=True, timeout=30)
        assert p.returncode==2, p.stderr
        observed=json.loads((tmp/'late-jump-cli/result.json').read_text())
        assert observed['timestamp_discontinuities']==1 and observed['resets'][-1]['adjacent_time_error']
        rows=list(csv.DictReader((tmp/'late-jump-cli/samples.csv').open()))
        assert all(int(r['dsp_ready'])==0 for r in rows[-8:])
        report['checks'].append('独立复核反例：10秒后100ms突跳被拦并重置恢复段')

        # UBSan跑实际可执行探针；不向Python进程加载Sanitizer动态库。
        exe = tmp / 'ubsan-probe'
        subprocess.run([os.environ.get('CC') or shutil.which('clang') or 'cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-O2', '-ffp-contract=off',
                        '-fsanitize=undefined', '-fno-sanitize-recover=all', str(ROOT / 'v12_dsp.c'),
                        str(ROOT / 'probe.c'), '-o', str(exe)], check=True, timeout=30, capture_output=True)
        commands = '\n'.join(' '.join(map(str, row)) for row in np.vstack([a, b])) + '\nR\n' + ' '.join(['8388608']*8) + '\n'
        for fs in (2000, 4000):
            for notch in (0, 1):
                p = subprocess.run([str(exe), str(fs), str(notch)], input=commands, text=True,
                                   capture_output=True, check=True, timeout=10)
                assert len(p.stdout.splitlines()) == 17 and p.stdout.splitlines()[-1] == '-2'
                assert 'runtime error:' not in p.stderr
        report['checks'].append('4配置实际可执行UBSan探针')

        # 反例一：每帧清状态，必须破坏正确参考输出。
        broken = tmp / 'reset.c'
        text = (ROOT / 'v12_dsp.c').read_text().replace('unsigned ch, stage;\n if (!s ||', 'unsigned ch, stage;\n v12_dsp_reset(s);\n if (!s ||')
        assert text != (ROOT / 'v12_dsp.c').read_text()
        broken.write_text(text)
        mutant_lib = compile_library(tmp, source=broken)
        raw = np.tile(np.vstack([a, b]), (20, 1))
        observed = DSP(mutant_lib, 2000, False).process(raw)[0]
        expected = signal.sosfilt(reference(2000, False), (raw.astype(float)-raw[0]) / 8388608., axis=0)
        assert np.max(abs(observed - expected)) > 1e-3
        report['negative_controls'].append('逐帧清状态错误被数值对照检出')
        # 反例二：回放不在缺口/新会话重置，必须破坏缺口首行。
        mutant = (ROOT / 'replay.py').read_text().replace('                dsp.reset()\n                segment += 1', '                segment += 1')
        ns = {'__name__': 'replay_mutant', '__file__': str(ROOT / 'replay.py')}
        exec(compile(mutant, str(ROOT / 'replay.py'), 'exec'), ns)
        ns['replay'](events, tmp / 'broken-replay', library, 2000)
        bad_rows = list(csv.DictReader((tmp / 'broken-replay/samples.csv').open()))
        assert abs(float(bad_rows[8]['filtered_fs1']) - float(clean_b[0, 0])) > 1e-3
        report['negative_controls'].append('缺口不清状态错误被字节回放检出')

        arm = tmp / 'v12_dsp.o'
        command = ['arm-none-eabi-gcc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-O2',
                   '-ffreestanding', '-ffp-contract=off', '-mcpu=cortex-m4', '-mthumb', '-mfpu=fpv4-sp-d16', '-mfloat-abi=hard',
                   '-c', str(ROOT / 'v12_dsp.c'), '-o', str(arm)]
        p = subprocess.run(command, capture_output=True, text=True, timeout=30)
        report['arm_object'] = dict(passed=p.returncode == 0, exit_code=p.returncode,
                                     diagnostic=p.stderr, linked_firmware=False)
        assert p.returncode == 0, p.stderr
        size = subprocess.run(['arm-none-eabi-size', str(arm)], capture_output=True, text=True, check=True, timeout=10)
        report['arm_object']['size_output'] = size.stdout.strip().replace(str(arm), 'v12_dsp.o')
    report['source_sha256'] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                               for name in ('generate.py', 'coefficients.h', 'profiles.json', 'v12_dsp.c',
                                            'v12_dsp.h', 'runtime.py', 'replay.py', 'probe.c', 'check.py')}
    if os.environ.get('WRITE_RESULTS') == '1':
        (ROOT / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

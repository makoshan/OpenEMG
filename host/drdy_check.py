"""V12 R01 台架：用逻辑分析仪抓包判断 DRDY 有没有假沿、每帧有没有读完。

不依赖 F05 固件的自报：F05 遇到任何异常沿只报 Overrun 并停采，分不出是串扰假沿还是读得慢。
这里只看线上的电平。

抓包（PulseView / sigrok 导出 VCD，只记电平变化）：
  长抓 10 分钟：只接 DRDY、CS（J1 第 7、6 脚，GND 第 2 脚），用来数沿。
  短抓 2 秒：再加 SCLK（J1 第 3 脚），用来看每帧时钟数、SCLK 实际频率和读帧余量。
CSV 也能读，但必须带时间列（Saleae 的变化表格式）；逐点 CSV 太大，不要用。

用法：
  python3 drdy_check.py capture.vcd --fs 2000 [--drdy DRDY --cs CS --sclk SCLK] [--json]
  python3 drdy_check.py --check      # 合成数据自检：干净的要过，五种坏的必须红
退出码：0 通过，1 不通过，2 输入有问题。
"""
import argparse
import bisect
import csv
import json
import re
import statistics
import sys
import tempfile

UNITS = {'s': 1.0, 'ms': 1e-3, 'us': 1e-6, 'ns': 1e-9, 'ps': 1e-12, 'fs': 1e-15}


def read_vcd(path, names):
    """返回 {名字: [(时间s, 电平)]} 和抓包结束时间。只取 names 里要的 1 位信号。"""
    scale, ids, tr, t, t_end = None, {}, {n: [] for n in names}, 0.0, 0.0
    with open(path) as f:
        text = f.read()
    head, _, body = text.partition('$enddefinitions')
    m = re.search(r'\$timescale\s+(\d+)\s*(\w+)\s+\$end', head)
    if not m:
        raise SystemExit(f'{path}: 没有 $timescale')
    scale = int(m.group(1)) * UNITS[m.group(2)]
    for code, name in re.findall(r'\$var\s+\w+\s+1\s+(\S+)\s+(\S+)(?:\s+\[\d+\])?\s+\$end', head):
        if name in tr:
            ids[code] = name
    missing = set(names) - set(ids.values())
    if missing:
        raise SystemExit(f'{path}: 找不到信号 {sorted(missing)}；文件里有 {re.findall(r"var\s+\w+\s+1\s+\S+\s+(\S+)", head)}')
    for tok in body.split():
        if tok[0] == '#':
            t = int(tok[1:]) * scale
            t_end = t
        elif tok[0] in '01' and tok[1:] in ids:
            tr[ids[tok[1:]]].append((t, int(tok[0])))
    return tr, t_end


def read_csv(path, names):
    """Saleae / PulseView 带时间列的 CSV：第一列 'Time [单位]'，其余列按表头名字取。"""
    with open(path, newline='') as f:
        rows = [r for r in csv.reader(f) if r and not r[0].startswith(';')]
    head = [h.strip() for h in rows[0]]
    m = re.match(r'Time\s*\[(\w+)\]', head[0])
    if not m:
        raise SystemExit(f'{path}: 第一列不是 Time [单位]，逐点 CSV 请改导出 VCD')
    scale = UNITS[m.group(1)]
    missing = [n for n in names if n not in head]
    if missing:
        raise SystemExit(f'{path}: 找不到列 {missing}；表头是 {head}')
    col = {n: head.index(n) for n in names}
    tr = {n: [] for n in names}
    for r in rows[1:]:
        t = float(r[0]) * scale
        for n, c in col.items():
            v = int(float(r[c]))
            if not tr[n] or tr[n][-1][1] != v:
                tr[n].append((t, v))
    return tr, float(rows[-1][0]) * scale


def edges(tr, level):
    """电平变成 level 的时刻（第一个点是初值，不算沿）。"""
    return [t for (t, v), (_, p) in zip(tr[1:], tr) if v == level and p != level]


def analyze(sig, t_end, fs, tol, has_cs, has_sclk, min_margin):
    d = edges(sig['DRDY'], 0)
    if len(d) < 3:
        return {'ok': False, 'reason': f'DRDY 下降沿只有 {len(d)} 个'}
    gaps = [b - a for a, b in zip(d, d[1:])]
    period = statistics.median(gaps)            # 用实测周期，ADS 内部时钟本身有偏差
    real, false_edges, missing = [d[0]], [], 0
    for t in d[1:]:
        gap = t - real[-1]
        if gap < 0.9 * period:                  # 比一个周期短得多：假沿
            false_edges.append(t)
            continue
        if gap > 1.5 * period:                  # 中间少了沿：DRDY 本身丢脉冲或线断续
            missing += round(gap / period) - 1
        real.append(t)
    r = {
        'fs_nominal': fs, 'fs_measured': round(1 / period, 3),
        'fs_error_pct': round((1 / period / fs - 1) * 100, 3),
        'duration_s': round(t_end - d[0], 3), 'drdy_edges': len(d), 'real_edges': len(real),
        'false_edges': len(false_edges), 'missing_edges': missing,
        'shortest_gap_us': round(min(gaps) * 1e6, 3),
    }
    bad = []
    if abs(r['fs_error_pct']) > tol * 100:
        bad.append(f"实测采样率偏离标称 {r['fs_error_pct']}%")
    if false_edges:
        bad.append(f'{len(false_edges)} 个假沿')
    if missing:
        bad.append(f'少了 {missing} 个沿')
    if has_cs:
        cs = sig['CS']
        cs_t = [t for t, _ in cs]
        cs_fall, cs_rise = edges(cs, 0), edges(cs, 1)

        def cs_low(t):
            i = bisect.bisect_right(cs_t, t) - 1
            return i >= 0 and cs[i][1] == 0
        r['false_edges_while_cs_low'] = sum(cs_low(t) for t in false_edges)
        lat, done, unread = [], [], 0
        for a, b in zip(real, real[1:] + [float('inf')]):
            i = bisect.bisect_right(cs_fall, a)
            if i == len(cs_fall) or cs_fall[i] >= b:
                if b != float('inf'):
                    unread += 1                 # 下一个 DRDY 来之前没读这一帧
                continue
            j = bisect.bisect_right(cs_rise, cs_fall[i])
            if j == len(cs_rise):
                continue
            lat.append(cs_fall[i] - a)
            done.append(cs_rise[j] - a)
            if cs_rise[j] > b:
                unread += 1                     # 读到一半被下一帧追上
        r['unread_frames'] = unread
        if done:
            r['read_start_max_us'] = round(max(lat) * 1e6, 1)
            r['read_done_max_us'] = round(max(done) * 1e6, 1)
            r['margin_min_us'] = round((period - max(done)) * 1e6, 1)
        if unread:
            bad.append(f'{unread} 帧没在下一个 DRDY 前读完')
        elif done and r['margin_min_us'] < min_margin:
            # 读完了但离下一帧太近：BLE 中断一晚就会漏帧
            bad.append(f"读帧余量最小 {r['margin_min_us']} µs，低于 {min_margin} µs")
        if has_sclk:
            rise = edges(sig['SCLK'], 1)
            per_burst, inner = [], []
            for a, b in zip(cs_fall, cs_rise[bisect.bisect_right(cs_rise, cs_fall[0]):] if cs_fall else []):
                lo, hi = bisect.bisect_left(rise, a), bisect.bisect_left(rise, b)
                per_burst.append(hi - lo)
                inner += [y - x for x, y in zip(rise[lo:hi], rise[lo + 1:hi])]
            if per_burst:
                r['sclk_per_read'] = statistics.median(per_burst)
            if inner:
                r['sclk_mhz'] = round(1 / statistics.median(inner) / 1e6, 3)
    r['ok'] = not bad
    r['reason'] = '；'.join(bad) or '通过'
    return r


def run(path, fs, tol, drdy, cs, sclk, min_margin=20.0):
    names = {'DRDY': drdy}
    if cs:
        names['CS'] = cs
    if sclk:
        if not cs:
            raise SystemExit('看 SCLK 需要同时给 CS')
        names['SCLK'] = sclk
    reader = read_vcd if path.lower().endswith('.vcd') else read_csv
    raw, t_end = reader(path, list(names.values()))
    sig = {k: raw[v] for k, v in names.items()}
    return analyze(sig, t_end, fs, tol, bool(cs), bool(sclk), min_margin)


def synth(path, fs=2000, seconds=1.0, sclk_hz=2e6, glitches=0, drop=False, skip_read=False):
    """合成 R01 时序：DRDY 每周期落下，30 µs 后 CS 拉低读 216 个时钟，第一个时钟处 DRDY 回高。
    读是一帧接一帧顺序做的（和固件一样）：上一帧没读完，下一帧只能往后拖；拖过下一个 DRDY 就整帧跳过。"""
    ev, n, cursor = [], int(fs * seconds), 0.0
    half = 0.5 / sclk_hz
    for k in range(n):
        t = 100e-6 + k / fs                     # 不从 0 开始：首个沿落在 t=0 会被当成初值
        if drop and k == n // 2:
            continue
        ev.append((t, 'd', 0))
        cs0 = max(t + 30e-6, cursor)
        if (skip_read and k == n // 3) or cs0 >= t + 1 / fs:
            ev.append((t + 0.4 / fs, 'd', 1))   # 没人读，DRDY 自己在下一帧前回高
            continue
        ev.append((cs0, 'c', 0))
        for i in range(216):
            ev.append((cs0 + 1e-6 + 2 * i * half, 's', 1))
            ev.append((cs0 + 1e-6 + (2 * i + 1) * half, 's', 0))
        ev.append((cs0 + 1e-6 + half, 'd', 1))
        cs1 = cs0 + 2e-6 + 216 * 2 * half
        ev.append((cs1, 'c', 1))
        cursor = cs1 + 2e-6
        if k < glitches:                        # 读帧中途 DRDY 被 SCLK 带出一个 1 µs 的低脉冲
            g = cs0 + 20e-6
            ev += [(g, 'd', 0), (g + 1e-6, 'd', 1)]
    ev.sort()
    with open(path, 'w') as f:
        f.write('$timescale 1 ns $end\n$scope module top $end\n'
                '$var wire 1 ! DRDY $end\n$var wire 1 " CS $end\n$var wire 1 # SCLK $end\n'
                '$upscope $end\n$enddefinitions $end\n#0\n$dumpvars\n1!\n1"\n0#\n$end\n')
        code = {'d': '!', 'c': '"', 's': '#'}
        for t, w, v in ev:
            f.write(f'#{round(t * 1e9)}\n{v}{code[w]}\n')
        f.write(f'#{round(seconds * 1e9)}\n')


def self_check():
    cases = [  # (说明, 合成参数, 分析时给的 fs, 应该通过吗)
        ('干净 2k / 2MHz', {}, 2000, True),
        ('读帧中 3 个假沿', {'glitches': 3}, 2000, False),
        ('少一个 DRDY 沿', {'drop': True}, 2000, False),
        ('有一帧没读', {'skip_read': True}, 2000, False),
        ('采样率配错', {}, 4000, False),
        ('4k 下 1MHz 只剩 2 µs 余量', {'fs': 4000, 'sclk_hz': 1e6}, 4000, False),
        ('4k 下 0.8MHz 读不完', {'fs': 4000, 'sclk_hz': 0.8e6}, 4000, False),
        ('4k 下 4MHz', {'fs': 4000, 'sclk_hz': 4e6}, 4000, True),
    ]
    failed = 0
    with tempfile.TemporaryDirectory() as tmp:
        for name, kw, fs, want in cases:
            p = f'{tmp}/x.vcd'
            synth(p, **kw)
            r = run(p, fs, 0.03, 'DRDY', 'CS', 'SCLK')
            good = r['ok'] == want
            failed += not good
            print(('PASS' if good else 'FAIL'), name, '→', r['reason'])
        p = f'{tmp}/c.vcd'
        synth(p, glitches=3)
        r = run(p, 2000, 0.03, 'DRDY', 'CS', 'SCLK')
        extra = [('假沿都在 CS 低电平内', r['false_edges_while_cs_low'] == 3),
                 ('每帧 216 个时钟', r['sclk_per_read'] == 216),
                 ('SCLK 测得 2MHz', abs(r['sclk_mhz'] - 2.0) < 0.01)]
        synth(p)
        r = run(p, 2000, 0.03, 'DRDY', None, None)
        extra.append(('只给 DRDY 也能判', r['ok'] and r['real_edges'] == 2000))
        # 同一份数据转成 Saleae 式 CSV，结论必须一样
        tr, _ = read_vcd(p, ['DRDY', 'CS'])
        rows = sorted({t for n in tr for t, _ in tr[n]})
        with open(f'{tmp}/c.csv', 'w') as f:
            f.write('Time [s],DRDY,CS\n')
            lv = {'DRDY': 1, 'CS': 1}
            idx = {n: 0 for n in tr}
            for t in rows:
                for n in tr:
                    while idx[n] < len(tr[n]) and tr[n][idx[n]][0] <= t:
                        lv[n] = tr[n][idx[n]][1]
                        idx[n] += 1
                f.write(f'{t:.9f},{lv["DRDY"]},{lv["CS"]}\n')
        r2 = run(f'{tmp}/c.csv', 2000, 0.03, 'DRDY', 'CS', None)
        extra.append(('CSV 与 VCD 结论一致', r2['ok'] and r2['real_edges'] == r['real_edges']))
        for name, good in extra:
            failed += not good
            print(('PASS' if good else 'FAIL'), name)
    print('drdy_check self-check', 'FAIL' if failed else 'PASS')
    return 1 if failed else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('capture', nargs='?')
    ap.add_argument('--fs', type=float, help='标称采样率，2000 或 4000')
    ap.add_argument('--fs-tol', type=float, default=0.03, help='实测采样率允许偏离比例（假设值，ADS 内部振荡器误差待按手册核）')
    ap.add_argument('--drdy', default='DRDY')
    ap.add_argument('--cs', default='CS', help="不接 CS 时传 ''")
    ap.add_argument('--sclk', default='', help='短抓时给 SCLK 的信号名')
    ap.add_argument('--min-margin-us', type=float, default=20.0, help='读完到下一个 DRDY 的最小余量（假设值，台架前冻结）')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.check:
        return self_check()
    if not a.capture or not a.fs:
        ap.print_usage()
        return 2
    r = run(a.capture, a.fs, a.fs_tol, a.drdy, a.cs or None, a.sclk or None, a.min_margin_us)
    if a.json:
        print(json.dumps(r, ensure_ascii=False))
    else:
        for k, v in r.items():
            print(f'{k}: {v}')
    return 0 if r['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())

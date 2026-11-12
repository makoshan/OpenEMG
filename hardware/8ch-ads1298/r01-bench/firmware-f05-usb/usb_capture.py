"""F05-USB 主机采集：经 USB 串口发命令、收帧、原样归档。只许离体（J1-12 拔掉时互锁失效）。

用法：python usb_capture.py --port /dev/cu.usbmodemXXXX --mode test --seconds 20 --out host/v12-captures/<新目录>
归档：raw.bin（串口原始字节，一字不改）、summary.json（解析统计）。
"""
from pathlib import Path
import argparse, json, struct, sys, time

MODES = {'test': b'TST1', 'short': b'SHT1', 'ext': b'EXR1', 'power': b'PWR1', 'idle': b'', 'diag': b'DIAG', 'blind': b'BLND', 'hold': b'HOLD'}  # 采样只开 TST1/SHT1；PWR1 只开电源；idle 不发命令只看状态
FAULTS = ['None', 'Locked', 'Argument', 'Rails', 'Identity', 'Readback', 'Frame', 'Overrun', 'Timeout', 'Cancelled']


def crc16(data, crc=0xFFFF):
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def encode(kind, payload):
    body = bytes([kind, len(payload)]) + payload
    return b'\xa5\x5a' + body + struct.pack('<H', crc16(body))


class Parser:
    """逐字节找帧头；CRC 不对就丢一个字节重新同步，计入 crc_errors，不猜内容。"""
    def __init__(self):
        self.buf = bytearray()
        self.crc_errors = 0

    def feed(self, data):
        self.buf += data
        out = []
        while True:
            i = self.buf.find(b'\xa5\x5a')
            if i < 0:
                del self.buf[:max(0, len(self.buf) - 1)]
                return out
            del self.buf[:i]
            if len(self.buf) < 4 or len(self.buf) < 6 + self.buf[3]:
                return out
            n = self.buf[3]
            body, crc = bytes(self.buf[2:4 + n]), struct.unpack_from('<H', self.buf, 4 + n)[0]
            if crc16(body) != crc:
                self.crc_errors += 1
                del self.buf[:1]
                continue
            out.append((body[0], body[2:]))
            del self.buf[:6 + n]


def decode_sample(p):
    seq, t_us = struct.unpack_from('<II', p)
    frame = p[8:35]  # seq 最高位=固件推算的帧（DOUT 沿漏看，时间戳是算的），低 31 位是真序号
    ch = []
    for i in range(8):
        v = int.from_bytes(frame[3 + 3 * i:6 + 3 * i], 'big')
        ch.append(v - (1 << 24) if v & 0x800000 else v)
    return seq & 0x7FFFFFFF, t_us, frame[0] & 0xF0, ch, bool(seq >> 31)


def decode_status(p):
    fault, active, released, oe_n, edges, sent, usb_full, avdd_mv, vbat_mv = struct.unpack('<BBBBIIIHH', p)
    return dict(fault=fault, fault_name=FAULTS[fault] if fault < len(FAULTS) else f'?{fault}',
                active=bool(active), released=bool(released), drdy_edges=edges, sent=sent, usb_full=usb_full,
                last_check_oe_n=None if oe_n == 0xFF else oe_n,
                last_check_avdd_V=None if avdd_mv == 0xFFFF else avdd_mv / 1000,
                xiao_vbat_V=None if vbat_mv == 0xFFFF else vbat_mv / 1000)


def square_check(c):
    """内部测试源应是两电平方波：按中点分两堆，两堆都要有足够样本、堆内离散远小于两堆间距。"""
    if len(c) < 200:
        return dict(ok=False, why='样本太少')
    mid = (min(c) + max(c)) / 2
    lo, hi = [v for v in c if v < mid], [v for v in c if v >= mid]
    if min(len(lo), len(hi)) < 0.2 * len(c):
        return dict(ok=False, why='不是两电平')
    m_lo, m_hi = sum(lo) / len(lo), sum(hi) / len(hi)
    step = m_hi - m_lo
    # 数字滤波会在每个跳变沿留下几个中间值：去掉跳变前后各 3 个样本再算离散
    flips = [i for i, (a, b) in enumerate(zip(c, c[1:])) if (a < mid) != (b < mid)]
    near = set(j for i in flips for j in range(i - 2, i + 4))
    dev = sorted(abs(v - (m_lo if v < mid else m_hi)) for i, v in enumerate(c) if i not in near)
    spread = dev[int(0.99 * (len(dev) - 1))] if dev else float('inf')
    edges = len(flips)
    return dict(ok=step > 0 and spread < 0.25 * step, step=round(step), spread=round(spread), transitions=edges)


def summarize(frames, crc_errors, mode=None):
    meta, statuses, seqs, chans, bad_head, t, inferred, edge_report, drdy_select = None, [], [], [[] for _ in range(8)], 0, [], 0, None, None
    for kind, p in frames:
        if kind == 3:
            m = json.loads(p.decode())
            if m.get('diag'):
                if m.get('diag') == 3:
                    edge_report = m
                elif m.get('diag') == 7:  # 启动自检选了 DRDY 脚还是 DOUT 代 DRDY
                    drdy_select = m
                print('诊断：', json.dumps(m, ensure_ascii=False), flush=True)
            else:
                meta = m
        elif kind == 2:
            statuses.append(decode_status(p))
        elif kind == 1:
            seq, t_us, head, ch, inf = decode_sample(p)
            inferred += inf
            seqs.append(seq); t.append(t_us)
            bad_head += head != 0xC0
            for i, v in enumerate(ch):
                chans[i].append(v)
    gaps = sum(1 for a, b in zip(seqs, seqs[1:]) if b != a + 1)
    dt = [(b - a) & 0xFFFFFFFF for a, b in zip(t, t[1:])]
    last = statuses[-1] if statuses else None
    checks = None
    if mode == 'test':
        sq = [square_check(c) for c in chans]
        steps = [x['step'] for x in sq if x['ok']]
        checks = dict(square=sq, all_square=all(x['ok'] for x in sq),
                      steps_consistent=len(steps) == 8 and max(steps) <= 1.2 * min(steps),
                      no_usb_full=bool(last) and last['usb_full'] == 0,
                      edges_match_sent=bool(last) and abs(last['drdy_edges'] - last['sent']) <= 1)
    return dict(meta=meta, mode=mode, checks=checks, samples=len(seqs), inferred_samples=inferred, edge_report=edge_report, drdy_select=drdy_select, seq_gaps=gaps, crc_errors=crc_errors, bad_status_header=bad_head,
                first_seq=seqs[0] if seqs else None, last_seq=seqs[-1] if seqs else None,
                mean_interval_us=sum(dt) / len(dt) if dt else None,
                channels=[dict(min=min(c), max=max(c), p2p=max(c) - min(c), mean=round(sum(c) / len(c))) if c else None for c in chans],
                last_status=statuses[-1] if statuses else None, status_frames=len(statuses),
                physical_device_verified=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--port', required=True)
    ap.add_argument('--mode', choices=MODES, required=True)
    ap.add_argument('--seconds', type=float, default=20)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--reg', action='append', default=[], help='采集中改寄存器，aavv 十六进制，只放行内部信号（固件再查一遍）')
    a = ap.parse_args()
    if a.out.exists():
        ap.error('归档目录已存在，拒绝覆盖')
    import serial  # 只在真采时需要
    a.out.mkdir(parents=True)
    raw = open(a.out / 'raw.bin', 'wb')
    parser, frames = Parser(), []
    with serial.Serial(a.port, 115200, timeout=0.05) as s:
        s.dtr = True
        time.sleep(0.5)
        s.reset_input_buffer()
        if a.mode == 'ext':
            print('外部输入：J3 只许接信号发生器和分压器，绝不接人体（J1-12 接地时互锁失效）', flush=True)
        s.write(b'META\n')
        if MODES[a.mode]:
            s.write(MODES[a.mode] + b'\n')
        for r in a.reg:
            s.write(b'W' + r.encode() + b'\n')
        print('已发送', MODES[a.mode].decode(), '；启动约需 6 秒（POR 5s + 参考 1s），这 6 秒算在 --seconds 里', flush=True)
        end = time.monotonic() + a.seconds
        while time.monotonic() < end:
            data = s.read(4096)
            if data:
                raw.write(data)
                new = parser.feed(data)
                frames += new
                if a.mode in ('power', 'idle'):  # 电源测试：实时打印固件读到的 AVDD 和 OE_N
                    for kind, p in new:
                        if kind == 2:
                            st = decode_status(p)
                            print(f"AVDD={st['last_check_avdd_V']} V  OE_N={st['last_check_oe_n']}  电池={st['xiao_vbat_V']} V  fault={st['fault_name']}", flush=True)
        s.write(b'STOP\n')
        stop_end = time.monotonic() + 1
        while time.monotonic() < stop_end:
            data = s.read(4096)
            if data:
                raw.write(data)
                frames += parser.feed(data)
    raw.close()
    summary = summarize(frames, parser.crc_errors, a.mode)
    (a.out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    # CRC 全对只说明 USB 没传错；推算帧和非主动停机都判不通过
    last = summary['last_status'] or {}
    ok = (summary['samples'] and not summary['seq_gaps'] and not summary['crc_errors'] and not summary['bad_status_header']
          and not summary['inferred_samples'] and last.get('fault_name') in ('None', 'Cancelled'))
    if a.mode == 'test':
        c = summary['checks']
        # 台阶一致性只报告不判：R01 实测测试源幅度随增益/幅度压缩、各路不同，而电源和温度通道核过增益准确（README）
        ok = ok and c['all_square'] and c['no_usb_full'] and c['edges_match_sent']
    print('结论：', '通过' if ok else '不通过', '（主机判读，不是实物验收）')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

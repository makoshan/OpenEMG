"""Self-guided on-device gesture trial over USB: prompts each action, reads the 2 Hz 'w'
stream and any GESTURE events for that action, and prints what the watch decided.
Run from Terminal; the watch must be worn. Nothing is uploaded or triggered."""
import re, sys, time
from pathlib import Path
import serial
from serial.tools import list_ports

BOARD = '9B648DB7317019E2'
PLAN = [('直拳', 'punch')] * 5 + [('顺时针画圈', 'circle')]


def port():
    p = [x for x in list_ports.comports() if x.serial_number == BOARD]
    if len(p) != 1 or p[0].pid != 0x8045: sys.exit(f'MAKO 应用模式未找到: {[(x.device, hex(x.pid)) for x in p]}')
    return p[0].device


class Reader:
    """Drains the port continuously on a thread. macOS CDC stops its IN pipe once ~1 KB sits
    unread, and a tcflush (reset_input_buffer) on a stopped pipe leaves it silent for good;
    so the host must never stop reading and must never flush — take lines from here instead."""
    def __init__(self, link):
        import threading, collections
        self.link, self.lines, self.stop = link, collections.deque(), False
        threading.Thread(target=self.run, daemon=True).start()
    def run(self):
        buf = ''
        while not self.stop:
            n = self.link.in_waiting
            if n:
                buf += self.link.read(n).decode('ascii', 'replace')
                while '\n' in buf:
                    line, buf = buf.split('\n', 1); self.lines.append(line)
            else:
                time.sleep(.02)
    def take(self):
        out = []
        while True:
            try: out.append(self.lines.popleft())
            except IndexError: return out


def drain(link, seconds, sink):
    """Kept for callers without a Reader: read-and-discard is safe, tcflush is not."""
    end = time.time() + seconds; buf = ''
    while time.time() < end:
        n = link.in_waiting
        if n:
            buf += link.read(n).decode('ascii', 'replace')
            while '\n' in buf:
                line, buf = buf.split('\n', 1); sink.append(line)
        else:
            time.sleep(.02)


def summarise(lines, expect):
    wins = [l for l in lines if l.startswith('G ')]
    events = [l.split()[1] for l in lines if l.startswith('GESTURE')]
    best = {}
    for l in wins:
        parts = l.split(); scores = list(map(float, parts[-4:])); am = parts[2].split('=')[1]
        best[am] = max(best.get(am, 0), max(scores))
    rebooted = any(l.startswith('MAKO DAILY') or 'sync=0' in l for l in lines)
    top = max(best.items(), key=lambda kv: kv[1]) if best else ('?', 0)
    verdict = '✓ 识别' if expect in events else ('△ argmax 对但分数没过门槛/门控' if top[0] == expect else '✗ 判成 ' + top[0])
    return f'{verdict:22} 窗口 {len(wins):2}  事件 {events or "无"}  各类最高分 ' + ' '.join(f'{k}={v:.2f}' for k, v in sorted(best.items())) + ('  ★中途重启' if rebooted else '')


def main():
    log = Path(__file__).parent / 'research' / f'gesture-trial-{time.strftime("%Y%m%d-%H%M%S")}.txt'
    with serial.Serial(port(), 115200, timeout=.2, write_timeout=2) as link:
        time.sleep(2); reader = Reader(link); link.write(b'w\n'); time.sleep(3); junk = reader.take()
        # Fail fast: no status line in 3 s means another process owns the port or the app is
        # silent; six actions of "0 windows" would otherwise look like a model verdict.
        if not any(l.startswith('ver=') for l in junk):
            sys.exit('手表 3 秒内没有任何状态行：检查串口是否被 8766/其它进程占用（lsof /dev/cu.usbmodem*），或 upgrade.py --check')
        if not any('WSTREAM on' in l for l in junk):
            sys.exit('未收到 WSTREAM on：固件没有 w 命令（需 1.7.3+），upgrade.py --check 看版本')
        results = []
        try:
            for i, (name, expect) in enumerate(PLAN, 1):
                input(f'[{i}/{len(PLAN)}] {name}：准备好按 Enter：')
                for n in (3, 2, 1): print(n, flush=True); time.sleep(1)
                reader.take()                      # discard what arrived while waiting; never flush
                print('\a开始', flush=True); time.sleep(4.5); lines = reader.take()
                r = summarise(lines, expect); results.append((name, r)); print('   ', r, flush=True)
                log.parent.mkdir(exist_ok=True)
                with log.open('a') as f: f.write(f'## {i} {name} ({expect})\n' + '\n'.join(lines) + '\n')
        finally:
            link.write(b'w\n'); time.sleep(.3); reader.stop = True
    print('\n结果：'); [print(f'  {n}: {r}') for n, r in results]; print('日志:', log)


if __name__ == '__main__':
    if '--check' in sys.argv:
        s = summarise(['G punch argmax=punch 0.10 0.05 0.80 0.05', 'GESTURE punch 0.80'], 'punch'); assert s.startswith('✓')
        s = summarise(['G other argmax=punch 0.10 0.05 0.55 0.30'], 'punch'); assert s.startswith('△')
        s = summarise(['G other argmax=other 0.0 0.0 0.0 1.0', 'MAKO DAILY 1.7.3'], 'punch'); assert s.startswith('✗') and '重启' in s
        print('PASS: verdicts for recognised, under-threshold, misclassified and rebooted'); sys.exit(0)
    main()

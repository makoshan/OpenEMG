"""控制串口：把实时识别结果从另一个串口发给外设（唯理上位机「控制串口」的 Mac 版）。

格式（唯理原格式加密看不到，2026-10-15 Mako 定）：默认 115200 8N1，认出的动作一变就发一行 ASCII「编号\\n」，
经典组 classic_N 发 N，放松和随意动手（不触发）都发 0；同一编号保持不重复发，其它动作组的类别不发。

    python3 wl8_ctrl.py --check      # 假串口 + 本机伪终端（pty）端到端自检
"""
import re
import threading
import time
from collections import deque

BAUDS = (9600, 115200)
STABLE_N = 3          # 连续 3 次同一类（服务端 100 ms 一次 → 300 ms）才算认出，和页面 STABLE_N 同口径


def code(label):
    """类别 → 发出的编号。放松和随意动手（*_move，不触发）发 0，classic_N → N，其它类别不发（None）。"""
    if 'rest' in label or label.endswith('_move'):
        return 0
    m = re.fullmatch(r'classic_(\d+)', label)
    return int(m.group(1)) if m else None


def _open_serial(port, baud):
    import serial
    return serial.Serial(port, baud, timeout=0, write_timeout=.2, exclusive=True)


class CtrlSerial:
    def __init__(self, opener=_open_serial):
        self.opener, self.lock = opener, threading.Lock()
        self.opening = threading.Lock()                  # open 整段串行：连改两次波特率时两个请求不交错
        self.conn, self.port, self.baud, self.error = None, '', 115200, ''
        self.log = deque(maxlen=20)
        self.reset()

    def reset(self):
        """识别开始 / 停止时清掉防抖：下一次认出的动作一定会发。"""
        self.cand, self.n, self.sent = None, 0, None

    def open(self, port, baud=115200):
        # 兼容 macOS (/dev/cu.*, /dev/ttys*) 与 Linux (/dev/ttyUSB*, /dev/ttyACM*, /dev/pts/* 伪终端自检)
        if not isinstance(port, str) or not re.fullmatch(r'/dev/(?:(?:cu\.|tty\.|ttys|ttyUSB|ttyACM|ttyAMA|ttyS)[\w.\-]+|pts/\d+)', port):
            raise ValueError('控制串口要选 /dev/cu.* 或 /dev/ttyUSB* /dev/ttyACM* 这样的串口')
        if baud not in BAUDS:
            raise ValueError(f'波特率只支持 {"、".join(map(str, BAUDS))}')
        with self.opening:
            self.close()
            try:
                conn = self.opener(port, baud)
            except Exception as e:                           # 被占用 / 拔了：如实告诉页面，不抛 500
                self.port, self.baud, self.error = port, baud, f'控制串口打不开：{e}'
                raise ValueError(self.error) from e
            with self.lock:
                self.conn, self.port, self.baud, self.error = conn, port, baud, ''
            self.reset()
            return self.state()

    def close(self):
        with self.lock:
            conn, self.conn = self.conn, None
        if conn is not None:
            try: conn.close()
            except Exception: pass

    def _write(self, num, label):
        with self.lock:
            if self.conn is None:
                return False
            try:
                self.conn.write(f'{num}\n'.encode('ascii'))
            except Exception as e:                           # 拔线：关口、记原因，识别照跑
                try: self.conn.close()
                except Exception: pass
                self.conn, self.error = None, f'控制串口断开：{e}'
                return False
            self.log.appendleft({'t': round(time.time(), 3), 'code': num, 'label': label})
            return True

    def test(self):
        if self.conn is None:
            raise ValueError('控制串口还没打开')
        if not self._write(0, 'test'):
            raise ValueError(self.error or '控制串口写入失败')
        self.sent = None                                     # 外设刚收到 0：下一次认出的动作要重新发，哪怕和上次一样
        return self.state()

    def feed(self, pred):
        """每次识别结果（已过门槛）喂进来；稳定了且和上次发的不同才写一行。"""
        if self.conn is None or not pred:
            return
        top = pred.get('top')
        self.n = self.n + 1 if top == self.cand else 1
        self.cand = top
        num = code(top)
        # 按编号去重：放松和随意动手都是 0，手乱动时两者来回跳也只发一次 0（复核 #77）
        if self.n < STABLE_N or num is None or num == self.sent:
            return
        if self._write(num, top):
            self.sent = num

    def state(self):
        return {'port': self.port, 'baud': self.baud, 'open': self.conn is not None, 'error': self.error, 'log': list(self.log)}


def check():
    class Fake:
        def __init__(self): self.out, self.dead = b'', False
        def write(self, b):
            if self.dead: raise OSError('设备已拔出')
            self.out += b
        def close(self): pass
    fake = Fake()
    c = CtrlSerial(opener=lambda port, baud: fake)
    for bad in (('COM3', 115200), ('/dev/cu.x;rm', 115200), ('/dev/pts/x', 115200), ('/dev/pts/0;rm', 115200), ('/dev/cu.usbserial-1', 4800)):
        try: c.open(*bad)
        except ValueError: continue
        raise AssertionError(f'坏参数没被拒绝 {bad}')
    for ok_port in ('/dev/pts/0', '/dev/ttyUSB0', '/dev/ttyACM0', '/dev/cu.usbserial-1'):
        c.open(ok_port)
    assert code('classic_move') == 0 and code('classic_rest') == 0 and code('classic_16') == 16 and code('finger_index') is None
    seq = ['classic_rest'] * 3 + ['classic_3'] * 2 + ['classic_rest'] + ['classic_3'] * 5 + ['classic_12'] * 3 + ['finger_index'] * 4 + ['classic_rest'] * 3
    for top in seq:
        c.feed({'top': top})
    assert fake.out == b'0\n3\n12\n0\n', fake.out                  # 抖两下不发、保持不重复、别组类别不发
    assert [x['code'] for x in c.state()['log']] == [0, 12, 3, 0]
    before = fake.out
    for top in ['classic_move'] * 3 + ['classic_rest'] * 3 + ['classic_move'] * 3:
        c.feed({'top': top})
    assert fake.out == before, fake.out                          # 已经发过 0：放松 ↔ 随意动手来回切不再发
    for top in ['classic_2'] * 3 + ['classic_move'] * 3 + ['classic_rest'] * 3:
        c.feed({'top': top})
    assert fake.out == before + b'2\n0\n', fake.out
    c.test(); c.feed({'top': 'classic_rest'})             # 测试发了 0 之后保持放松也要重发一次，外设才跟实际对上
    assert fake.out.endswith(b'0\n0\n'), fake.out
    fake.dead = True
    for _ in range(3): c.feed({'top': 'classic_5'})
    st = c.state(); assert not st['open'] and '断开' in st['error'], st
    try: c.test()
    except ValueError: pass
    else: raise AssertionError('关着的口居然能发测试')
    c2 = CtrlSerial(opener=lambda p, b: (_ for _ in ()).throw(OSError('Resource busy')))
    try: c2.open('/dev/cu.busy')
    except ValueError as e: assert '打不开' in str(e) and 'busy' in c2.state()['error']
    else: raise AssertionError('打不开的口没报错')
    pty_note = '无 pyserial，跳过 pty'
    try:
        import serial  # noqa: F401
    except ImportError:
        serial = None
    if serial is not None:                                   # 真 pyserial 打开本机伪终端，从另一端读回
        import os
        master, slave = os.openpty()
        real = CtrlSerial()
        real.open(os.ttyname(slave), 115200)
        real.test()
        for _ in range(3): real.feed({'top': 'classic_7'})
        time.sleep(.05)
        got = os.read(master, 64)
        real.close(); os.close(master); os.close(slave)
        assert got == b'0\n7\n', got
        pty_note = 'pty 端到端读回 0\\n7\\n'
    print(f'wl8_ctrl check passed: 防抖 3 帧、保持不重发、别组不发、拔线关口、打不开报原因；{pty_note}')


if __name__ == '__main__':
    import sys
    if '--check' in sys.argv:
        check()

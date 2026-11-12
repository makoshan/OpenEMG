# 录制一批的两个停法：一帧都没收到就当场停（数据源断了，后面只会白录）；页面点「停下这一批」也会停。
# Run: python3 check_emg_record_stop.py
import tempfile, threading, time
from pathlib import Path
import emg_web

LABEL = emg_web.LABELS.get('emg', emg_web.TIERS)[0]


class StubRig:
    kind = 'emg'
    def __init__(self, error=None, slow=0):
        self.calls, self.error, self.slow = 0, error, slow
    def take(self, *args):
        self.calls += 1
        time.sleep(self.slow)
        if self.error: raise ValueError(self.error)
        return {'frames': 4000}


def run(rig, count, stop_after=None):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        s = emg_web.Session(rig, {'train': {'emg': root / 'train'}, 'rewear': {'emg': root / 'rewear'}})
        s.record(LABEL, count, 'train', 'test', 1, 'high', countdown=0)
        if stop_after is not None:
            threading.Timer(stop_after, lambda: setattr(s, 'stop_requested', True)).start()
        deadline = time.monotonic() + 5
        while s.busy and time.monotonic() < deadline: time.sleep(.01)
        assert not s.busy, '这一批没结束'
        return s


s = run(StubRig('只收到 0 帧（应 4000）'), 5)
assert s.log[-1].endswith('尝试 1 条，收下 0 条进 train/'), s.log[-3:]
assert any('没有收到任何数据，已停下这一批' in l for l in s.log)

r = StubRig('丢包 3'); run(r, 5)
assert r.calls == 5, '别的拒收原因照旧录满一批，只有 0 帧才停'

r = StubRig(slow=.15); s = run(r, 10, stop_after=.2)
assert 1 <= r.calls < 10 and any('已按要求停下这一批' in l for l in s.log), (r.calls, s.log[-3:])
assert s.log[-1].endswith(f'尝试 {r.calls} 条，收下 {r.calls} 条进 train/'), s.log[-1]

r = StubRig()
with tempfile.TemporaryDirectory() as tmp:
    s = emg_web.Session(r, {'train': {'emg': Path(tmp) / 'train'}, 'rewear': {'emg': Path(tmp) / 'rewear'}})
    s.stop_requested = True                        # 上一批留下的停止请求
    s.record(LABEL, 3, 'train', 'test', 1, 'high', countdown=0)
    while s.busy: time.sleep(.01)
assert r.calls == 3, '上一批的停止请求不能带到下一批'
print('PASS: 0 帧当场停本批、其它拒收照旧、页面停止生效且条数如实、停止不串到下一批')

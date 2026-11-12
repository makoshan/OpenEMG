"""校准真实录制入口的口令顺序、取消、失败与默认路径；不接设备。"""
from pathlib import Path
import tempfile
from unittest.mock import patch
import emg_web
import calibration_voice


def run_case(calibration=True, fail=False, cancel=False):
    events = []
    class Rig:
        kind = 'wl8'
        def take(self, *args, **kwargs):
            events.append('take')
            assert session.progress['phase'] == 'NOW'
            return {'frames': 4000}
    class Voice:
        def __init__(self, stopped): events.append('voice')
        def prepare(self, label):
            events.append('prepare:' + label)
            if cancel: session.stop_requested = True
            if fail: raise ValueError('语音失败')
        def cue(self, key, wait=True): events.append(key if wait else key + '!')   # ! = 不等播完就开窗
        def close(self): events.append('close')
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        sets = {s: {k: root / s / k for k in ('emg', 'emgimu', 'wl8')} for s in ('train', 'rewear')}
        # 不启动设备控制器；测试实际Session.record，不替换录制状态机。
        session = object.__new__(emg_web.Session)
        session.rig, session.sets, session.issue = Rig(), sets, None
        session.progress, session.log, session.stop_requested = {}, [], False
        session.start = lambda name, fn: fn()
        with patch.dict(emg_web.LABELS, wl8=('mouse_index', 'mouse_rest')), patch.object(calibration_voice, 'CalibrationVoice', Voice), patch.object(emg_web.time, 'sleep', lambda _: None):
            try: session.record('mouse_index', 1, 'train', '', 9, 'high', 3, calibration=calibration)
            except ValueError:
                assert fail or type(calibration) is not bool
                if not fail: raise
    return events


assert run_case() == ['voice', 'prepare:mouse_index', 'go!', 'take', 'release', 'close'], '「开始」要不等播完就开窗（go!），结束口令仍等播完'
# 非阻塞口令：cue(wait=False) 必须立刻返回、不等播放子进程结束（否则录制窗晚开 ≈ 音频时长）；wait=True 仍走 _run 等播完
def check_nonblocking_cue():
    import calibration_voice as cv, time as _t
    class P:
        def __init__(self, *a, **k): pass
        def poll(self): return None
        def terminate(self): pass
        def wait(self, timeout=None): pass
    real = cv.subprocess.Popen; cv.subprocess.Popen = P
    try:
        v = cv.CalibrationVoice(lambda: False); v.files = {'go': 'x.aiff'}
        t = _t.monotonic(); v.cue('go', wait=False); assert _t.monotonic() - t < .05, '非阻塞口令不能等播完'
        assert len(v.children) == 1, '非阻塞子进程要登记，close 时收掉'
        ran = []; v._run = lambda args, timeout=15: ran.append(args)
        v.cue('go'); assert ran and ran[0][0] == '/usr/bin/afplay', '阻塞口令仍走 _run 等播完'
        v.close()
    finally: cv.subprocess.Popen = real
check_nonblocking_cue()

assert run_case(False) == ['take'], '普通录制不加入校准语音'
assert run_case(fail=True) == ['voice', 'prepare:mouse_index', 'close'], '语音准备失败不能录数据'
assert run_case(cancel=True) == ['voice', 'prepare:mouse_index', 'close'], '放松提示阶段停下不能录数据'
try:
    # 非布尔值不能意外打开播报。
    run_case('true')
except ValueError:
    pass
else:
    raise AssertionError('校准选项字符串被接受')
print('校准口令：录制顺序、默认静音、失败不录、取消不录、类型校验通过')

# 保存前取消必须在真实Wl8实现生效；不能仅替身口头拒绝。
import wl8
with tempfile.TemporaryDirectory() as d:
    rig = wl8.FakeWl8Rig()
    root = Path(d)
    try: rig.take('pinch', 'high', root, '', 9, cancelled=lambda: True)
    except ValueError as e: assert '未保存' in str(e)
    else: raise AssertionError('取消的条目仍收下')
    assert not list(root.rglob('*.npz')), '取消后不能产生训练文件'
    rig.take('pinch', 'high', root, '', 9)
    assert len(list(root.rglob('*.npz'))) == 1, '未取消的阳性对照必须落盘'
print('校准取消：真实保存边界无文件，正常阳性对照一条通过')

# 固定口令缓存：同一句只合成一次，半文件/失败不会进入可复用缓存。
with tempfile.TemporaryDirectory() as d, patch.object(calibration_voice.Path, 'home', return_value=Path(d)), patch.object(calibration_voice.sys, 'platform', 'darwin'):
    v = calibration_voice.CalibrationVoice(lambda: False)
    calls = []
    def synth(args, timeout=15):
        assert args[0] == '/usr/bin/say' and timeout == 60
        calls.append(1); Path(args[-2]).write_bytes(b'x' * 8192)
    v._run = synth
    one = v._audio('缓存测试'); two = v._audio('缓存测试')
    assert one == two and len(calls) == 1
    def broken(args, timeout=15):
        Path(args[-2]).write_bytes(b'x' * 4096)
        raise ValueError('合成取消')
    v._run = broken
    try: v._audio('失败测试')
    except ValueError: pass
    else: raise AssertionError('合成失败仍被接受')
    assert len(list((Path(d) / '.cache/yuanli-calibration-voice').glob('*.aiff'))) == 1
    v.close()
print('语音缓存：相同口令仅合成一次，失败半文件不发布通过')

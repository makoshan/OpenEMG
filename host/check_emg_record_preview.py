"""Verify preview arrives before the binary take, without consuming its bytes."""
import io
import zlib
from unittest.mock import patch
import numpy as np
import usb_emg

counts = usb_emg._synth('rest', np.random.default_rng(12)).astype('<i2')
payload = counts.tobytes()
frames = [f'S {i} 10 ' + ' '.join(map(str, counts[i:i+10])) for i in range(0, 2000, 10)]
class Serial:
    def __init__(self, corrupt=False):
        header = f'EMG 1000 2000 {zlib.crc32(payload):x} 1000 1003 0\n'
        self.data = io.BytesIO(('RECORDING 2\n'+'\n'.join(frames)+'\n'+header).encode()+ (payload[:-1]+bytes([payload[-1]^1]) if corrupt else payload))
        self.commands = []
    @property
    def in_waiting(self): return len(self.data.getbuffer())-self.data.tell()
    def read(self,n): return self.data.read(n)
    def write(self,b): self.commands.append(b)
for corrupt in (False,True):
    conn=Serial(corrupt); seen=[]
    def preview(line):
        assert conn.in_waiting >= len(payload), 'preview delivered after payload'
        seen.append(line)
    with patch.object(usb_emg,'_drain'):
        try: actual, worn, railed, timing=usb_emg.read_take(conn,preview=preview)
        except ValueError:
            assert corrupt
        else:
            assert not corrupt
            np.testing.assert_array_equal(actual,counts)
    assert seen==frames and conn.commands==[b'R']
print('PASS: 200 preview frames before payload; exact samples; corrupted CRC rejected')
for dropped in (False, True):
    conn = Serial()
    selected = frames[1:] if dropped else frames
    conn.data = io.BytesIO(('RECORDING 2\n' + '\n'.join(selected) + '\n' + f'EMGP 1000 2000 {zlib.crc32(payload):x} 1000 1003 0\n').encode())
    try:
        actual, *_ = usb_emg.read_take(conn, preview=lambda line: None, stream_only=True)
    except usb_emg.RejectedTake:
        assert dropped
    else:
        assert not dropped
        np.testing.assert_array_equal(actual, counts)
    assert conn.commands == [b'V']
print('PASS: stream-only raw reconstruction and CRC; dropped preview frame rejected')

conn=Serial(); order=[]
with patch.object(usb_emg,'_drain'), patch.object(usb_emg,'validate',side_effect=lambda *args: (order.append('validate') or (1000,0))):
    usb_emg.read_take(conn,preview=lambda line:None,on_received=lambda:order.append('resume'))
assert order == ['resume','validate']
print('PASS: live stream resumes before quality calculation')

conn=Serial(); events=[]
with patch.object(usb_emg, '_drain'):
    _, _, _, timing = usb_emg.read_take(conn, preview=lambda line: events.append('frame'),
        on_started=lambda timing: events.append('start'))
assert events[0] == 'start' and events[1:] == ['frame'] * 200
assert timing['command_sent_host_ns'] <= timing['recording_ack_host_ns'] <= timing['first_preview_host_ns'] <= timing['recording_received_host_ns']
assert timing['first_preview_device_ms'] == 0
conn=Serial(); conn.data=io.BytesIO(b'ERROR no capture\n'); events=[]
try:
    usb_emg.read_take(conn, preview=lambda line: None, on_started=lambda t: events.append('start'))
except (RuntimeError, TimeoutError, ValueError): pass
else: raise AssertionError('missing acknowledgement accepted')
assert not events, 'cue emitted without board acknowledgement'
print('PASS: cue follows device acknowledgement, precedes frames; missing acknowledgement never cues')

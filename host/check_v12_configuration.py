"""真实C发包→V12Rig：首次来源门、两次配置切换及非法重启反例。"""
import sys
from pathlib import Path
import v12
c=v12.load_codec()
packets=[bytes.fromhex(s) for s in Path(sys.argv[1]).read_text().splitlines()]
r=v12.V12Rig(allow_real=True);got=[];r.frame_subscribers.append(got.append)
for p in packets:r.feed_packet(p)
assert sum(len(a) for a in got)==3
assert len(r.rx.boundaries)==2 and r.rx.sessions==3 and r.rx.reordered==0
assert all(b['missing_samples'] is None for b in r.rx.boundaries)
for mode in ('denied','unmarked','duplicate'):
 q=v12.V12Rig(allow_real=mode!='denied')
 try:
  if mode=='denied':q.feed_packet(packets[0])
  else:
   q.feed_packet(packets[0]);p=bytearray(packets[1])
   if mode=='unmarked':p[3]&=~4
   else:q.feed_packet(p);p=packets[1]
   q.feed_packet(p)
 except ValueError:pass
 else:raise AssertionError(mode)
print('配置切换C→V12Rig通过：2边界，0拒收/乱序；来源门、无标记重启、重复边界均报错')

# 配置空档不属于段内时间戳异常；新段C DSP必须重新预热。
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'firmware/dsp-f03'))
from replay import replay,compile_library
with tempfile.TemporaryDirectory() as tmp:
    result=replay([dict(packet_hex=p.hex(),mtu=247) for p in packets],Path(tmp)/'replay',compile_library(tmp),2000,allow_real=True)
    assert result['timestamp_discontinuities']==0 and result['accepted_samples']==3
    assert [x['reason'] for x in result['resets']]==['session','configuration','configuration']
print('配置空档DSP回放通过：3段，0段内时间异常')

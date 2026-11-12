"""pack16 自检：用实际生成的 v12_stream.c 打包，主机 codec.decode_pack16 还原，必须逐帧等于原帧。不接设备。"""
from pathlib import Path
import importlib.util, random, shutil, subprocess, sys, tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location('dout_build', HERE / 'build.py')
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
spec = importlib.util.spec_from_file_location('v12_codec_py', ROOT / 'firmware/offline-f01/codec.py')
codec = importlib.util.module_from_spec(spec); sys.modules[spec.name] = codec; spec.loader.exec_module(codec)
TOOLCHAIN = 'platformio/toolchain-gccarmnoneeabi@1.120301.0'

HARNESS = r'''
#include "v12_stream.h"
#include <stdio.h>
#include <string.h>
static v12_stream s;
int main(void){
 if(v12_stream_init(&s,2000))return 2;
 unsigned n;uint64_t t=1000;
 while(scanf("%u",&n)==1){
  if(n==0xffffffffu){if(v12_stream_skip(&s,3))return 3;continue;}  /* 序号缺口 */
  int32_t raw[8];unsigned st,k;if(scanf("%x",&st)!=1)return 4;
  for(k=0;k<8;++k)if(scanf("%d",&raw[k])!=1)return 5;
  unsigned slot=(s.head+s.count)%V12_STREAM_RING;
  if(v12_stream_push(&s,raw,t)||s.count>V12_STREAM_RING)return 6;
  s.ring[slot].frame[0]=(uint8_t)(st>>16);s.ring[slot].frame[1]=(uint8_t)(st>>8);s.ring[slot].frame[2]=(uint8_t)st;
  t+=500;
  while(s.count>=n){const uint8_t *p;size_t len;if(v12_stream_peek(&s,247,&p,&len))return 7;
   for(size_t i=0;i<len;++i){printf("%02x",p[i]);}printf("\n");if(v12_stream_commit(&s))return 8;}
 }
 const uint8_t *p;size_t len;
 while(s.count){if(v12_stream_peek(&s,247,&p,&len))return 9;for(size_t i=0;i<len;++i){printf("%02x",p[i]);}printf("\n");v12_stream_commit(&s);}
 printf("cap %u\n",v12_pack16_capacity(247));
 return 0;
}
'''


def run(copies):
    stage = b.stage(TOOLCHAIN, copies)
    rng = random.Random(copies)
    frames, lines, v, seq = [], [], [0] * 8, 0
    expected = {}  # sequence -> 27 字节原帧
    for i in range(6000):
        if i == 3000:
            lines.append('4294967295'); seq += 3; continue
        # 随机游走 + 偶尔大跳（超 int16）+ 偶尔状态字变化，覆盖三种提前收包
        v = [max(-0x800000, min(0x7fffff, x + rng.randint(-3000, 3000) + (rng.choice([-1, 1]) * 40000 if rng.random() < .01 else 0))) for x in v]
        st = 0xc00000 | (0x0100 if rng.random() < .02 else 0)
        expected[seq] = bytes([st >> 16, st >> 8 & 255, st & 255]) + b''.join(x.to_bytes(3, 'big', signed=True) for x in v)
        seq += 1
        lines.append(f"{rng.choice([1, 5, 20, 40])} {st:x} " + ' '.join(map(str, v)))
    with tempfile.TemporaryDirectory(prefix='pack16-') as tmp:
        tmp = Path(tmp); (tmp / 'h.c').write_text(HARNESS)
        inc = ['-I' + str(stage / 'src'), '-I' + str(HERE / 'tests/stubs')]
        exe = tmp / 'h'
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', *inc, str(tmp / 'h.c'),
                        *(str(stage / 'src' / n) for n in ('v12_stream.c', 'v12_codec.c', 'v12_dsp.c')), '-lm', '-o', str(exe)], check=True)
        out = subprocess.run([str(exe)], input='\n'.join(lines) + '\n', capture_output=True, text=True, check=True).stdout.split('\n')
    assert out[-2] == f'cap {13 if copies == 1 else 6}', out[-2]
    rx = codec.Receiver(allow_real=True, decoder=lambda d, m: codec.decode_pack16(d, m, 1 + copies))
    got, sizes = {}, []
    for h in out[:-2]:
        data = bytes.fromhex(h); sizes.append(len(data)); assert len(data) <= 244
        p = rx.receive(data, 247)
        for k, f in enumerate(p.frames):
            got[p.sequence + k] = f
    assert got == expected, '还原帧与原帧不一致'
    assert rx.missing_samples == 3, rx.missing_samples  # 只有人为造的缺口
    # 反例：协议号不符、两份不一致、长度不对都要拒收
    good = bytes.fromhex(next(h for h in out if len(h) // 2 == max(sizes)))
    bads = [bytes([4 - copies]) + good[1:], good[:-1]]  # 协议号错、截断
    if copies == 2:
        bads.append(good[:-1] + bytes([good[-1] ^ 1]))  # 两份不一致
    for bad in bads:
        try:
            codec.decode_pack16(bad, 247, 1 + copies); raise SystemExit('反例没被拒收')
        except ValueError:
            pass
    frames_per_packet = len(expected) / len(sizes)
    print(f'copies={copies}：{len(expected)} 帧 / {len(sizes)} 包，平均 {frames_per_packet:.2f} 帧/包，最大 {max(sizes)} B，逐帧还原一致')


if __name__ == '__main__':
    plain = b.stage(TOOLCHAIN, 0)
    assert 'pack16' not in (plain / 'src/v12_stream.c').read_text() + (plain / 'src/main.cpp').read_text(), '默认构建不该带 pack16'
    run(1); run(2)
    assert 'stream.count<v12_pack16_capacity(link_mtu))return;' in (b.stage(TOOLCHAIN, 1) / 'src/flow_control.h').read_text(), '攒包门槛补丁没打上'
    sys.path.insert(0, str(ROOT / 'host'))
    import json, v12_ble
    meta = dict(profile='F05_ADS_CANDIDATE', protocol=2, pack16_copies=1, channels=8, fs_Hz=2000, spi_Hz=2000000,
                bench_measured=True, build_id='0' * 16)
    v12_ble.validate_metadata(json.dumps(meta).encode())
    for bad in (dict(pack16_copies=2), dict(protocol=4), dict(pack16_copies=None)):
        try:
            v12_ble.validate_metadata(json.dumps({**meta, **bad}).encode()); raise SystemExit(f'元数据反例没被拒收：{bad}')
        except ValueError:
            pass
    print('pack16 自检通过')

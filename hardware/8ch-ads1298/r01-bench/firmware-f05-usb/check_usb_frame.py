"""帧格式跨语言自检：C++ 编码器（src/usb_frame.h）输出的字节，Python 解析器必须原样解出；坏 CRC 必须被拒。
用法：python check_usb_frame.py   （需要 c++ 编译器；不接设备）"""
from pathlib import Path
import subprocess, sys, tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import usb_capture as uc  # noqa: E402

CPP = r'''
#include "usb_frame.h"
#include <cstdio>
int main(){
  uint8_t f[27]={0xC0,0,0}; for(int i=0;i<8;++i){f[3+3*i]=(i&1)?0xFF:0x00; f[4+3*i]=0x12; f[5+3*i]=uint8_t(i);}
  uint8_t out[300]; size_t n=usbf::sample(7,123456,f,out);
  n+=usbf::status(8,false,true,42,7,0,out+n,1,4987);
  for(size_t i=0;i<n;++i){printf("%02x",out[i]);} printf("\n");
}
'''


def main():
    with tempfile.TemporaryDirectory() as d:
        src, exe = Path(d) / 't.cpp', Path(d) / 't'
        src.write_text(CPP)
        subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', str(HERE / 'src'), str(src), '-o', str(exe)], check=True)
        data = bytes.fromhex(subprocess.run([str(exe)], capture_output=True, text=True, check=True).stdout.strip())
    p = uc.Parser()
    frames = p.feed(b'\x00\xa5junk' + data)  # 前面加垃圾，测重新同步
    assert [k for k, _ in frames] == [1, 2] and p.crc_errors == 0, frames
    seq, t, head, ch, inf = uc.decode_sample(frames[0][1])
    assert (seq, t, head, inf) == (7, 123456, 0xC0, False)
    seq2, *_, inf2 = uc.decode_sample(bytes([7, 0, 0, 0x80]) + frames[0][1][4:])  # 最高位=推算帧
    assert (seq2, inf2) == (7, True)
    assert ch == [0x001200 + i if i % 2 == 0 else (0xFF1200 + i) - (1 << 24) for i in range(8)], ch
    st = uc.decode_status(frames[1][1])
    assert st['fault_name'] == 'Timeout' and st['released'] and st['drdy_edges'] == 42 and st['sent'] == 7, st
    assert st['last_check_oe_n'] == 1 and st['last_check_avdd_V'] == 4.987, st
    assert uc.encode(1, frames[0][1]) == data[:len(data) - 26], 'Python 编码与 C++ 不一致'
    bad = bytearray(data); bad[10] ^= 1  # 改一个负载字节
    p2 = uc.Parser(); f2 = p2.feed(bytes(bad))
    assert [k for k, _ in f2] == [2] and p2.crc_errors >= 1, (f2, p2.crc_errors)
    s = uc.summarize(frames + [(3, b'{"diag":7,"drdy_source":"dout_mirror","d6_hits":0,"mode":0}')], 0)
    assert s['drdy_select']['drdy_source'] == 'dout_mirror', s['drdy_select']
    assert s['samples'] == 1 and s['seq_gaps'] == 0 and s['last_status']['fault'] == 8 and s['inferred_samples'] == 0
    # 方波判定：两电平方波通过；噪声、单电平不通过
    sqw = [10000 if (i // 500) % 2 else -10000 for i in range(4000)]
    assert uc.square_check(sqw)['ok']
    # 带滤波过渡样本的真实形状：每个沿两侧各有 2 个中间值，也必须判通过
    sqt = [(-10000 + 20000 * ((i % 1000) >= 500)) for i in range(4000)]
    for k in range(500, 4000, 500):
        sqt[k - 1], sqt[k], sqt[k + 1 if k + 1 < 4000 else k] = sqt[k - 1] // 2, 0, sqt[k + 1 if k + 1 < 4000 else k] // 2
    assert uc.square_check(sqt)['ok'], uc.square_check(sqt)
    assert not uc.square_check([0] * 4000)['ok']
    import random; random.seed(1)
    assert not uc.square_check([random.randint(-50, 50) for _ in range(4000)])['ok']
    print('PASS：USB 帧 C++→Python 解析、垃圾前缀重同步、坏 CRC 拒收、汇总统计、方波判定正反例；未接设备')


if __name__ == '__main__':
    main()

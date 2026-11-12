"""台架给 agent 的眼睛：固定机位拍照 + 逻辑分析仪命令行抓包，不用人拍照、不用人从 PulseView 导出。

只看不碰：不控上电、不刷机、不接人体；硬件锁规矩照旧。拍到的图、抓到的波形都只是证据，不是验收。

用法：
  bench_rig.py cams                                  # 列出摄像头
  bench_rig.py snap [--cam 桌上视角] [--label r01-top] # 拍一张，存 host/v12-captures/bench/
  bench_rig.py scan                                  # 列出 sigrok 认到的逻辑分析仪
  bench_rig.py la --driver fx2lafw --rate 24M --time 2s --map D0=DRDY,D1=CS,D2=SCLK --fs 2000
      # 抓包存 VCD，给了 --fs 就直接交给 drdy_check 判；长抓数沿用 --rate 1M --time 600s 且不接 SCLK
  bench_rig.py --check                               # 用 sigrok 的 demo 驱动做阳性对照，不需要硬件
退出码：0 通过，1 不通过或设备/输入有问题（看输出文字），2 用法不对。
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import drdy_check

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'v12-captures', 'bench')


def stamp(label, ext):
    os.makedirs(OUT, exist_ok=True)
    t = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    return os.path.join(OUT, f'{t}-{label}.{ext}' if label else f'{t}.{ext}')


def need(tool, hint):
    if not shutil.which(tool):
        raise SystemExit(f'没有 {tool}：{hint}')


def cameras():
    need('ffmpeg', 'brew install ffmpeg')
    p = subprocess.run(['ffmpeg', '-hide_banner', '-f', 'avfoundation', '-list_devices', 'true', '-i', ''],
                       capture_output=True, text=True)
    video = p.stderr.split('audio devices')[0]
    return [n for n in re.findall(r'\] \[\d+\] (.+)', video) if not n.startswith('Capture screen')]


def snap(cam, label, timeout=20):
    names = cameras()
    hit = [n for n in names if cam in n]
    if not hit:
        raise SystemExit(f'没有名字含「{cam}」的摄像头；现有 {names}')
    out = stamp(label, 'jpg')
    # 丢掉前 20 帧再存：刚开流时自动曝光还没稳，第一帧常常偏暗
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 'avfoundation', '-pixel_format', 'nv12',
           '-framerate', '30', '-i', hit[0], '-vf', r'select=gte(n\,20)', '-frames:v', '1', '-y', out]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise SystemExit(f'{timeout}s 没拍到：多半是相机权限没给（系统设置 → 隐私与安全性 → 相机），'
                         f'或 iPhone 连续互通相机没唤醒')
    if p.returncode or not os.path.exists(out) or os.path.getsize(out) < 5000:
        raise SystemExit(f'拍照失败：{p.stderr.strip()[-300:]}')
    return {'camera': hit[0], 'file': out, 'bytes': os.path.getsize(out)}


def la(driver, rate, dur, mapping, out=None, samples=None):
    need('sigrok-cli', 'brew install sigrok-cli')
    out = out or stamp('la', 'vcd')
    cmd = ['sigrok-cli', '-d', driver, '--config', f'samplerate={rate}', '--channels', mapping,
           '-O', 'vcd', '-o', out]
    cmd += ['--samples', str(samples)] if samples else ['--time', dur]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode or not os.path.exists(out):
        raise SystemExit(f'抓包失败（{" ".join(cmd)}）：{p.stderr.strip()[-300:]}')
    return out


def self_check():
    failed = 0
    with tempfile.TemporaryDirectory() as tmp:
        # 阳性对照：demo 驱动一定有跳变，抓不到或改名不生效就是管道坏了
        p = la('demo', '1M', None, 'D0=DRDY,D1=CS', f'{tmp}/demo.vcd', samples=20000)
        tr, t_end = drdy_check.read_vcd(p, ['DRDY', 'CS'])
        cases = [('demo 抓包能按新名字读回', all(len(tr[n]) > 2 for n in tr)),
                 ('抓包时长对得上 20000 点 @1MHz', abs(t_end - 0.02) < 0.002)]
        try:
            snap('不存在的相机xyz', None)
            cases.append(('相机名写错要报错', False))
        except SystemExit:
            cases.append(('相机名写错要报错', True))
    for name, good in cases:
        failed += not good
        print(('PASS' if good else 'FAIL'), name)
    print('bench_rig self-check', 'FAIL' if failed else 'PASS')
    return 1 if failed else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', nargs='?', choices=['cams', 'snap', 'scan', 'la'])
    ap.add_argument('--cam', default='桌上视角', help='摄像头名字里的一段；默认 iPhone 俯拍的桌上视角')
    ap.add_argument('--label', default='')
    ap.add_argument('--driver', default='fx2lafw', help='sigrok 驱动名，先跑 scan 看')
    ap.add_argument('--rate', default='24M', help='SCLK 4MHz 至少要 24M；只数 DRDY 沿 1M 够')
    ap.add_argument('--time', default='2s')
    ap.add_argument('--map', default='D0=DRDY,D1=CS,D2=SCLK', help='分析仪通道=信号名，只写接了的')
    ap.add_argument('--fs', type=float, help='给了就把抓包交给 drdy_check 判，2000 或 4000')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    if a.check:
        return self_check()
    if a.cmd == 'cams':
        print('\n'.join(cameras()))
        return 0
    if a.cmd == 'scan':
        need('sigrok-cli', 'brew install sigrok-cli')
        return subprocess.run(['sigrok-cli', '--scan']).returncode
    if a.cmd == 'snap':
        print(json.dumps(snap(a.cam, a.label), ensure_ascii=False))
        return 0
    if a.cmd == 'la':
        r = {'file': la(a.driver, a.rate, a.time, a.map)}
        if a.fs:
            names = dict(kv.split('=')[::-1] for kv in a.map.split(','))
            r['drdy'] = drdy_check.run(r['file'], a.fs, 0.03, 'DRDY', 'CS' if 'CS' in names else None,
                                       'SCLK' if 'SCLK' in names else None)
        print(json.dumps(r, ensure_ascii=False))
        return 0 if r.get('drdy', {}).get('ok', True) else 1
    ap.print_usage()
    return 2


if __name__ == '__main__':
    sys.exit(main())

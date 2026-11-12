"""OpenSignals (r)evolution 文本格式的读写（公开规范，support.pluxbiosignals.com ".TXT Format"，2022-10-24）。

    # OpenSignals Text File Format. Version 1
    # {"<device key>": {...头 JSON...}}
    # EndOfHeader
    nSeq<TAB>DI<TAB>CH1<TAB>...

只做两件事：把 take_file 里那份头原样写进第二行；把 nSeq / DI / 各通道按 tab 写出。
读回用 numpy.loadtxt(comments='#')，不自己写解析器。
"""
import json
from pathlib import Path

import numpy as np

MAGIC = '# OpenSignals Text File Format. Version 1'
END = '# EndOfHeader'


def write(path, header, data, di=None, device_key=None, fmt='%.6g'):
    """header：device_desc.header() 那份 dict；data：(n, ch) 数组（µV 或 raw，看 header['convertedValues']）。"""
    path = Path(path)
    data = np.asarray(data)
    if data.ndim != 2:
        raise ValueError('data 必须是 (n, ch)')
    n, ch = data.shape
    if len(header['column']) != 2 + ch:
        raise ValueError(f"header.column 有 {len(header['column'])} 列，数据是 {ch} 路 + nSeq + DI")
    if 'sampling rate' not in header:
        raise ValueError('header 缺 sampling rate')
    key = device_key or header.get('device name') or header.get('device') or 'device'
    di = np.zeros(n, np.uint8) if di is None else np.asarray(di).reshape(n, -1)[:, 0]
    body = np.column_stack([np.arange(n), di, data])
    with path.open('w') as f:
        f.write(MAGIC + '\n')
        f.write('# ' + json.dumps({key: header}, ensure_ascii=False) + '\n')
        f.write(END + '\n')
        np.savetxt(f, body, delimiter='\t', fmt=['%d', '%d'] + [fmt] * ch)
    return path


def read(path):
    """返回 (header dict, data (n, ch), di (n,))。头取第二行 JSON 的第一个设备。"""
    path = Path(path)
    with path.open() as f:
        first = f.readline().rstrip('\n')
        if not first.startswith('# OpenSignals Text File Format'):
            raise ValueError(f'{path.name} 不是 OpenSignals 文本文件')
        second = f.readline().rstrip('\n')
        if not second.startswith('# '):
            raise ValueError('第二行应是 # {JSON}')
        meta = json.loads(second[2:])
        third = f.readline().rstrip('\n')
        if third != END:
            raise ValueError('第三行应是 # EndOfHeader')
    if not isinstance(meta, dict) or not meta:
        raise ValueError('头 JSON 为空')
    header = next(iter(meta.values()))
    for k in ('sampling rate', 'column'):
        if k not in header:
            raise ValueError(f'头缺 {k}')
    body = np.loadtxt(path, comments='#', delimiter='\t', ndmin=2)
    if body.shape[1] != len(header['column']):
        raise ValueError(f"数据 {body.shape[1]} 列，头说 {len(header['column'])} 列")
    return header, body[:, 2:], body[:, 1].astype(np.uint8)

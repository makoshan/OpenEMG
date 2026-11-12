"""段文件 `.h5`（EMG_STUDIO_V2_PLAN 附录 B.2）与会话目录。

    /raw int32 (n,ch)  /uv float32 (n,ch)  /seq uint32 (n,)  /t_host_ns int64 (m,)
    /imu int16 (m,6)   /di uint8 (n,k)     /events 表(t_s, label, source)
    attrs['header'] = 与 OpenSignals .txt 第二行同一份 JSON（device_desc.header() + x_yuanli）

目录：<root>/sessions/<日期_设备_佩戴号>/NNNN_<label>.h5 + session.json
"""
import json
import re
import time
from pathlib import Path

import h5py
import numpy as np

import gates
import osig_txt

EVENT_DT = np.dtype([('t_s', np.float64), ('label', h5py.string_dtype('utf-8')), ('source', h5py.string_dtype('utf-8'))])
SAFE = re.compile(r'[^A-Za-z0-9_\-\u4e00-\u9fff]+')


def session_dir(root, desc, donning, when=None, device_tag=None):
    when = when or time.localtime()
    tag = SAFE.sub('', device_tag or desc.id)
    d = Path(root) / 'sessions' / f'{time.strftime("%Y-%m-%d", when)}_{tag}_d{int(donning):02d}'
    return d


def new_session(root, desc, *, subject, donning, hand='', placement='', notes='', device_tag=None):
    d = session_dir(root, desc, donning, device_tag=device_tag)
    if d.exists() and (d / 'session.json').exists():
        return json.loads((d / 'session.json').read_text()), d
    d.mkdir(parents=True, exist_ok=True)
    meta = {'session': d.name, 'device_id': desc.id, 'device_snapshot': desc.to_json(), 'subject': str(subject), 'donning': int(donning),
            'hand': hand, 'placement': placement, 'photo': None, 'started': time.strftime('%Y-%m-%dT%H:%M:%S'), 'ended': None, 'takes': [], 'notes': notes}
    (d / 'session.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
    return meta, d


def _update_session(d, fn):
    p = Path(d) / 'session.json'
    meta = json.loads(p.read_text())
    fn(meta)
    p.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
    return meta


def end_session(d):
    return _update_session(d, lambda m: m.__setitem__('ended', time.strftime('%Y-%m-%dT%H:%M:%S')))


def next_index(d):
    files = sorted(Path(d).glob('[0-9][0-9][0-9][0-9]_*.h5'))
    return int(files[-1].name[:4]) + 1 if files else 1


def write(d, desc, arrays, label, *, session_meta=None, seconds=None, dropped=0, extra=None, index=None):
    """写一段。arrays 来自 TakeRecorder.arrays() 或等价 dict。返回 (path, gate)。"""
    d = Path(d)
    uv = np.asarray(arrays['uv'], np.float32)
    n = len(uv)
    gate = gates.check(desc, uv, seconds=seconds, dropped=dropped)
    idx = index if index is not None else next_index(d)
    label_safe = SAFE.sub('', label) or 'take'
    path = d / f'{idx:04d}_{label_safe}.h5'
    header = desc.header(session=(session_meta or {}).get('session', d.name), donning=(session_meta or {}).get('donning'),
                         subject=(session_meta or {}).get('subject'), placement=(session_meta or {}).get('placement'),
                         take_label=label, gate=gate, seconds=round(n / desc.fs_Hz, 3), dropped=int(dropped),
                         recorded_at=time.strftime('%Y-%m-%dT%H:%M:%S'), **(extra or {}))
    header['date'], header['time'] = time.strftime('%Y-%m-%d'), time.strftime('%H:%M:%S')
    with h5py.File(path, 'w') as f:
        f.create_dataset('raw', data=np.asarray(arrays['raw'], np.int32).reshape(n, -1), compression='gzip')
        f.create_dataset('uv', data=uv.reshape(n, -1), compression='gzip')
        f.create_dataset('seq', data=np.asarray(arrays['seq'], np.uint32)[:n])
        f.create_dataset('t_host_ns', data=np.asarray(arrays.get('t_host_ns', np.zeros(0)), np.int64))
        if arrays.get('imu') is not None and len(arrays['imu']):
            ds = f.create_dataset('imu', data=np.asarray(arrays['imu'], np.int16))
            if desc.imu:
                for k, v in desc.imu.items():
                    if v is not None:
                        ds.attrs[k] = v
        if arrays.get('di') is not None and len(arrays['di']):
            f.create_dataset('di', data=np.asarray(arrays['di'], np.uint8).reshape(n, -1))
        ev = arrays.get('events') or []
        f.create_dataset('events', data=np.array([(float(t), str(l), str(s)) for t, l, s in ev], EVENT_DT))
        f.attrs['header'] = json.dumps(header, ensure_ascii=False)
    _update_session(d, lambda m: m['takes'].append({'file': path.name, 'label': label, 'seconds': round(n / desc.fs_Hz, 3), 'gate': gate}))
    return path, gate


def read_header(path):
    with h5py.File(path, 'r') as f:
        return json.loads(f.attrs['header'])


def read(path, which=('uv',), frm=None, to=None):
    """读指定数据集；frm/to 为样本序号区间。"""
    out = {}
    with h5py.File(path, 'r') as f:
        out['header'] = json.loads(f.attrs['header'])
        for k in which:
            if k not in f:
                out[k] = None
                continue
            ds = f[k]
            if k in ('raw', 'uv', 'seq', 'di') and (frm is not None or to is not None):
                out[k] = ds[slice(frm, to)]
            else:
                out[k] = ds[()]
    return out


def events(path):
    with h5py.File(path, 'r') as f:
        ev = f['events'][()] if 'events' in f else np.zeros(0, EVENT_DT)
    return [(float(e['t_s']), e['label'].decode() if isinstance(e['label'], bytes) else str(e['label']),
             e['source'].decode() if isinstance(e['source'], bytes) else str(e['source'])) for e in ev]


def export_txt(path, out=None, converted=True):
    """一段 .h5 → OpenSignals .txt。converted=True 写 µV（convertedValues 1），否则写 raw（0）。"""
    path = Path(path)
    data = read(path, which=('uv' if converted else 'raw', 'di'))
    header = dict(data['header'], convertedValues=1 if converted else 0)
    out = Path(out) if out else path.parent.parent.parent / 'exports' / f'{path.parent.name}_{path.stem}.txt'
    out.parent.mkdir(parents=True, exist_ok=True)
    key = header.get('x_yuanli', {}).get('device_id', header.get('device', 'device'))
    return osig_txt.write(out, header, data['uv' if converted else 'raw'], di=data.get('di'), device_key=key)


def list_sessions(root):
    root = Path(root) / 'sessions'
    if not root.exists():
        return []
    out = []
    for d in sorted(root.iterdir()):
        p = d / 'session.json'
        if p.exists():
            m = json.loads(p.read_text())
            out.append({k: m.get(k) for k in ('session', 'device_id', 'subject', 'donning', 'hand', 'placement', 'started', 'ended')} | {'n_takes': len(m.get('takes', [])), 'dir': str(d)})
    return out


def list_takes(root, session=None):
    root = Path(root) / 'sessions'
    if not root.exists():
        return []
    dirs = [root / session] if session else sorted(x for x in root.iterdir() if x.is_dir())
    out = []
    for d in dirs:
        p = d / 'session.json'
        if not p.exists():
            continue
        m = json.loads(p.read_text())
        for t in m.get('takes', []):
            out.append(dict(t, session=m['session'], device_id=m['device_id'], donning=m['donning'], subject=m.get('subject'), path=str(d / t['file'])))
    return out

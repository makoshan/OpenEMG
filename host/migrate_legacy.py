"""旧 wl8 数据（emg-wl8-data[-rewear]/<label>/*.npz + .json）→ 新会话目录 .h5（附录 E）。

- 旧文件夹名 = 标签；json 里的 session/donning 决定会话；没有 json 的按文件 mtime 日期 + donning 0。
- 只读旧包，不改不删；重复运行幂等（按源文件名记在 session.json takes[].legacy）。
- 原始生物信号仍留在工程目录，不进 git。
用法：PY migrate_legacy.py <工程根> [--src emg-wl8-data emg-wl8-data-rewear]
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np

import device_desc
import take_file

DEFAULT_SRC = ('emg-wl8-data', 'emg-wl8-data-rewear')


def legacy_files(roots):
    for root in roots:
        root = Path(root)
        if not root.exists():
            continue
        for f in sorted(root.glob('*/*.npz')):
            yield f.parent.name, f


def migrate_one(desc, label, f, out_root, done):
    meta_p = f.with_suffix('.json')
    meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
    with np.load(f, allow_pickle=False) as z:
        emg = z['emg_uv'].astype(np.float32)
        imu = z['imu'] if 'imu' in z else None
        fs = int(z['emg_hz']) if 'emg_hz' in z else desc.fs_Hz
    if fs != desc.fs_Hz or emg.shape[1] != desc.n_channels:
        raise ValueError(f'{f.name}: {fs} Hz × {emg.shape[1]} 路，与 {desc.id} 描述不符')
    donning = int(meta.get('donning', 0))
    day = (meta.get('recordedAt') or time.strftime('%Y-%m-%d', time.localtime(f.stat().st_mtime)))[:10]
    when = time.strptime(day, '%Y-%m-%d')
    d = take_file.session_dir(out_root, desc, donning, when=when, device_tag=f'{desc.id}-legacy')
    if str(f) in done.get(str(d), set()):
        return None
    if not (d / 'session.json').exists():
        d.mkdir(parents=True, exist_ok=True)
        (d / 'session.json').write_text(json.dumps({'session': d.name, 'device_id': desc.id, 'device_snapshot': desc.to_json(), 'subject': meta.get('subject', 'legacy'),
                                                    'donning': donning, 'hand': '', 'placement': meta.get('sensor', ''), 'photo': None, 'started': meta.get('recordedAt', day),
                                                    'ended': None, 'takes': [], 'notes': f'从 {f.parent.parent.name} 迁移', 'legacy': True}, ensure_ascii=False, indent=2) + '\n')
    gain = np.array(desc.gains())
    arrays = {'uv': emg, 'raw': np.round(emg / gain).astype(np.int32), 'seq': np.arange(len(emg), dtype=np.uint32), 't_host_ns': np.zeros(0, np.int64),
              'imu': imu, 'events': []}
    path, gate = take_file.write(d, desc, arrays, label, session_meta=json.loads((d / 'session.json').read_text()),
                                 extra={'legacy_file': f.name, 'legacy_set': f.parent.parent.name})
    take_file._update_session(d, lambda m: m['takes'][-1].__setitem__('legacy', str(f)))
    return path, gate


def done_index(out_root):
    """{会话目录: {已迁移的旧文件路径}}，幂等用。"""
    done = {}
    for s in take_file.list_sessions(out_root):
        m = json.loads((Path(s['dir']) / 'session.json').read_text())
        done[s['dir']] = {t.get('legacy') for t in m.get('takes', []) if t.get('legacy')}
    return done


def migrate(project_root, srcs=DEFAULT_SRC, device_id='wl8', progress=print):
    desc = device_desc.load(device_id)
    out_root = Path(project_root)
    done = done_index(out_root)
    n_ok = n_skip = n_bad = 0
    for label, f in legacy_files([Path(project_root) / s for s in srcs]):
        try:
            r = migrate_one(desc, label, f, out_root, done)
        except ValueError as e:
            n_bad += 1
            progress(f'跳过 {f}: {e}')
            continue
        if r is None:
            n_skip += 1
        else:
            n_ok += 1
            progress(f'{f.parent.name}/{f.name} → {r[0].relative_to(out_root)} gate={"ok" if r[1]["ok"] else r[1]["why"]}')
    return {'migrated': n_ok, 'skipped': n_skip, 'rejected': n_bad}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('project_root')
    ap.add_argument('--src', nargs='*', default=list(DEFAULT_SRC))
    ap.add_argument('--device', default='wl8')
    a = ap.parse_args()
    print(json.dumps(migrate(a.project_root, a.src, a.device), ensure_ascii=False))

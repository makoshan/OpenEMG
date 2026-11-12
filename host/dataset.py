"""数据集文件 `datasets/<name>.json`（EMG_STUDIO_V2_PLAN 附录 B.4）：文件清单 + 三集划分 + 标签映射 + 质量门版本。

规则：
- split_by = session：同一会话（一次佩戴）的所有段进同一个集；独立测试集只能来自没参与训练的会话。
- 入集前再跑一次饱和门（文件可能是旧迁移来的，录制时没过门）。
- 每个文件记 sha256；训练前核对，文件被改过就拒绝。
"""
import hashlib
import json
import time
from pathlib import Path

import numpy as np

import device_desc
import gates
import take_file

GATE_VERSION = '2026-10'
SPLITS = ('train', 'validation', 'test')


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def auto_split(sessions):
    """按会话名排序：最后一个做 test，倒数第二做 validation，其余 train；少于 3 个会话时相应为空。"""
    s = sorted(set(sessions))
    if len(s) >= 3:
        return {**{x: 'train' for x in s[:-2]}, s[-2]: 'validation', s[-1]: 'test'}
    if len(s) == 2:
        return {s[0]: 'train', s[1]: 'validation'}
    return {x: 'train' for x in s}


def build(root, name, label_map, session_split=None, device_id=None, require_gate=True):
    """扫 <root>/sessions 生成数据集。label_map: {录制标签: 训练标签或 None(不入集)}。"""
    root = Path(root)
    takes = take_file.list_takes(root)
    if device_id:
        takes = [t for t in takes if t['device_id'] == device_id]
    items, rejected = [], []
    for t in takes:
        lab = label_map.get(t['label'], None) if label_map else t['label']
        if lab is None:
            continue
        gate = dict(t.get('gate') or {})
        if require_gate and not gate.get('ok', False):
            rejected.append({'file': t['path'], 'why': gate.get('why', '录制时未过门')})
            continue
        # 入集饱和复查：训练加载历史上没有这道门（HANDOFF 2026-10-10）
        hdr = take_file.read_header(t['path'])
        desc = device_desc.load(hdr['x_yuanli']['device_id'])
        uv = take_file.read(t['path'], ('uv',))['uv']
        g2 = gates.check(desc, uv, dropped=int(hdr['x_yuanli'].get('dropped', 0)))
        if require_gate and not g2['ok']:
            rejected.append({'file': t['path'], 'why': '入集复查：' + g2['why']})
            continue
        rel = str(Path(t['path']).relative_to(root))
        items.append({'file': rel, 'label': lab, 'session': t['session'], 'split': None, 'sha256': sha256(t['path']), 'seconds': t.get('seconds')})
    # 只对真正入集的会话划分：全被剔除的会话不占 test 位
    split_of = dict(auto_split({it['session'] for it in items}), **(session_split or {}))
    for it in items:
        it['split'] = split_of.get(it['session'], 'train')
    ds = {'name': name, 'created': time.strftime('%Y-%m-%dT%H:%M:%S'), 'gate_version': GATE_VERSION, 'label_map': label_map,
          'split_by': 'session', 'device_id': device_id, 'items': items, 'rejected': rejected}
    ds['summary'] = summary(ds)
    return ds


def summary(ds):
    out = {s: {} for s in SPLITS}
    sess = {s: set() for s in SPLITS}
    for it in ds['items']:
        out[it['split']][it['label']] = out[it['split']].get(it['label'], 0) + 1
        sess[it['split']].add(it['session'])
    return {**out, 'sessions': {s: sorted(v) for s, v in sess.items()}, 'rejected': len(ds.get('rejected', []))}


def validate(ds, root=None, check_sha=True):
    """合法返回 True；否则抛 ValueError。"""
    if ds.get('split_by') != 'session':
        raise ValueError('只支持 split_by=session')
    seen = {}
    for it in ds['items']:
        if it['split'] not in SPLITS:
            raise ValueError(f"未知 split {it['split']}")
        if it['label'] is None:
            raise ValueError(f"{it['file']} 标签为空")
        prev = seen.setdefault(it['session'], it['split'])
        if prev != it['split']:
            raise ValueError(f"会话 {it['session']} 同时出现在 {prev} 与 {it['split']}：按佩戴划分不允许")
    if check_sha and root is not None:
        for it in ds['items']:
            p = Path(root) / it['file']
            if not p.exists():
                raise ValueError(f'文件不存在 {it["file"]}')
            if sha256(p) != it['sha256']:
                raise ValueError(f'文件被改过：{it["file"]}')
    labels_train = {it['label'] for it in ds['items'] if it['split'] == 'train'}
    if len(labels_train) < 2:
        raise ValueError('训练集少于两类')
    return True


def save(ds, root):
    validate(ds, root)
    d = Path(root) / 'datasets'
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{ds['name']}.json"
    p.write_text(json.dumps(ds, ensure_ascii=False, indent=1) + '\n')
    return p


def load(root, name):
    p = Path(root) / 'datasets' / f'{name}.json'
    ds = json.loads(p.read_text())
    validate(ds, root)
    return ds


def list_datasets(root):
    d = Path(root) / 'datasets'
    if not d.exists():
        return []
    out = []
    for p in sorted(d.glob('*.json')):
        ds = json.loads(p.read_text())
        out.append({'name': ds['name'], 'created': ds['created'], 'summary': ds.get('summary'), 'device_id': ds.get('device_id')})
    return out


def records(ds, root, split):
    """[(uv (n,ch) float, label, session)]；按文件名排序，复现用。"""
    out = []
    for it in sorted((i for i in ds['items'] if i['split'] == split), key=lambda i: i['file']):
        uv = take_file.read(Path(root) / it['file'], ('uv',))['uv'].astype(np.float64)
        out.append((uv, it['label'], it['session']))
    return out


def fingerprint(ds):
    h = hashlib.sha256()
    for it in sorted(ds['items'], key=lambda i: i['file']):
        h.update(f"{it['file']}|{it['label']}|{it['split']}|{it['sha256']}".encode())
    return h.hexdigest()[:16]

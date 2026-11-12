"""数据集门禁（附录 B.4/G）：3 会话 × 3 标签合成工程 → 自动按会话划分 train/validation/test；
同会话跨集必失败；sha 不符必失败；饱和段入集被剔除；标签映射 None 不入集；训练集单类必失败。"""
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dataset as dsmod
import device_desc as dd
import take_file


def synth_project(tmp, desc, sessions=3, labels=('rest', 'pinch', 'fist'), per=4, seed=0, fs=2000):
    rng = np.random.default_rng(seed)
    amp = {'rest': 8, 'pinch': 40, 'fist': 90, 'open': 60}
    for s in range(sessions):
        meta, d = take_file.new_session(tmp, desc, subject='S01', donning=s + 1, device_tag=f'{desc.id}{s}')
        for lab in labels:
            for k in range(per):
                n = 2 * fs
                uv = rng.normal(0, amp[lab], (n, desc.n_channels)).astype(np.float32)
                uv[:, :4] *= 1.0 if lab != 'pinch' else 1.6      # 让类别在通道上有差异
                arr = {'uv': uv, 'raw': np.round(uv / np.array(desc.gains())).astype(np.int32), 'seq': np.arange(n, dtype=np.uint32), 'events': []}
                take_file.write(d, desc, arr, lab, session_meta=meta, seconds=2.0)
    return tmp


def main():
    tmp = Path(tempfile.mkdtemp())
    desc = dd.load('fake')
    synth_project(tmp, desc)
    # 一段饱和、一段无标签映射
    meta, d = take_file.new_session(tmp, desc, subject='S01', donning=9, device_tag='fakeX')
    sat = np.full((4000, 8), desc.limits['rail_uV'], np.float32)
    take_file.write(d, desc, {'uv': sat, 'raw': np.zeros((4000, 8), np.int32), 'seq': np.arange(4000, dtype=np.uint32), 'events': []}, 'fist', session_meta=meta, seconds=2.0)
    take_file.write(d, desc, {'uv': sat * 0 + 5, 'raw': np.zeros((4000, 8), np.int32), 'seq': np.arange(4000, dtype=np.uint32), 'events': []}, 'junk', session_meta=meta, seconds=2.0)
    ds = dsmod.build(tmp, 'demo', {'rest': 'rest', 'pinch': 'pinch', 'fist': 'fist', 'junk': None})
    assert len(ds['items']) == 36 and len(ds['rejected']) == 1, (len(ds['items']), ds['rejected'])
    sm = ds['summary']
    assert sm['train'] == {'rest': 4, 'pinch': 4, 'fist': 4} and sm['validation']['fist'] == 4 and sm['test']['rest'] == 4, sm
    assert len(sm['sessions']['train']) == 1 and len(sm['sessions']['test']) == 1
    p = dsmod.save(ds, tmp)
    ds2 = dsmod.load(tmp, 'demo')
    assert dsmod.fingerprint(ds2) == dsmod.fingerprint(ds) and dsmod.list_datasets(tmp)[0]['name'] == 'demo'
    print(f'  demo: 36 段入集（饱和 1 段剔除，junk 不入集）→ {json.dumps({k: sm[k] for k in dsmod.SPLITS}, ensure_ascii=False)}')
    # 手工划分覆盖：把 3 个会话全放 train，test 空
    names = sorted({it['session'] for it in ds['items']})
    ds3 = dsmod.build(tmp, 'alltrain', {'rest': 'rest', 'pinch': 'pinch', 'fist': 'fist'}, session_split={n: 'train' for n in names})
    assert ds3['summary']['test'] == {} and sum(ds3['summary']['train'].values()) == 36
    print('  手工划分：3 会话全 train，test 为空（训练器会报「无独立测试」）')
    # 必失败
    bad = json.loads(json.dumps(ds))
    bad['items'][0]['split'] = 'test'
    try:
        dsmod.validate(bad, tmp)
        raise AssertionError('同会话跨集通过了')
    except ValueError as e:
        print(f'  红 ✓ 同会话跨集: {e}')
    bad = json.loads(json.dumps(ds))
    bad['items'][0]['sha256'] = '0' * 64
    try:
        dsmod.validate(bad, tmp)
        raise AssertionError('sha 不符通过了')
    except ValueError as e:
        print(f'  红 ✓ sha 不符: {e}')
    bad = json.loads(json.dumps(ds))
    bad['items'] = [it for it in bad['items'] if not (it['split'] == 'train' and it['label'] != 'rest')]
    try:
        dsmod.validate(bad, tmp)
        raise AssertionError('训练集单类通过了')
    except ValueError as e:
        print(f'  红 ✓ 训练集单类: {e}')
    # 文件被改后 load 必失败
    f = tmp / ds['items'][0]['file']
    with open(f, 'ab') as fh:
        fh.write(b'\0')
    try:
        dsmod.load(tmp, 'demo')
        raise AssertionError('文件改动后仍加载成功')
    except ValueError as e:
        print(f'  红 ✓ 文件被改: {e}')
    print('check_dataset: 按会话划分 / 饱和剔除 / 标签映射 通过，4 条必失败全红')


if __name__ == '__main__':
    main()

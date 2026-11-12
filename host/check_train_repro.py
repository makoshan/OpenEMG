"""统一训练器门禁（附录 D/G）：合成 3 会话数据集 → lda 训练；validation/test 平衡准确率 ≥ 0.9（可分合成数据）；
同数据集同 seed 两次 run 指标逐值相同；run.json 带数据集指纹；test 空时 metrics.test=None 并有「无独立测试」说明；
每类不足 5 条必失败；未知训练器必失败；冻结 production.json；fs=2000 时特征与 wl8_train.features 逐值相同；
cnn：有 torch 跑一遍小 epoch，没有 torch 报 ImportError（打印 SKIP）。"""
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_dataset
import dataset as dsmod
import device_desc as dd
import trainer
import wl8_train


def main():
    tmp = Path(tempfile.mkdtemp())
    desc = dd.load('fake')
    check_dataset.synth_project(tmp, desc, sessions=3, per=6)
    lm = {'rest': 'rest', 'pinch': 'pinch', 'fist': 'fist'}
    ds = dsmod.build(tmp, 'demo', lm)
    dsmod.save(ds, tmp)
    out = tmp / 'models'
    logs = []
    r1 = trainer.train(ds, tmp, desc, trainer='lda', seed=0, out_root=out, progress=logs.append)
    r2 = trainer.train(ds, tmp, desc, trainer='lda', seed=0, out_root=out, progress=lambda *_: None)
    assert r1['metrics'] == r2['metrics'], '同数据同 seed 两次指标不同'
    assert r1['dataset']['fingerprint'] == dsmod.fingerprint(ds) and r1['features_version'] == trainer.FEATURES_VERSION
    m = {k: v['balanced_acc'] for k, v in r1['metrics'].items()}
    assert m['validation'] >= .9 and m['test'] >= .9, m
    assert r1['metrics']['test']['confusion']['rows'] == ['fist', 'pinch', 'rest']
    assert (out / r1['id'] / 'run.json').exists() and (out / r1['id'] / 'model.npz').exists()
    z = np.load(out / r1['id'] / 'model.npz')
    assert str(z['kind']) == 'lda-npz' and z['mu'].shape == (3, 40)
    print(f'  lda: train/val/test = {m}，两次训练指标逐值相同，{r1["seconds"]} s')
    assert any(l.get('stage') == 'done' for l in logs)
    # 特征与 wl8_train 对齐（2000 Hz × 8 路）
    e = np.random.default_rng(1).normal(0, 20, (2000, 8))
    assert np.allclose(trainer.features(e, 2000), wl8_train.features(e)), '特征与 wl8_train 不一致'
    print('  features(fs=2000, 8ch) 与 wl8_train.features 逐值相同')
    # 无独立测试
    names = sorted({it['session'] for it in ds['items']})
    ds3 = dsmod.build(tmp, 'notest', lm, session_split={names[0]: 'train', names[1]: 'train', names[2]: 'validation'})
    r3 = trainer.train(ds3, tmp, desc, trainer='lda', seed=0, out_root=out, progress=lambda *_: None)
    assert r3['metrics']['test'] is None and '无独立测试' in r3['note']
    print(f'  test 空：metrics.test=None，note=「{r3["note"]}」')
    # 冻结
    prod = trainer.freeze(out, r1['id'])
    assert trainer.production(out)['run_id'] == r1['id'] and prod['labels'] == ['fist', 'pinch', 'rest']
    assert len(trainer.runs(out)) == 3
    print(f'  freeze → production.json run_id={prod["run_id"]}')
    # 必失败
    few = json.loads(json.dumps(ds))
    fist_train = [it for it in few['items'] if it['split'] == 'train' and it['label'] == 'fist']
    few['items'] = [it for it in few['items'] if it not in fist_train[2:]]      # 训练集 fist 只留 2 条
    try:
        trainer.train(few, tmp, desc, trainer='lda', seed=0, out_root=out, progress=lambda *_: None)
        raise AssertionError('每类不足 5 条却训了')
    except ValueError as e:
        print(f'  红 ✓ 每类不足: {e}')
    try:
        trainer.train(ds, tmp, desc, trainer='svm', seed=0, out_root=out)
        raise AssertionError('未知训练器通过了')
    except ValueError as e:
        print(f'  红 ✓ 未知训练器: {e}')
    try:
        trainer.freeze(out, 'nope')
        raise AssertionError('冻结不存在的 run 通过了')
    except ValueError as e:
        print(f'  红 ✓ 冻结不存在的 run: {e}')
    # cnn
    try:
        r4 = trainer.train(ds, tmp, desc, trainer='cnn', seed=0, out_root=out, progress=lambda *_: None, epochs=3, min_per_class=3)
        mc = {k: (v or {}).get('balanced_acc') for k, v in r4['metrics'].items()}
        assert r4['metrics']['train'] is not None and (out / r4['id'] / 'model.npz').exists()
        print(f'  cnn(3 epoch): {mc}（只验证链路，不看分数）')
    except ImportError as e:
        print(f'  SKIP cnn: {e}（用 EMGPY 跑本脚本可覆盖）')
    print('check_train_repro: lda 复现 / 指纹 / 无独立测试 / 冻结 通过，3 条必失败全红')


if __name__ == '__main__':
    main()

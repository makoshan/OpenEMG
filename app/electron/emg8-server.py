"""Mac 八通道采集入口：复用手表采集器，扩展独立的拇指标签和完整训练校验。"""
import argparse
import json
from pathlib import Path
import runpy
import sys
import tempfile
from zipfile import BadZipFile
from zlib import error as CompressionError
from datetime import datetime

PROFILES = json.loads(Path(__file__).with_name('emg8-profiles.json').read_text())
THUMB = PROFILES['thumb-four']


def install(firmware_root):
    sys.path.insert(0, str(Path(firmware_root).resolve()))
    import numpy as np
    import wl8
    import wl8_train
    # 在 emg_web 建立标签表前扩展；旧屈腕 left/right 原样保留。
    wl8.LABELS = tuple(dict.fromkeys((*wl8.LABELS, *(l for p in PROFILES.values() for l in p.get('captureLabels', p['labels'])))))
    synth = wl8._synth_frames
    def synth_frames(label, *args, **kwargs):
        # 只给 --fake 自检使用的合成通道模式；真实采集不调用它。
        aliases = {'classic_rest': 'rest', 'thumb_rest': 'rest', 'thumb_left': 'left', 'thumb_right': 'right', 'meta_rest': 'rest', 'meta_index': 'pinch', 'meta_middle': 'middle', 'meta_side': 'rub', 'meta_other': 'fist', 'motion_rest': 'rest', 'motion_hold': 'pinch', 'motion_other': 'fist', 'ai_rest': 'rest', 'ai_summon': 'middle', 'ai_up': 'left', 'ai_down': 'right', 'ai_left': 'rub', 'ai_right': 'fist',
                   # EgoEMG 六手势：各配一种合成模式，假腕带回放时训练分得开
                   'ego_rest': 'rest', 'ego_pinch_middle': 'middle', 'ego_thumb_slide': 'rub', 'ego_index_bow': 'pinch', 'ego_ring_thumb': 'left', 'ego_claw5': 'fist'}
        for p in PROFILES.values():
            if p.get('protocol'):
                for l in p.get('captureLabels', p['labels']):
                    aliases.setdefault(l, 'middle' if 'middle' in l else 'pinch')
        return synth(aliases.get(label, label), *args, **kwargs)
    wl8._synth_frames = synth_frames
    original = wl8_train.train
    import importlib.util
    spec = importlib.util.spec_from_file_location("pt_emg_meta", Path(__file__).with_name("emg8-meta.py"))
    meta_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(meta_module)
    meta_module.install(wl8_train, PROFILES, wl8)
    # 校准口令名从动作组清单补（gestures[].voice，没有就用 name）：新加动作组不用再改 host/calibration_voice.py
    import calibration_voice
    for p in PROFILES.values():
        for label, g in (p.get('gestures') or {}).items():
            calibration_voice.NAMES.setdefault(label, g.get('voice') or g['name'])

    def train(root, labels=wl8_train.DEFAULT_LABELS, since=None, progress=print, seed=0):
        labels = list(labels)
        validation = None
        special = next((p for p in PROFILES.values() if p.get('protocol') and set(labels) == set(p['labels']) and len(labels) == len(p['labels'])), None)
        protocol_labels = {l for p in PROFILES.values() if p.get('protocol') for l in p.get('captureLabels', p['labels'])}
        if protocol_labels & set(labels) and special is None:
            raise ValueError('专训必须包含本组全部基础类别；练习与校准样本不能混入分类器')
        checked = special or THUMB
        if special and special.get('calibrate'):
            # 每次佩戴校准：不查重戴目录，只要求这次佩戴每类够数；load 已按最新佩戴编号过滤
            current = {}
            for label in labels:
                for f in (Path(root) / 'emg-wl8-data' / label).glob('*.npz'):
                    try: d = json.loads(f.with_suffix('.json').read_text()).get('donning')
                    except (OSError, ValueError, AttributeError): d = None
                    if type(d) is int: current.setdefault(d, {}).setdefault(label, 0); current[d][label] += 1
            if not current: raise ValueError('还没有这次佩戴的校准数据')
            wear = max(current); n = current[wear]
            need = int(special['calibrate'].get('minTrain', checked['minTrain']))      # 校准每类 3 条（3 轮 × 1），不是普通专训的 5
            missing = [l for l in labels if n.get(l, 0) < need]
            if missing:
                raise ValueError(f'第 {wear} 次佩戴每类至少 {need} 条，还缺：' + '、'.join(checked['gestures'][l]['name'] for l in missing))
            # 逐文件校验这次佩戴的训练样本（与普通专训同口径）：坏文件、短样本、非数值都拒绝，别进 load 里回绕出垃圾窗；放松异常条排除后再数条数
            rest_rms = {}
            for label in labels:
                for f in sorted((Path(root) / 'emg-wl8-data' / label).glob('*.npz')):
                    try: d = json.loads(f.with_suffix('.json').read_text()).get('donning')
                    except (OSError, ValueError, AttributeError): d = None
                    if d != wear: continue
                    try:
                        with np.load(f, allow_pickle=False) as z: emg = z['emg_uv']
                    except (OSError, KeyError, BadZipFile, EOFError, CompressionError, ValueError):
                        raise ValueError(f'{label}/{f.name} 不是有效的八通道样本，请移出后重录')
                    if emg.dtype.kind not in 'fiu' or emg.ndim != 2 or emg.shape[1] != 8 or len(emg) < wl8_train.FS or not np.isfinite(emg).all():
                        raise ValueError(f'{label}/{f.name} 不是有效的八通道样本，请移出后重录')
                    if checked['gestures'].get(label, {}).get('kind') == 'rest': rest_rms[f'{label}/{f.name}'] = float(np.median(np.std(emg.astype(float), axis=0)))
            outliers = wl8_train.rest_outliers(rest_rms)
            for x in outliers: n[x.split('/')[0]] -= 1
            missing = [l for l in labels if n.get(l, 0) < need]
            if missing:
                raise ValueError(f'第 {wear} 次佩戴有 {len(outliers)} 条放松样本底噪异常（手在动或电极脱落）已排除，还缺：' + '、'.join(checked['gestures'][l]['name'] for l in missing) + '；用「再补一轮」补')
            report, model = original(root, labels, since, progress, seed)
            report['validation'] = {'status': 'calibration', 'donning': wear, 'reason': f'每次佩戴校准：只用第 {wear} 次佩戴的 {sum(n.values())} 条训练；分数是同次佩戴留一估计，摘下重戴要重新校准'}
            report['window_ms'] = model['window_ms'] = int(special.get('windowMs', 200)); model['short'] = True   # 短窗特征（emg8-meta features），实时识别按这个标志选管线，不再靠 ms<1000 猜
            report['features'] = f"{report['window_ms']} ms 八通道频段功率；每条取滤波能量最大处的短窗"
            report['excluded'] = {'files': sorted(outliers), 'rule': f'本次佩戴放松条底噪 > max(放松条下四分位 × {wl8_train.REST_FACTOR:g}, {int(wl8_train.REST_FLOOR_UV)} µV) 视为手在动 / 脱落，不进训练；动作条不剔，录制时按幅度门槛当场重录'}
            if not all(np.isfinite(model[key]).all() for key in ('mu', 'sinv', 'W')):
                raise ValueError('训练产生无效数值，请检查信号并重录')
            # 新算法仅旁路记录；失败不影响原分类器，也不把未验证模型接到游戏。
            if special.get('game') == 'tianjie':
                try:
                    import adaptive_intent
                    rest = next(l for l in labels if special['gestures'][l].get('kind') == 'rest')
                    model['adaptive_intent'] = adaptive_intent.fit_directory(root, labels, rest, wear, outliers, since)
                    report['adaptive_intent'] = dict(status='shadow', version=adaptive_intent.VERSION, donning=wear, validated_for_control=False)
                except Exception as e:
                    report['adaptive_intent'] = dict(status='unavailable', reason=type(e).__name__, validated_for_control=False)
            json.dumps(report, allow_nan=False)
            return report, model
        if special or any(l.startswith('thumb_') for l in labels):
            if not special and (len(labels) != len(THUMB['labels']) or set(labels) != set(THUMB['labels'])):
                raise ValueError('拇指训练必须包含静止和上、下、左、右五类，不能混入屈腕标签')
            wears = {'train': set(), 'rewear': set()}
            counts = {}
            validation_errors = []
            for split, folder in [('train', 'emg-wl8-data'), ('rewear', 'emg-wl8-data-rewear')]:
                counts[split] = {}
                for label in labels:
                    n = 0
                    for f in sorted((Path(root) / folder / label).glob('*.npz')):
                        if since and f.stat().st_mtime < since:
                            continue
                        n += 1
                        try:
                            loaded = np.load(f, allow_pickle=False)
                            if not isinstance(loaded, np.lib.npyio.NpzFile):
                                raise ValueError(f'{label}/{f.name} 不是有效的八通道样本，请移出后重录')
                            with loaded as z:
                                emg = z['emg_uv']
                            if emg.dtype.kind not in 'fiu' or emg.ndim != 2 or emg.shape[1] != 8 or len(emg) < wl8_train.FS or not np.isfinite(emg).all():
                                raise ValueError(f'{label}/{f.name} 不是有效的八通道样本，请移出后重录')
                            meta = json.loads(f.with_suffix('.json').read_text())
                            if not isinstance(meta, dict):
                                raise ValueError(f'{label}/{f.name} 缺少有效佩戴编号，请重录')
                            donning = meta.get('donning')
                            if type(donning) is not int or not 1 <= donning <= 20:
                                raise ValueError(f'{label}/{f.name} 缺少有效佩戴编号，请重录')
                            wears[split].add(donning)
                        except (ValueError, OSError, KeyError, BadZipFile, EOFError, CompressionError):
                            # 训练样本有问题仍拒绝；验证损坏只取消验证，不改原文件或佩戴事实。
                            if split == 'train':
                                raise
                            validation_errors.append(f'{label}/{f.name} 验证样本无效')
                    counts[split][label] = n
            missing = [l for l in labels if counts['train'][l] < checked['minTrain']]
            if missing:
                raise ValueError('每类至少 5 条训练样本，还缺：' + '、'.join(checked['gestures'][l]['name'] for l in missing))
            if not sum(counts['rewear'].values()):
                validation_errors.append('还没有重戴验证数据')
            else:
                missing = [l for l in labels if counts['rewear'][l] < checked['minRewear']]
                if missing:
                    validation_errors.append('重戴验证每类至少 3 条，还缺：' + '、'.join(checked['gestures'][l]['name'] for l in missing))
                if wears['train'] & wears['rewear']:
                    validation_errors.append('训练与验证数据用了相同佩戴编号；请实际摘下重戴、增加编号后录验证集')
            validation = {'status': 'unverified' if validation_errors else 'verified',
                          'reason': '；'.join(dict.fromkeys(validation_errors)), 'available_counts': counts['rewear']}
        if validation and validation['status'] == 'unverified':
            # 临时视图只让分类器看到训练集；不合格验证不能产生准确率、混淆矩阵或学习曲线验证分数。
            with tempfile.TemporaryDirectory(prefix='pt-emg-train-only-') as tmp:
                (Path(tmp) / 'emg-wl8-data').symlink_to((Path(root) / 'emg-wl8-data').resolve(), target_is_directory=True)
                # 训练集有多次佩戴时 wl8_train 会按佩戴编号留一次佩戴估分；本组规矩是没有合格重戴不出分，进度和结果里都拿掉
                report, model = original(tmp, labels, since, lambda e: e.get('stage') == 'rewear' or progress(dict(e, rewear=None) if e.get('stage') == 'done' else e), seed)
            if report.pop('rewear_source', None) == '留一次佩戴':
                for k in ('confusion', 'shuffled', 'per_channel'): report.pop(k, None)
                report['rewear'] = None
            report['note'] = '基础模型已生成，未完成重戴验证。' + validation['reason'] + '。原始验证数据已保留，本次未用于评分。'
        else:
            report, model = original(root, labels, since, progress, seed)
        if validation:
            report['validation'] = validation
        if special:
            report['window_ms'] = int(special.get('windowMs', 200))
            report['sequence_validation'] = {'status': 'unverified', 'reason': '分类分数仅验证接触状态；双击、长按和转动组合仍需现场试用'}
            report['features'] = '200 ms 八通道频段功率；每条录制取中间短窗，按整条样本划分验证'
            model['window_ms'] = report['window_ms']; model['short'] = True
            if special['protocol'] == 'taps':
                report['sequence_trials'] = meta_module.sequence_trials(Path(root), model, wl8_train, since)
            if special['protocol'] == 'motion':
                report['motion_calibration'] = meta_module.calibrate(Path(root), since)
        if not all(np.isfinite(model[key]).all() for key in ('mu', 'sinv', 'W')):
            raise ValueError('训练产生无效数值，请检查信号并重录')
        json.dumps(report, allow_nan=False)  # 图表和分数不能带 NaN / Infinity。
        if special or any(l.startswith('thumb_') for l in labels):
            # 四向组不继承旧 rest 的底噪剔除，结果不能宣称已自动筛掉动作错录。
            report['excluded'] = {'files': [], 'rule': '专用手势组未执行静止底噪剔除；需检查实际动作是否录对'}
        return report, model

    wl8_train.train = train
    def save(run, model, out_root):
        # 同秒反复训练也保留各自模型，避免覆盖恢复点。
        rid = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        dest = Path(out_root) / rid
        dest.mkdir(parents=True, exist_ok=False)
        report = dict(run, id=rid, created=datetime.now().isoformat(timespec='seconds'))
        np.savez(dest / 'model.npz', classes=np.array(model['classes']), mu=model['mu'],
                 sinv=model['sinv'], W=model['W'], bands=np.array(wl8_train.BANDS), fs=wl8_train.FS, shrink=wl8_train.SHRINK, window_ms=model.get('window_ms', 1000), short=bool(model.get('short', False)), **wl8_train.rest_extra(model))
        if 'adaptive_intent' in model:
            import adaptive_intent, hashlib
            try:
                data = dict(model['adaptive_intent'], legacy_sha256=hashlib.sha256((dest / 'model.npz').read_bytes()).hexdigest())
                adaptive_intent.save(data, dest / 'adaptive-intent.json')
            except Exception as e:
                report['adaptive_intent'] = dict(status='unavailable', reason=type(e).__name__, validated_for_control=False)
        (dest / 'run.json').write_text(json.dumps(report, ensure_ascii=False, indent=1))
        return dest
    wl8_train.save = save
    return wl8_train


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--firmware-root', required=True)
    args, remaining = parser.parse_known_args()
    install(args.firmware_root)
    # App 被强杀时自己退出：否则成孤儿，一直占着腕带串口（父进程变了 = App 没了）
    import os, threading, time
    parent = os.getppid()
    def watch_parent():
        while os.getppid() == parent: time.sleep(1)
        os._exit(0)
    threading.Thread(target=watch_parent, daemon=True).start()
    sys.argv = [str(Path(args.firmware_root) / 'emg_web.py'), '--wl8', *remaining]
    runpy.run_path(sys.argv[0], run_name='__main__')

"""Project-bound five-gesture training. Test data is opened only by explicit evaluate."""
import argparse
import hashlib
import json
import pickle
from pathlib import Path

import numpy as np
import usb_emg

LABELS = ('rest', 'pinch', 'rub', 'snap', 'fist')
from emg_book_models import CLASSICAL, DEEP, book_features, build
MODELS = ('lda', 'svm', 'cnn') + CLASSICAL + DEEP
DEEP_MODELS = ('cnn',) + DEEP


def dataset(root, split, labels=LABELS):
    rows, truth, manifest, warnings = [], [], [], []
    for label in labels:
        files = sorted((root / split / label).glob('*.npz'))
        if len(files) < (30 if split == 'train' else 10):
            raise ValueError(f'{split}/{label} 数量不足')
        for path in files:
            with np.load(path, allow_pickle=False) as z:
                x = np.asarray(z['emg'], dtype=float)
                if x.shape != (2000,) or not np.isfinite(x).all() or int(z['emg_hz']) != 1000:
                    raise ValueError(f'数据格式错误：{path.name}')
                if str(z['label']) != label or int(z['worn_permille']) < 990:
                    raise ValueError(f'标签或贴合无效：{path.name}')
            digest = hashlib.sha256(x.astype('<f8').tobytes()).hexdigest()
            manifest.append({'file': str(path.relative_to(root)), 'sha256': digest})
            rail = float(np.mean((x <= usb_emg.RAIL_LOW) | (x >= usb_emg.RAIL_HIGH)))
            if rail > .01: raise ValueError(f'样本触及量程边界：{path.name}')
            hum = usb_emg.mains_share(x)
            if hum > .8: warnings.append(f'{split}/{path.name}：工频能量占比 {hum:.0%}')
            rows.append(usb_emg.clean(x)); truth.append(labels.index(label))
    return np.asarray(rows), np.asarray(truth), manifest, warnings


def features(x):
    parts = x.reshape(len(x), 8, 250)
    return np.concatenate([np.sqrt(np.mean(parts**2, axis=2)), np.mean(abs(parts), axis=2),
                           np.mean(abs(np.diff(parts, axis=2)), axis=2)], axis=1)


def shape_features(x):
    # 50 ms envelope retains timing; relative shape reduces gain sensitivity.
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or x.shape[1] != 2000 or not np.isfinite(x).all():
        raise ValueError('Expected finite 2 s trials')
    scale = np.maximum(np.sqrt(np.mean(x*x, axis=1, keepdims=True)), 1e-6)
    envelope = np.sqrt(np.mean(x.reshape(-1,40,50)**2, axis=2)) / scale
    return np.concatenate([envelope, np.log1p(scale), np.quantile(envelope,[.1,.5,.9],axis=1).T],axis=1)


def dataset_id(manifest):
    return hashlib.sha256(json.dumps(sorted((r['file'],r['sha256']) for r in manifest), separators=(',',':')).encode()).hexdigest()[:16]


def network():
    import torch
    return torch.nn.Sequential(torch.nn.Conv1d(1, 8, 15, stride=4, padding=7), torch.nn.ReLU(),
        torch.nn.Conv1d(8, 16, 9, stride=4, padding=4), torch.nn.ReLU(),
        torch.nn.AdaptiveAvgPool1d(8), torch.nn.Flatten(), torch.nn.Linear(128, 5))


def report(y, predicted, labels=LABELS):
    n = len(labels)
    matrix = [[int(np.sum((y == a) & (predicted == b))) for b in range(n)] for a in range(n)]
    recalls = [matrix[i][i] / sum(matrix[i]) for i in range(n)]
    return {'balanced_accuracy': float(np.mean(recalls)), 'accuracy': float(np.mean(y == predicted)),
            'recall': dict(zip(labels, recalls)), 'labels': list(labels), 'confusion': matrix, 'samples': len(y)}


def predict(model, kind, x):
    if isinstance(model, dict) and model.get('features') == 'rms-shape-v1':
        return model['estimator'].predict(shape_features(x))
    if kind not in DEEP_MODELS: return model.predict(book_features(x) if kind in CLASSICAL else features(x))
    import torch
    net = network() if kind == 'cnn' else build(kind, **model.get('config', {})); net.load_state_dict(model['weights']); net.eval()
    with torch.no_grad():
        logits = net(torch.tensor(x[:, None] / model['scale'], dtype=torch.float32))
        if not torch.isfinite(logits).all(): raise ValueError('模型输出非有限值')
        return logits.argmax(1).numpy()


def train(root, output, kind, *, epochs=80, representation="baseline", labels=LABELS):
    if representation not in ("baseline", "rms-shape-v1") or (representation != "baseline" and kind != "svm"):
        raise ValueError("Representation requires SVM")
    if kind not in MODELS: raise ValueError('未知模型')
    labels = tuple(labels)
    # 深度网络输出层写死 5 类；别的动作组（和八通道同一份清单）只走经典模型
    if kind in DEEP_MODELS and labels != LABELS: raise ValueError('深度模型只支持原五类')
    x, y, training, warnings = dataset(root, 'train', labels)
    v, vy, validation, vw = dataset(root, 'validation', labels)
    if {r['sha256'] for r in training} & {r['sha256'] for r in validation}:
        raise ValueError('训练与验证包含重复原始样本')
    if kind in DEEP_MODELS:
        import torch
        torch.set_num_threads(2); torch.manual_seed(42)
        net = network() if kind == 'cnn' else build(kind); scale = max(float(x.std()), 1e-6)
        tx = torch.tensor(x[:, None] / scale, dtype=torch.float32); ty = torch.tensor(y)
        optimizer = torch.optim.Adam(net.parameters(), lr=.001, weight_decay=.01)
        for epoch in range(epochs):
            for indices in torch.randperm(len(y)).split(30):
                optimizer.zero_grad(); loss = torch.nn.functional.cross_entropy(net(tx[indices]), ty[indices])
                if not torch.isfinite(loss): raise ValueError('训练损失非有限值，停止保存')
                loss.backward(); optimizer.step()
        model = {'weights': net.state_dict(), 'scale': scale}
    else:
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
        from sklearn.svm import SVC
        from sklearn.neighbors import KNeighborsClassifier
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.neural_network import MLPClassifier
        classifier = {'lda': lambda: LinearDiscriminantAnalysis(solver='lsqr', shrinkage='auto'),
            'svm': lambda: SVC(C=1, kernel='rbf', gamma='scale'),
            'knn': lambda: KNeighborsClassifier(n_neighbors=5),
            'rf': lambda: RandomForestClassifier(n_estimators=200, min_samples_leaf=2, random_state=42, n_jobs=2),
            'mlp': lambda: MLPClassifier(hidden_layer_sizes=(64,32), max_iter=500, random_state=42)}[kind.removesuffix('_features')]()
        if representation == 'rms-shape-v1':
            classifier = SVC(C=10, kernel='rbf', gamma='scale')
            model = {'features':representation,'estimator':make_pipeline(StandardScaler(),classifier)}
            model['estimator'].fit(shape_features(x),y)
        else:
            model = make_pipeline(StandardScaler(), classifier); model.fit(book_features(x) if kind in CLASSICAL else features(x), y)
    output.mkdir(parents=True, exist_ok=False)
    if kind in DEEP_MODELS:
        torch.save(model, output / 'model.pt')
    else:
        (output / 'model.pkl').write_bytes(pickle.dumps(model))
    result = {'model': kind, 'seed': 42, 'preprocessing': 'usb_emg.clean; 1kHz; 2s',
              'dataset_id': dataset_id(training + validation), 'representation': representation,
              'implementation': 'book-single-channel-v1' if kind in CLASSICAL + DEEP else 'baseline-v1',
              'epochs': epochs if kind in DEEP_MODELS else None,
              'labels': list(labels), 'validation': report(vy, predict(model, kind, v), labels), 'warnings': warnings + vw,
              'manifest': training + validation, 'test': None,
              'note': ('书中方法的单通道实验适配，非原实验复现；' if kind in CLASSICAL + DEEP else '') + '离线整条分类；尚未验证连续识别、误触发或动作提前量'}
    (output / 'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def evaluate(root, output):
    result = json.loads((output / 'report.json').read_text())
    if result.get('test') is not None: return result
    labels = tuple(result.get('labels') or LABELS)          # 旧报告没有 labels 字段：就是原五类
    x, y, manifest, warnings = dataset(root, 'test', labels)
    if {r['sha256'] for r in manifest} & {r['sha256'] for r in result['manifest']}:
        raise ValueError('独立测试与训练/验证包含重复原始样本')
    if result['model'] in DEEP_MODELS:
        import torch
        model = torch.load(output / 'model.pt', map_location='cpu', weights_only=True)
    else:
        # Only loads artifacts created locally in this project's validated run directory.
        model = pickle.loads((output / 'model.pkl').read_bytes())
    result['test'] = report(y, predict(model, result['model'], x), labels)
    result['test_manifest'] = manifest; result['warnings'] += warnings
    (output / 'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['train', 'evaluate'])
    p.add_argument('--data', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    p.add_argument('--model', choices=MODELS, default='lda'); p.add_argument('--representation', choices=['baseline','rms-shape-v1'],default='baseline')
    p.add_argument('--labels', default=','.join(LABELS), help='逗号分隔的类别（与八通道动作组同一份清单）；默认原五类'); a = p.parse_args()
    result = train(a.data, a.output, a.model, representation=a.representation, labels=a.labels.split(',')) if a.action == 'train' else evaluate(a.data, a.output)
    print(json.dumps({k: v for k, v in result.items() if k not in ('manifest', 'test_manifest')}, ensure_ascii=False))

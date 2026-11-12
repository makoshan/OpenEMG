"""One-pass comparison on the five-gesture project. Fits on train, scores validation once.

Never opens the test split. Architectures from the textbook TOC are reduced to a
single 1 kHz channel and fixed hyperparameters; they are not the book's multi-channel setups.
"""
import json
from pathlib import Path

import numpy as np

import emg_gesture_train as base

LABELS = base.LABELS
NAMES = ('放松', '捏合', '搓动', '响指', '握拳')


def locked(root, split):
    if split == 'test':
        raise RuntimeError('独立测试集保持封存')
    return base.dataset(root, split)


def rich(x):
    parts = x.reshape(len(x), 8, 250)
    rms = np.sqrt(np.mean(parts ** 2, axis=2))
    mav = np.mean(np.abs(parts), axis=2)
    wl = np.mean(np.abs(np.diff(parts, axis=2)), axis=2)
    var = np.var(parts, axis=2)
    sign = np.sign(parts)
    sign[sign == 0] = 1
    zc = np.mean(sign[:, :, 1:] * sign[:, :, :-1] < 0, axis=2)
    slope = np.diff(parts, axis=2)
    ssc = np.mean(slope[:, :, 1:] * slope[:, :, :-1] < 0, axis=2)
    spec = np.fft.rfft(parts, axis=2)
    power = np.abs(spec) ** 2
    freqs = np.fft.rfftfreq(250, d=0.001)
    total = power.sum(axis=2) + 1e-12
    mean_f = (power * freqs).sum(axis=2) / total
    half = np.cumsum(power, axis=2) >= (total[:, :, None] / 2)
    median_f = freqs[np.argmax(half, axis=2)]
    return np.concatenate([rms, mav, wl, var, zc, ssc, mean_f, median_f], axis=1)


def gasf(x, n=32):
    index = np.linspace(0, x.shape[1] - 1, n).astype(int)
    z = x[:, index]
    span = np.maximum(z.max(axis=1, keepdims=True) - z.min(axis=1, keepdims=True), 1e-8)
    z = np.clip(2 * (z - z.min(axis=1, keepdims=True)) / span - 1, -1, 1)
    phi = np.arccos(z)
    cosine, sine = np.cos(phi), np.sin(phi)
    field = cosine[:, :, None] * cosine[:, None, :] - sine[:, :, None] * sine[:, None, :]
    return field[:, None].astype(np.float32)


def squash(v):
    import torch
    squared = (v * v).sum(-1, keepdim=True)
    return squared / (1 + squared) * v / (squared.sqrt() + 1e-8)


class DigitCaps:
    def __new__(cls, n_in, d_in, n_out=5, d_out=8):
        import torch
        class _Digit(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.weight = torch.nn.Parameter(torch.randn(n_in, n_out, d_out, d_in) * 0.01)

            def forward(self, primary):
                vote = torch.einsum('ijko,bio->bijk', self.weight, primary)
                logits = vote.new_zeros(vote.shape[0], n_in, n_out)
                output = None
                for step in range(3):
                    couple = torch.softmax(logits, dim=2)
                    total = torch.einsum('bij,bijk->bjk', couple, vote)
                    output = squash(total)
                    if step < 2:
                        logits = logits + torch.einsum('bijk,bjk->bij', vote, output)
                return output
        return _Digit()


def build(kind):
    import torch
    models = {
        'cnn': base.network,
        'tcn': TCN,
        'lstm': lambda: SeqNet(torch.nn.LSTM),
        'rnn': lambda: SeqNet(torch.nn.RNN),
        'cnn-lstm': CNNLSTM,
        'gaf-cnn': GafCNN,
        'capsnet': CapsNet,
        'cnn-capsnet': CNNCaps,
        'capsnet-gru': CapsGRU,
        'dual-stream': DualStream,
    }
    return models[kind]()


class SeqNet:
    def __new__(cls, cell):
        import torch
        class _Net(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.proj = torch.nn.Linear(250, 16)
                self.cell = cell(16, 16, batch_first=True)
                self.out = torch.nn.Linear(16, 5)

            def forward(self, wave):
                hidden = torch.relu(self.proj(wave.reshape(wave.shape[0], 8, 250)))
                sequence, _ = self.cell(hidden)
                return self.out(sequence[:, -1])
        return _Net()


class TCN:
    def __new__(cls):
        import torch
        layers, channels = [], 1
        for dilation in (1, 2, 4, 8):
            layers += [torch.nn.Conv1d(channels, 16, 5, padding=2 * dilation, dilation=dilation), torch.nn.ReLU()]
            channels = 16
        layers += [torch.nn.AdaptiveAvgPool1d(1), torch.nn.Flatten(), torch.nn.Linear(16, 5)]
        return torch.nn.Sequential(*layers)


class CNNLSTM:
    def __new__(cls):
        import torch
        class _Net(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.conv = torch.nn.Sequential(
                    torch.nn.Conv1d(1, 8, 15, stride=4, padding=7), torch.nn.ReLU(),
                    torch.nn.Conv1d(8, 16, 9, stride=4, padding=4), torch.nn.ReLU())
                self.cell = torch.nn.LSTM(16, 16, batch_first=True)
                self.out = torch.nn.Linear(16, 5)

            def forward(self, wave):
                encoded = self.conv(wave[:, None]).transpose(1, 2)
                sequence, _ = self.cell(encoded)
                return self.out(sequence[:, -1])
        return _Net()


class GafCNN:
    def __new__(cls):
        import torch
        return torch.nn.Sequential(
            torch.nn.Conv2d(1, 8, 3, padding=1), torch.nn.ReLU(), torch.nn.MaxPool2d(2),
            torch.nn.Conv2d(8, 16, 3, padding=1), torch.nn.ReLU(), torch.nn.MaxPool2d(2),
            torch.nn.Flatten(), torch.nn.Linear(16 * 8 * 8, 5))


class CapsNet:
    def __new__(cls):
        import torch
        class _Net(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.conv = torch.nn.Conv2d(1, 16, 3, stride=2, padding=1)
                self.digits = DigitCaps(4 * 16 * 16, 4)

            def forward(self, image):
                primary = torch.relu(self.conv(image))
                primary = primary.reshape(image.shape[0], 4, 4, 16, 16).permute(0, 1, 3, 4, 2)
                primary = squash(primary.reshape(image.shape[0], -1, 4))
                return self.digits(primary)
        return _Net()


class CNNCaps:
    def __new__(cls):
        import torch
        class _Net(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.embed = torch.nn.Sequential(
                    torch.nn.Conv2d(1, 8, 3, padding=1), torch.nn.ReLU(), torch.nn.MaxPool2d(4),
                    torch.nn.Flatten(), torch.nn.Linear(8 * 8 * 8, 16), torch.nn.ReLU())
                self.caps = CapsNet()
                self.out = torch.nn.Linear(16 + 5, 5)

            def forward(self, image):
                length = self.caps(image).norm(dim=-1)
                return self.out(torch.cat([self.embed(image), length], dim=1))
        return _Net()


class CapsGRU:
    def __new__(cls):
        import torch
        class _Net(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.proj = torch.nn.Linear(250, 16)
                self.cell = torch.nn.GRU(16, 8, batch_first=True)
                self.digits = DigitCaps(8, 8)

            def forward(self, wave):
                hidden = torch.relu(self.proj(wave.reshape(wave.shape[0], 8, 250)))
                sequence, _ = self.cell(hidden)
                return self.digits(sequence)
        return _Net()


class DualStream:
    def __new__(cls):
        import torch
        class _Net(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.wave = torch.nn.Sequential(
                    torch.nn.Conv1d(1, 8, 15, stride=4, padding=7), torch.nn.ReLU(),
                    torch.nn.Conv1d(8, 16, 9, stride=4, padding=4), torch.nn.ReLU(),
                    torch.nn.AdaptiveAvgPool1d(1), torch.nn.Flatten())
                self.feat = torch.nn.Sequential(torch.nn.Linear(24, 16), torch.nn.ReLU())
                self.out = torch.nn.Linear(32, 5)

            def forward(self, wave, feat):
                return self.out(torch.cat([self.wave(wave[:, None]), self.feat(feat)], dim=1))
        return _Net()


def fit_table(kind, train_x, train_y):
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
    from sklearn.svm import SVC
    table = rich(train_x) if kind.endswith('-rich') else base.features(train_x)
    name = kind.replace('-rich', '')
    if name == 'knn':
        clf = KNeighborsClassifier(n_neighbors=5)
    elif name == 'rf':
        clf = RandomForestClassifier(n_estimators=300, max_depth=6, min_samples_leaf=2, random_state=42)
    elif name == 'lda':
        clf = LinearDiscriminantAnalysis(solver='lsqr', shrinkage='auto')
    elif name == 'svm':
        clf = SVC(C=1, kernel='rbf', gamma='scale')
    else:
        raise ValueError(kind)
    model = make_pipeline(StandardScaler(), clf)
    model.fit(table, train_y)
    return model


def predict_table(model, kind, samples):
    table = rich(samples) if kind.endswith('-rich') else base.features(samples)
    return model.predict(table)


def fit_net(kind, train_x, train_y, train_feat=None):
    import torch
    torch.manual_seed(42)
    torch.set_num_threads(2)
    net = build(kind)
    margin = kind in ('capsnet', 'capsnet-gru')
    scale = max(float(train_x.std()), 1e-6)
    xt = inputs(kind, train_x, scale)
    if not (kind.startswith('gaf') or kind in ('capsnet', 'cnn-capsnet')):
        net.scale = scale
    yt = torch.tensor(train_y)
    feat = None if train_feat is None else torch.tensor(train_feat, dtype=torch.float32)
    opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-2)
    net.train()
    for _ in range(80):
        for index in torch.randperm(len(yt)).split(30):
            opt.zero_grad()
            pred = net(xt[index], feat[index]) if kind == 'dual-stream' else net(xt[index])
            if margin:
                length = pred.norm(dim=-1)
                target = torch.nn.functional.one_hot(yt[index], 5).float()
                loss = (target * torch.relu(0.9 - length) ** 2 + 0.5 * (1 - target) * torch.relu(length - 0.1) ** 2).sum(1).mean()
            else:
                loss = torch.nn.functional.cross_entropy(pred, yt[index])
            loss.backward()
            opt.step()
    net.eval()
    return net


def inputs(kind, samples, scale):
    import torch
    if kind.startswith('gaf') or kind in ('capsnet', 'cnn-capsnet'):
        return torch.tensor(gasf(samples))
    wave = torch.tensor(samples / scale, dtype=torch.float32)
    return wave[:, None] if kind in ('cnn', 'tcn') else wave


def predict_net(kind, net, samples, feat=None):
    import torch
    xt = inputs(kind, samples, getattr(net, 'scale', 1.0))
    with torch.no_grad():
        pred = net(xt, torch.tensor(feat, dtype=torch.float32)) if kind == 'dual-stream' else net(xt)
    if kind in ('capsnet', 'capsnet-gru'):
        return pred.norm(dim=-1).argmax(1).numpy()
    return pred.argmax(1).numpy()


def row(kind, train_y, train_hat, val_y, val_hat):
    train = base.report(train_y, train_hat)
    val = base.report(val_y, val_hat)
    return {'model': kind, 'train_balanced_accuracy': train['balanced_accuracy'],
            'validation_balanced_accuracy': val['balanced_accuracy'],
            'validation_recall': {NAMES[i]: val['recall'][LABELS[i]] for i in range(5)},
            'confusion': val['confusion']}


def main():
    root = Path(__file__).resolve().parent / 'emg-gesture-data'
    x, y, train_manifest, train_warnings = locked(root, 'train')
    v, vy, val_manifest, val_warnings = locked(root, 'validation')
    if {item['sha256'] for item in train_manifest} & {item['sha256'] for item in val_manifest}:
        raise RuntimeError('训练与验证包含重复样本')
    feat = base.features(x)
    vfeat = base.features(v)
    table_models = ('knn', 'lda', 'svm', 'rf', 'knn-rich', 'lda-rich', 'svm-rich', 'rf-rich')
    net_models = ('cnn', 'rnn', 'lstm', 'tcn', 'cnn-lstm', 'gaf-cnn', 'capsnet', 'cnn-capsnet', 'capsnet-gru', 'dual-stream')
    rows = []
    for kind in table_models:
        model = fit_table(kind, x, y)
        rows.append(row(kind, y, predict_table(model, kind, x), vy, predict_table(model, kind, v)))
        print(kind, f"{rows[-1]['validation_balanced_accuracy']:.3f}", flush=True)
    for kind in net_models:
        net = fit_net(kind, x, y, feat if kind == 'dual-stream' else None)
        rows.append(row(kind, y, predict_net(kind, net, x, feat if kind == 'dual-stream' else None),
                        vy, predict_net(kind, net, v, vfeat if kind == 'dual-stream' else None)))
        print(kind, f"{rows[-1]['validation_balanced_accuracy']:.3f}", flush=True)
    skipped = [
        {'model': '遗传算法/差分进化/粒子群/蚁群选通道', 'reason': '只有一路 Cheez 信号，没有通道可以选'},
        {'model': '肌电与超声波融合', 'reason': '没有超声波通道'},
    ]
    out = {'protocol': 'fit train only; score validation once; test sealed',
           'train': 150, 'validation': 50, 'seed': 42, 'epochs': 80,
           'rows': rows, 'skipped': skipped,
           'warnings': len(train_warnings) + len(val_warnings)}
    dest = Path(__file__).resolve().parents[1] / 'evidence' / '2026-09-27-emg-model-sweep.json'
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print('wrote', dest)


if __name__ == '__main__':
    main()

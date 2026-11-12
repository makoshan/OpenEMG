"""Single-channel research adaptations; see research/emg-book-models.md, not paper reproductions."""
import numpy as np

CLASSICAL = ('lda_features', 'svm_features', 'knn', 'rf', 'mlp')
DEEP = ('rnn', 'lstm', 'gru', 'cnn_lstm', 'gaf_cnn', 'gaf_cnn_lstm', 'gaf_caps', 'gaf_cnn_caps',
        'caps_gru', 'dual_stream', 'feature_fusion')


def book_features(x):
    """Seven book features per 250 ms block; SampEn m=2, r=.2 SD, AR4 least squares."""
    result = []
    for row in x:
        blocks = []
        for w in row.reshape(8, 250):
            d = np.diff(w)
            threshold = 0.01 * w.std()
            zc = np.sum((w[:-1] * w[1:] < 0) & (np.abs(d) > threshold))
            ssc = np.sum((d[:-1] * d[1:] < 0) & (np.minimum(np.abs(d[:-1]), np.abs(d[1:])) > threshold))
            lag = np.lib.stride_tricks.sliding_window_view(w, 5)
            ar = np.linalg.lstsq(lag[:, :4], lag[:, 4], rcond=1e-6)[0]
            templates = np.lib.stride_tricks.sliding_window_view(w, 3)
            distance = np.abs(templates[:, None, :] - templates[None, :, :])
            radius = 0.2 * w.std()
            b = np.triu(np.max(distance[:, :, :2], axis=2) <= radius, 1).sum()
            a = np.triu(np.max(distance, axis=2) <= radius, 1).sum()
            entropy = -np.log((a + 0.5) / (b + 0.5))
            blocks.extend([np.mean(np.abs(w)), zc, ssc, np.sum(np.abs(d)), *ar,
                           np.sqrt(np.mean(w * w)), entropy])
        result.append(blocks)
    return np.asarray(result)


def build(kind, hidden=32, pooling="last", gaf_mode="mean", dropout=0.):
    if hidden not in (32,64,128,256) or pooling not in ("last","mean") or gaf_mode not in ("mean","rms") or not 0 <= dropout < 1:
        raise ValueError("Invalid network configuration")
    import torch
    from torch import nn

    class Capsules(nn.Module):
        def __init__(self):
            super().__init__()
            self.primary = nn.Linear(32, 64)
            self.weight = nn.Parameter(0.1 * torch.randn(8, 5, 8, 8))

        def forward(self, x):
            u = self.primary(x).reshape(-1, 8, 8)
            norm = (u * u).sum(-1, keepdim=True)
            u = norm / (1 + norm) * u / torch.sqrt(norm + 1e-8)
            votes = torch.einsum('bid,ijdo->bijo', u, self.weight)
            logits = votes.new_zeros(votes.shape[:3])
            for _ in range(3):
                couple = logits.softmax(-1)[..., None]
                total = (couple * votes).sum(1)
                squared = (total * total).sum(-1, keepdim=True)
                v = squared / (1 + squared) * total / torch.sqrt(squared + 1e-8)
                logits = logits + (votes * v[:, None]).sum(-1)
            return v.flatten(1)

    class BookNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.kind = kind
            self.conv = nn.Sequential(
                nn.Conv1d(1, 16, 9, padding=4), nn.ReLU(), nn.AvgPool1d(10),
                nn.Conv1d(16, 32, 5, padding=2), nn.ReLU(), nn.AdaptiveAvgPool1d(40))
            self.image = nn.Sequential(
                nn.Conv2d(1, 8, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
                nn.Conv2d(8, 16, 3, padding=1), nn.ReLU(), nn.AdaptiveAvgPool2d((4, 4)))
            self.image_fc = nn.Linear(256, 32)
            recurrent = {'rnn': nn.RNN, 'gru': nn.GRU, 'caps_gru': nn.GRU}.get(kind, nn.LSTM)
            inputs = 32 if kind == 'cnn_lstm' else 64 if kind == 'gaf_cnn_lstm' else 10
            self.recurrent = recurrent(inputs, hidden, batch_first=True)
            self.dropout = nn.Dropout(dropout)
            self.caps = Capsules()
            if kind == 'gaf_caps':
                size = 40
            elif kind == 'gaf_cnn_caps':
                size = 72
            elif kind == 'caps_gru':
                size = 40 + hidden
            elif kind == 'feature_fusion':
                size = 35 + hidden
            elif kind == 'dual_stream':
                size = 32 + hidden
            elif kind in ('rnn','lstm','gru','cnn_lstm','gaf_cnn_lstm'):
                size = hidden
            else:
                size = 32
            self.head = nn.Linear(size, 5)

        def temporal(self, sequence):
            values = self.recurrent(sequence)[0]
            return values.mean(1) if pooling == "mean" else values[:, -1]

        def forward(self, x):
            k = self.kind
            sequence = x[:, 0].reshape(-1, 200, 10)
            if k.startswith('gaf'):
                parts = x[:, 0].reshape(-1, 40, 50)
                z = (parts.square().mean(-1)+1e-8).sqrt() if gaf_mode == "rms" else parts.mean(-1)
                lo = z.amin(1, keepdim=True)
                span = z.amax(1, keepdim=True) - lo
                z = (2 * (z - lo) / span.clamp_min(1e-8) - 1).clamp(-1, 1)
                sine = torch.sqrt((1 - z * z).clamp_min(0))
                gaf = z[:, :, None] * z[:, None, :] - sine[:, :, None] * sine[:, None, :]
                image = self.image(gaf[:, None])
                spatial = self.image_fc(image.flatten(1))
                if k == 'gaf_cnn_lstm':
                    sequence = image.permute(0, 2, 1, 3).reshape(-1, 4, 64)
                    out = self.temporal(sequence)
                elif k == 'gaf_caps':
                    out = self.caps(spatial)
                elif k == 'gaf_cnn_caps':
                    out = torch.cat([spatial, self.caps(spatial)], 1)
                else:
                    out = spatial
            elif k in ('rnn', 'lstm', 'gru'):
                out = self.temporal(sequence)
            else:
                spatial = self.conv(x)
                if k == 'cnn_lstm':
                    out = self.temporal(spatial.transpose(1, 2))
                else:
                    temporal = self.temporal(sequence)
                    pooled = spatial.mean(-1)
                    if k == 'caps_gru':
                        out = torch.cat([self.caps(pooled), temporal], 1)
                    else:
                        out = torch.cat([pooled, temporal], 1)
                        if k == 'feature_fusion':
                            mav = x.abs().mean((1, 2))
                            wl = x.diff(dim=2).abs().mean((1, 2))
                            zc = (x[:, :, :-1] * x[:, :, 1:] < 0).float().mean((1, 2))
                            out = torch.cat([out, torch.stack([mav, wl, zc], 1)], 1)
            return self.head(self.dropout(out))

    if kind not in DEEP:
        raise ValueError('Unknown research network')
    return BookNet()

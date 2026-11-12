"""同次佩戴的峰值/全过程双模板候选，仅供本机离线回放，未接游戏控制。

固定等权混合两个收缩 LDA；沿用频带特征，不把高幅肌电直接判为坏接触。
这里没有未知动作训练集，置信值也不是校准后的正确率，不能代替真人连续验收。
"""
import numpy as np
from adaptive_intent import FS, WINDOW, STEP, observation
from wl8_train import fit as lda_fit, scores

VERSION = 'intent-mixture-v1'


def fit(records, rest, donning):
    if type(donning) is not int or donning < 1:
        raise ValueError('需要本次佩戴编号')
    labels = [r['label'] for r in records]
    classes = sorted(set(labels))
    if rest not in classes or len(classes) < 2 or any(labels.count(c) < 3 for c in classes):
        raise ValueError('本次佩戴每类至少三条独立录音')
    peak = np.asarray([r['x'] for r in records], float)
    windows = [np.asarray([w[0] for w in r['windows']], float) for r in records]
    if peak.shape != (len(records), 40) or not np.isfinite(peak).all() or any(
        x.ndim != 2 or x.shape[1] != 40 or len(x) == 0 or not np.isfinite(x).all() for x in windows
    ):
        raise ValueError('训练特征无效')
    # 每条录音贡献相同数量的窗，避免较长录音在训练里权重更大。
    count = min(map(len, windows))
    x = np.concatenate([w[np.linspace(0, len(w)-1, count).astype(int)] for w in windows])
    models = [lda_fit(peak, np.array(labels)), lda_fit(x, np.repeat(labels, count))]
    data = dict(version=VERSION, fs=FS, window=WINDOW, step=STEP, donning=donning,
                rest=rest, classes=classes, windows_per_record=count, records=len(records),
                mode='offline', validated_for_control=False,
                models=[{k: m[k].tolist() for k in ('mu', 'sinv')} for m in models])
    Model(data)
    return data


class Model:
    def __init__(self, data):
        if (data.get('version'), data.get('fs'), data.get('window'), data.get('step')) != (VERSION, FS, WINDOW, STEP):
            raise ValueError('候选版本不兼容')
        if type(data.get('donning')) is not int or data['donning'] < 1:
            raise ValueError('佩戴编号无效')
        self.classes = list(data['classes']); self.rest = data['rest']; self.data = data
        if len(self.classes) < 2 or len(set(self.classes)) != len(self.classes) or self.rest not in self.classes:
            raise ValueError('类别无效')
        if len(data['models']) != 2:
            raise ValueError('需要两个模板')
        self.models = []
        for m in data['models']:
            mu, inv = np.asarray(m['mu'], float), np.asarray(m['sinv'], float)
            if mu.shape != (len(self.classes), 40) or inv.shape != (40, 40) or not np.isfinite(mu).all() or not np.isfinite(inv).all():
                raise ValueError('模板形状或数值无效')
            if not np.allclose(inv, inv.T) or np.linalg.eigvalsh(inv).min() <= 0:
                raise ValueError('模板协方差无效')
            self.models.append(dict(classes=self.classes, mu=mu, sinv=inv))

    def predict(self, x):
        x = np.asarray(x, float)
        if x.shape != (40,) or not np.isfinite(x).all():
            raise ValueError('需要有限的40维特征')
        p = sum(scores(m, x[None])[1][0] for m in self.models) / 2
        if not np.isfinite(p).all():
            raise ValueError('预测溢出')
        return p


class Decoder:
    """连续三窗达到游戏门槛才消耗准备状态；开头和断流后都需重新放松。"""
    def __init__(self, classes, rest):
        self.classes = list(classes); self.rest = rest
        if rest not in self.classes or len(set(self.classes)) != len(self.classes) or len(self.classes) < 2:
            raise ValueError('类别无效')
        self.reset()

    def reset(self):
        self.armed = False; self.candidate = None; self.count = 0; self.rest_count = 0

    def push(self, probs):
        p = np.asarray(probs, float)
        if p.shape != (len(self.classes),) or not np.isfinite(p).all() or np.any(p < 0) or not np.isclose(p.sum(), 1):
            self.reset()
            return None
        k = int(p.argmax()); label = self.classes[k]
        # 对齐旧游戏三位小数协议；没有达到游戏门槛的窗口不能把一次动作耗掉。
        confidence = round(float(p[k]), 3)
        if confidence < (.65 if label == self.rest else .8):
            self.candidate = None; self.count = 0; self.rest_count = 0
            return None
        if label == self.rest:
            self.candidate = None; self.count = 0; self.rest_count += 1
            if self.rest_count >= 2:
                self.armed = True
            return None
        self.rest_count = 0
        self.count = self.count + 1 if label == self.candidate else 1
        self.candidate = label
        if self.armed and self.count >= 3:
            self.armed = False
            return label
        return None


class Stream:
    """调用方在断流或换佩戴时必须 reset；按样本切窗，分块大小不改变结果。"""
    def __init__(self, data):
        self.model = Model(data)
        self.decoder = Decoder(self.model.classes, self.model.rest)
        self.reset()

    def reset(self):
        self.buffer = np.empty((0, 8)); self.samples = 0; self.next_end = WINDOW
        self.decoder.reset()

    def push(self, raw):
        raw = np.asarray(raw, float)
        if raw.ndim != 2 or raw.shape[1] != 8 or not np.isfinite(raw).all():
            self.reset()
            raise ValueError('原始数据块无效')
        results = []; offset = 0
        while offset < len(raw):
            take = min(self.next_end - self.samples, len(raw) - offset)
            self.buffer = np.concatenate([self.buffer, raw[offset:offset+take]])[-WINDOW:]
            self.samples += take; offset += take
            if self.samples == self.next_end:
                x, q, rms = observation(self.buffer)
                # 平线只清状态，不把放松幅度高直接当成坏接触。
                flat = bool(np.any(rms < 1e-6) or np.any(q[24:] > .98))
                p = self.model.predict(x)
                if flat:
                    self.decoder.reset()
                event = None if flat else self.decoder.push(p)
                results.append(dict(sample_end=self.samples, window_start=self.samples-WINDOW,
                                    probs=p.tolist(), event=event, flatline=flat, mode='offline', version=VERSION))
                self.next_end += STEP
        return results


def main():
    import argparse
    import json
    from pathlib import Path
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--model', type=Path, required=True)
    ap.add_argument('--raw', type=Path, required=True, help='同次佩戴原始npz；不访问设备')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise ValueError('不覆盖已有回放结果')
    stream = Stream(json.loads(args.model.read_text()))
    # 用原始文件旁的元数据核对佩戴段，禁止跨人/跨佩戴套用。
    meta = json.loads(args.raw.with_suffix('.json').read_text())
    if meta.get('dropped', 0) != 0:
        raise ValueError('录音有丢帧且没有缺口位置，不能按连续数据回放')
    binding = stream.model.data.get('binding')
    if not binding or binding != [str(meta.get('recordedAt', ''))[:10], meta.get('donning'), str(meta.get('session', ''))]:
        raise ValueError('录音与模型佩戴段不匹配')
    with np.load(args.raw, allow_pickle=False) as z:
        if 'emg_hz' not in z or float(z['emg_hz']) != FS:
            raise ValueError('采样率不匹配')
        ticks = stream.push(z['emg_uv'])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x') as f:
        json.dump(dict(version=VERSION, mode='offline', ticks=ticks), f, ensure_ascii=False)
    print('本机回放完成：', len(ticks), '窗；未发送控制事件')


if __name__ == '__main__':
    main()

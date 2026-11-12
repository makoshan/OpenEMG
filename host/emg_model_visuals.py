"""Reproducible figures for the saved five-gesture artifacts; never reads test/."""
import argparse
import html
import json
import pickle
from pathlib import Path

import numpy as np

import emg_gesture_train as train

LABELS = train.LABELS
COLORS = ('#5167d8', '#e08443', '#39a278', '#c85b7b', '#7a5cc7')
NAMES = {
    'lda': 'LDA', 'lda_features': '增强特征 LDA', 'svm': 'SVM', 'svm_features': '增强特征 SVM',
    'knn': 'KNN', 'rf': '随机森林', 'mlp': 'MLP', 'cnn': '1D CNN', 'rnn': 'RNN', 'lstm': 'LSTM',
    'gru': 'GRU', 'cnn_lstm': 'CNN-LSTM', 'dual_stream': '双流', 'feature_fusion': '多特征融合',
    'caps_gru': 'CapsNet-GRU', 'gaf_cnn': 'GAF-CNN', 'gaf_cnn_lstm': 'GAF-CNN-LSTM',
    'gaf_caps': 'GAF-CapsNet', 'gaf_cnn_caps': 'GAF-CNN-CapsNet',
}


def load_trials(data_root, manifest, split):
    rows, labels, paths = [], [], []
    for entry in manifest:
        rel = Path(entry['file'])
        if rel.parts[0] != split:
            continue
        path = data_root / rel
        # Old rub-v1 was intentionally archived after these immutable runs.
        if not path.exists():
            path = data_root.parent / 'archive/rub-v1-单次滑动-20260928' / rel
        with np.load(path, allow_pickle=False) as z:
            rows.append(train.usb_emg.clean(np.asarray(z['emg'], dtype=float)))
            labels.append(LABELS.index(str(z['label'])))
            paths.append(rel)
    return np.asarray(rows), np.asarray(labels), paths


def artifact(run):
    report = json.loads((run / 'report.json').read_text())
    suffix = 'pt' if report['model'] in train.DEEP_MODELS else 'pkl'
    path = run / f'model.{suffix}'
    if suffix == 'pt':
        import torch
        model = torch.load(path, map_location='cpu', weights_only=True)
    else:
        model = pickle.loads(path.read_bytes())
    return report, model


def vectors(kind, x):
    return train.book_features(x) if kind in train.CLASSICAL else train.features(x)


def svg_open(title, w=1000, h=620):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{html.escape(title)}">
<style>text{{font-family:-apple-system,BlinkMacSystemFont,"Noto Sans CJK SC",sans-serif;fill:#172235}}.t{{font-size:25px;font-weight:600}}.s{{font-size:15px;fill:#536175}}.a{{font-size:13px;fill:#536175}}.n{{font-size:15px;font-weight:600}}.grid{{stroke:#d9e0ea;stroke-width:1}}.axis{{stroke:#7f8b9c;stroke-width:1.25}}</style>
<rect width="100%" height="100%" fill="#fff"/><text class="t" x="42" y="42">{html.escape(title)}</text>'''


def svg_close(note='仅训练/重戴验证；未读取独立 test 集'):
    return f'<text class="s" x="42" y="598">{html.escape(note)}</text></svg>'


def write(path, body):
    path.write_text(body, encoding='utf-8')


def bar_compare(kind, report, model, x, y, vx, vy, out):
    pred, vpred = train.predict(model, kind, x), train.predict(model, kind, vx)
    a = train.report(y, pred)['balanced_accuracy'] * 100
    b = train.report(vy, vpred)['balanced_accuracy'] * 100
    title = f'{NAMES[kind]}：训练成绩与重戴验证'
    s = svg_open(title, 1000, 330)
    s += '<text class="s" x="42" y="70">同一重戴验证口径（五类召回平均）；训练高、重戴未同步提高 = 记住训练集</text>'
    for i, (label, value, color) in enumerate((('训练', a, '#6074d8'), ('重戴验证', b, '#db7445'))):
        y0 = 115 + i * 82; width = 760 * value / 100
        s += f'<text class="n" x="42" y="{y0 + 29}">{label}</text><rect x="150" y="{y0}" width="760" height="42" rx="4" fill="#edf0f5"/><rect x="150" y="{y0}" width="{width:.1f}" height="42" rx="4" fill="{color}"/><text class="n" x="925" y="{y0 + 29}">{value:.1f}%</text>'
    gap = a - b
    s += f'<text class="s" x="42" y="300">训练 − 重戴：{gap:+.1f} 个百分点</text></svg>'
    write(out, s)
    return pred, vpred, a, b


def projection(x, y, vx):
    # sklearn's stored lsqr LDA has no transform(); this is a visualization-only fit.
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler().fit(x)
    lda = LinearDiscriminantAnalysis(solver='svd', n_components=2).fit(scaler.transform(x), y)
    return lda.transform(scaler.transform(x)), lda.transform(scaler.transform(vx))


def scatter(kind, x, y, vx, vy, vpred, out, tuned=None):
    p, vp = projection(vectors(kind, x), y, vectors(kind, vx))
    panels = [(NAMES[kind], p, y, None), ('重戴：圆=判对，×=判错', vp, vy, vpred)]
    if tuned is not None:
        panels[1] = ('原 SVM 重戴：圆=对，×=错', vp, vy, vpred)
    allp = np.vstack([p, vp]); lo, hi = allp.min(0), allp.max(0); pad = np.maximum((hi-lo)*.08, .1); lo -= pad; hi += pad
    s = svg_open(f'{NAMES[kind]}：特征在 LDA 两轴上的投影')
    for j, (head, pts, truth, pred) in enumerate(panels):
        left = 50 + j * 490; top, size = 90, 425
        s += f'<rect x="{left}" y="{top}" width="{size}" height="{size}" fill="#fbfcfe" stroke="#cdd6e2"/><text class="n" x="{left}" y="76">{head}</text>'
        for i in range(5):
            s += f'<circle cx="{left+14+i*85}" cy="540" r="5" fill="{COLORS[i]}"/><text class="a" x="{left+23+i*85}" y="545">{LABELS[i]}</text>'
        for point, label, i in zip(pts, truth, range(len(truth))):
            px = left + 16 + (point[0]-lo[0])/(hi[0]-lo[0])*(size-32); py = top + size-16 - (point[1]-lo[1])/(hi[1]-lo[1])*(size-32)
            wrong = pred is not None and pred[i] != label
            mark = f'<path d="M {px-5:.1f} {py-5:.1f} L {px+5:.1f} {py+5:.1f} M {px+5:.1f} {py-5:.1f} L {px-5:.1f} {py+5:.1f}" stroke="{COLORS[label]}" stroke-width="2"/>' if wrong else f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{COLORS[label]}" fill-opacity=".78"/>'
            s += mark
        s += f'<text class="a" x="{left+size/2-25}" y="{top+size+24}">LDA 轴 1</text><text class="a" x="{left-4}" y="{top+size/2}" transform="rotate(-90 {left-4} {top+size/2})">LDA 轴 2</text>'
    note = 'LDA(lsqr) 本身不能 transform；此处按同一训练样本重拟合仅用于二维显示。'
    write(out, s + svg_close(note))


def knn_neighbors(model, x, y, vx, vy, vpred, out):
    errors = np.flatnonzero(vpred != vy)[:8]
    s = svg_open('KNN：每条重戴错样本的 5 个训练近邻')
    if not len(errors):
        s += '<text class="n" x="42" y="100">没有重戴错样本可标注。</text>'
    else:
        dist, ids = model[-1].kneighbors(model[:-1].transform(vectors('knn', vx[errors])), n_neighbors=5)
        for row, (err, ds, ns) in enumerate(zip(errors, dist, ids)):
            y0 = 90 + row*58
            s += f'<text class="a" x="42" y="{y0+20}">#{err+1} 真={LABELS[vy[err]]} → 判={LABELS[vpred[err]]}</text>'
            for col, (d, n) in enumerate(zip(ds, ns)):
                xx=285+col*126; lab=LABELS[y[n]]
                s += f'<rect x="{xx}" y="{y0}" width="112" height="34" rx="4" fill="{COLORS[y[n]]}" fill-opacity=".18"/><text class="a" x="{xx+7}" y="{y0+14}">{lab}</text><text class="a" x="{xx+7}" y="{y0+28}">d={d:.2f}</text>'
        s += '<text class="s" x="42" y="570">色块是邻居的训练标签；同类稀少或错类更近时，KNN 会随邻居投票出错。</text>'
    write(out, s + svg_close())


def feature_importance(model, out):
    importance = model[-1].feature_importances_
    if len(importance) == 80:
        names = ('MAV', 'ZC', 'SSC', 'WL（绝对差分和）', 'AR1', 'AR2', 'AR3', 'AR4', 'RMS', 'SampEn')
        importance = importance.reshape(8, 10).sum(0)
        title = '随机森林：保存的 80 维书中特征重要度（按 8 段汇总）'
    else:
        names = tuple(f'第{i+1}段 {metric}' for metric in ('RMS','MAV','MAD') for i in range(8))
        title = '随机森林：24 维特征重要度'
    order = np.argsort(importance)[::-1]
    s = svg_open(title)
    maxv = max(importance.max(), 1e-8)
    for row, idx in enumerate(order):
        y0=80+row*20; w=680*importance[idx]/maxv
        s += f'<text class="a" x="42" y="{y0+13}">{names[idx]}</text><rect x="175" y="{y0}" width="{w:.1f}" height="14" fill="#6074d8"/><text class="a" x="{865}" y="{y0+13}">{importance[idx]:.3f}</text>'
    write(out, s + svg_close('模型实际输入为 80 维；重要度是森林对分裂的依赖，不等于因果解释。'))


def heatmap(s, matrix, x0, y0, title):
    cell=54; m=max(max(row) for row in matrix) or 1
    s += f'<text class="n" x="{x0}" y="{y0-25}">{title}</text><text class="a" x="{x0+130}" y="{y0-7}">预测 →</text><text class="a" x="{x0-35}" y="{y0+140}" transform="rotate(-90 {x0-35} {y0+140})">真实 →</text>'
    for i, label in enumerate(LABELS):
        s += f'<text class="a" x="{x0+i*cell+6}" y="{y0-2}">{label}</text><text class="a" x="{x0-38}" y="{y0+i*cell+32}">{label}</text>'
        for j, value in enumerate(matrix[i]):
            alpha=.12+.78*value/m
            s += f'<rect x="{x0+j*cell}" y="{y0+i*cell}" width="{cell-2}" height="{cell-2}" fill="#6074d8" fill-opacity="{alpha:.2f}"/><text class="a" x="{x0+j*cell+21}" y="{y0+i*cell+31}">{value}</text>'
    return s


def mlp_heatmaps(y, pred, vy, vpred, out):
    s=svg_open('MLP：训练混淆与重戴混淆')
    s=heatmap(s, train.report(y,pred)['confusion'],100,120,'训练')
    s=heatmap(s, train.report(vy,vpred)['confusion'],570,120,'重戴验证')
    write(out,s+svg_close('训练矩阵接近对角线、重戴矩阵分散时，说明泛化没有随训练成绩提升。'))


def waveform_errors(kind, vx, vy, vpred, out, sequence=False):
    errors=np.flatnonzero(vpred!=vy)[:3]
    s=svg_open(f'{NAMES[kind]}：重戴判错样本')
    if not len(errors): s += '<text class="n" x="42" y="110">没有重戴错样本可画。</text>'
    for row, idx in enumerate(errors):
        top=80+row*160; xx=210; ww=700; signal=vx[idx]
        lo, hi = signal.min(), signal.max(); span=max(hi-lo,1e-8)
        points=' '.join(f'{xx+i*ww/(len(signal)-1):.1f},{top+110-(v-lo)/span*95:.1f}' for i,v in enumerate(signal[::10]))
        s += f'<text class="n" x="42" y="{top+25}">真={LABELS[vy[idx]]} → 判={LABELS[vpred[idx]]}</text><polyline points="{points}" fill="none" stroke="#6074d8" stroke-width="1.4"/>'
        if sequence:
            energy=np.sqrt(np.mean(signal.reshape(200,10)**2,axis=1)); emax=max(energy.max(),1e-8)
            bars=''.join(f'<rect x="{xx+i*ww/200:.1f}" y="{top+145-energy[i]/emax*28:.1f}" width="3" height="{energy[i]/emax*28:.1f}" fill="#db7445"/>' for i in range(200))
            s += bars+'<text class="a" x="210" y="'+str(top+158)+'">200 帧 × 每帧 10 点的能量；末帧分类见左。</text>'
    note='波形来自已保存的重戴样本，展示网络实际判错，而非不可回放的训练损失。'
    write(out,s+svg_close(note))


def dual_view(kind, vx, vy, vpred, out):
    idx=next(iter(np.flatnonzero(vpred!=vy)),0); signal=vx[idx]; top=110; xx=160; ww=770
    energy=np.sqrt(np.mean(signal.reshape(200,10)**2,axis=1)); emax=max(energy.max(),1e-8); lo,hi=signal.min(),signal.max(); span=max(hi-lo,1e-8)
    points=' '.join(f'{xx+i*ww/(len(signal)-1):.1f},{top+95-(v-lo)/span*82:.1f}' for i,v in enumerate(signal[::10]))
    s=svg_open(f'{NAMES[kind]}：同一错样本的两路输入')
    s+=f'<text class="n" x="42" y="75">真={LABELS[vy[idx]]} → 判={LABELS[vpred[idx]]}</text><text class="a" x="42" y="{top+22}">左路：2 秒波形</text><polyline points="{points}" fill="none" stroke="#6074d8" stroke-width="1.5"/>'
    s+=f'<text class="a" x="42" y="{top+160}">右路：200×10 能量序列</text>'
    s+=''.join(f'<rect x="{xx+i*ww/200:.1f}" y="{top+250-energy[i]/emax*75:.1f}" width="3" height="{energy[i]/emax*75:.1f}" fill="#db7445"/>' for i in range(200))
    write(out,s+svg_close('两路被拼接后仍错，说明此样本的波形与时序能量都未提供可分信息。'))


def gaf(x, mode='mean'):
    z=x.reshape(40,50)
    z=np.sqrt(np.mean(z*z,axis=1)) if mode=='rms' else z.mean(1)
    span=max(float(z.max()-z.min()),1e-8); z=np.clip(2*(z-z.min())/span-1,-1,1)
    return z[:,None]*z[None,:]-np.sqrt(np.maximum(1-z*z,0))[:,None]*np.sqrt(np.maximum(1-z*z,0))[None,:]


def gaf_images(kind, x, y, vx, vy, out, mode='mean'):
    a=np.flatnonzero(y==LABELS.index('rub'))[0]; b=np.flatnonzero(vy==LABELS.index('rub'))[0]
    s=svg_open(f'{NAMES[kind]}：训练与重戴的搓动 GASF（40×40）')
    for panel,(head,image) in enumerate((('训练搓动',gaf(x[a],mode)),('重戴搓动',gaf(vx[b],mode)))):
        left=140+panel*420; top=100; cell=8
        s+=f'<text class="n" x="{left}" y="75">{head}</text>'
        for i in range(40):
            for j in range(40):
                v=(image[i,j]+1)/2; r=int(35+190*v); g=int(75+100*(1-v)); bcol=int(135+80*(1-v))
                s+=f'<rect x="{left+j*cell}" y="{top+i*cell}" width="{cell}" height="{cell}" fill="rgb({r},{g},{bcol})"/>'
    write(out,s+svg_close('每条样本都缩放到 −1…1；原始幅度差被去除，GASF 因而可能把两次佩戴变得很相似。'))


def build(project, out, only=None):
    data=project/'data/emg/emg-gesture-data'; root=project/'models/emg/five-gestures'
    runs=sorted(p for p in root.glob('20260927-*') if (p/'report.json').exists())
    if len(runs)!=19: raise ValueError(f'Expected 19 baseline runs, found {len(runs)}')
    out.mkdir(parents=True,exist_ok=True); index=[]
    previous = {row['model']: row for row in json.loads((out/'index.json').read_text())} if (out/'index.json').exists() else {}
    for run in runs:
        report,model=artifact(run); kind=report['model']; x,y,_=load_trials(data,report['manifest'],'train');vx,vy,_=load_trials(data,report['manifest'],'validation')
        if only and kind not in only:
            continue
        pred,vpred,score,rewear=bar_compare(kind,report,model,x,y,vx,vy,out/f'{kind}-compare.svg')
        if kind in ('lda','lda_features','svm','svm_features'):
            scatter(kind,x,y,vx,vy,vpred,out/f'{kind}-why.svg')
            if kind == 'svm':
                s = svg_open('原 SVM：重戴验证混淆矩阵')
                s = heatmap(s, report['validation']['confusion'], 350, 130, '真=搓动一行：捏合 4、响指 4、握拳 1、搓动 1')
                write(out/'svm-rewear-confusion.svg', s + svg_close())
        elif kind=='knn': knn_neighbors(model,x,y,vx,vy,vpred,out/'knn-why.svg')
        elif kind=='rf': feature_importance(model,out/'rf-why.svg')
        elif kind=='mlp': mlp_heatmaps(y,pred,vy,vpred,out/'mlp-why.svg')
        elif kind=='cnn': waveform_errors(kind,vx,vy,vpred,out/'cnn-why.svg')
        elif kind in ('rnn','lstm','gru'): waveform_errors(kind,vx,vy,vpred,out/f'{kind}-why.svg',sequence=True)
        elif kind in ('cnn_lstm','dual_stream','feature_fusion','caps_gru'): dual_view(kind,vx,vy,vpred,out/f'{kind}-why.svg')
        elif kind.startswith('gaf_'): gaf_images(kind,x,y,vx,vy,out/f'{kind}-why.svg')
        else: raise ValueError(kind)
        previous[kind]={'model':kind,'name':NAMES[kind],'run':run.name,'training_balanced_accuracy':score,'rewear_balanced_accuracy':rewear}
    index=[previous[k] for k in sorted(previous)]
    s=svg_open('19 个模型：训练成绩与重戴验证的同口径对照', 1120, 760)
    s+='<text class="s" x="42" y="68">每行两条：蓝=训练，橙=重戴验证。独立 test 集未读取。</text>'
    for row,item in enumerate(index):
        y0=92+row*31; train_w=540*item['training_balanced_accuracy']/100; rewear_w=540*item['rewear_balanced_accuracy']/100
        s+=f'<text class="a" x="42" y="{y0+14}">{item["name"]}</text><rect x="215" y="{y0}" width="540" height="11" fill="#edf0f5"/><rect x="215" y="{y0}" width="{train_w:.1f}" height="11" fill="#6074d8"/><rect x="215" y="{y0+13}" width="540" height="11" fill="#edf0f5"/><rect x="215" y="{y0+13}" width="{rewear_w:.1f}" height="11" fill="#db7445"/><text class="a" x="770" y="{y0+10}">{item["training_balanced_accuracy"]:.1f}%</text><text class="a" x="825" y="{y0+24}">{item["rewear_balanced_accuracy"]:.1f}%</text>'
    s+='<rect x="915" y="91" width="12" height="12" fill="#6074d8"/><text class="a" x="933" y="102">训练</text><rect x="985" y="91" width="12" height="12" fill="#db7445"/><text class="a" x="1003" y="102">重戴</text>'
    write(out/'all-models-compare.svg',s+svg_close('每个模型另有一张 why 图；训练曲线未保存，不能补画 TensorBoard 曲线。'))
    (out/'index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2))
    return index


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--models');a=p.parse_args()
    results=build(a.project,a.out,set(a.models.split(',')) if a.models else None)
    print(json.dumps({'models':len(results),'out':str(a.out),'test_read':False},ensure_ascii=False))

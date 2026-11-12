"""个体自适应实验解码器。只用过去窗口；质量分数是异常程度，不冒充接触概率。

模型绑定同一次佩戴。默认只输出影子结果，不接管游戏；旧分类器不变。
"""
import json
import hashlib
from pathlib import Path
import numpy as np
from scipy.signal import welch
from scipy.special import logsumexp

VERSION = 'adaptive-intent-v1'
FS, WINDOW, STEP = 2000, 2000, 100
BANDS = ((20,45),(55,95),(105,145),(155,245),(255,445))


def observation(raw):
    x=np.asarray(raw,float)
    if x.shape != (WINDOW,8) or not np.isfinite(x).all():raise ValueError('需要有限值的1000ms八通道窗')
    x=x-x.mean(0)
    f,p=welch(x,FS,nperseg=400,axis=0)
    ok=f>=20
    for k in range(1,20):ok &= np.abs(f-50*k)>4
    feat=np.array([np.log(p[ok & (f>=lo) & (f<hi)].mean(0)+1e-9) for lo,hi in BANDS]).ravel()
    total=p[(f>=5)&(f<=950)].sum(0)+1e-12
    low=p[(f>=5)&(f<20)].sum(0)/total
    line=p[np.any(np.abs(f[:,None]-np.arange(50,951,50)[None,:])<=1,axis=1)].sum(0)/total
    rms=np.sqrt(np.mean(x*x,axis=0))
    crest=np.max(np.abs(x),axis=0)/np.maximum(rms,1e-9)
    flat=np.mean(np.diff(x,axis=0)==0,axis=0)
    quality=np.r_[low,line,np.log1p(crest),flat]
    return feat,quality,rms


def robust_scale(x, floor):
    center=np.median(x,axis=0)
    return center,np.maximum(1.4826*np.median(np.abs(x-center),axis=0),floor)


def gaussian_fit(x,y,classes):
    mu=np.array([x[y==c].mean(0) for c in classes])
    residual=np.array([a-mu[classes.index(c)] for a,c in zip(x,y)])
    cov=residual.T@residual/len(x)
    # 小样本使用收缩协方差并给最小数值正则，避免40维矩阵奇异。
    cov=.5*cov+.5*np.eye(x.shape[1])*max(float(np.trace(cov)/x.shape[1]),1e-3)
    return mu,np.linalg.inv(cov)


def distances(x,mu,inv):
    d=x[:,None,:]-mu[None,:,:]
    return np.einsum('nci,ij,ncj->nc',d,inv,d)


def fit(records, rest, donning):
    """每条记录只有一个训练窗；records含x/q，不能把同条相邻窗拆成独立样本。"""
    if type(donning) is not int or donning<1:raise ValueError('缺少佩戴编号')
    classes=sorted({r['label'] for r in records})
    if rest not in classes or len(classes)<2 or any(sum(r['label']==c for r in records)<3 for c in classes):raise ValueError('本次佩戴每类至少3条独立录音')
    x=np.array([r['x'] for r in records],float);q=np.array([r['q'] for r in records],float);y=np.array([r['label'] for r in records])
    if x.shape!=(len(records),40) or q.shape!=(len(records),32) or not np.isfinite(x).all() or not np.isfinite(q).all():raise ValueError('训练特征无效')
    center,scale=robust_scale(x[y==rest],.5)
    z=(x-center)/scale
    # 温度和未知类距离只由训练侧整条留一估计，绝不读取待测录音。
    held=[]
    for i in range(len(z)):
        train=np.arange(len(z))!=i
        fc,fs=robust_scale(x[train & (y==rest)],.5)
        fm,fi=gaussian_fit((x[train]-fc)/fs,y[train],classes)
        held.append(distances(((x[i]-fc)/fs)[None],fm,fi)[0])
    held=np.array(held);target=np.array([classes.index(c) for c in y])
    temperatures=(1.,2.,4.,8.,16.,32.)
    losses=[]
    for t in temperatures:
        logits=-held/(2*t)
        losses.append(float(np.mean(logsumexp(logits,axis=1)-logits[np.arange(len(y)),target])))
    temperature=temperatures[int(np.argmin(losses))]
    radii=np.array([max(float(np.quantile(held[y==c,ci],.95)),1.) for ci,c in enumerate(classes)])
    qm=[];qs=[]
    for c in classes:
        a,b=robust_scale(q[y==c],np.tile([.02,.02,.12,.005],(8,1)).T.ravel())
        qm.append(a);qs.append(b)
    mu,inv=gaussian_fit(z,y,classes)
    return dict(version=VERSION,donning=donning,rest=rest,classes=classes,center=center.tolist(),scale=scale.tolist(),
                mu=mu.tolist(),inv=inv.tolist(),radius=radii.tolist(),quality_center=np.array(qm).tolist(),quality_scale=np.array(qs).tolist(),
                temperature=temperature,temperature_nll=min(losses),window=WINDOW,step=STEP,fs=FS,
                calibration_records=len(records),mode='shadow',validated_for_control=False)


class DurationDecoder:
    """在线显式持续时间状态模型（HSMM的展开状态实现），不回看未来修正已出的招。

    放松至少100ms才准备；起势至少100ms才能进入保持，保持阶段只出一次。
    持续时间是待实测的固定先验；输出附后验，不以状态机冒充已训练时序网络。
    """
    def __init__(self,classes,rest):
        self.classes=list(classes);self.rest=rest;self.ri=self.classes.index(rest)
        self.states=[('rest',rest,1),('rest',rest,2)]
        for c in self.classes:
            if c!=rest:self.states.extend([('onset',c,1),('onset',c,2),('hold',c,1)])
        n=len(self.states);a=np.zeros((n,n));a[0,1]=1;a[1,1]=.96
        for i in range(2,n,3):
            a[1,i]=.04/(len(classes)-1)
            a[i,i+1]=.9;a[i,0]=.1
            a[i+1,i+2]=.9;a[i+1,0]=.1
            a[i+2,i+2]=.95;a[i+2,0]=.05
        self.log_transition=np.full((n,n),-np.inf);self.log_transition[a>0]=np.log(a[a>0])
        self.reset()
    def reset(self):
        # 起始无已准备假设；必须先见到真实的放松证据。
        self.alpha=np.full(len(self.states),-np.inf);self.alpha[0]=0;self.armed=False;self.uncertain_ticks=0;self.rest_ticks=0
    def push(self,probs,accepted=True,reason=None):
        p=np.asarray(probs,float)
        # 类间过渡的概率不确定仍更新状态信念；坏信号、未知分布和断流必须清空。
        soft = not accepted and reason == 'uncertain'
        self.uncertain_ticks = self.uncertain_ticks + 1 if soft else 0
        if (not accepted and not soft) or self.uncertain_ticks > 10 or p.shape!=(len(self.classes),) or not np.isfinite(p).all() or np.any(p<0) or p.sum()<=0:
            self.reset();return dict(phase='unknown',label=None,event=None,posterior=0.)
        p=p/p.sum();emission=np.log(np.maximum([p[self.classes.index(c)] for _,c,_ in self.states],1e-9))
        a=logsumexp(self.alpha[:,None]+self.log_transition,axis=0)+emission
        self.alpha=a-logsumexp(a);post=np.exp(self.alpha);i=int(post.argmax());phase,label,_=self.states[i]
        self.rest_ticks = self.rest_ticks + 1 if accepted and p[self.ri]>=.6 else 0
        if self.rest_ticks>=2 and post[1]>=.8:self.armed=True
        event=None
        if accepted and phase=='hold' and post[i]>=.8 and p[self.classes.index(label)]>=.6 and self.armed:
            event=label;self.armed=False
        return dict(phase='uncertain' if soft else phase,label=label,event=event,posterior=float(post[i]))


class Model:
    def __init__(self,data):
        if data.get('version')!=VERSION or data.get('window')!=WINDOW or data.get('fs')!=FS or data.get('step')!=STEP:raise ValueError('不兼容的实验模型')
        if type(data.get('donning')) is not int or data['donning']<1:raise ValueError('佩戴编号无效')
        self.data=data;self.classes=list(data['classes']);self.rest=data['rest']
        n=len(self.classes)
        if n<2 or len(set(self.classes))!=n or self.rest not in self.classes:raise ValueError('类别无效')
        for key,shape in [('center',(40,)),('scale',(40,)),('mu',(n,40)),('inv',(40,40)),('radius',(n,)),('quality_center',(n,32)),('quality_scale',(n,32))]:
            arr=np.asarray(data[key],float)
            if arr.shape!=shape or not np.isfinite(arr).all():raise ValueError('模型参数无效：'+key)
            setattr(self,key,arr)
        if np.any(self.scale<=0) or np.any(self.quality_scale<=0) or np.any(self.radius<=0) or not 0<float(data['temperature'])<=32:raise ValueError('模型尺度无效')
        if not np.allclose(self.inv,self.inv.T) or np.linalg.eigvalsh(self.inv).min()<=0:raise ValueError('协方差无效')
    def predict(self,x,q,rms):
        if any(np.asarray(a).shape!=shape or not np.isfinite(a).all() for a,shape in ((x,(40,)),(q,(32,)),(rms,(8,)))):raise ValueError('预测特征无效')
        z=(np.asarray(x)-self.center)/self.scale
        d=distances(z[None],self.mu,self.inv)[0]
        logits=-d/(2*self.data['temperature']);p=np.exp(logits-logsumexp(logits));top=int(p.argmax())
        # 类条件质量包络保留正常动作自身的频谱；输出异常分数，不断言电极故障。
        quality=np.abs((np.asarray(q)-self.quality_center[top])/self.quality_scale[top])
        qscore=float(np.quantile(quality,.9));novel=float(d[top]/self.radius[top])
        order=np.sort(p);margin=float(order[-1]-order[-2])
        hard=bool(np.any(np.asarray(rms)<1e-6) or np.any(np.asarray(q)[24:]> .98))
        reason='flatline' if hard else 'quality_outlier' if qscore>6 else 'unknown_distance' if novel>1.5 else 'uncertain' if p[top]<.6 or margin<.15 else 'accepted'
        return dict(probs=p.tolist(),top=self.classes[top],accepted=reason=='accepted',reason=reason,
                    quality_score=qscore,novelty_ratio=novel,margin=margin,confidence=float(p[top]))


class Stream:
    def __init__(self,data):
        self.model=Model(data);self.decoder=DurationDecoder(self.model.classes,self.model.rest);self.reset()
    def reset(self):
        self.buffer=np.empty((0,8));self.samples=0;self.next_end=WINDOW;self.decoder.reset()
    def push(self,raw):
        x=np.asarray(raw,float)
        if x.ndim!=2 or x.shape[1]!=8 or not np.isfinite(x).all():self.reset();raise ValueError('实时块无效')
        results=[];offset=0
        # 按样本边界切窗；一次大块与多次小块必须产生完全相同结果。
        while offset<len(x):
            take=min(self.next_end-self.samples,len(x)-offset)
            self.buffer=np.concatenate([self.buffer,x[offset:offset+take]])[-WINDOW:]
            offset+=take;self.samples+=take
            if self.samples==self.next_end:
                f,q,rms=observation(self.buffer);r=self.model.predict(f,q,rms)
                r.update(self.decoder.push(r['probs'],r['accepted'],r['reason']))
                r.update(sample_end=self.samples,window_start=self.samples-WINDOW,mode='shadow',version=VERSION)
                results.append(r);self.next_end+=STEP
        return results


def save(data,path):
    Model(data) # 写前校验，非法模型不留下半文件。
    p=Path(path);temp=p.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,allow_nan=False));temp.replace(p)


def load(path):return json.loads(Path(path).read_text())


def peak_record(raw,label):
    """离线标定沿用产品峰值取窗；实时预测不调用此函数、不看未来。"""
    from scipy.signal import butter,sosfiltfilt
    e=np.asarray(raw,float)
    if e.ndim!=2 or e.shape[1]!=8 or len(e)<WINDOW or not np.isfinite(e).all():raise ValueError('训练录音无效')
    mid=len(e)//2
    if len(e)>WINDOW:
        sos=butter(4,[20,450],'bandpass',fs=FS,output='sos')
        env=np.convolve((sosfiltfilt(sos,e,axis=0)**2).sum(1),np.ones(400)/400,'same')
        mid=WINDOW//2+int(np.argmax(env[WINDOW//2:len(e)-WINDOW//2]))
    x,q,rms=observation(e[mid-WINDOW//2:mid+WINDOW//2])
    return dict(label=label,x=x,q=q,rms=rms)


def fit_directory(root,labels,rest,donning,excluded=(),since=None):
    records=[];hashes=[];batches=set()
    for label in labels:
        for p in sorted((Path(root)/'emg-wl8-data'/label).glob('*.npz')):
            if f'{label}/{p.name}' in excluded or (since and p.stat().st_mtime<since):continue
            meta=json.loads(p.with_suffix('.json').read_text())
            if meta.get('donning')!=donning:continue
            # 编号可能跨天重用；多批次拒绝候选，不能冒充同一次佩戴。
            batches.add((str(meta.get('recordedAt',''))[:10],str(meta.get('session',''))))
            with np.load(p,allow_pickle=False) as z:records.append(peak_record(z['emg_uv'],label))
            hashes.append(hashlib.sha256(p.read_bytes()).hexdigest())
    if len(batches)!=1 or not next(iter(batches))[0]:raise ValueError('佩戴编号对应多批次或缺少日期')
    data=fit(records,rest,donning);data['training_sha256']=sorted(hashes)
    data['batch_sha256']=hashlib.sha256(json.dumps(sorted(batches),ensure_ascii=False).encode()).hexdigest()
    return data

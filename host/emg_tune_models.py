"""Per-model bounded search using TRAIN only; rewear validation is scored after selection.
No test reads. Baselines are preserved. Each candidate and final seed is recorded.
"""
import argparse, copy, itertools, json, pickle, time
from pathlib import Path
import numpy as np
import torch
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
import emg_gesture_train as t


def configs(kind):
    base=kind.removesuffix('_features')
    if base=='lda':return [{'shrinkage':v} for v in ('auto',.05,.3,.7)]
    if base=='svm':return [dict(C=c,gamma=g) for c,g in itertools.product((.1,1,10,100),('scale',.004,.4))]
    if base=='knn':return [dict(n_neighbors=n,weights=w) for n,w in itertools.product((3,5,9,15),('uniform','distance'))]
    if base=='rf':return [dict(min_samples_leaf=n,max_depth=d) for n,d in itertools.product((2,5,10),(None,6))]
    if base=='mlp':return [dict(hidden_layer_sizes=h,alpha=a) for h,a in itertools.product(((32,),(64,32)),(.0001,.01,.1))]
    values=[dict(lr=.001,wd=.01,batch=30,net={},augment=False),
            dict(lr=.001,wd=0.,batch=30,net={},augment=False),
            dict(lr=.0003,wd=.0001,batch=15,net={},augment=False)]
    if kind=='cnn':
        values += [dict(lr=.003,wd=.0001,batch=30,net={},augment=False),
                   dict(lr=.001,wd=.001,batch=15,net={},augment=True)]
    else:
        values += [dict(lr=.001,wd=.0001,batch=15,net={'hidden':64,'pooling':'mean','dropout':.2},augment=False),
                   dict(lr=.0003,wd=0.,batch=30,net={'hidden':128,'pooling':'mean','dropout':.2},augment=False)]
        if kind.startswith('gaf'):
            values += [dict(lr=.001,wd=0.,batch=15,net={'gaf_mode':'rms','pooling':'mean','dropout':.2},augment=False)]
        else:
            values += [dict(lr=.001,wd=.0001,batch=15,net={'hidden':64,'pooling':'mean','dropout':.2},augment=True)]
    return values


def classical(kind,config,seed):
    k=kind.removesuffix('_features')
    model={'lda':lambda:LinearDiscriminantAnalysis(solver='lsqr',**config),
           'svm':lambda:SVC(**config), 'knn':lambda:KNeighborsClassifier(**config),
           'rf':lambda:RandomForestClassifier(n_estimators=200,random_state=seed,n_jobs=2,**config),
           'mlp':lambda:MLPClassifier(max_iter=600,random_state=seed,**config)}[k]()
    return make_pipeline(StandardScaler(),model)


def fit_deep(kind,cfg,x,y,seed,epochs,hold=None):
    torch.manual_seed(seed)
    net=t.network() if kind=='cnn' else t.build(kind,**cfg['net'])
    scale=max(float(x.std()),1e-6)
    tx=torch.tensor(x[:,None]/scale,dtype=torch.float32);ty=torch.tensor(y)
    hx=torch.tensor(hold[0][:,None]/scale,dtype=torch.float32) if hold else None
    opt=torch.optim.Adam(net.parameters(),lr=cfg['lr'],weight_decay=cfg['wd'])
    best=-1.;best_loss=float('inf');best_epoch=epochs;weights=None;history=[]
    for epoch in range(1,epochs+1):
        net.train()
        for ids in torch.randperm(len(y)).split(cfg['batch']):
            inputs=tx[ids]
            if cfg['augment']:
                inputs=inputs*torch.exp(.15*torch.randn(len(ids),1,1))
                shift=int(torch.randint(-50,51,()).item())
                inputs=torch.nn.functional.pad(inputs,(max(shift,0),max(-shift,0)))[:,:,max(-shift,0):max(-shift,0)+2000]
            opt.zero_grad();loss=torch.nn.functional.cross_entropy(net(inputs),ty[ids])
            if not torch.isfinite(loss):raise ValueError('nonfinite loss')
            loss.backward();torch.nn.utils.clip_grad_norm_(net.parameters(),5);opt.step()
        if epoch%5==0 or epoch==epochs:
            net.eval()
            with torch.no_grad():
                logits=net(tx);train=t.report(y,logits.argmax(1).numpy())
                entry={'epoch':epoch,'loss':float(torch.nn.functional.cross_entropy(logits,ty)), 'train':train}
                if hold:
                    out=net(hx);score=t.report(hold[1],out.argmax(1).numpy())
                    hl=float(torch.nn.functional.cross_entropy(out,torch.tensor(hold[1])))
                    entry['inner_holdout']=score;entry['holdout_loss']=hl
                    if score['balanced_accuracy']>best or (score['balanced_accuracy']==best and hl<best_loss):
                        best=score['balanced_accuracy'];best_loss=hl;best_epoch=epoch;weights=copy.deepcopy(net.state_dict())
                history.append(entry)
            if hold and epoch>=40 and epoch-best_epoch>=25:break
    if hold:net.load_state_dict(weights)
    return {'weights':net.state_dict(),'scale':scale,'config':cfg['net']},history,best_epoch


def run(project,out,max_epochs=120):
    torch.set_num_threads(2)
    model_root=project/'models/emg/five-gestures'
    if (model_root/'frozen.txt').exists():raise ValueError('test already frozen')
    out.mkdir(parents=True,exist_ok=False)
    root=project/'data/emg/emg-gesture-data'
    x,y,manifest,warnings=t.dataset(root,'train')
    # Last third of each class by filename/time is inner holdout. Whole trials never split.
    fit=np.concatenate([np.flatnonzero(y==i)[:-10] for i in range(5)])
    hold=np.concatenate([np.flatnonzero(y==i)[-10:] for i in range(5)])
    assert not set(fit)&set(hold)
    assert not ({manifest[i]['sha256'] for i in fit}&{manifest[i]['sha256'] for i in hold})
    summary={'selection':'train only, chronological last10/class inner holdout; NOT independent wear sessions',
             'seeds':[42,73],'max_epochs':max_epochs,'inner_fit':[manifest[i] for i in fit],
             'inner_holdout':[manifest[i] for i in hold],'models':[]}
    caches={'base':t.features(x),'book':t.book_features(x)}
    for kind in t.MODELS:
        if (model_root/'frozen.txt').exists():raise ValueError('test frozen while tuning')
        candidates=[];folder=out/kind;folder.mkdir()
        fx=caches['book' if kind in t.CLASSICAL else 'base']
        for idx,cfg in enumerate(configs(kind)):
            started=time.monotonic()
            if kind in t.DEEP_MODELS:
                model,history,epoch=fit_deep(kind,cfg,x[fit],y[fit],42,max_epochs,(x[hold],y[hold]))
                score=t.report(y[hold],t.predict(model,kind,x[hold]));tr=t.report(y[fit],t.predict(model,kind,x[fit]))
            else:
                model=classical(kind,cfg,42);model.fit(fx[fit],y[fit]);history=[];epoch=None
                score=t.report(y[hold],model.predict(fx[hold]));tr=t.report(y[fit],model.predict(fx[fit]))
            entry={'config':cfg,'inner_holdout':score,'train':tr,'epoch':epoch,'history':history,'seconds':time.monotonic()-started}
            candidates.append(entry)
            (folder/'candidates.json').write_text(json.dumps(candidates,ensure_ascii=False,indent=2))
            print(kind,idx+1,'/',len(configs(kind)),'inner',score['balanced_accuracy'],'epoch',epoch,flush=True)
        # Deterministic tie-break: preserve earlier/simpler candidate. No rewear validation here.
        selected=max(range(len(candidates)),key=lambda i:round(candidates[i]['inner_holdout']['balanced_accuracy'],12))
        choice=candidates[selected];cfg=choice['config'];final=[]
        for seed in (42,73):
            if kind in t.DEEP_MODELS:
                model,history,_=fit_deep(kind,cfg,x,y,seed,choice['epoch'])
                torch.save(model,folder/f'seed-{seed}.pt')
            else:
                model=classical(kind,cfg,seed);model.fit(fx,y);history=[]
                (folder/f'seed-{seed}.pkl').write_bytes(pickle.dumps(model))
            final.append({'seed':seed,'train':t.report(y,t.predict(model,kind,x)),'history':history})
        record={'model':kind,'selected_candidate':selected,'config':cfg,'epochs':choice['epoch'],'inner_score':choice['inner_holdout'],'seeds':final}
        summary['models'].append(record)
        (out/'selection.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    # Only after every model's configuration is locked, read rewear validation once for reporting.
    v,vy,validation,vw=t.dataset(root,'validation')
    assert not ({m['sha256'] for m in manifest}&{m['sha256'] for m in validation})
    for record in summary['models']:
        kind=record['model'];folder=out/kind
        for seed_report in record['seeds']:
            seed=seed_report['seed']
            model=torch.load(folder/f'seed-{seed}.pt',weights_only=True) if kind in t.DEEP_MODELS else pickle.loads((folder/f'seed-{seed}.pkl').read_bytes())
            seed_report['validation']=t.report(vy,t.predict(model,kind,v))
        if (model_root/'frozen.txt').exists():raise ValueError('test frozen before publication')
        # Publish seed42 only, chosen in advance, never choose seeds using validation.
        dest=model_root/f'{out.name}-{kind}';dest.mkdir(exist_ok=False)
        suffix='pt' if kind in t.DEEP_MODELS else 'pkl'
        (dest/f'model.{suffix}').write_bytes((folder/f'seed-42.{suffix}').read_bytes())
        report={'model':kind,'seed':42,'implementation':'per-model-tuning-v1','config':record['config'],'epochs':record['epochs'],
                'validation':record['seeds'][0]['validation'],'training':record['seeds'][0]['train'],
                'seed_checks':[{k:v for k,v in seed.items() if k!='history'} for seed in record['seeds']],'manifest':manifest+validation,'warnings':warnings+vw,'test':None,
                'note':'训练集内选参数；重戴验证仅用于报告；seed42预先固定；独立测试未运行'}
        (dest/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    summary['validation_manifest']=validation
    (out/'results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    print('ALL DONE',out,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--epochs',type=int,default=120);a=p.parse_args();run(a.project,a.output,a.epochs)

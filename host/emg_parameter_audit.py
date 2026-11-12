"""Read-only train/validation audit. Never reads test; writes diagnostics, no production models."""
import argparse, json, pickle
from pathlib import Path
import numpy as np
import torch
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
import emg_gesture_train as t


def audit(project, output):
    torch.set_num_threads(2)
    root=project/'data/emg/emg-gesture-data'
    x,y,manifest,_=t.dataset(root,'train'); v,vy,vm,_=t.dataset(root,'validation')
    assert not ({r['sha256'] for r in manifest}&{r['sha256'] for r in vm})
    result={'split_note':'CV only within training trials; not proof of cross-session performance. Independent test unopened.',
            'manifest':manifest+vm,'saved_runs':[],'svm_search':{},'learning_curves':[]}
    for p in sorted((project/'models/emg/five-gestures').glob('*/report.json')):
        r=json.loads(p.read_text());kind=r['model']
        model=torch.load(p.parent/'model.pt',weights_only=True,map_location='cpu') if kind in t.DEEP_MODELS else pickle.loads((p.parent/'model.pkl').read_bytes())
        train=t.report(y,t.predict(model,kind,x));val=t.report(vy,t.predict(model,kind,v))
        assert np.isclose(val['balanced_accuracy'],r['validation']['balanced_accuracy'])
        result['saved_runs'].append({'id':p.parent.name,'model':kind,'train':train,'validation':val})
        print(kind,round(train['balanced_accuracy'],3),round(val['balanced_accuracy'],3),flush=True)
    fx=t.features(x);fv=t.features(v)
    search=GridSearchCV(make_pipeline(StandardScaler(),SVC()),{'svc__C':[.1,1,10,100], 'svc__gamma':['scale',.004,.4]},
        scoring='balanced_accuracy',cv=StratifiedKFold(3,shuffle=True,random_state=42),n_jobs=1)
    search.fit(fx,y)
    result['svm_search']={'params':search.best_params_,'train_cv':search.best_score_,
        'validation':t.report(vy,search.predict(fv)),
        'candidates':[{'params':p,'mean':float(m),'std':float(s)} for p,m,s in zip(search.cv_results_['params'],search.cv_results_['mean_test_score'],search.cv_results_['std_test_score'])]}
    print('SVM train-CV selected',result['svm_search'],flush=True)
    # Controlled diagnostic: same seed/architecture, change only weight decay. No best-epoch selection on validation.
    scale=max(float(x.std()),1e-6);tx=torch.tensor(x[:,None]/scale,dtype=torch.float32);tv=torch.tensor(v[:,None]/scale,dtype=torch.float32);ty=torch.tensor(y)
    for kind in ('cnn','gaf_caps','gaf_cnn_lstm'):
        for wd in (.01,0.):
            torch.manual_seed(42);net=t.network() if kind=='cnn' else t.build(kind)
            opt=torch.optim.Adam(net.parameters(),lr=.001,weight_decay=wd)
            curve=[]
            for epoch in range(1,161):
                net.train()
                for idx in torch.randperm(len(y)).split(30):
                    opt.zero_grad();loss=torch.nn.functional.cross_entropy(net(tx[idx]),ty[idx]);assert torch.isfinite(loss)
                    loss.backward();opt.step()
                if epoch in (1,10,20,40,80,160):
                    net.eval()
                    with torch.no_grad():
                        logits=net(tx);pred=net(tv).argmax(1).numpy()
                        curve.append({'epoch':epoch,'train_loss':float(torch.nn.functional.cross_entropy(logits,ty)),
                            'train_accuracy':float((logits.argmax(1)==ty).float().mean()),'validation':t.report(vy,pred)})
            result['learning_curves'].append({'model':kind,'weight_decay':wd,'lr':.001,'seed':42,'curve':curve})
            print('curve',kind,wd,[(r['epoch'],round(r['train_accuracy'],2),round(r['validation']['balanced_accuracy'],2)) for r in curve],flush=True)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    audit(a.project,a.output)

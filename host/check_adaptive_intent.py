"""候选算法的因果性、拒识、模型隔离和实时接线检查；不连接设备。"""
import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
import numpy as np
import adaptive_intent as ai


def training():
    rng=np.random.default_rng(43);records=[]
    for k,c in enumerate(('rest','a','b')):
        for _ in range(6):
            x=rng.normal(0,.1,40);x[k*8:(k+1)*8]+=5
            records.append(dict(label=c,x=x,q=np.r_[np.full(16,.1),np.full(8,1.5),np.zeros(8)]))
    return records


class AdaptiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records=training();cls.data=ai.fit(cls.records,'rest',1)
    def test_each_wear_scale_invariance(self):
        # 二十倍底噪仍按本次佩戴的相对频谱判断，没有150µV拦截。
        shifted=[dict(r,x=r['x']+2*np.log(20)) for r in self.records]
        other=ai.Model(ai.fit(shifted,'rest',2));m=ai.Model(self.data)
        for a,b in zip(self.records,shifted):
            p=m.predict(a['x'],a['q'],np.full(8,20));q=other.predict(b['x'],b['q'],np.full(8,400))
            np.testing.assert_allclose(p['probs'],q['probs'],atol=1e-9)
            self.assertTrue(q['accepted']);self.assertEqual(q['top'],a['label'])
    def test_high_confidence_unknown_rejected(self):
        r=self.records[0];m=ai.Model(self.data)
        p=m.predict(r['x']+100,r['q'],np.ones(8))
        self.assertFalse(p['accepted']);self.assertEqual(p['reason'],'unknown_distance')
    def test_flat_and_quality_rejected(self):
        r=self.records[0];m=ai.Model(self.data)
        self.assertEqual(m.predict(r['x'],r['q'],np.zeros(8))['reason'],'flatline')
        q=r['q'].copy();q[:8]=.95
        self.assertEqual(m.predict(r['x'],q,np.ones(8))['reason'],'quality_outlier')
    def test_duration_rearm_and_unknown(self):
        d=ai.DurationDecoder(['rest','a','b'],'rest')
        rest=[.999,.0005,.0005];act=[.0005,.999,.0005]
        self.assertFalse(any(d.push(act)['event'] for _ in range(30)))
        for _ in range(10):d.push(rest)
        self.assertEqual(sum(bool(d.push(act)['event']) for _ in range(40)),1)
        d.push(act,False)
        self.assertFalse(any(d.push(act)['event'] for _ in range(10)))
        for _ in range(10):d.push(rest)
        self.assertEqual(sum(bool(d.push(act)['event']) for _ in range(20)),1)
    def test_one_rest_tick_is_not_ready(self):
        d=ai.DurationDecoder(['rest','a'],'rest')
        d.push([.999,.001]);self.assertFalse(d.armed)
        self.assertFalse(any(d.push([.001,.999])['event'] for _ in range(15)))
        d.reset();d.push([.999,.001]);d.push([.999,.001]);self.assertTrue(d.armed)
    def test_uncertain_transition_is_not_signal_fault(self):
        d=ai.DurationDecoder(['rest','a','b'],'rest')
        for _ in range(5):d.push([.99,.005,.005])
        for _ in range(4):self.assertIsNone(d.push([.48,.48,.04],False,'uncertain')['event'])
        self.assertTrue(d.armed)
        self.assertEqual(sum(bool(d.push([.001,.998,.001])['event']) for _ in range(10)),1)
        for _ in range(11):d.push([.4,.4,.2],False,'uncertain')
        self.assertFalse(d.armed)

    def test_chunk_and_prefix_invariance(self):
        raw=np.random.default_rng(5).normal(size=(4800,8))
        whole=ai.Stream(self.data).push(raw);s=ai.Stream(self.data);parts=[]
        for x in np.array_split(raw,37):parts.extend(s.push(x))
        self.assertEqual(whole,parts)
        self.assertEqual(ai.Stream(self.data).push(raw[:3100]),whole[:12])
        s.reset();self.assertEqual(s.push(raw[:1999]),[])
        self.assertEqual(s.push(raw[1999:2000])[0]['sample_end'],2000)
    def test_invalid_model_and_input(self):
        for key,value in [('version','bad'),('donning',True),('scale',[0]*40),('inv',(-np.eye(40)).tolist())]:
            d=copy.deepcopy(self.data);d[key]=value
            with self.assertRaises(ValueError):ai.Model(d)
        with self.assertRaises(ValueError):ai.Stream(self.data).push(np.full((20,8),np.nan))
        with self.assertRaises(ValueError):ai.fit(self.records[:2],'rest',1)
    def test_reused_wear_number_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'emg-wl8-data'/'rest';folder.mkdir(parents=True)
            for i,day in enumerate(('2026-10-14','2026-10-15')):
                p=folder/f'{i}.npz';np.savez(p,emg_uv=np.ones((2000,8)))
                p.with_suffix('.json').write_text(json.dumps(dict(donning=1,recordedAt=day,session='same')))
            with self.assertRaisesRegex(ValueError,'多批次'):ai.fit_directory(root,['rest'],'rest',1)
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'model.json';ai.save(self.data,path)
            self.assertEqual(self.data,ai.load(path))
    def test_runtime_shadow_and_legacy_identical(self):
        # 使用真实产品包装器；同一原模型有无候选，旧输出逐字相同。
        entry=Path(__file__).resolve().parents[1]/'app/electron/emg8-server.py'
        spec=importlib.util.spec_from_file_location('test_server',entry);server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)
        trainer=server.install(entry.parents[2]/'host')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);legacy=trainer.fit(np.array([r['x'] for r in self.records]),np.array([r['label'] for r in self.records]))
            legacy['W']=np.zeros((40,2));legacy['short']=True
            dest=trainer.save({},legacy,root);plain=trainer.LivePredictor(dest/'model.npz')
            ai.save(dict(self.data,legacy_sha256=hashlib.sha256((dest/'model.npz').read_bytes()).hexdigest()),dest/'adaptive-intent.json')
            shadow=trainer.LivePredictor(dest/'model.npz')
            raw=np.random.default_rng(2).normal(size=(3000,8));count=0
            for block in np.array_split(raw,30):
                a=plain.push(block);b=shadow.push(block)
                if a is not None:
                    info=b.pop('adaptive_intent');a.pop('adaptive_intent')
                    self.assertEqual(a,b);self.assertEqual(info['status'],'active');count+=len(info['ticks'])
            self.assertEqual(count,11)
            shadow.set_mask([2]);self.assertEqual(shadow.push(raw)['adaptive_intent']['status'],'masked_channels_unsupported')
            before=shadow.buf.copy();since=shadow.since
            shadow.set_mask([])
            np.testing.assert_array_equal(shadow.buf,before);self.assertEqual(shadow.since,since)
            self.assertIsNotNone(shadow.push(raw[:100]));self.assertEqual(shadow.shadow.samples,100)
            shadow.reset();self.assertEqual(shadow.shadow.samples,0)
            # 真正走序号缺口包装器；丢包后不得把旧窗接到新数据。
            import wl8
            rig=wl8.FakeWl8Rig();rig._feed(wl8._frame(wl8.EMG,0,bytes(24)))
            shadow.push(raw);rig._feed(wl8._frame(wl8.EMG,2,bytes(24)))
            self.assertEqual(shadow.push(raw[:100])['probs'],{})
            self.assertEqual(shadow.shadow.samples,0);self.assertFalse(shadow.shadow.decoder.armed)
            bad=dict(self.data,legacy_sha256='wrong');ai.save(bad,dest/'adaptive-intent.json')
            broken=trainer.LivePredictor(dest/'model.npz');self.assertEqual(broken.push(raw)['adaptive_intent']['status'],'ValueError')
            legacy['adaptive_intent']=self.data
            with patch.object(ai,'save',side_effect=OSError('模拟候选写盘失败')):
                saved=trainer.save({},legacy,root)
            self.assertTrue((saved/'model.npz').exists())
            self.assertEqual(json.loads((saved/'run.json').read_text())['adaptive_intent']['status'],'unavailable')

    def test_short_live_snr_pool_and_temperature_calibration(self):
        # 端到端检验：带 rest_rms + temp 的短窗模型在 ShortLive 中启用因果 Score(snr_db) 加权池化与两步放松释放，且输出校准 noul。
        entry=Path(__file__).resolve().parents[1]/'app/electron/emg8-server.py'
        spec=importlib.util.spec_from_file_location('test_server_pool',entry);server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)
        trainer=server.install(entry.parents[2]/'host')
        rng=np.random.default_rng(19)
        gains=dict(seal_rest=np.full(8,20.),seal_poxie=np.array([20,250,250,20,20,20,20,20.]),
                   seal_daozhi=np.array([20,20,20,250,250,20,20,20.]),seal_wulei=np.array([20,20,20,20,20,250,250,20.]))
        labels=list(gains.keys())
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for l in labels:
                d=root/'emg-wl8-data'/l;d.mkdir(parents=True,exist_ok=True)
                for i in range(4):
                    e=(rng.normal(0,1,(4000,8))*gains[l]).astype(np.float32)
                    np.savez(d/f'{l}-{i}.npz',emg_uv=e,emg_hz=2000)
                    (d/f'{l}-{i}.json').write_text(json.dumps(dict(donning=1)))
            rep,model=trainer.train(root,labels,progress=lambda *_:None)
            self.assertIn('noise_ratio',rep);self.assertTrue(rep['noise_ratio']['ok'])
            dest=trainer.save(rep,model,root/'models')
            lp=trainer.LivePredictor(dest/'model.npz')
            self.assertIsNotNone(lp.rest_rms);self.assertGreater(lp.temp,0)
            # 先喂高信噪比破邪印 24 步（满 1000ms 窗并连推 5 步），验证高 SNR 池化稳住与校准 noul 输出
            for _ in range(24):
                r=lp.push(rng.normal(0,1,(100,8))*gains['seal_poxie'])
            self.assertEqual(r['top'],'seal_poxie');self.assertGreater(r['score'],0.7);self.assertIn('noul',r)
            # 随后喂放松样本填满整窗并连出两步静息，必须立即清空动作池化并回到 seal_rest，无拖尾
            for _ in range(22):
                r=lp.push(rng.normal(0,1,(100,8))*gains['seal_rest'])
            self.assertEqual(r['top'],'seal_rest');self.assertLess(r['snr_db'],1.5)
            # 因果性检查：篡改未来样本绝不改变已输出的预测、noul 与 score
            lp.reset();raw1=rng.normal(0,1,(2600,8))*gains['seal_poxie'];raw2=raw1.copy();raw2[2200:]*=-50
            out1=[lp.push(raw1[i:i+100]) for i in range(0,2200,100)]
            lp.reset();out2=[lp.push(raw2[i:i+100]) for i in range(0,2200,100)]
            for a,b in zip(out1,out2):
                if a is not None:
                    a=dict(a);b=dict(b);a.pop('adaptive_intent',None);b.pop('adaptive_intent',None)
                    self.assertEqual(a,b)


if __name__=='__main__':unittest.main()

"""连续验证的落盘/故障自检；假采集器、临时目录，不接手环和摄像头。"""
import base64
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from validation_recording import ValidationRecording, ms


class RecordingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.rig=SimpleNamespace(streaming=True,replay=None,chunk_subscribers=[],boundary_subscribers=[])
        self.rec=ValidationRecording(self.rig,self.tmp.name,lambda:dict(run_id='test'))
        self.body=dict(video_consent=True,donning=1)
    def tearDown(self):
        self.rec.stop();self.tmp.cleanup()
    def start(self):
        self.rec.start(self.body)
    def action(self,action,**kw):
        return self.rec.action(dict(action=action,id=self.rec.id,**kw))
    def raw(self,seq=(254,255,0,1)):
        self.rec.chunk(np.arange(len(seq)*8).reshape(-1,8),np.empty((0,6)),np.array(seq),np.full(len(seq),0xAA),int(ms()*1e6))
    def video(self):
        self.action('video',index=0,base64=base64.b64encode(bytes.fromhex('1a45dfa3')+b'test').decode())
    def timeline(self,freeze=False):
        ev=[dict(kind='sync',client_ms=i,send_ms=i,receive_ms=i+1,host_ms=ms(),rtt_ms=1) for i in range(3)]
        ev+=[dict(kind='video_start',client_ms=10),dict(kind='video_frame',client_ms=20,frame_ms=20)]
        if not freeze:ev+=[dict(kind='video_frame',client_ms=30,frame_ms=30)]
        ev+=[dict(kind='video_stop',client_ms=40 if not freeze else 4000)]
        self.action('events',events=[dict(e,event_id=i) for i,e in enumerate(ev)])
    def test_candidate_model_saved_with_hash(self):
        import hashlib
        models=Path(self.tmp.name)/'models';(models/'test').mkdir(parents=True)
        (models/'test'/'model.npz').write_bytes(b'legacy-model')
        candidate=b'{"mode":"shadow"}'
        (models/'test'/'adaptive-intent.json').write_bytes(candidate)
        self.rec.models=models;self.start()
        self.assertEqual((self.rec.dir/'adaptive-intent.json').read_bytes(),candidate)
        self.assertEqual(self.rec.info['adaptive_intent_sha256'],hashlib.sha256(candidate).hexdigest())
    def test_shadow_timeline_starts_before_recording(self):
        self.start();self.raw()
        tick=dict(window_start=3000,sample_end=5000)
        p=dict(adaptive_intent=dict(status='active',sample_cursor=5050,epoch=0,ticks=[tick]))
        self.rec.prediction(p,2000,ms())
        self.assertEqual(p['adaptive_intent']['validation_offset'],-5046)
        self.assertEqual(tick['validation'],dict(window_start=-2046,window_end=-46,has_full_window=False))
    def test_raw_and_prediction_link(self):
        self.start();self.raw();p={'probs':{'rest':1}}
        self.rec.prediction(p,8,ms())
        self.assertEqual(p['validation']['window_end'],4)
        self.assertEqual(p['validation']['window_start'],-4)
        self.assertEqual(np.fromfile(self.rec.dir/'emg.bin',dtype='<i4').size,32)
        self.assertEqual((self.rec.dir/'seq.bin').read_bytes(),bytes([254,255,0,1]))
    def test_gap_stops_without_joining(self):
        self.start();self.raw();self.raw((3,4));self.assertFalse(self.rec.active)
        self.assertEqual(self.rec.n,4);self.assertFalse(self.rig.chunk_subscribers)
    def test_bad_packet_type(self):
        self.start();self.rec.chunk(np.zeros((1,8)),np.empty((0,6)),[1],[0xBB],int(ms()*1e6))
        self.assertEqual(self.rec.n,0);self.assertFalse(self.rec.active)
    def test_complete_only_with_coverage_and_normal_end(self):
        self.start();self.raw();self.video();self.timeline();self.action('stop',reason='计划完成')
        self.assertTrue(self.action('finish',video_chunks=1,video_ok=True)['complete'])
        self.assertEqual(json.loads((self.rec.dir/'session.json').read_text())['annotation_status'],'pending')
    def test_freeze_not_complete(self):
        self.start();self.raw();self.video();self.timeline(True);self.action('stop',reason='计划完成')
        self.assertFalse(self.action('finish',video_chunks=1,video_ok=True)['complete'])
    def test_fault_not_complete(self):
        self.start();self.raw();self.video();self.timeline();self.action('stop',reason='包序号缺失或重复')
        self.assertFalse(self.action('finish',video_chunks=1,video_ok=True)['complete'])
    def test_reviewer_counterexample(self):
        self.start();self.raw((1,2))
        with self.assertRaises(ValueError):self.action('video',index=0,base64=base64.b64encode(b'not webm').decode())
        self.action('events',events=[dict(kind='video_frame',client_ms=1,event_id=0)])
        self.action('stop',reason='原始块时序不连续')
        self.assertFalse(self.action('finish',video_chunks=0,video_ok=True)['complete'])
    def test_duplicate_event_rejected_atomically(self):
        self.start()
        with self.assertRaises(ValueError):self.action('events',events=[dict(kind='cue',client_ms=1,event_id=0)]*2)
        self.assertEqual(self.rec.last_event_id,-1)
    def test_start_open_failure_recoverable(self):
        orig=Path.open; opened=[]
        def fail(path,*args,**kwargs):
            if path.name=='imu.bin':raise OSError('模拟磁盘失败')
            f=orig(path,*args,**kwargs)
            if path.name=='emg.bin':opened.append(f)
            return f
        with patch.object(Path,'open',fail):
            with self.assertRaises(OSError):self.start()
        self.assertTrue(all(f.closed for f in opened));self.assertFalse(self.rec.active)
        self.assertFalse(self.rig.chunk_subscribers);self.start();self.assertTrue(self.rec.active)
    def test_start_metadata_failure_recoverable(self):
        with patch.object(Path,'replace',side_effect=OSError('模拟元数据失败')):
            with self.assertRaises(OSError):self.start()
        self.start();self.assertTrue(self.rec.active)
    def test_stop_error_detaches_and_can_finalize(self):
        self.start()
        with patch.object(self.rec,'_event',side_effect=OSError('模拟写入失败')):self.rec.stop()
        self.assertFalse(self.rig.chunk_subscribers);self.assertFalse(self.rec.files)
        self.assertFalse(self.action('finish',video_chunks=0,video_ok=False)['complete'])
    def test_abandoned_renderer_can_start_independent_segment(self):
        self.start();self.raw();old=self.rec.dir
        self.rec.check_health(self.rec.heartbeat+5001)
        self.assertTrue(self.rec.finalized);self.assertFalse(self.rec.active)
        self.assertEqual(json.loads((old/'session.json').read_text())['state'],'incomplete')
        self.start();self.assertNotEqual(old,self.rec.dir);self.assertEqual(self.rec.n,0)
    def test_abandoned_after_raw_stop_can_restart(self):
        self.start();self.raw();self.rec.stop('原始数据中断')
        self.rec.check_health(self.rec.heartbeat+5001)
        self.start();self.assertTrue(self.rec.active)

    def test_repeated_session_resets(self):
        self.start();self.raw();self.action('stop');self.action('finish',video_chunks=0,video_ok=False)
        self.start();self.assertEqual(self.rec.n,0);self.assertEqual(self.rec.frame_n,0)

class HttpRecordingTests(unittest.TestCase):
    def test_real_http_decode_save_and_output_guards(self):
        import emg_web, wl8, threading, urllib.request, urllib.error
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); rig=wl8.FakeWl8Rig()
            sets={k:{kind:root/p.name for kind,p in v.items()} for k,v in emg_web.SETS.items()}
            with patch.object(emg_web,'HERE',root):
                session=emg_web.Session(rig,sets,model_root=root/'models')
            self.assertEqual(session.validation.root,root/'v12-captures'/'validation-local')
            model=session.wl8_models()/'fixture';model.mkdir(parents=True);(model/'model.npz').write_bytes(b'local-model-fixture')
            session.live8=dict(run_id='fixture',threshold_uv=0,sensitivity=1,min_prob=0,predictor=SimpleNamespace(mask=[]))
            server=emg_web.server_for(session,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            def call(body,path='validation'):
                req=urllib.request.Request(f'http://127.0.0.1:{server.server_port}/api/emg/wl8/{path}',data=json.dumps(body).encode(),headers={'Content-Type':'application/json','X-Mako-Collector':'1','X-Mako-Project':''})
                try:
                    with urllib.request.urlopen(req,timeout=3) as r:return r.status,json.load(r)
                except urllib.error.HTTPError as e:return e.code,json.load(e)
            try:
                code,started=call(dict(action='start',video_consent=True,donning=1));self.assertEqual(code,200)
                raw,_=wl8._synth_frames('rest',rig.rng,seconds=.1,seq0=0)
                rig._feed(raw)
                self.assertGreater(session.validation.n,0)
                self.assertEqual(call(dict(action='tune'),'live')[0],400)
                self.assertEqual(call(dict(action='enable'),'cursor')[0],400)
                self.assertEqual(call(dict(action='left_click'),'action')[0],400)
                call(dict(action='stop',id=started['id'],reason='用户停止'))
                # 录像收尾超过失联期限时，页面仍发心跳，不应被提前封存。
                import time
                for _ in range(6):
                    call(dict(action='clock',id=started['id']));time.sleep(1)
                self.assertFalse(session.validation.finalized)
                code,_=call(dict(action='video',id=started['id'],index=0,base64=base64.b64encode(bytes.fromhex('1a45dfa3')+b'test').decode()))
                self.assertEqual(code,200)
                code,done=call(dict(action='finish',id=started['id'],video_chunks=0,video_ok=False))
                self.assertEqual(code,200);self.assertFalse(done['complete']);self.assertTrue(done['finalized'])
                self.assertTrue((Path(done['path'])/'emg.bin').stat().st_size>0)
                self.assertEqual(Path(done['path']).parent,root/'v12-captures'/'validation-local')
                self.assertEqual((Path(done['path'])/'model.npz').read_bytes(),b'local-model-fixture')
            finally:
                session.validation.stop();server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()

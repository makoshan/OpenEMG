"""本机连续验证存档：原始块、视频和事件分别记账，不进入训练/上传目录。"""
import base64
import hashlib
import json
import math
import threading
import time
import uuid
from pathlib import Path
import numpy as np


def ms(): return time.monotonic_ns()/1e6


class ValidationRecording:
    def __init__(self, rig, root, live_info, models=None):
        self.rig, self.root, self.live_info = rig, Path(root), live_info
        self.models = models
        self.lock = threading.RLock()
        self.active = False
        self.id = None
        self.fault = ''
        self.dir = None
        self.video_n = 0
        self.video_bytes = 0
        self.frame_n = 0
        self.n = 0
        self.last_seq = None
        self.last_host = None
        self.files = {}
        self.finalized = False
        self.last_event_id = -1

    def _write_meta(self):
        tmp = self.dir/'session.tmp.json'
        tmp.write_text(json.dumps(self.info, ensure_ascii=False, indent=2))
        tmp.replace(self.dir/'session.json')

    def _event(self, kind, **data):
        # 每行立即写出；崩溃留下partial，不伪装完成。
        with (self.dir/'events.jsonl').open('a') as f:
            f.write(json.dumps(dict(kind=kind, host_ms=ms(), emg_index=self.n, **data), ensure_ascii=False, allow_nan=False)+'\n')

    def state(self):
        return dict(id=self.id, active=self.active, reason=self.fault, samples=self.n,
                    video_chunks=self.video_n, video_bytes=self.video_bytes, video_frames=self.frame_n,
                    finalized=self.finalized, path=str(self.dir) if self.dir else None)

    def start(self, body):
        with self.lock:
            if self.active or (self.id and not self.finalized): raise ValueError('上一段尚未收尾，请先停止保存')
            info = self.live_info()
            if not info or getattr(self.rig,'replay',None): raise ValueError('先连接真实手环并开始识别')
            if not getattr(self.rig,'streaming',False): raise ValueError('手环没有数据')
            if body.get('video_consent') is not True: raise ValueError('需要明确同意仅本机手部视频')
            wear = body.get('donning')
            if type(wear) is not int or wear < 1: raise ValueError('缺少佩戴编号')
            # 启动失败也能重试；不留下无法取得会话编号的活动录制。
            try:
                self.id = uuid.uuid4().hex; self.dir = self.root/self.id; self.dir.mkdir(parents=True)
                self.active=True; self.finalized=False; self.fault=''; self.n=0; self.video_n=0; self.video_bytes=0; self.frame_n=0
                self.last_seq=None; self.last_host=None; self.last_event_id=-1
                self.prediction_n=0; self.video_events=[]
                self.started=ms(); self.heartbeat=self.started
                self.info=dict(protocol='continuous-validation-v1', id=self.id, state='partial',
                               started_wall=time.time(), started_host_ms=self.started, fs=2000,
                               donning=wear, model=info, video_consent=True, local_only=True,
                               note='提示不是动作真值；需核对视频起止。块时间是主机收到时间，非硬件采样时间。',
                               format=dict(emg='little-endian int32 Nx8', imu='little-endian int16 Nx6', seq='uint8', kinds='uint8'))
                if self.models is not None:
                    model = (Path(self.models)/info['run_id']/'model.npz').read_bytes()
                    (self.dir/'model.npz').write_bytes(model)
                    self.info['model_sha256'] = hashlib.sha256(model).hexdigest()
                    sidecar = Path(self.models)/info['run_id']/'adaptive-intent.json'
                    if sidecar.exists():
                        candidate = sidecar.read_bytes()
                        (self.dir/'adaptive-intent.json').write_bytes(candidate)
                        self.info['adaptive_intent_sha256'] = hashlib.sha256(candidate).hexdigest()
                self._write_meta()
                self.files={}
                for k in ('emg','imu','seq','kinds'): self.files[k]=(self.dir/(k+'.bin')).open('wb')
                self.rig.chunk_subscribers.append(self.chunk)
                self.rig.boundary_subscribers.append(self.boundary)
                self._event('start')
                threading.Thread(target=self._watch, args=(self.id,), daemon=True).start()
                return self.state()
            except Exception:
                self.active=False; self.finalized=True
                for coll,cb in [(self.rig.chunk_subscribers,self.chunk),(self.rig.boundary_subscribers,self.boundary)]:
                    if cb in coll: coll.remove(cb)
                for f in self.files.values(): f.close()
                self.files={}
                raise

    def _watch(self, sid):
        while True:
            time.sleep(.1)
            with self.lock:
                if self.id != sid or self.finalized: return
                self.check_health()

    def check_health(self, now=None):
        with self.lock:
            now=ms() if now is None else now
            if self.finalized: return
            if now-self.heartbeat>5000:
                # 页面崩溃丢失会话编号后，把旧段封为不完整，下一次另起新段。
                self.stop('页面失去联系')
                self.finalized=True
                self.info.update(state='incomplete', annotation_status='pending',
                                 video_chunks=self.video_n, video_bytes=self.video_bytes,
                                 video_frames=self.frame_n, finished_wall=time.time(), abandoned=True)
                try:self._write_meta()
                except OSError as exc:self.fault='失联后保存失败：'+str(exc)
            elif self.active:
                if now-(self.last_host if self.last_host is not None else self.started)>1000:self.stop('原始数据中断')
                elif now-self.started>600000:self.stop('超过最长10分钟')

    def boundary(self, event):
        with self.lock:
            if self.active: self.stop('采集配置或连接发生变化')

    def chunk(self, emg, imu, seq, kinds, host_ns):
        with self.lock:
            if not self.active:return
            try:
                now=host_ns/1e6
                if self.last_host is not None and (now<=self.last_host or now-self.last_host>500):
                    self.stop('原始块时序不连续');return
                seq=np.asarray(seq,dtype=np.uint8); kinds=np.asarray(kinds,dtype=np.uint8)
                e=np.asarray(emg);m=np.asarray(imu)
                if e.ndim!=2 or e.shape[1]!=8 or m.ndim!=2 or m.shape[1]!=6 or len(seq)!=len(kinds) or len(seq)!=len(e)+len(m) or np.count_nonzero(kinds==0xAA)!=len(e) or np.count_nonzero(kinds==0xBB)!=len(m) or not np.isfinite(e).all() or not np.isfinite(m).all():
                    self.stop('原始块格式无效');return
                chain=seq.astype(int) if self.last_seq is None else np.r_[self.last_seq,seq.astype(int)]
                if len(chain)>1 and np.any(np.diff(chain)%256!=1):self.stop('包序号缺失或重复');return
                if len(seq):self.last_seq=int(seq[-1])
                self.last_host=now
                for key,arr,dtype in [('emg',e,'<i4'),('imu',m,'<i2'),('seq',seq,'u1'),('kinds',kinds,'u1')]:
                    self.files[key].write(np.asarray(arr,dtype=dtype).tobytes());self.files[key].flush()
                with (self.dir/'chunks.jsonl').open('a') as f:
                    f.write(json.dumps(dict(host_ns=int(host_ns),emg_index=self.n,emg_n=len(e),imu_n=len(m),packet_n=len(seq)))+'\n')
                self.n+=len(e)
            except Exception as exc:
                self.stop('原始数据保存失败：'+str(exc))

    def prediction(self, pred, window_n=0, started_ms=None):
        with self.lock:
            if self.active:
                try:
                    self.prediction_n+=1
                    pred['validation']=dict(id=f'{self.id}:{self.prediction_n}', window_start=self.n-window_n, window_end=self.n)
                    shadow=pred.get('adaptive_intent', {})
                    if shadow.get('status')=='active' and type(shadow.get('sample_cursor')) is int:
                        # 原始chunk先入库、预测后回调；把持续识别的样本零点映射到本次录制。
                        offset=self.n-shadow['sample_cursor']
                        shadow['validation_offset']=offset
                        for tick in shadow.get('ticks', []):
                            start=tick['window_start']+offset;end=tick['sample_end']+offset
                            tick['validation']=dict(window_start=start,window_end=end,has_full_window=start>=0)
                    self._event('prediction', prediction=pred, inference_start_ms=started_ms)
                except Exception as exc:self.stop('预测保存失败：'+str(exc))

    def stop(self, reason='用户停止'):
        with self.lock:
            if self.active:
                self.active=False;self.fault=reason
                for coll,cb in [(self.rig.chunk_subscribers,self.chunk),(self.rig.boundary_subscribers,self.boundary)]:
                    if cb in coll:coll.remove(cb)
                for f in self.files.values():f.close()
                self.files={}
                self.info.update(raw_stopped_host_ms=ms(),stop_reason=reason,emg_samples=self.n)
                try:
                    self._event('raw_stop',reason=reason)
                    self._write_meta()
                except Exception as exc:
                    self.fault='停止保存失败：'+str(exc)
                
            return self.state()

    def action(self, body):
        action=body.get('action')
        if action=='start': return self.start(body)
        with self.lock:
            if not self.id or body.get('id')!=self.id:raise ValueError('连续验证会话不匹配')
            if action=='status':return self.state()
            if action=='clock':
                self.heartbeat=ms();return dict(host_ms=ms(),**self.state())
            if action=='stop':return self.stop(str(body.get('reason','用户停止'))[:100])
            if self.finalized: raise ValueError('这段已经收尾')
            if action=='events':
                events=body.get('events')
                if not isinstance(events,list) or len(events)>300:raise ValueError('事件数量无效')
                # 先整批校验，避免重试时部分写入。
                last=self.last_event_id
                allowed={'sync','cue','video_frame','video_start','video_stop','trigger','gate','capture_error'}
                for ev in events:
                    if not isinstance(ev,dict) or ev.get('kind') not in allowed or type(ev.get('event_id')) is not int or ev['event_id']<=last:raise ValueError('事件乱序或重复')
                    t=ev.get('client_ms')
                    if isinstance(t,bool) or not isinstance(t,(int,float)) or not math.isfinite(t):raise ValueError('事件时间无效')
                    json.dumps(ev,allow_nan=False);last=ev['event_id']
                for ev in events:
                    self._event('client',event=ev)
                    if ev['kind']=='video_frame':self.frame_n+=1
                    if ev['kind'] in ('video_start','video_stop','video_frame','sync','capture_error'):self.video_events.append(ev)
                self.last_event_id=last;return self.state()
            if action=='video':
                if type(body.get('index')) is not int or body['index']!=self.video_n:raise ValueError('视频分片不连续')
                encoded=body.get('base64')
                if not isinstance(encoded,str) or len(encoded)>12_000_000:raise ValueError('视频分片过大')
                data=base64.b64decode(encoded,validate=True)
                if not data:raise ValueError('空视频分片')
                if self.video_n==0 and not data.startswith(bytes.fromhex('1a45dfa3')):raise ValueError('视频缺少WebM文件头')
                if self.video_bytes+len(data)>512_000_000:raise ValueError('视频超过512MB上限')
                with (self.dir/'hand.webm').open('ab') as f:f.write(data)
                self.video_n+=1;self.video_bytes+=len(data);return self.state()
            if action=='finish':
                if self.active:raise ValueError('原始录制尚未停止')
                starts=[e['client_ms'] for e in self.video_events if e['kind']=='video_start']
                stops=[e['client_ms'] for e in self.video_events if e['kind']=='video_stop']
                frames=[e.get('frame_ms',float('nan')) for e in self.video_events if e['kind']=='video_frame']
                syncs=[e for e in self.video_events if e['kind']=='sync']
                coverage=bool(len(starts)==1 and len(stops)==1 and len(frames)>1 and
                              all(isinstance(t,(int,float)) and math.isfinite(t) for t in frames) and
                              all(0<b-a<=1000 for a,b in zip(frames,frames[1:])) and
                              abs(frames[0]-starts[0])<=1000 and 0<=stops[0]-frames[-1]<=1000 and
                              len(syncs)>=3 and not any(e['kind']=='capture_error' for e in self.video_events))
                # 故障中断可以保存，但绝不计作完整验证。视频仍须人工解码、标注验收。
                complete=bool(self.n and self.video_bytes and coverage and self.fault=='计划完成' and
                              body.get('video_chunks')==self.video_n and body.get('video_ok') is True)
                self.info.update(state='saved-awaiting-annotation' if complete else 'incomplete', video_chunks=self.video_n,
                                 video_bytes=self.video_bytes, video_frames=self.frame_n, annotation_status='pending',finished_wall=time.time())
                self._write_meta();self.finalized=True
                return dict(**self.state(),complete=complete)
            raise ValueError('未知连续验证操作')

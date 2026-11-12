"""无硬件：V12包→同步重置→真实HTTP SSE边界与新段。"""
import http.client,json,tempfile,threading
from pathlib import Path
import numpy as np
import v12,emg_web,emg_live,wl8_train,wl8_cursor

def run():
 rig=v12.V12Rig(allow_real=True);c=rig.codec
 session=emg_web.Session.__new__(emg_web.Session)
 session.rig=rig;session.project=None;session.pred_subscribers=[];session.events=['old']
 lp=wl8_train.LivePredictor.__new__(wl8_train.LivePredictor)
 lp.win=2000;lp.step=200;lp.buf=np.ones((1900,8));lp.since=1900
 session.live8={'predictor':lp,'last':{'top':'old'}}
 det=emg_live.Detector(lambda w:('rest',1),[0,1]);det.feed(np.ones((100,8)))
 det.pending=20;session.live=det
 rig.boundary_subscribers.append(session.stream_boundary)
 rig.frame_subscribers.append(lambda samples: lp.push(samples))
 with tempfile.TemporaryDirectory() as tmp:
  cursor=wl8_cursor.Controller(rig,Path(tmp),voice=False)
  session.cursor=cursor;cursor.ebuf=[np.ones((5,8))];cursor.mode='log'
  server=emg_web.server_for(session,0);worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
  conn=http.client.HTTPConnection('127.0.0.1',server.server_address[1],timeout=3)
  try:
   conn.request('GET','/api/emg/stream8');response=conn.getresponse();assert response.status==200
   def packet(seq,ts,flags):return c.encode(c.Packet(seq,ts,flags,(bytes.fromhex('c00000')+bytes(24),)))
   def event():
    lines=[]
    while True:
     line=response.readline().decode().strip()
     if not line:break
     lines.append(line)
    data=json.loads(next(x[6:] for x in lines if x.startswith('data: ')))
    return lines,data
   rig.feed_packet(packet(0,1000,2));_,first=event();assert first['segment']==0
   rig.feed_packet(packet(0,11000,6));lines,boundary=event();assert 'event: boundary' in lines
   _,second=event();assert second['segment']==1 and second['sample_index']==0
   assert boundary['missing_samples'] is None
   assert len(lp.buf)==1 and lp.since==1 and session.live8['last'] is None
   assert lp.push(np.ones((100,8))) is None # 若未重置，1900+100会进入分类，必报红。
   assert not det.ready and det.pending is None and len(det.ring)==0
   assert cursor.mode=='off' and not cursor.ebuf and cursor.pcal is None
   assert session.events==[]
   rig.disconnect();lines,event_data=event();assert event_data['reason']=='disconnect'
   assert len(lp.buf)==0 and not det.ready
   rig.feed_packet(packet(0,21000,2));_,third=event();assert third['segment']==2 and third['sample_index']==0
  finally:
   conn.close();server.shutdown();server.server_close();worker.join(3)
 print('PASS：真实HTTP配置边界先于新段；预测/检测/光标窗口清空并重新预热')
if __name__=='__main__':run()

# 独立光标客户端满队列时，边界必须抢先停止，不能排在旧动作后面。
if __name__=='__main__':
 import queue,io
 from unittest.mock import patch
 q=queue.Queue(maxsize=1);q.put(('emg',np.ones((8,8))))
 with patch.object(wl8_cursor.urllib.request,'urlopen',side_effect=[io.BytesIO(b'{"rig":{"kind":"wl8"}}'),io.BytesIO(b'event: boundary\ndata: {}\n\n')]):
  wl8_cursor.stream(q)
 assert q.get_nowait()[0]=='error' and q.empty()
 print('PASS：满客户端队列先清旧动作再发边界停止')

import sys,tempfile,threading,urllib.request,urllib.error,json,time
from pathlib import Path
sys.path.insert(0,'firmware')
import emg_web
with tempfile.TemporaryDirectory() as d:
 root=Path(d)
 sets={k:{kind:root/'data'/'emg'/p.name for kind,p in v.items()} for k,v in emg_web.SETS.items()}
 s=emg_web.Session(emg_web.FakeRig(),sets,project={'id':'test-project','name':'test'})
 srv=emg_web.server_for(s,0); threading.Thread(target=srv.serve_forever,daemon=True).start()
 def get(route,body=None,project=''):
  req=urllib.request.Request(f'http://127.0.0.1:{srv.server_port}'+route,data=None if body is None else json.dumps(body).encode(),headers={'X-Mako-Collector':'1','X-Mako-Project':project})
  try:
   with urllib.request.urlopen(req) as r:return r.status
  except urllib.error.HTTPError as e:return e.code
 assert get('/guide')==409
 assert get('/guide?project=other')==409
 assert get('/guide?project=test-project')==200
 assert get('/api/emg/record',{},'other')==409
 assert get('/api/emg/record',{},'test-project')==400
 assert get('/api/emg/record',{'task':'gestures','label':'rest','set':'train','count':1,'countdown':0},'test-project')==202
 for _ in range(100):
  if not s.busy: break
  time.sleep(.05)
 assert s.gesture_counts()['train']['rest']==1
 assert all(p.is_relative_to(root/'data'/'emg') for p in s.gesture_sets().values())
 srv.shutdown();srv.server_close()
print('Project isolation: wrong/missing identity rejected; project data roots PASS')

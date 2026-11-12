"""Capture polling must not read training reports; full training state remains available."""
import json, tempfile, threading, urllib.request
from pathlib import Path
from unittest.mock import patch
import emg_web
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    sets={s:{'emg':root/s} for s in ('train','rewear')}
    session=emg_web.Session(emg_web.FakeRig(),sets,model_root=root/'models')
    srv=emg_web.server_for(session,0)
    threading.Thread(target=srv.serve_forever,daemon=True).start()
    try:
        with patch.object(session,'gesture_training',side_effect=AssertionError('capture read reports')):
            with urllib.request.urlopen(f'http://127.0.0.1:{srv.server_port}/api/emg/state?view=capture') as r:
                state=json.load(r)
            assert state['gesture_training'] is None
            assert 'gesture_counts' in state and 'diagnostic' in state and 'capture_issue' in state
        with patch.object(session,'gesture_training',return_value={'runs':['sentinel']}) as reports:
            assert session.state()['gesture_training']['runs']==['sentinel']
            reports.assert_called_once()
    finally:srv.shutdown();srv.server_close()
print('PASS: capture HTTP skips reports; full training state still reads them')

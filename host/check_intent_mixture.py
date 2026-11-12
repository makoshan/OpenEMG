"""离线双模板候选：触发契约、训练等权、分块因果性与拒绝路径。"""
import copy
import json
from pathlib import Path
import sys
import unittest
import tempfile
import subprocess
import numpy as np
import intent_mixture as im
from wl8_train import fit, scores
sys.path.insert(0, str(Path(__file__).resolve().parent/'research'))
from adaptive_intent_recovery import RetainReady, game_events, export_model
from adaptive_intent_compare import legacy_events

CLASSES = ['seal_a', 'seal_rest']
REST = [.05, .95]
ACTION = [.95, .05]


def records():
    rng = np.random.default_rng(35)
    return [dict(label=c, x=rng.normal(i*3, 1, 40),
                 windows=[(rng.normal(i*3, 1, 40),) for _ in range(3+j)])
            for i,c in enumerate(CLASSES) for j in range(4)]


class Checks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = records()
        cls.data = im.fit(cls.rows, 'seal_rest', 1)

    def test_contract_regression(self):
        p = np.array([REST]*2 + [[.7,.3]]*3 + [ACTION]*3)
        self.assertEqual(legacy_events(p, CLASSES, 'seal_rest'), [])
        d = im.Decoder(CLASSES, 'seal_rest')
        self.assertEqual([d.push(x) for x in p], [None]*7+['seal_a'])
        self.assertEqual([d.push(ACTION) for _ in range(20)], [None]*20)
        for x in [REST]*2+[ACTION]*2:
            self.assertIsNone(d.push(x))
        self.assertEqual(d.push(ACTION), 'seal_a')

    def test_no_initial_or_gap_readiness(self):
        d = im.Decoder(CLASSES, 'seal_rest')
        self.assertEqual([d.push(ACTION) for _ in range(5)], [None]*5)
        for x in [REST]*2:
            d.push(x)
        d.reset()
        self.assertEqual([d.push(ACTION) for _ in range(5)], [None]*5)

    def test_invalid_clears_readiness(self):
        for bad in ([np.nan, 0], [1], [-.1,1.1], [0,0]):
            d = im.Decoder(CLASSES, 'seal_rest')
            for x in [REST]*2:
                d.push(x)
            self.assertIsNone(d.push(bad))
            self.assertFalse(d.armed)
        d = RetainReady(CLASSES, 'seal_rest'); d.armed = True
        d.push([np.nan, 0], False, 'uncertain')
        self.assertFalse(d.armed)

    def test_three_consecutive_same_action(self):
        d = im.Decoder(CLASSES, 'seal_rest'); d.armed = True
        for x in [ACTION, ACTION, [.79,.21], ACTION, ACTION]:
            self.assertIsNone(d.push(x))
        self.assertEqual(d.push(ACTION), 'seal_a')

    def test_record_weight_and_reference(self):
        rows = self.rows
        n = min(len(r['windows']) for r in rows)
        a = fit(np.array([r['x'] for r in rows]), np.array([r['label'] for r in rows]))
        x = np.concatenate([np.array([w[0] for w in r['windows']])[np.linspace(0,len(r['windows'])-1,n).astype(int)] for r in rows])
        b = fit(x, np.repeat([r['label'] for r in rows], n))
        m = im.Model(json.loads(json.dumps(self.data)))
        self.assertEqual(self.data['windows_per_record'], 3)
        for z in x:
            np.testing.assert_allclose(m.predict(z), (scores(a,z[None])[1][0]+scores(b,z[None])[1][0])/2)

    def test_reference_trigger_parity(self):
        rng = np.random.default_rng(88)
        p = rng.dirichlet([.2,.2], size=1000)
        d = im.Decoder(CLASSES, 'seal_rest'); d.armed = True
        out = []
        for i,x in enumerate(p):
            event = d.push(x)
            if event:
                out.append(dict(label=event,clip_seconds=1+i*.05))
        self.assertEqual(out, game_events(p, CLASSES, True))

    def test_chunk_and_prefix_causality(self):
        raw = np.random.default_rng(9).normal(size=(4100,8))*50
        a = im.Stream(self.data).push(raw)
        s = im.Stream(self.data); b = []
        for chunk in np.array_split(raw, 23):
            b.extend(s.push(chunk))
        self.assertEqual(a, b)
        self.assertEqual(im.Stream(self.data).push(raw[:3000]), a[:11])
        self.assertEqual([r['sample_end'] for r in a], list(range(2000,4101,100)))
        s.reset(); self.assertEqual(s.push(raw[:3000]), a[:11])

    def test_flatline_and_bad_block(self):
        s = im.Stream(self.data); s.decoder.armed = True
        ticks = s.push(np.zeros((2200,8)))
        self.assertTrue(all(t['flatline'] and t['event'] is None for t in ticks))
        self.assertFalse(s.decoder.armed)
        with self.assertRaises(ValueError):
            s.push(np.full((1,8), np.nan))
        self.assertEqual(s.samples, 0)

    def test_export_session_identity(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            a = export_model(self.data, ('2026-10-15',1,'a'), folder)
            b = export_model(self.data, ('2026-10-15',1,'b'), folder)
            self.assertNotEqual(a,b)
            self.assertEqual(json.loads(a.read_text())['binding'][-1], 'a')
            with self.assertRaises(FileExistsError):
                export_model(self.data, ('2026-10-15',1,'a'), folder)

    def test_cli_gap_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            model = export_model(self.data, ('2026-10-15',1,'a'), folder)
            raw = folder/'raw.npz'
            np.savez(raw, emg_uv=np.random.default_rng(7).normal(size=(2200,8)), emg_hz=2000)
            meta = dict(recordedAt='2026-10-15T12:00', donning=1, session='a', dropped=0)
            raw.with_suffix('.json').write_text(json.dumps(meta))
            args = [sys.executable, str(Path(im.__file__)), '--model', str(model), '--raw', str(raw)]
            good = subprocess.run(args+['--out',str(folder/'good.json')],capture_output=True)
            self.assertEqual(good.returncode,0,good.stderr)
            meta['dropped'] = 10
            raw.with_suffix('.json').write_text(json.dumps(meta))
            bad = subprocess.run(args+['--out',str(folder/'bad.json')],capture_output=True)
            self.assertNotEqual(bad.returncode,0)
            self.assertIn('录音有丢帧',bad.stderr.decode())
            self.assertFalse((folder/'bad.json').exists())

    def test_invalid_model_and_training(self):
        for key,value in [('donning',0), ('step',200), ('version','old')]:
            d = copy.deepcopy(self.data); d[key] = value
            with self.assertRaises(ValueError):
                im.Model(d)
        with self.assertRaises(ValueError):
            im.fit(self.rows[:2], 'seal_rest', 1)
        d = copy.deepcopy(self.data); d['models'][0]['sinv'][0][0] = -1e10
        with self.assertRaises(ValueError):
            im.Model(d)


if __name__ == '__main__':
    unittest.main(verbosity=2)

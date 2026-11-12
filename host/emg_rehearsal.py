"""Versioned five-trial preflight. Never writes to training or test directories."""
import json
import uuid
from pathlib import Path

LABELS = ('rest', 'pinch', 'rub', 'snap', 'fist')
PROTOCOL = 'single-action-v3'

def state(root):
    root = Path(root)
    marker = root / 'session.json'
    meta = json.loads(marker.read_text()) if marker.exists() else {}
    counts = {label: len(list((root / 'wear-1' / label).glob('*.npz'))) for label in LABELS}
    return {**meta, 'counts': {'wear-1': counts}, 'complete': all(n == 1 for n in counts.values()),
            'training_eligible': False, 'review_required': bool(sum(counts.values()))}

def start(root, participant, placement, battery_confirmed):
    root = Path(root)
    if (root / 'session.json').exists():
        return state(root)
    fields = [participant, placement]
    if not all(isinstance(v, str) and 0 < len(v.strip()) <= 160 and not any(c in v for c in '\r\n') for v in fields):
        raise ValueError('请填写用户和佩戴位置，每项最多 160 字')
    if battery_confirmed is not True:
        raise ValueError('请先确认电脑电池供电，已断开充电器和扩展坞')
    meta = {'id': str(uuid.uuid4()), 'protocol': PROTOCOL, 'participant': participant.strip(),
            'placement': placement.strip(), 'battery_confirmed_by_user': True, 'donning': 1,
            'stage': 'rehearsal', 'quality_rule': 'capture-checks-plus-review-v1',
            'actions': {'rest':'relax', 'pinch':'single-contact-release', 'rub':'single-slide-release',
                        'snap':'single-snap-release', 'fist':'comfortable-fist-release'},
            'cue_ms': {'relax':0, 'action':400, 'release':1400}, 'sample_ms':2000,
            'training_eligible':False}
    root.mkdir(parents=True, exist_ok=True)
    temp = root / 'session.tmp'
    temp.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    temp.replace(root / 'session.json')
    return state(root)

def destination(root, label, count, which):
    current = state(root)
    if not current.get('id'):
        raise ValueError('请先填写并确认预演条件')
    if label not in LABELS or which != 'wear-1' or count != 1:
        raise ValueError('预演每次只录一个动作的一条数据')
    expected = next((k for k in LABELS if current['counts']['wear-1'][k] < 1), None)
    if label != expected:
        raise ValueError('请按预演顺序录制；已保存的动作不能重复覆盖')
    return Path(root) / 'wear-1', current

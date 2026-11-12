import os
"""Small integrity check for saved EMG model-review figures; does not read data/test."""
import json
from pathlib import Path


OUT = Path(os.environ.get('EMG_FIG_OUT', '/tmp/openemg-model-visuals'))
rows = json.loads((OUT / 'index.json').read_text())
assert len(rows) == 19
assert len(list(OUT.glob('*-compare.svg'))) == 20  # 19 models plus all-models summary
assert len(list(OUT.glob('*-why.svg'))) == 19
assert (OUT / 'svm-rewear-confusion.svg').exists()
assert len(list(OUT.glob('*.svg'))) == 40
assert all('<svg ' in p.read_text() and 'nan' not in p.read_text().lower() for p in OUT.glob('*.svg'))
svm = next(row for row in rows if row['model'] == 'svm')
assert abs(svm['training_balanced_accuracy'] - 72.6666666667) < .01
assert abs(svm['rewear_balanced_accuracy'] - 66) < .01
print('PASS 19 models, 40 SVGs, finite values; baseline SVM 72.7% / 66.0%')

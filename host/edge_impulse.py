"""Validated local MAKO -> Edge Impulse bundles. Never connects to the network."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import numpy as np
import gesture_model as gm
from gesture_model import POINTS, PROFILE, SPLITS, edge_window, load_records, write_json

# LABELS is NOT imported by name: `from gesture_model import LABELS` binds the tuple at
# import time, so a later set_labels() -- which is how --merge folds hook/uppercut into
# punch -- would leave this module still counting six classes while load_records returned
# four. Read gm.LABELS at call time instead.

CATEGORIES = {'train':'training', 'validation':'validation', 'test':'testing'}
AXES = ['ax','ay','az','gx','gy','gz']


def export_dataset(data, output):
    output=Path(output).resolve()
    if output.exists():raise FileExistsError('Output exists; choose a new bundle directory')
    records,rejected=load_records(data)
    if rejected:raise ValueError('Dataset rejected: '+json.dumps(rejected,ensure_ascii=False))
    if not records:raise ValueError('No confirmed, valid recordings; diagnostics are not training data')
    target=np.arange(POINTS)*1000/PROFILE['hz']
    prepared=[]
    for record in records:
        try:rows=edge_window(record['samples'])
        except ValueError as exc:raise ValueError(f"{exc}: {record['path']}") from exc
        prepared.append((record,rows))
    labels=gm.LABELS
    counts={split:{label:sum(r['split']==split and r['label']==label for r in records)
                   for label in labels} for split in SPLITS}
    # The fold travels with the bundle: an Edge Impulse project built from a four-class export
    # must not be fed a six-class one later, and the manifest is the only place that records it.
    manifest={'schema':1,'count':len(records),'counts':counts,'profile':PROFILE,'axes':AXES,
              'labels':list(labels),'merge':dict(gm.MERGE),
              'timestamp_unit':'ms','interval_ms':1000/52,'csv_span_ms':float(target[-1]),
              'resampling':'linear at exact nominal 52Hz, no extrapolation',
              'ready_for_training':all(counts['train'][k]>=20 and counts['validation'][k]>=5 for k in labels),
              'uploaded':False,'model_trained':False,'files':[]}
    output.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.mako-ei-',dir=output.parent))
    try:
        info={s:{'version':1,'files':[]} for s in SPLITS}
        for record,rows in prepared:
            relative=Path(record['split'])/f"{record['label']}.{record['digest']}.csv"
            path=stage/relative;path.parent.mkdir(exist_ok=True)
            with path.open('x',newline='') as f:
                writer=csv.writer(f);writer.writerow(['timestamp',*AXES])
                for timestamp,axes in zip(target,rows):writer.writerow([f'{timestamp:.9f}',*axes])
            metadata={'session':record['session'],'mako_split':record['split'],'hand':'left',
                      'capture_sha256':record['digest'],'timing_source':record['quality']['timing_source'],
                      'accel_unit':'g','gyro_unit':'deg/s'}
            item={'path':relative.as_posix(),'category':CATEGORIES[record['split']],
                  'label':{'type':'label','label':record['label']},'metadata':metadata}
            info[record['split']]['files'].append(item)
            manifest['files'].append({'csv':relative.as_posix(),'csv_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                                     'source':str(Path(record['path']).resolve()),
                                     'source_sha256':hashlib.sha256(Path(record['path']).read_bytes()).hexdigest(),
                                     'original_quality':record['quality'],**metadata,'label':record['label']})
        for split in SPLITS:write_json(stage/f'{split}.labels',info[split])
        write_json(stage/'manifest.json',manifest)
        (stage/'UPLOAD.txt').write_text('LOCAL ONLY. No data has been uploaded.\n'
            'Enable Explicit validation set in Edge Impulse before importing validation.\n'
            'Run from this bundle directory after account/project login:\n'
            'edge-impulse-uploader --info-file train.labels\n'
            'edge-impulse-uploader --info-file validation.labels\n'
            'Only after model choices are frozen:\n'
            'edge-impulse-uploader --info-file test.labels\n'
            'Do not rebalance/auto-split. Compare project counts and metadata with manifest.json.\n')
        # Reserve the destination exclusively; a racing export cannot overwrite it.
        output.mkdir()
        try:
            for path in stage.iterdir():shutil.move(str(path),output/path.name)
        except Exception:
            shutil.rmtree(output)
            raise
    finally:shutil.rmtree(stage)
    return {'output':str(output),'count':len(records),'counts':counts,'labels':list(labels),
            'merge':dict(gm.MERGE),'ready_for_training':manifest['ready_for_training'],'uploaded':False}


def verify_bundle(directory):
    root=Path(directory).resolve();manifest=json.loads((root/'manifest.json').read_text())
    if manifest.get('schema')!=1 or not manifest.get('files'):raise ValueError('Invalid bundle manifest')
    for item in manifest['files']:
        path=root/item['csv']
        if not path.resolve().is_relative_to(root):raise ValueError('CSV path escapes bundle')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=item['csv_sha256']:raise ValueError('CSV hash mismatch')
    expected={split:[] for split in SPLITS}
    for item in manifest['files']:
        split=item['mako_split']
        expected[split].append({'path':item['csv'],'category':CATEGORIES[split],
                               'label':{'type':'label','label':item['label']},
                               'metadata':{key:item[key] for key in ('session','mako_split','hand','capture_sha256','timing_source','accel_unit','gyro_unit')}})
    for split,files in expected.items():
        if json.loads((root/f'{split}.labels').read_text())!={'version':1,'files':files}:
            raise ValueError('Upload split/metadata mismatch')
    return {'verified':True,'count':len(manifest['files']),'uploaded':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    export=sub.add_parser('export');export.add_argument('--data',required=True);export.add_argument('--output',required=True)
    export.add_argument('--labels',default=','.join(gm.ALL_LABELS),help='comma-separated class set for the bundle')
    export.add_argument('--merge',default='',help='fold left-out classes into a kept one, e.g. hook=punch,uppercut=punch')
    verify=sub.add_parser('verify');verify.add_argument('--bundle',required=True)
    args=parser.parse_args()
    try:
        if args.command=='export':
            gm.set_labels(args.labels.split(','),dict(p.split('=',1) for p in args.merge.split(',') if p))
        result=export_dataset(args.data,args.output) if args.command=='export' else verify_bundle(args.bundle)
    except (ValueError,KeyError,TypeError,OSError) as exc:parser.exit(1,f'{exc}\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()

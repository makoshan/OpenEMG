from pathlib import Path
import subprocess,tempfile,json,hashlib,os
ROOT=Path(__file__).resolve().parent
GOLDEN='01010101010203040102030405060708c00001800000ffffff0000000000017fffff01e240fe1dc000002a'
def run(args,timeout):
    try:
        r=subprocess.run(args,text=True,capture_output=True,timeout=timeout)
        return dict(exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr,timed_out=False)
    except subprocess.TimeoutExpired as e:
        return dict(exit_code=None,stdout=(e.stdout or b'').decode() if isinstance(e.stdout,bytes) else e.stdout or '',stderr=(e.stderr or b'').decode() if isinstance(e.stderr,bytes) else e.stderr or '',timed_out=True)
report=dict(scope='bounded host runtime diagnostic, no hardware',source_sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in ('v12_codec.c','v12_codec.h','host_probe.c')},sanitizer_option_environment_present={k:k in os.environ for k in ('ASAN_OPTIONS','UBSAN_OPTIONS')},modes={})
with tempfile.TemporaryDirectory(prefix='v12-f01-diagnostic-') as t:
    t=Path(t);minimal=t/'minimal.c';minimal.write_text('int main(void){return 0;}\n')
    for name,flags in [('plain',[]),('ubsan',['-fsanitize=undefined']),('asan',['-fsanitize=address']),('combined',['-fsanitize=address,undefined'])]:
        row={};report['modes'][name]=row
        row['minimal_compile']=run(['clang','-std=c99',*flags,str(minimal),'-o',str(t/name)],30)
        if row['minimal_compile']['exit_code']!=0:continue
        row['minimal_run']=run([str(t/name)],5)
        if row['minimal_run']['exit_code']!=0:row['probe_skipped']='runtime minimal did not finish cleanly';continue
        row['probe_compile']=run(['clang','-std=c99','-Wall','-Wextra','-Werror',*flags,str(ROOT/'v12_codec.c'),str(ROOT/'host_probe.c'),'-o',str(t/(name+'-probe'))],30)
        if row['probe_compile']['exit_code']!=0:continue
        row['probe_golden']=run([str(t/(name+'-probe')),GOLDEN,'247'],5)
        row['golden_matches']=row['probe_golden']['exit_code']==0 and row['probe_golden']['stdout'].splitlines()==[GOLDEN,'-8388608,-1,0,1,8388607,123456,-123456,42']
        print(name,{'minimal_exit':row['minimal_run']['exit_code'],'golden_matches':row.get('golden_matches')},flush=True)
(ROOT/'sanitizer-diagnostic.json').write_text(json.dumps(report,indent=2)+'\n')

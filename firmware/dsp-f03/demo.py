"""用合成F01包运行实际回放CLI，出图；不读取任何设备或人体数据。"""
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'offline-f01'))
from codec import Packet, encode


def main():
    fs = 4000
    time = np.arange(fs*8)/fs
    raw = np.rint((.25+.05*(time>=3)+3e-5*np.sin(2*np.pi*100*time)+
                   2e-4*np.sin(2*np.pi*50*time))*8388608).astype(np.int32)
    events=[]
    for first in range(0, len(raw), 8):
        if fs*5 <= first < fs*5+16:
            continue
        frames=[]
        for code in raw[first:first+8]:
            frames.append(bytes.fromhex('c00000')+int(code).to_bytes(3, 'big', signed=True)*8)
        packet=Packet(first, first*250, 3 if first==0 else 1, tuple(frames))
        events.append(dict(packet_hex=encode(packet).hex(), mtu=247))
    with tempfile.TemporaryDirectory(prefix='v12-dsp-demo-') as tmp:
        tmp=Path(tmp)
        path=tmp/'events.jsonl'
        path.write_text(''.join(json.dumps(e)+'\n' for e in events))
        subprocess.run([sys.executable, str(ROOT/'replay.py'), str(path), str(tmp/'output'),
                        '--fs', str(fs), '--notch'], check=True, capture_output=True, timeout=30)
        result=json.loads((tmp/'output/result.json').read_text())
        rows=list(csv.DictReader((tmp/'output/samples.csv').open()))
    assert result['synthetic_sessions']==1 and result['real_label_sessions']==0
    assert result['missing_samples']==16 and result['accepted_samples']==len(raw)-16
    assert not result['rejected_events'] and result['timestamp_discontinuities']==0
    t=np.array([int(row['sequence'])/fs for row in rows])
    unfiltered=np.array([int(row['raw1'])/8388608. for row in rows])
    filtered=np.array([float(row['filtered_fs1']) for row in rows])
    ready=np.array([int(row['dsp_ready']) for row in rows])
    fig, ax=plt.subplots(3,1,figsize=(10,7))
    ax[0].plot(t,unfiltered,lw=.6,color='gray')
    ax[0].set(ylabel='Raw / full scale',title='Synthetic F01 replay through actual C DSP: 4 kSPS')
    ax[0].axvline(3,ls='--',color='black',lw=.8,label='Bias step')
    ax[0].legend(fontsize=8)
    zoom=(t>=7)&(t<7.1)
    ax[1].plot(t[zoom],(unfiltered[zoom]-np.mean(unfiltered[zoom]))*1e6,label='Raw: local mean removed',color='gray',lw=1)
    ax[1].plot(t[zoom],filtered[zoom]*1e6,label='C causal HP15 / LP600 / 50Hz Q30',color='#0072B2',lw=1)
    ax[1].set(ylabel='1e-6 of full scale',title='100 Hz small signal + 50 Hz interference; synthetic only')
    ax[1].legend(fontsize=8)
    ax[2].step(t,ready,where='post',lw=1,color='#0072B2')
    ax[2].axvspan(5,5.004,color='black',alpha=.3,label='16 samples missing')
    ax[2].set(xlabel='Time (s)',ylabel='DSP ready flag',ylim=(-.1,1.1),title='Reset guard after startup and gap (not a physical settling guarantee)')
    ax[2].legend(fontsize=8)
    for a in ax:
        a.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(ROOT/'demo.png',dpi=150)
    plt.close(fig)
    result['source_sha256']['demo.py']=hashlib.sha256((ROOT/'demo.py').read_bytes()).hexdigest()
    result['plot_sha256']=hashlib.sha256((ROOT/'demo.png').read_bytes()).hexdigest()
    result['temporary_samples_retained']=False
    (ROOT/'demo-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(synthetic=True,frames=result['accepted_samples'],missing=result['missing_samples'],
                         resets=len(result['resets']),hardware_tested=False),ensure_ascii=False))


if __name__=='__main__':
    main()

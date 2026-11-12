"""Synthetic differential receiver checks; no transport or device operations."""
from pathlib import Path
import hashlib,json,random,subprocess,tempfile
from codec import Packet,Receiver,encode
ROOT=Path(__file__).resolve().parent
FRAME=bytes.fromhex('c00001800000ffffff0000000000017fffff01e240fe1dc000002a')
def packet(seq,ts,flags=1,n=1):return encode(Packet(seq,ts,flags,(FRAME,)*n))
def scenario(allow_real):
    r=Receiver(allow_real); commands=[];expected=[]
    def disconnect():r.disconnect();commands.append('D')
    def feed(data,mtu=247):
        try:r.receive(data,mtu);accepted=1
        except ValueError:accepted=0
        commands.append(f'{mtu} {data.hex()}')
        expected.append([accepted,int(r.expected is not None),r.expected or 0,r.last_timestamp or 0,int(bool(r.synthetic)),r.accepted_samples,r.missing_samples,r.reordered,r.malformed,r.sessions])
    feed(packet(0,0));feed(packet(0,0,3,2));feed(packet(5,10,1,2))
    feed(packet(5,11));feed(packet(7,10));feed(packet(7,12,0));feed(packet(0,0,3))
    feed(b'broken');feed(packet(7,12));feed(packet(8,13),23);feed(packet(8,13))
    disconnect();feed(packet(9,20));feed(packet(0,0,2));feed(packet(0,0,3))
    disconnect();feed(packet(0,0,3))
    # Reach wrap through valid forward gaps, without directly seeding receiver internals.
    feed(packet(0x7fffffff,1));feed(packet(0xfffffffe,2,1,2));feed(packet(0,3))
    feed(packet(0x80000001,4));feed(packet(1,4)) # exact half-range rejection then recovery
    disconnect();feed(packet(0,0,3))
    rng=random.Random(1202)
    for _ in range(500):
        action=rng.randrange(8)
        if action==0:disconnect();feed(packet(0,0,3));continue
        seq=r.expected or 0;ts=(r.last_timestamp or 0)+1
        if action==1:feed(packet(seq,ts,1,rng.randrange(1,9)))
        elif action==2:feed(packet((seq+rng.randrange(1,20))&0xffffffff,ts))
        elif action==3:feed(packet((seq-1)&0xffffffff,ts))
        elif action==4:feed(packet(seq,r.last_timestamp or 0))
        elif action==5:feed(packet(0,0,3))
        elif action==6:feed(packet(seq,ts,0))
        else:feed(packet(seq,ts)[:-rng.randrange(1,20)])
    return '\n'.join(commands)+'\n',expected

def main():
    report={'status':'SYNTHETIC_RECEIVER_CHECKS_PASSED','hardware_tested':False,'target_firmware_built':False,'runs':[]}
    with tempfile.TemporaryDirectory(prefix='v12-receiver-') as tmp:
        tmp=Path(tmp)
        for sanitizer in (False,True):
            binary=tmp/('receiver-ubsan' if sanitizer else 'receiver')
            cmd=['clang','-std=c99','-Wall','-Wextra','-Werror',*(['-fsanitize=undefined','-fno-sanitize-recover=all'] if sanitizer else []),*[str(ROOT/f) for f in ('v12_codec.c','v12_receiver.c','receiver_probe.c')],'-o',str(binary)]
            subprocess.run(cmd,check=True,timeout=30)
            for allow_real in (False,True):
                commands,expected=scenario(allow_real)
                result=subprocess.run([str(binary),str(int(allow_real))],input=commands,text=True,capture_output=True,check=True,timeout=5)
                actual=[[int(x) for x in line.split(',')] for line in result.stdout.splitlines()]
                assert actual==expected,(sanitizer,allow_real,next((i for i,(a,b) in enumerate(zip(actual,expected)) if a!=b),None))
                assert 'runtime error:' not in result.stderr
                report['runs'].append({'sanitizer':'UBSan' if sanitizer else 'none','allow_real':allow_real,'packet_transitions':len(expected),'all_ten_state_fields_match':True})
        report['negative_controls']=[]
        for label,old,new in (
            ('reorder guard removed','delta>=UINT32_C(0x80000000)','0'),
            ('timestamp guard removed','p.timestamp_us<=r->last_timestamp','0')):
            broken=tmp/'broken.c';broken.write_text((ROOT/'v12_receiver.c').read_text().replace(old,new))
            binary=tmp/'broken'
            subprocess.run(['clang','-std=c99','-Wall','-Wextra','-Werror','-I',str(ROOT),str(ROOT/'v12_codec.c'),str(broken),str(ROOT/'receiver_probe.c'),'-o',str(binary)],check=True,timeout=30)
            commands,expected=scenario(False)
            result=subprocess.run([str(binary),'0'],input=commands,text=True,capture_output=True,check=True,timeout=5)
            actual=[[int(x) for x in line.split(',')] for line in result.stdout.splitlines()]
            assert actual!=expected,'negative control escaped differential checks'
            report['negative_controls'].append({'mutation':label,'detected':True})
        # Compiler availability does not imply SDK, libc, board, link or pin validation.
        report['arm_objects']=[]
        for source in ('v12_codec.c','v12_receiver.c'):
            result=subprocess.run(['arm-none-eabi-gcc','-std=c99','-Wall','-Wextra','-Werror','-ffreestanding','-mcpu=cortex-m4','-mthumb','-c',str(ROOT/source),'-o',str(tmp/(source+'.o'))],text=True,capture_output=True,timeout=30)
            report['arm_objects'].append({'source':source,'passed':result.returncode==0,'exit_code':result.returncode,'diagnostic':result.stderr})
        report['arm_check']='object compilation only; missing libc headers may block codec; no SDK or linked target firmware'
    report['checks']=['first-session requirement','duplicate/overlap and exact-half-range rejection','monotonic timestamps','source isolation and explicit real-source opt-in','malformed/MTU rejection preserves sample state','valid next packet after rejection','disconnect preserves cumulative counters and resets session state','uint32 wrap through valid packets','output packet untouched on rejection']
    report['source_sha256']={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in ('codec.py','v12_codec.c','v12_codec.h','v12_receiver.c','v12_receiver.h','receiver_probe.c','receiver_check.py')}
    (ROOT/'receiver-results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()

"""Host C/Python protocol interoperability tests. Every fixture is synthetic."""
from pathlib import Path
import os,shutil,subprocess,tempfile,json,hashlib,random,argparse
from codec import *
ROOT=Path(__file__).resolve().parent

def rejected(fn):
    try:fn()
    except ValueError:return
    raise AssertionError('bad input accepted')

def main(sanitizer=None):
    checks=[]
    with tempfile.TemporaryDirectory(prefix='v12-f01-host-') as t:
        binary=Path(t)/'probe'
        subprocess.run([os.environ.get('CC') or shutil.which('clang') or 'cc','-std=c99','-Wall','-Wextra','-Werror','-g',*(['-fsanitize=undefined','-fno-sanitize-recover=all'] if sanitizer=='undefined' else []),str(ROOT/'v12_codec.c'),str(ROOT/'host_probe.c'),'-o',str(binary)],check=True,timeout=30)
        frame=bytes.fromhex('c00001800000ffffff0000000000017fffff01e240fe1dc000002a')
        values=(-8388608,-1,0,1,8388607,123456,-123456,42)
        golden=bytes.fromhex('01010101010203040102030405060708')+frame
        assert decode_frame(frame)==(0xc00001,values)
        p=decode(golden);assert p.sequence==0x04030201 and p.timestamp_us==0x0807060504030201 and p.flags==SYNTHETIC
        assert encode(p)==golden
        result=subprocess.run([str(binary),golden.hex(),'247'],text=True,capture_output=True,check=True,timeout=5)
        assert result.stdout.splitlines()==[golden.hex(),','.join(map(str,values))]
        checks+=['clang C99 warning-as-error host build'+(' with UBSan' if sanitizer else ''),'hand-written 24-bit signed limits and status preservation','hand-written little-endian header','C/Python exact golden bytes interoperability']
        for mtu,count in ((247,8),(185,6)):
            packet=Packet(0,500,3,(frame,)*count);data=encode(packet,mtu)
            assert len(data)==16+27*count and decode(data,mtu)==packet
            result=subprocess.run([str(binary),data.hex(),str(mtu)],capture_output=True,text=True,check=True,timeout=5)
            assert result.stdout.splitlines()[0]==data.hex()
            rejected(lambda:encode(Packet(0,500,3,(frame,)*(count+1)),mtu))
        assert capacity(23)==0
        rejected(lambda:encode(Packet(0,0,3,(frame,)),23))
        checks.append('MTU247=8, MTU185=6, MTU23 rejects one frame without silent truncation')
        bad=[golden[:i] for i in range(len(golden))]+[golden+b'\x00']
        for index,value in [(0,2),(1,2),(2,0),(2,9),(3,0x80),(3,3)]:
            x=bytearray(golden);x[index]=value;bad.append(bytes(x))
        rng=random.Random(1201);bad.extend(bytes(rng.randrange(256) for _ in range(rng.randrange(0,232))) for _ in range(50))
        for data in bad:
            rejected(lambda:decode(data))
            r=subprocess.run([str(binary),data.hex(),'247'],capture_output=True,text=True,timeout=5)
            assert r.returncode!=0 and 'AddressSanitizer' not in r.stderr and 'runtime error:' not in r.stderr
        checks.append(f'{len(bad)} truncated/trailing/bad-version/type/count/flags/session and deterministic garbage inputs rejected by both C/Python')
        rejected(lambda:decode(golden,23));rejected(lambda:signed24(b'\0\0'));rejected(lambda:encode(Packet(-1,0,1,(frame,))))
        rejected(lambda:encode(Packet(0,-1,1,(frame,))))
        rejected(lambda:encode(Packet(0,0,-1,(frame,))))
        for mtu in (0,22,518,float('nan'),True):rejected(lambda:capacity(mtu))
        r=Receiver()
        packet=lambda seq,ts,flags=1,n=1:encode(Packet(seq,ts,flags,(frame,)*n))
        rejected(lambda:r.receive(packet(0,0)))
        r.receive(packet(0,1000,3,2));r.receive(packet(5,4000,1,2))
        assert r.missing_samples==3 and r.accepted_samples==4
        rejected(lambda:r.receive(packet(5,4500)));assert r.reordered==1
        rejected(lambda:r.receive(packet(7,3000)))
        rejected(lambda:r.receive(packet(7,4500,0)))
        rejected(lambda:r.receive(packet(0,0,3)))
        try:r.receive(b'broken')
        except ValueError:pass
        assert r.malformed==1 and r.accepted_samples==4 and r.expected==7
        r.disconnect();rejected(lambda:r.receive(packet(7,5000)))
        r.receive(packet(0,0,3));assert r.sessions==2
        # Seed the otherwise ~25-day counter boundary, without fabricating preceding samples.
        r.expected=0xfffffffe;r.last_timestamp=0
        r.receive(packet(0xfffffffe,1000,1,2));r.receive(packet(0,2000))
        assert r.expected==1
        rejected(lambda:Receiver().receive(packet(0,0,2)))
        checks+=['missing-sample count without filling','duplicate/reorder rejected','nonmonotonic timestamp rejected','explicit reconnect/session reset','uint32 sample-sequence wrap','synthetic/real mixing and default real-source rejection','malformed packet counter and state unchanged']
        report=dict(status='HOST_PROTOCOL_TESTS_PASSED',scope='synthetic fixtures and portable C99 only',checks=checks,source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'codec.py',ROOT/'v12_codec.h',ROOT/'v12_codec.c',ROOT/'host_probe.c',ROOT/'check.py']},not_run=['nRF52840 cross compile','ADS/XIAO pin map and startup hardware','DRDY SPI acquisition','IMU protocol configuration','BLE transport and ring-buffer backpressure','30 minute real stream','electrical safety'],firmware_target_built=False,hardware_tested=False,sanitizer_runtime='UBSan full checks passed' if sanitizer else 'not run in this command',asan_runtime='minimal main timed out; prior failure preserved')
        os.environ.get('WRITE_RESULTS')=='1' and (ROOT/('results-ubsan.json' if sanitizer else 'results.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--sanitizer',choices=['undefined'])
    main(parser.parse_args().sanitizer)

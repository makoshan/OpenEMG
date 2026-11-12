"""合成原始码→真实C队列/F01包→F03实际回放命令；无设备。"""
from pathlib import Path
import hashlib
import json
import math
import subprocess
import sys
import tempfile
from check import ROOT, compile_probe, probe


def main():
    results = []
    with tempfile.TemporaryDirectory(prefix='v12-f04-e2e-') as temporary:
        binary = Path(temporary)/'probe'
        compile_probe(binary)
        for fs in (2000,4000):
            period, timestamp, sequence = 1000000//fs, 1000000, 0
            commands = []
            # 留出足够恢复段；一次16样本缺口必须显式保留在包序号/回放中。
            for block in range(150):
                if block == 75:
                    commands.append('K 16')
                    sequence += 16
                    timestamp += 16*period
                for _ in range(8):
                    value = int(100000+40000*math.sin(2*math.pi*100*sequence/fs))
                    commands.append(f'P {timestamp} {value}')
                    sequence += 1
                    timestamp += period
                commands += ['N 247','C']
            events = [dict(packet_hex=packet.hex(),mtu=247)
                      for _,packet in probe(binary,fs,commands) if packet]
            digest = hashlib.sha256(json.dumps(events,sort_keys=True).encode()).hexdigest()[:16]
            directory = ROOT/'artifacts'/f'e2e-{fs}-{digest}'
            directory.mkdir(parents=True,exist_ok=True)
            source = directory/'events.jsonl'
            source.write_text(''.join(json.dumps(event)+'\n' for event in events))
            # 回放拒绝覆写已有证据；重复检查在新的本任务临时目录运行。
            output = Path(temporary)/f'replay-{fs}'
            command = [sys.executable,str(ROOT.parent/'dsp-f03/replay.py'),str(source),str(output),'--fs',str(fs)]
            run = subprocess.run(command,text=True,capture_output=True,timeout=30)
            (directory/'replay.log').write_text(run.stdout+run.stderr)
            assert run.returncode == 0, run.stderr
            result = json.loads((output/'result.json').read_text())
            assert result['accepted_samples'] == 1200 and result['accepted_packets'] == 150
            assert result['missing_samples'] == 16 and result['timestamp_discontinuities'] == 0
            assert result['synthetic_sessions'] == 1 and result['real_label_sessions'] == 0
            assert [item['reason'] for item in result['resets']] == ['session','gap']
            import shutil
            for name in ['result.json','samples.csv']:
                shutil.copyfile(output/name,directory/name)
            results.append(dict(fs_Hz=fs,source='synthetic_host',accepted_samples=1200,
                                missing_samples=16,exit_code=run.returncode,physical_device=False,
                                input_sha256=result['input_sha256'],samples_sha256=result['samples_sha256'],
                                evidence=str(directory.relative_to(ROOT))))
    (ROOT/'e2e-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(results,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()

"""主机队列差分检查；合成输入，不访问USB、BLE或AFE。"""
from pathlib import Path
import hashlib
import json
import random
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'offline-f01'))
from codec import Packet, capacity, decode, decode_frame, encode
from sdk_patch import patched_bluefruit


def compile_probe(output, source=None, sanitizer=False):
    command = ['clang', '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror', '-ffp-contract=off',
               '-I', str(ROOT / 'src'), str(ROOT / 'host_probe.c'),
               str(source or ROOT / 'src/v12_stream.c'), str(ROOT / 'src/codec.c'),
               str(ROOT / 'src/dsp.c'), '-o', str(output)]
    if sanitizer:
        command += ['-fsanitize=undefined', '-fno-sanitize-recover=all']
    subprocess.run(command, check=True, capture_output=True, text=True)


def probe(binary, fs, commands):
    result = subprocess.run([str(binary), str(fs)], input='\n'.join(commands)+'\n',
                            text=True, capture_output=True, timeout=15, check=True)
    assert not result.stderr, result.stderr
    rows = [line.split(',') for line in result.stdout.splitlines()]
    assert len(rows) == len(commands)
    return [(tuple(map(int, row[:9])), bytes.fromhex(row[9])) for row in rows]


class Reference:
    """Python列表队列与独立F01编码器；不复制C的环形索引。"""
    def __init__(self, fs):
        self.fs = fs
        self.queue = []
        self.pending = b''
        self.pending_count = 0
        self.sequence = self.produced = self.dropped = self.skipped = 0
        self.sent_packets = self.sent_samples = self.processed = self.ready = 0
        self.started = False

    def run(self, command):
        fields = command.split()
        op = fields[0]
        rc, data = 0, b''
        if op == 'I':
            self.__init__(self.fs)
        elif op == 'P':
            timestamp, base = map(int, fields[1:])
            if base < -8388608 or base + 7 > 8388607:
                rc = -1
            else:
                guard = 208 if self.fs == 2000 else 415
                self.ready = int(self.processed >= guard)
                self.processed = min(guard, self.processed + 1)
                sequence = self.sequence
                self.sequence = (self.sequence + 1) & 0xffffffff
                self.produced += 1
                if len(self.queue) == 128:
                    self.dropped += 1
                else:
                    frame = b'\xc0\0\0' + b''.join((base+ch).to_bytes(3, 'big', signed=True) for ch in range(8))
                    self.queue.append((sequence, timestamp, frame))
        elif op == 'K':
            count = int(fields[1])
            if count and not self.produced:
                rc = -1
            elif count:
                self.sequence = (self.sequence + count) & 0xffffffff
                self.skipped += count
                self.processed = self.ready = 0
        elif op == 'N':
            mtu = int(fields[1])
            if not 46 <= mtu <= 517 or (self.pending and len(self.pending) > mtu-3):
                rc = -2
            elif self.pending:
                data = self.pending
            elif not self.queue:
                rc = -3
            else:
                selected = self.queue[:capacity(mtu)]
                contiguous = [selected[0]]
                for sample in selected[1:]:
                    previous = contiguous[-1]
                    if sample[0] != (previous[0]+1) & 0xffffffff or sample[1]-previous[1] != 1000000//self.fs:
                        break
                    contiguous.append(sample)
                self.pending_count = len(contiguous)
                self.pending = encode(Packet(contiguous[0][0], contiguous[0][1], 1 if self.started else 3,
                                             tuple(v[2] for v in contiguous)), mtu)
                data = self.pending
        elif op == 'C':
            if not self.pending:
                rc = -1
            else:
                del self.queue[:self.pending_count]
                self.sent_samples += self.pending_count
                self.sent_packets += 1
                self.started = True
                self.pending = b''
                self.pending_count = 0
        else:
            raise AssertionError(command)
        return ((rc, len(self.queue), self.produced, self.dropped, self.skipped,
                 self.sent_packets, self.sent_samples, self.processed, self.ready), data)


def compare(binary, fs, commands):
    reference = Reference(fs)
    for index, (command, actual) in enumerate(zip(commands, probe(binary, fs, commands))):
        expected = reference.run(command)
        assert actual == expected, (fs, index, command, actual, expected)
        if actual[1]:
            packet = decode(actual[1], int(command.split()[1]))
            assert all(decode_frame(frame)[0] == 0xc00000 for frame in packet.frames)


def scenario(fs):
    period = 1000000//fs
    commands = ['N 247', 'C', 'K 1', 'N 23', 'N 45', 'N 518', 'P 1000 -8388609', 'P 1000 8388601']
    commands += [f'P {1000+i*period} {-8388608+i}' for i in range(8)]
    commands += ['N 247', 'N 185', 'N 517', 'C', 'C']
    # 首包未提交而入队/溢出，必须保留同一字节串和序号0。
    commands += ['I'] + [f'P {1000+i*period} {i}' for i in range(8)] + ['N 247']
    commands += [f'P {1000+i*period} {i}' for i in range(8,140)] + ['N 247', 'C']
    commands += [f'P {1000+i*period} {i}' for i in range(140,148)]
    commands += ['N 247', 'C']*16
    # 故意缺样、时间跳变和32位序号回卷，不得跨缺口合包。
    commands += ['I', 'P 1000 1', 'K 3', f'P {1000+4*period} 2', 'N 247', 'C', 'N 247', 'C']
    commands += ['I', 'P 1000 1', f'P {1000+10*period} 2', 'N 247', 'C', 'N 247', 'C']
    commands += ['I', 'P 1000 1', 'N 247', 'C', 'K 4294967294', 'P 2000 -1', f'P {2000+period} -2', 'N 247', 'C']
    # 零缺样必须是无操作；正缺样必须重置恢复标记。
    commands += ['I'] + [f'P {1000+i*period} 2' for i in range(fs//5)]
    commands += ['K 0', 'K 1', f'P {1000+(fs//5+1)*period} 3']
    rng = random.Random(fs)
    commands += ['I']
    timestamp = 1000
    for _ in range(2400):
        choice = rng.randrange(12)
        if choice < 6:
            commands.append(f'P {timestamp} {rng.randrange(-8388608,8388601)}')
            timestamp += period
        elif choice < 8:
            commands.append(f'N {rng.choice([23,45,46,185,247,517,518])}')
        elif choice < 10:
            commands.append('C')
        elif choice == 10:
            count = rng.randrange(6)
            commands.append(f'K {count}')
            timestamp += count*period
        else:
            commands.append('I')
    return commands


def sdk_lifecycle(source, folder):
    text = source.decode()
    disconnect = text.split('case BLE_GAP_EVT_DISCONNECTED:',1)[1].split('case BLE_GAP_EVT_RSSI_CHANGED:',1)[0]
    release = disconnect[disconnect.index('      delete _connection[conn_hdl];'):].split('    }',1)[0]
    dispatch = text[text.index('  // Periph event handler'):text.index('  // Discovery Event Handler')]
    # 用存活标记代替真正释放；提取真实删除/分发语句，确定性检出释放后的角色访问。
    release = release.replace('delete _connection[conn_hdl]', 'release_connection(_connection[conn_hdl])')
    cpp = '''#include <cstdlib>
static bool bad=false;
enum { BLE_GAP_ROLE_PERIPH=1, BLE_GAP_ROLE_CENTRAL=2 };
struct Connection { bool alive=true; int getRole() { if(!alive) bad=true; return 1; } };
static void release_connection(Connection *p) { p->alive=false; }
struct Handler { void _eventHandler(void*) {} } Periph,Central;
int main() { Connection object; Connection *_connection[]={&object}; Connection *conn=&object;
unsigned conn_hdl=0; void *evt=nullptr;
''' + release + dispatch + '\nreturn bad?2:0; }\n'
    path = folder/'sdk-lifecycle.cpp'
    path.write_text(cpp)
    binary = folder/'sdk-lifecycle'
    subprocess.run(['clang++','-std=c++11','-Wall','-Wextra','-Werror',str(path),'-o',str(binary)],check=True,capture_output=True)
    return subprocess.run([str(binary)],capture_output=True).returncode


def main():
    result = {'source': 'synthetic_host', 'physical_device': False, 'profiles': {}, 'negative_controls': []}
    with tempfile.TemporaryDirectory(prefix='v12-f04-check-') as folder:
        folder = Path(folder)
        for sanitizer in (False, True):
            binary = folder/('ubsan' if sanitizer else 'ordinary')
            compile_probe(binary, sanitizer=sanitizer)
            for fs in (2000,4000):
                commands = scenario(fs)
                compare(binary, fs, commands)
                result['profiles'][f'{fs}_{"ubsan" if sanitizer else "ordinary"}'] = len(commands)
        source = (ROOT/'src/v12_stream.c').read_text()
        mutants = {
            '合包跨缺口': source.replace('count=i; break;', 'break;'),
            '零缺样错误清状态': source.replace(' if(!count) return V12_STREAM_OK;\n', ''),
            '首包缺会话标记': source.replace('1u|(s->started?0u:2u)', '1u'),
        }
        for name, content in mutants.items():
            assert content != source
            path = folder/(str(len(result['negative_controls']))+'.c')
            path.write_text(content)
            binary = folder/(path.stem+'-probe')
            compile_probe(binary, path)
            try:
                compare(binary, 2000, scenario(2000))
            except AssertionError:
                result['negative_controls'].append(name)
            else:
                raise AssertionError('故意破坏未检出: '+name)
        # 用本机实际SDK针脚源，故意改D0，必须被构建前检查拒绝。
        board = Path.home()/'.platformio/packages/framework-arduinoadafruitnrf52-seeed/variants/Seeed_XIAO_nRF52840_Sense/variant.cpp'
        check = ROOT/'verify_board.py'
        subprocess.run([sys.executable,str(check),str(board)], check=True, capture_output=True)
        changed = board.read_text().replace('  2,', '  4,', 1)
        assert changed != board.read_text()
        path = folder/'bad-variant.cpp'
        path.write_text(changed)
        failed = subprocess.run([sys.executable,str(check),str(path)], capture_output=True)
        assert failed.returncode != 0
        result['negative_controls'].append('实际板包D0错脚')
        result['sdk_variant_sha256'] = hashlib.sha256(board.read_bytes()).hexdigest()
        bluefruit = board.parents[2]/'libraries/Bluefruit52Lib/src/bluefruit.cpp'
        sdk_source = bluefruit.read_bytes()
        assert sdk_lifecycle(patched_bluefruit(sdk_source),folder) == 0
        assert sdk_lifecycle(sdk_source,folder) == 2
        try:
            patched_bluefruit(sdk_source+b'\n')
        except ValueError:
            pass
        else:
            raise AssertionError('未审查SDK必须拒绝')
        result['negative_controls'] += ['原SDK释放后角色访问','未审查SDK禁止套补丁']
    result['files_sha256'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in sorted(ROOT.rglob('*')) if p.is_file() and p.suffix in ('.c','.h','.cpp','.py') and not ({'.pio','artifacts'} & set(p.parts)) and p.name != 'harness.cpp'}
    (ROOT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()

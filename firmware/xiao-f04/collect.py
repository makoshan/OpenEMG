"""核构建输入与真实ELF/HEX/DFU包，保留本地产物；不刷机。"""
from pathlib import Path
import binascii
import hashlib
import json
import subprocess
import tempfile
import zipfile
from sdk_patch import patched_bluefruit

ROOT = Path(__file__).resolve().parent
SDK = Path.home()/'.platformio/packages/framework-arduinoadafruitnrf52-seeed'
TOOL = Path.home()/'.platformio/packages/toolchain-gccarmnoneeabi/bin'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def validate_inputs(record):
    for name, expected in record['source_sha256'].items():
        if name == 'sdk/variant.cpp':
            actual = (SDK/'variants/Seeed_XIAO_nRF52840_Sense/variant.cpp').read_bytes()
        elif name.startswith('sdk/bluefruit.cpp.'):
            actual = (SDK/'libraries/Bluefruit52Lib/src/bluefruit.cpp').read_bytes()
            if name.endswith('.patched'):
                actual = patched_bluefruit(actual)
        else:
            actual = (ROOT.parent/name).read_bytes()
        if sha(actual) != expected:
            raise ValueError('源码已变，旧构建过期: '+name)
    signature = sha((json.dumps(record['source_sha256'],sort_keys=True)+record['environment']).encode())[:16]
    if signature != record['build_id']:
        raise ValueError('构建ID和输入清单不符')


def intel_hex(text):
    memory, base, ended = {}, 0, False
    for line in text.splitlines():
        if ended or not line.startswith(':'):
            raise ValueError('非法HEX记录')
        record = bytes.fromhex(line[1:])
        if len(record) != record[0]+5 or sum(record)&255:
            raise ValueError('HEX校验和/长度错误')
        count, address, kind = record[0], int.from_bytes(record[1:3],'big'), record[3]
        data = record[4:4+count]
        if kind == 0:
            for offset, byte in enumerate(data):
                key = base+address+offset
                if key in memory:
                    raise ValueError('HEX地址重复')
                memory[key] = byte
        elif kind == 1:
            if count or address:
                raise ValueError('非法HEX结束记录')
            ended = True
        elif kind in (2,4):
            if count != 2:
                raise ValueError('非法HEX地址记录')
            base = int.from_bytes(data,'big') << (4 if kind == 2 else 16)
        elif kind not in (3,5):
            raise ValueError('不支持HEX记录')
    if not ended or not memory:
        raise ValueError('HEX不完整')
    start, end = min(memory), max(memory)+1
    if start != 0x27000 or end > 0xed000:
        raise ValueError('应用镜像越过已核链接区域')
    return start, bytes(memory.get(key,255) for key in range(start,end))


def main():
    records = []
    for environment, fs in [('synthetic_2k',2000),('synthetic_4k',4000)]:
        directory = ROOT/'.pio/build'/environment
        inputs = json.loads((directory/'generated/build-inputs.json').read_text())
        validate_inputs(inputs)
        # 过期清单必须拒绝，不能只检查文件存在。
        bad = json.loads(json.dumps(inputs))
        bad['source_sha256']['firmware-f04/src/main.cpp'] = '0'*64
        try:
            validate_inputs(bad)
        except ValueError:
            pass
        else:
            raise AssertionError('过期清单未拒绝')
        elf = directory/'firmware.elf'
        symbols = subprocess.check_output([str(TOOL/'arm-none-eabi-nm'),str(elf)],text=True)
        for symbol in ['v12_encode','v12_dsp_frame','v12_stream_push','v12_stream_peek']:
            if not any(line.split()[-1] == symbol for line in symbols.splitlines()):
                raise ValueError('ELF未链接预期模块: '+symbol)
        with tempfile.TemporaryDirectory(prefix='v12-f04-rodata-') as temporary:
            rodata = Path(temporary)/'rodata'
            # 此链接脚本把只读数据并入.text；另给输出ELF，避免工具改写原镜像。
            subprocess.run([str(TOOL/'arm-none-eabi-objcopy'),'--dump-section',f'.text={rodata}',str(elf),str(Path(temporary)/'copy.elf')],check=True,capture_output=True)
            if inputs['build_id'].encode() not in rodata.read_bytes():
                raise ValueError('运行镜像未包含当前构建ID')
        start, binary = intel_hex((directory/'firmware.hex').read_text())
        with zipfile.ZipFile(directory/'firmware.zip') as archive:
            if archive.testzip() is not None:
                raise ValueError('DFU压缩包损坏')
            application = json.loads(archive.read('manifest.json'))['manifest']['application']
            zipped = archive.read(application['bin_file'])
            if zipped != binary:
                raise ValueError('HEX和DFU二进制不一致')
            crc = binascii.crc_hqx(binary,65535)
            init = application['init_packet_data']
            if init['firmware_crc16'] != crc or init['softdevice_req'] != [0x123]:
                raise ValueError('DFU的CRC/SoftDevice版本不匹配')
        sizes = subprocess.check_output([str(TOOL/'arm-none-eabi-size'),'-A',str(elf)],text=True).splitlines()
        sections = {line.split()[0]:int(line.split()[1]) for line in sizes if line.startswith('.')}
        flash = sum(sections.get(name,0) for name in ['.text','.data','.rodata','.text.align','.ARM.exidx'])
        ram = sum(sections.get(name,0) for name in ['.data','.bss','.noinit'])
        record = dict(environment=environment,fs_Hz=fs,build_id=inputs['build_id'],profile='F04_SYNTHETIC',
                      afe_enabled=False,flashed=False,physical_device_verified=False,
                      flash_bytes=flash,static_ram_bytes=ram,linker_heap_region_bytes=sections.get('.heap',0),application_start=hex(start),
                      application_binary_bytes=len(binary),dfu_crc16=crc,
                      source_sha256=inputs['source_sha256'],artifacts={})
        destination = ROOT/'artifacts'/(environment+'-'+inputs['build_id'])
        destination.mkdir(parents=True,exist_ok=True)
        for name in ['firmware.elf','firmware.hex','firmware.zip']:
            payload = (directory/name).read_bytes()
            target = destination/name
            if target.exists() and target.read_bytes() != payload:
                raise ValueError('同构建ID存在不同产物，拒绝覆盖: '+str(target))
            target.write_bytes(payload)
            record['artifacts'][name] = dict(bytes=len(payload),sha256=sha(payload),path=str(target.relative_to(ROOT)))
        (destination/'manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
        records.append(record)
    result = dict(state='已实现未验收',profiles=records,negative_controls=['两环境旧源码清单均被拒绝'])
    (ROOT/'build-manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps([{key:record[key] for key in ['environment','build_id','flash_bytes','static_ram_bytes','flashed']} for record in records],ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()

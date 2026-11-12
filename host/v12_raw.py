"""V12 原始记录格式；页面和 BLE 入口共用，不依赖显示或训练库。"""
from dataclasses import asdict, is_dataclass
import hashlib
import json
from pathlib import Path


class RawArchive:
    """诊断记录：原包与断连事件可直接交给现有 dsp-f03/replay.py（仅协议 1；adc_profile.transport_protocol 为 2/3 的是 pack16 差分包，replay 会整体拒收，要先用 codec.decode_pack16 还原）。单调用者串行写入。"""
    def __init__(self, directory, profile, codec, allow_real, voltage_at=None):
        directory = Path(directory)
        adc_profile = asdict(profile) if is_dataclass(profile) else dict(profile)
        if voltage_at is None:
            afe = adc_profile.get('afe') or ('ADS1292' if adc_profile.get('vref_V') in (2.42, 4.033) else 'ADS1298')
            if afe not in ('ADS1298', 'ADS1292'):
                raise ValueError(f'未知 AFE 型号：{afe!r}')
            voltage_at = f'{afe} PGA input'
        elif voltage_at not in ('ADS1298 PGA input', 'ADS1292 PGA input'):
            raise ValueError(f'未知输入折算位置：{voltage_at!r}')
        metadata = dict(format='V12 raw events v1', adc_profile=adc_profile,
                        voltage_at=voltage_at, calibration_verified=False,
                        hardware_verified=False, allow_real=allow_real,
                        source_authentication=False,
                        codec_sha256=hashlib.sha256(Path(codec.__file__).read_bytes()).hexdigest())
        # 整个目录必须是新的，防止把两次佩戴/两套刻度混进同一个文件。
        directory.mkdir(parents=True, exist_ok=False)
        (directory / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
        self.file = (directory / 'events.jsonl').open('x', encoding='utf-8')
        self.directory = directory
        self.imu_file = None

    def enable_imu(self, profile):
        metadata_path = self.directory / 'metadata.json'
        metadata = json.loads(metadata_path.read_text())
        metadata['imu_profile'] = dict(profile)
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n')
        self.imu_file = (self.directory / 'imu-events.jsonl').open('x', encoding='utf-8')

    def write_imu(self, event):
        self.imu_file.write(json.dumps(event, ensure_ascii=False)+'\n')
        self.imu_file.flush()

    def write(self, event):
        self.file.write(json.dumps(event, ensure_ascii=False) + '\n')
        # 每次写入刷新 Python 缓冲；这是电脑端记录，不保证断电落盘或机内存储。
        self.file.flush()

    def close(self):
        self.file.close()
        if self.imu_file is not None:
            self.imu_file.close()

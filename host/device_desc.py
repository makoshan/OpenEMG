"""设备描述：`devices/<id>.json` 的加载与校验（EMG_STUDIO_V2_PLAN 附录 B.1）。

设备差异是数据不是代码：通道数、采样率、每路转换、能力都从这里来；页面和 Session 只问能力，不问 kind。
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEVICES_DIR = HERE / 'devices'
TRANSPORTS = ('serial', 'ble', 'usb', 'replay', 'fake')
DECODERS = ('wl8', 'wl18', 'v12', 'c08b', 'cheez')
SENSORS = ('EMG', 'ACC', 'GYR', 'CUSTOM')
CAPABILITIES = ('record', 'realtime', 'train', 'cursor', 'ab', 'imu')
REQUIRED = ('id', 'name', 'transport', 'decoder', 'n_channels', 'fs_Hz', 'channels')


class DescError(ValueError):
    pass


@dataclass
class DeviceDesc:
    id: str
    name: str
    transport: dict
    decoder: str
    n_channels: int
    fs_Hz: int
    channels: list
    fs_options: list = field(default_factory=list)
    resolution_bits: int = 16
    imu: dict | None = None
    digital_in: int = 0
    battery: bool = False
    electrode_layout: str = 'custom'
    capabilities: dict = field(default_factory=dict)
    limits: dict = field(default_factory=dict)
    notes: str = ''

    def cap(self, name):
        if name not in CAPABILITIES:
            raise DescError(f'未知能力 {name}')
        return bool(self.capabilities.get(name, False))

    def gains(self):
        return [float(c.get('gain', 1.0)) for c in self.channels]

    def offsets(self):
        return [float(c.get('offset', 0.0)) for c in self.channels]

    def labels(self):
        return [c['label'] for c in self.channels]

    def to_json(self):
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    def header(self, **extra):
        """OpenSignals .txt 第二行 / .h5 根 attrs 用的同一份头（B.2）。"""
        return {
            'device': self.id, 'device name': self.name, 'device connection': self.transport.get('kind', ''),
            'firmware version': extra.pop('firmware_version', ''), 'position': extra.pop('position', 0),
            'sensor': [c['sensor'] for c in self.channels], 'channels': list(range(1, self.n_channels + 1)),
            'resolution': [self.resolution_bits] * self.n_channels, 'sampling rate': self.fs_Hz,
            'column': ['nSeq', 'DI', *self.labels()], 'label': self.labels(),
            'digital IO': [0] * self.digital_in, 'mode': extra.pop('mode', 0), 'sync interval': 0,
            'special': [{} for _ in range(self.n_channels)], 'convertedValues': extra.pop('convertedValues', 1),
            'keywords': '', 'comments': extra.pop('comments', ''),
            'x_yuanli': dict(extra, device_id=self.id),
        }


def validate(d):
    """合法返回 DeviceDesc；否则抛 DescError 并说明哪一项。"""
    if not isinstance(d, dict):
        raise DescError('描述必须是 JSON 对象')
    missing = [k for k in REQUIRED if k not in d]
    if missing:
        raise DescError(f'缺字段 {missing}')
    if not isinstance(d['id'], str) or not d['id'] or not all(c.isalnum() or c == '-' for c in d['id']) or d['id'] != d['id'].lower():
        raise DescError('id 只能是小写字母数字与 -')
    t = d['transport']
    if not isinstance(t, dict) or t.get('kind') not in TRANSPORTS:
        raise DescError(f'transport.kind 必须是 {TRANSPORTS}')
    if d['decoder'] not in DECODERS:
        raise DescError(f'未知 decoder {d["decoder"]!r}，可用 {DECODERS}')
    n = d['n_channels']
    if type(n) is not int or n < 1:
        raise DescError('n_channels 必须是正整数')
    fs = d['fs_Hz']
    if type(fs) is not int or fs < 1:
        raise DescError('fs_Hz 必须是正整数')
    opts = d.get('fs_options') or [fs]
    if fs not in opts:
        raise DescError(f'fs_Hz {fs} 不在 fs_options {opts}')
    chs = d['channels']
    if not isinstance(chs, list) or len(chs) != n:
        raise DescError(f'channels 有 {len(chs) if isinstance(chs, list) else "?"} 路，n_channels 是 {n}')
    for i, c in enumerate(chs):
        for k in ('label', 'sensor', 'unit'):
            if k not in c:
                raise DescError(f'channels[{i}] 缺 {k}')
        if c['sensor'] not in SENSORS:
            raise DescError(f'channels[{i}].sensor {c["sensor"]!r} 不在 {SENSORS}')
        if type(c.get('gain', 1.0)) is bool or not isinstance(c.get('gain', 1.0), (int, float)) or c.get('gain', 1.0) == 0:
            raise DescError(f'channels[{i}].gain 必须是非零数')
    caps = d.get('capabilities', {})
    bad = [k for k in caps if k not in CAPABILITIES]
    if bad:
        raise DescError(f'未知能力 {bad}')
    if caps.get('imu') and not d.get('imu'):
        raise DescError('能力 imu 为真但没有 imu 描述')
    known = set(DeviceDesc.__dataclass_fields__)
    return DeviceDesc(**{**{k: v for k, v in d.items() if k in known}, 'fs_options': opts})


def load(id_or_path, devices_dir=DEVICES_DIR):
    p = Path(id_or_path)
    if p.suffix != '.json':
        p = Path(devices_dir) / f'{id_or_path}.json'
    if not p.exists():
        raise DescError(f'没有设备描述 {p.name}；可用：{sorted(x.stem for x in Path(devices_dir).glob("*.json"))}')
    return validate(json.loads(p.read_text()))


def available(devices_dir=DEVICES_DIR):
    return sorted(x.stem for x in Path(devices_dir).glob('*.json'))


def for_rig(rig):
    """老 Rig 对象 → 描述：按 kind 猜，给没走 --device 的旧启动路径用。"""
    kind = getattr(rig, 'kind', None)
    if kind == 'wl18':
        return load('wl18')
    if kind == 'wl8':
        if getattr(rig, 'replay', None):
            return load('replay')
        return load('fake' if type(rig).__name__.startswith('Fake') else 'wl8')
    if kind in ('c08b-16ch', 'c08b-8ch', 'c08b-2ch'):
        return load(kind)
    if type(rig).__name__.endswith('V12Rig'):
        return load('v12')
    return load('cheez')


if __name__ == '__main__':
    for i in available():
        d = load(i)
        print(i, d.n_channels, 'ch', d.fs_Hz, 'Hz', {k for k, v in d.capabilities.items() if v})

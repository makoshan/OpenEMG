"""C08B 共用双核主控（STM32L432KC + nRF52840）2/8/16 通道实时 BLE 流式接入契约。

职责与边界：
1. 编解码 C08B F01 传输包：
   - 协议 v4（16ch 双 ADS1298 无损）：16 字节头 + count×54 字节（status_a[3]+ch1..8[24]+status_b[3]+ch9..16[24]），MTU=247 下单包最多 4 帧（232 B）。
   - 协议 v1（8ch 单 ADS1298 / 2ch ADS1292）：复用 firmware/offline-f01/codec.py（16 字节头 + count×27 字节），MTU=247 下单包最多 8 帧（232 B）。
   - 6 轴 IMU 包：复用 v12_imu.py（36 字节，version=1, kind=2, count=1，时间戳同源 L432_DWT_1MHz）。
2. 冷启动动态子板识别：
   - 固件冷启动待机时 GATT META 如实报告 afe="NONE"（protocol=1, active_channels=0），绝不伪装成 16ch；
   - 支持只读子板探测模式（mode='probe' -> PRB1），以及启动采集后在首包到达时重读 META 动态绑定真实拓扑（ADS1298_DUAL v4 / ADS1298_SINGLE v1 / ADS1292 v1）。
3. 默认安全门禁：
   - allow_real 默认 False；真采样与 PRB1 探测模式必须同时具备 bench_measured=True、allow_real=True 与显式 expected build_id。
   - 双锁关闭状态下仅允许只读诊断（mode=None）或双核无电合成流通路自检（mode='synth' -> 发送 SYN1），且严格隔离合成标志与真实采样标志。
4. 四态：已实现未验收。主机编解码、归档回放与 Studio AcqHandler 合成通路已自检，不代表真机已刷写或完成离体台架/人体实测。
"""
import argparse
import asyncio
from dataclasses import asdict, dataclass
import importlib.util
import inspect
import json
import math
from pathlib import Path
import queue
import re
import struct
import sys
import threading
import time

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import v12_imu  # noqa: E402
from v12_raw import RawArchive  # noqa: E402
from v12_status import decode_status  # noqa: E402

UUID_PREFIX = '7b24c101-3948-4f03-9d11-12bb9d'
SERVICE, DATA, META, STATUS, CONTROL, IMU_DATA = (UUID_PREFIX + f'{i:06d}' for i in range(1, 7))

HEADER = struct.Struct('<BBBBIQ')
PROTO_V1_8CH = 1
PROTO_V4_16CH = 4
KIND_EMG = 1
FRAME_BYTES_8CH = 27
FRAME_BYTES_16CH = 54
MAX_FRAMES_8CH = 8
MAX_FRAMES_16CH = 4
ADS_STATUS_OK = bytes((0xC0, 0x00, 0x00))

REAL_COMMANDS = dict(test=b'TST1', short=b'SHT1', external=b'EXT1', rld=b'EXR1', rld_diag=b'RLD1')
PROBE_COMMAND = b'PRB1'
RREG_COMMAND = b'RREG'
WREG_COMMAND = b'WREG'
CLEAR_OVERRIDES_COMMAND = b'CLRO'
ALL_COMMANDS = dict(**REAL_COMMANDS, synth=b'SYN1', probe=PROBE_COMMAND)
STOP_COMMAND = b'STOP'
CHIP_SELECT = dict(u1=0, u2=1, both=2)

ADS1298_REG_ADDR_BY_NAME = dict(
    ID=0x00, CONFIG1=0x01, CONFIG2=0x02, CONFIG3=0x03, LOFF=0x04,
    CH1SET=0x05, CH2SET=0x06, CH3SET=0x07, CH4SET=0x08,
    CH5SET=0x09, CH6SET=0x0A, CH7SET=0x0B, CH8SET=0x0C,
    RLD_SENSP=0x0D, RLD_SENSN=0x0E, LOFF_SENSP=0x0F, LOFF_SENSN=0x10,
    LOFF_FLIP=0x11, LOFF_STATP=0x12, LOFF_STATN=0x13, GPIO=0x14,
    PACE=0x15, RESP=0x16, CONFIG4=0x17, WCT1=0x18, WCT2=0x19,
)


def _parse_reg_addr_token(token):
    t = str(token).strip().upper()
    if t in ADS1298_REG_ADDR_BY_NAME:
        return ADS1298_REG_ADDR_BY_NAME[t]
    val = int(t, 0)
    if not 0 <= val <= 0x19:
        raise ValueError(f'寄存器地址超出 0x00..0x19：{token!r}')
    return val


def encode_rreg_cmd(chip='both', addr=0x00):
    """编码 6 字节在线寄存器读取命令：b'RREG' + chip_sel(0/1/2) + addr(0x00..0x19)。"""
    chip_id = chip if type(chip) is int else CHIP_SELECT.get(str(chip).lower(), -1)
    if chip_id not in (0, 1, 2) or type(addr) is not int or not 0 <= addr <= 0x19:
        raise ValueError(f'无效 RREG 参数 chip={chip!r}, addr={addr!r}')
    return RREG_COMMAND + bytes((chip_id, addr))


def encode_wreg_cmd(chip, addr, val):
    """编码 7 字节在线安全寄存器写核命令：b'WREG' + chip_sel(0/1/2) + addr(0x00..0x19) + val(0..255)。"""
    chip_id = chip if type(chip) is int else CHIP_SELECT.get(str(chip).lower(), -1)
    if (
        chip_id not in (0, 1, 2)
        or type(addr) is not int or not 0 <= addr <= 0x19
        or type(val) is not int or not 0 <= val <= 0xFF
    ):
        raise ValueError(f'无效 WREG 参数 chip={chip!r}, addr={addr!r}, val={val!r}')
    return WREG_COMMAND + bytes((chip_id, addr, val))


def parse_rreg_spec(spec):
    """解析 CLI --rreg 参数（支持 '0x05'、'CONFIG3'、'u1:0x05'、'both:CH1SET'）。"""
    s = str(spec).strip()
    if ':' in s:
        chip_s, addr_s = s.split(':', 1)
        chip_key = chip_s.strip().lower()
    else:
        chip_key, addr_s = 'both', s
    if chip_key not in CHIP_SELECT:
        raise ValueError(f'未知芯片选择 {chip_key!r}（可选 u1 / u2 / both）')
    return chip_key, _parse_reg_addr_token(addr_s)


def parse_wreg_spec(spec):
    """解析 CLI --wreg 参数（格式 'u1:0x05=0x60' 或 'both:CH1SET=0x60'）。"""
    s = str(spec).strip()
    if ':' not in s or '=' not in s:
        raise ValueError(f'--wreg 格式必须为 <u1|u2|both>:<addr>=<val>，收到 {spec!r}')
    chip_s, rest = s.split(':', 1)
    addr_s, val_s = rest.split('=', 1)
    chip_key = chip_s.strip().lower()
    if chip_key not in CHIP_SELECT:
        raise ValueError(f'未知芯片选择 {chip_key!r}（可选 u1 / u2 / both）')
    addr = _parse_reg_addr_token(addr_s)
    val = int(val_s.strip(), 0)
    if not 0 <= val <= 0xFF:
        raise ValueError(f'寄存器值超出 0x00..0xFF：{val_s!r}')
    return chip_key, addr, val


def validate_c08b_reg_write_host(afe, chip_idx, addr, val):
    """与 stream_proto.h:c08b_validate_reg_write 逐位对齐的主机端寄存器安全掩码校验。"""
    if type(chip_idx) is not int or type(addr) is not int or type(val) is not int:
        return False, 0
    if not (0 <= val <= 0xFF):
        return False, 0
    if afe in ('ADS1298_DUAL', 'ADS1298_SINGLE'):
        max_chip = 1 if afe == 'ADS1298_DUAL' else 0
        if not (0 <= chip_idx <= max_chip):
            return False, 0
        if addr > 0x19 or addr in (0x00, 0x12, 0x13):
            return False, 0
        vm = 0xFF
        if addr == 0x01:
            if (val & 0x18) != 0 or (val & 0x07) == 0x07 or (val & 0x87) == 0x80:
                return False, 0
        elif addr == 0x02:
            if (val & 0xC8) != 0 or (val & 0x03) == 0x02:
                return False, 0
        elif addr == 0x03:
            if (val & 0xC0) != 0xC0 or (val & 0x38) != 0 or (chip_idx != 0 and (val & 0x04) != 0):
                return False, 0
            vm = 0xFE
        elif addr == 0x04:
            if (val & 0x03) == 0x02:
                return False, 0
        elif 0x05 <= addr <= 0x0C:
            if (val & 0x08) != 0 or (val & 0x70) == 0x70 or (val & 0x07) == 0x02:
                return False, 0
        elif addr in (0x0D, 0x0E):
            if chip_idx != 0 and val != 0x00:
                return False, 0
        elif addr in (0x0F, 0x10, 0x11):
            pass
        elif addr == 0x14:
            if (val & 0x0F) != 0x0F:
                return False, 0
            vm = 0x0F
        elif addr == 0x15:
            if val != 0x00:
                return False, 0
        elif addr == 0x16:
            if val != 0x20:
                return False, 0
        elif addr == 0x17:
            if (val & 0x19) != 0:
                return False, 0
        elif addr in (0x18, 0x19):
            if val != 0x00:
                return False, 0
        else:
            return False, 0
        return True, vm

    if afe == 'ADS1292':
        if chip_idx != 0 or addr > 0x0B or addr in (0x00, 0x08):
            return False, 0
        if addr == 0x01:
            return ((val & 0xF8) == 0 and (val & 0x07) != 0x07), 0x87
        if addr == 0x02:
            return ((val & 0xBC) == 0xA0), 0x7B
        if addr == 0x03:
            return ((val & 0x12) == 0x10), 0xFF
        if addr in (0x04, 0x05):
            return ((val & 0x70) != 0x70), 0xFF
        if addr in (0x06, 0x07):
            return ((val & 0xC0) == 0), 0x3F
        if addr == 0x09:
            return (val == 0x02), 0xFF
        if addr == 0x0A:
            return (val == 0x07), 0x87
        if addr == 0x0B:
            return ((val & 0x0C) == 0x0C), 0x0C
    return False, 0

C08B_IMU_PROFILE = dict(
    chip='LSM6DS3TR-C',
    odr_Hz=104,
    accel_range_g=8,
    gyro_range_dps=1000,
    accel_g_per_count=0.000244,
    gyro_dps_per_count=0.035,
    calibration_verified=False,
    alignment_verified=False,
    timestamp='L432 I2C1 poll (DWT 64-bit)',
    clock_source='L432_DWT_1MHz',
    clock_resolution_us=1,
)


def load_codec(path=None):
    if path is not None:
        target = Path(path)
    else:
        for rel in ('firmware/offline-f01/codec.py', 'v12/offline-f01/codec.py'):
            cand = ROOT / rel
            if cand.exists():
                target = cand
                break
        else:
            raise FileNotFoundError('未找到 offline-f01/codec.py（已查 firmware/ 与 v12/）')
    spec = importlib.util.spec_from_file_location('c08b_f01_codec', target)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_CODEC = load_codec()
SYNTHETIC = _CODEC.SYNTHETIC
SESSION_START = _CODEC.SESSION_START
RECONFIGURE = _CODEC.RECONFIGURE
Packet = _CODEC.Packet
signed24 = _CODEC.signed24


def capacity_16ch(mtu=247):
    """计算给定 ATT MTU 下单条通知可承载的 54B 16ch 帧数上限（最多 4 帧 = 232B）。"""
    if type(mtu) is not int or not 23 <= mtu <= 517:
        raise ValueError('无效的 ATT MTU')
    return min(MAX_FRAMES_16CH, max(0, (mtu - 3 - HEADER.size) // FRAME_BYTES_16CH))


def decode_frame_16ch(frame):
    """解码单帧 54B C08B 16ch 原始帧 -> (status_a_u24, status_b_u24, 16 个有符号 24-bit 整数)。"""
    if len(frame) != FRAME_BYTES_16CH:
        raise ValueError('C08B 16ch 帧长度必须为 54 字节')
    status_a = int.from_bytes(frame[0:3], 'big')
    ch_a = tuple(signed24(frame[i:i + 3]) for i in range(3, 27, 3))
    status_b = int.from_bytes(frame[27:30], 'big')
    ch_b = tuple(signed24(frame[i:i + 3]) for i in range(30, 54, 3))
    return status_a, status_b, ch_a + ch_b


def encode_frame_16ch(counts16, status_a=ADS_STATUS_OK, status_b=ADS_STATUS_OK):
    """将 16 路 24-bit 整数码值与双片 3B 状态字打包为 54B 原始帧。"""
    if len(status_a) != 3 or len(status_b) != 3:
        raise ValueError('ADS1298 状态字必须为 3 字节')
    if len(counts16) != 16:
        raise ValueError('16ch 帧必须包含 16 个通道码值')
    for v in counts16:
        if int(v) < -0x800000 or int(v) > 0x7FFFFF:
            raise ValueError('通道码值超出 24-bit 有符号范围')
    part_a = b''.join(int(v).to_bytes(3, 'big', signed=True) for v in counts16[:8])
    part_b = b''.join(int(v).to_bytes(3, 'big', signed=True) for v in counts16[8:])
    return bytes(status_a) + part_a + bytes(status_b) + part_b


def encode_16ch(packet, mtu=247):
    """编码 C08B F01 v4（16ch 无损双 ADS1298）数据包。"""
    if type(packet.sequence) is not int or not 0 <= packet.sequence <= 0xFFFFFFFF:
        raise ValueError('无效的采样序号')
    if type(packet.timestamp_us) is not int or not 0 <= packet.timestamp_us <= 0xFFFFFFFFFFFFFFFF:
        raise ValueError('无效的时间戳')
    if type(packet.flags) is not int or packet.flags < 0 or packet.flags & ~7:
        raise ValueError('未知的标志位')
    cap = capacity_16ch(mtu)
    if not 1 <= len(packet.frames) <= cap:
        raise ValueError('16ch 帧数超过当前 MTU 容量')
    if any(len(f) != FRAME_BYTES_16CH for f in packet.frames):
        raise ValueError('16ch 单帧长度必须为 54 字节')
    if packet.flags & SESSION_START and packet.sequence != 0:
        raise ValueError('会话首包采样序号必须为 0')
    if packet.flags & RECONFIGURE and not packet.flags & SESSION_START:
        raise ValueError('重配边界必须同时携带 SESSION_START')
    return HEADER.pack(PROTO_V4_16CH, KIND_EMG, len(packet.frames), packet.flags,
                       packet.sequence, packet.timestamp_us) + b''.join(packet.frames)


def decode_16ch(data, mtu=247):
    """解码 C08B F01 v4（16ch 无损双 ADS1298）数据包，可直接作为 codec.Receiver 的 decoder。"""
    data = bytes(data)
    cap = capacity_16ch(mtu)
    if len(data) < HEADER.size or len(data) > mtu - 3:
        raise ValueError('16ch 包截断或超过 MTU 上限')
    version, kind, count, flags, seq, ts = HEADER.unpack_from(data)
    if version != PROTO_V4_16CH or kind != KIND_EMG:
        raise ValueError('不是 C08B F01 v4 (16ch) EMG 包')
    if flags & ~7 or not 1 <= count <= cap:
        raise ValueError('16ch 标志位或帧计数无效')
    if len(data) != HEADER.size + count * FRAME_BYTES_16CH:
        raise ValueError('16ch 载荷长度与帧计数不符')
    if flags & SESSION_START and seq != 0:
        raise ValueError('会话首包采样序号必须为 0')
    if flags & RECONFIGURE and not flags & SESSION_START:
        raise ValueError('重配边界必须同时携带 SESSION_START')
    frames = tuple(data[i:i + FRAME_BYTES_16CH] for i in range(HEADER.size, len(data), FRAME_BYTES_16CH))
    return Packet(seq, ts, flags, frames)


def frame_status_valid(frame, protocol):
    """检查单帧状态字高 4 位是否为 0xC（16ch 同时核对 U1 与 U2 两片状态头）。"""
    if protocol == PROTO_V4_16CH:
        return len(frame) == FRAME_BYTES_16CH and (frame[0] >> 4) == 0xC and (frame[27] >> 4) == 0xC
    if protocol == PROTO_V1_8CH:
        return len(frame) == FRAME_BYTES_8CH and (frame[0] >> 4) == 0xC
    raise ValueError(f'不支持的协议版本 {protocol}')


@dataclass(frozen=True)
class C08BAdcProfile:
    """C08B 2/8/16ch 标称量程描述（不代表已完成实板寄存器读回或电压校准）。"""
    afe_topology: str = 'ADS1298_DUAL'
    vref_mV: int = 2400
    gain: int = 6
    fs_Hz: int = 1000
    channels: int = 16
    active_channels: int = 16
    transport_protocol: int = PROTO_V4_16CH
    afe: str = 'ADS1298'
    reference_verified: bool = False

    def __post_init__(self):
        if self.afe_topology not in ('ADS1298_DUAL', 'ADS1298_SINGLE', 'ADS1292'):
            raise ValueError(f'未知 C08B AFE 拓扑：{self.afe_topology!r}')
        expected_chip = 'ADS1292' if self.afe_topology == 'ADS1292' else 'ADS1298'
        if self.afe != expected_chip:
            object.__setattr__(self, 'afe', expected_chip)
        if type(self.gain) is not int or self.gain not in (1, 2, 3, 4, 6, 8, 12):
            raise ValueError('PGA 增益无效')
        if type(self.fs_Hz) is not int or self.fs_Hz not in (500, 1000, 2000, 4000):
            raise ValueError('采样率不在候选范围 (500/1000/2000/4000 Hz)')
        if self.afe_topology == 'ADS1298_DUAL':
            if (self.channels, self.active_channels, self.transport_protocol) != (16, 16, PROTO_V4_16CH):
                raise ValueError('ADS1298_DUAL 必须对应 channels=16, active_channels=16, protocol=4')
            if type(self.vref_mV) is not int or self.vref_mV not in (2400, 4000):
                raise ValueError('ADS1298 参考电压仅支持 2400 mV 或 4000 mV')
        elif self.afe_topology == 'ADS1298_SINGLE':
            if (self.channels, self.active_channels, self.transport_protocol) != (8, 8, PROTO_V1_8CH):
                raise ValueError('ADS1298_SINGLE 必须对应 channels=8, active_channels=8, protocol=1')
            if type(self.vref_mV) is not int or self.vref_mV not in (2400, 4000):
                raise ValueError('ADS1298 参考电压仅支持 2400 mV 或 4000 mV')
        else:
            if (self.channels, self.active_channels, self.transport_protocol) != (8, 2, PROTO_V1_8CH):
                raise ValueError('ADS1292 必须对应 channels=8（F01 v1 槽位）, active_channels=2, protocol=1')
            if type(self.vref_mV) is not int or self.vref_mV not in (2420, 4033):
                raise ValueError('ADS1292 参考电压仅支持 2420 mV 或 4033 mV')

    @property
    def vref_V(self):
        return self.vref_mV / 1000.0

    @property
    def uv_per_count(self):
        return (self.vref_mV * 1e3) / (self.gain * (2 ** 23 - 1))

    @classmethod
    def for_n_channels(cls, n_channels, fs_Hz=1000):
        if n_channels == 16:
            return cls('ADS1298_DUAL', 2400, 6, fs_Hz, 16, 16, PROTO_V4_16CH)
        if n_channels == 8:
            return cls('ADS1298_SINGLE', 2400, 6, fs_Hz, 8, 8, PROTO_V1_8CH)
        if n_channels == 2:
            return cls('ADS1292', 2420, 6, fs_Hz, 8, 2, PROTO_V1_8CH)
        raise ValueError(f'C08B 仅支持 2 / 8 / 16 通道，收到 {n_channels}')


def validate_c08b_metadata(raw, expected=None):
    """校验 C08B GATT META JSON 元数据，检查协议号、通道数、参考电压与构建 ID 一致性。"""
    meta = json.loads(bytes(raw))
    if not isinstance(meta, dict) or meta.get('profile') != 'C08B_DUAL_STREAM_CANDIDATE':
        raise ValueError('设备不是 C08B_DUAL_STREAM_CANDIDATE 候选固件')
    afe = meta.get('afe')
    if afe not in ('NONE', 'ADS1298_DUAL', 'ADS1298_SINGLE', 'ADS1292', 'UNKNOWN'):
        raise ValueError(f'未知固件 AFE 标识：{afe!r}')
    for key, values in dict(
        protocol=(PROTO_V1_8CH, PROTO_V4_16CH),
        channels=(8, 16),
        active_channels=(0, 2, 8, 16),
        fs_Hz=(500, 1000, 2000),
        spi_Hz=(1_000_000, 2_000_000, 4_000_000, 8_000_000),
        vref_mV=(2400, 2420),
        gain=(1, 2, 3, 4, 6, 8, 12),
        clock_resolution_us=(1,),
    ).items():
        if type(meta.get(key)) is not int or meta[key] not in values:
            raise ValueError(f'固件元数据 {key}={meta.get(key)!r} 无效')
    if type(meta.get('bench_measured')) is not bool:
        raise ValueError('固件台架锁字段无效')
    if type(meta.get('imu_enabled')) is not bool:
        raise ValueError('固件 IMU 开关字段无效')
    if meta.get('clock_source') != 'L432_DWT_1MHz':
        raise ValueError(f'固件时钟源无效：{meta.get("clock_source")!r}')
    if not isinstance(meta.get('build_id'), str) or not re.fullmatch('[0-9a-f]{16}', meta['build_id']):
        raise ValueError('固件构建 ID 必须为 16 位小写十六进制')
    if expected is not None and meta['build_id'] != expected:
        raise ValueError('设备构建 ID 与预期镜像不一致')

    proto, ch, act, vref, spi = (
        meta['protocol'], meta['channels'], meta['active_channels'], meta['vref_mV'], meta['spi_Hz']
    )
    if afe == 'ADS1298_DUAL':
        if (proto, ch, act, vref) != (PROTO_V4_16CH, 16, 16, 2400):
            raise ValueError('ADS1298_DUAL 元数据协议/通道/参考电压不一致')
    elif afe == 'ADS1298_SINGLE':
        if (proto, ch, act, vref) != (PROTO_V1_8CH, 8, 8, 2400):
            raise ValueError('ADS1298_SINGLE 元数据协议/通道/参考电压不一致')
    elif afe == 'ADS1292':
        if (proto, ch, act, vref, spi) != (PROTO_V1_8CH, 8, 2, 2420, 1_000_000):
            raise ValueError('ADS1292 元数据协议/通道/2.42V/1MHz SPI 不一致')
    else:
        if (proto, ch, act) != (PROTO_V1_8CH, 8, 0):
            raise ValueError(f'{afe} 未就绪态元数据通道描述不一致')

    if 'reg_overrides' in meta:
        ro = meta['reg_overrides']
        if type(ro) is not int or not (0 <= ro <= 52):
            raise ValueError(f'固件元数据 reg_overrides={ro!r} 无效')
    if 'last_reg' in meta:
        lr = meta['last_reg']
        if (
            not isinstance(lr, dict)
            or set(lr.keys()) != {'seq', 'addr', 'u1', 'u2'}
            or any(type(lr[k]) is not int for k in ('seq', 'addr', 'u1', 'u2'))
            or not (0 <= lr['seq'] <= 0xFFFF and 0 <= lr['addr'] <= 0x19 and 0 <= lr['u1'] <= 0xFF and 0 <= lr['u2'] <= 0xFF)
        ):
            raise ValueError(f'固件元数据 last_reg={lr!r} 无效')
    return meta


def profile_from_meta(meta, fallback_n_channels=16):
    afe = meta['afe']
    if afe in ('ADS1298_DUAL', 'ADS1298_SINGLE', 'ADS1292'):
        return C08BAdcProfile(
            afe_topology=afe,
            vref_mV=meta['vref_mV'],
            gain=meta['gain'],
            fs_Hz=meta['fs_Hz'],
            channels=meta['channels'],
            active_channels=meta['active_channels'],
            transport_protocol=meta['protocol'],
        )
    if meta['protocol'] == PROTO_V4_16CH:
        return C08BAdcProfile.for_n_channels(16, fs_Hz=meta['fs_Hz'])
    n_ch = 2 if fallback_n_channels == 2 else 8
    return C08BAdcProfile.for_n_channels(n_ch, fs_Hz=meta['fs_Hz'])


_RAW_ARCHIVE_HAS_VOLTAGE_AT = 'voltage_at' in inspect.signature(RawArchive.__init__).parameters


def _open_archive(directory, profile, codec, allow_real):
    vat = 'ADS1292 PGA input' if profile.afe == 'ADS1292' else 'ADS1298 PGA input'
    if _RAW_ARCHIVE_HAS_VOLTAGE_AT:
        return RawArchive(directory, profile, codec, allow_real, voltage_at=vat)
    archive = RawArchive(directory, profile, codec, allow_real)
    if profile.afe == 'ADS1292':
        meta_path = Path(directory) / 'metadata.json'
        m = json.loads(meta_path.read_text())
        if m.get('voltage_at') != vat:
            m['voltage_at'] = vat
            meta_path.write_text(json.dumps(m, ensure_ascii=False, indent=2) + '\n')
    return archive


async def capture_c08b(
    client,
    output,
    seconds=5.0,
    mode=None,
    allow_real=False,
    expected=None,
    queue_limit=1024,
    poll_seconds=0.5,
    with_imu=False,
    synth_channels=16,
    fs_hz=None,
    on_first_data=None,
):
    """C08B 离体台架 / 双核合成流 / 只读子板探测 BLE 入口。"""
    if not math.isfinite(seconds) or seconds <= 0 or not math.isfinite(poll_seconds) or poll_seconds <= 0:
        raise ValueError('时长与轮询间隔必须为正有限数')
    if type(queue_limit) is not int or queue_limit < 1:
        raise ValueError('接收队列上限无效')
    if synth_channels not in (2, 8, 16):
        raise ValueError('synth_channels 仅支持 2 / 8 / 16')
    if fs_hz is not None and (type(fs_hz) is not int or fs_hz not in (500, 1000, 2000)):
        raise ValueError('fs_hz 仅支持 None / 500 / 1000 / 2000')
    if fs_hz is not None and mode in (None, 'probe'):
        raise ValueError('fs_hz 覆盖仅适用于流式采集模式（synth / test / short / external / rld / rld_diag）')
    if type(with_imu) is not bool or (with_imu and mode in (None, 'probe')):
        raise ValueError('IMU 联合采集需明确指定流式采集模式')
    if mode is not None and mode not in ALL_COMMANDS:
        raise ValueError(f'未知采集模式 {mode!r}；可用 {tuple(ALL_COMMANDS)}')
    is_synth = (mode == 'synth')
    is_probe = (mode == 'probe')
    is_real = (mode in REAL_COMMANDS or is_probe)
    if is_real and (not allow_real or expected is None):
        raise ValueError('真实采集或 PRB1 子板探测需显式传入 allow_real=True 与 expected build_id（仅限离体台架）')

    service = client.services.get_service(SERVICE)
    required_chars = {DATA, META, STATUS, CONTROL} | ({IMU_DATA} if with_imu else set())
    if service is None or not required_chars.issubset({str(c.uuid).lower() for c in service.characteristics}):
        raise ValueError('设备缺少完整 C08B V12 BLE 服务特征')

    raw_meta = bytes(await asyncio.wait_for(client.read_gatt_char(META), 10))
    meta = validate_c08b_metadata(raw_meta, expected)
    raw_status = bytes(await asyncio.wait_for(client.read_gatt_char(STATUS), 10))
    initial_status = decode_status(raw_status)
    if initial_status['bench_measured'] != meta['bench_measured']:
        raise ValueError('META 与 STATUS 的台架锁状态不一致')
    if initial_status['spi_Hz'] is not None and initial_status['spi_Hz'] != meta['spi_Hz']:
        raise ValueError('META 与 STATUS 的 SPI 速率不一致')
    if initial_status['active'] or initial_status['fault']:
        raise ValueError(f'设备已在运行或存在故障（fault={initial_status["fault"]}），拒绝启动')
    if is_real:
        if not meta['bench_measured']:
            raise ValueError('固件台架锁未解开（bench_measured=false），拒绝发送真实 AFE 命令')
        if meta['afe'] == 'UNKNOWN':
            raise ValueError('固件报告子板状态 UNKNOWN，拒绝启动')
    if with_imu and not meta['imu_enabled']:
        raise ValueError('固件未启用 IMU 通道')

    codec = load_codec()
    output = Path(output)
    if output.exists():
        raise FileExistsError(f'归档目录已存在：{output}')
    diag = None
    diag_buffer = []

    active_meta = meta
    archive = None
    rx = None
    imu_rx = codec.Receiver(allow_real=(allow_real and not is_synth and not is_probe and mode is not None), decoder=v12_imu.decode)

    def _init_stream_pipeline(m):
        nonlocal active_meta, archive, rx, diag
        active_meta = m
        prof = profile_from_meta(m, fallback_n_channels=synth_channels)
        dec = decode_16ch if m['protocol'] == PROTO_V4_16CH else codec.decode
        stream_real = (allow_real and mode in REAL_COMMANDS)
        rx = codec.Receiver(allow_real=stream_real, decoder=dec)
        archive = _open_archive(output, prof, codec, allow_real=stream_real)
        if with_imu:
            archive.enable_imu(C08B_IMU_PROFILE)
        if diag is None:
            diag = (output / 'diagnostics.jsonl').open('x', encoding='utf-8')
            for ev in diag_buffer:
                diag.write(json.dumps(ev, ensure_ascii=False) + '\n')
            diag_buffer.clear()
            diag.flush()
        result.update(
            afe=m['afe'],
            protocol=m['protocol'],
            channels=m['channels'],
            active_channels=m['active_channels'],
            fs_Hz=m['fs_Hz'],
            spi_Hz=m['spi_Hz'],
        )

    incoming = queue.Queue(maxsize=queue_limit)
    overflow = 0
    subscriptions = []
    attempted = False
    first_data = []
    failure = None
    final_status = initial_status

    result = dict(
        state='运行中',
        mode=mode or 'status',
        afe=meta['afe'],
        protocol=meta['protocol'],
        channels=meta['channels'],
        active_channels=meta['active_channels'],
        build_id=meta['build_id'],
        fs_Hz=meta['fs_Hz'],
        spi_Hz=meta['spi_Hz'],
        packets=0,
        valid_samples=0,
        bad_packets=0,
        bad_status_frames=0,
        queue_overflow=0,
        missing_samples=0,
        physical_device_verified=False,
        stop_confirmed=False,
    )
    if with_imu:
        result.update(imu_packets=0, imu_samples=0, imu_bad_packets=0, imu_missing_samples=0)

    def diagnostic(event):
        if diag is None:
            diag_buffer.append(event)
        else:
            diag.write(json.dumps(event, ensure_ascii=False) + '\n')
            diag.flush()

    def on_notify(_, value, stream='adc'):
        nonlocal overflow
        if stream == 'adc' and not first_data:
            first_data.append(time.monotonic())
            if on_first_data is not None:
                on_first_data()
        try:
            incoming.put_nowait((time.monotonic_ns(), bytes(value), stream))
        except queue.Full:
            overflow += 1

    def drain():
        first_error = None
        while not incoming.empty():
            stamp, packet, stream = incoming.get_nowait()
            reported = client.mtu_size
            if type(reported) is not int or not 23 <= reported <= 517:
                raise ValueError('传输层返回无效 MTU')
            mtu = max(reported, len(packet) + 3)
            event = dict(packet_hex=packet.hex(), mtu=mtu)
            if stream == 'imu':
                archive.write_imu(event)
            else:
                archive.write(event)
            diagnostic(dict(stream=stream, notification_ns=stamp, reported_mtu=reported, decode_mtu=mtu))

            if stream == 'imu':
                result['imu_packets'] += 1
                try:
                    parsed = imu_rx.receive(packet, mtu)
                    if mode in REAL_COMMANDS and (parsed.flags & SYNTHETIC):
                        raise ValueError('真实采集模式收到了带 SYNTHETIC 标记的 IMU 包')
                    if is_synth and not (parsed.flags & SYNTHETIC):
                        raise ValueError('SYN1 合成模式收到了未标 SYNTHETIC 的 IMU 包')
                    result['imu_samples'] += 1
                except ValueError as err:
                    result['imu_bad_packets'] += 1
                    diagnostic(dict(rejected_imu_packet=str(err)))
                    first_error = first_error or err
                continue

            result['packets'] += 1
            try:
                if len(packet) > 232:
                    raise ValueError('超过 C08B F01 单包 232 字节上限')
                parsed = rx.receive(packet, mtu)
                if mode in REAL_COMMANDS and (parsed.flags & SYNTHETIC):
                    raise ValueError('真实采集模式收到了带 SYNTHETIC 标记的数据包')
                if is_synth and not (parsed.flags & SYNTHETIC):
                    raise ValueError('SYN1 合成模式收到了未标 SYNTHETIC 的数据包')
                bad = sum(not frame_status_valid(f, active_meta['protocol']) for f in parsed.frames)
                result['bad_status_frames'] += bad
                result['valid_samples'] += len(parsed.frames) - bad
                if bad:
                    raise ValueError('ADS 状态字高 4 位无效（含 U1/U2 双片检查），原包已落盘')
            except ValueError as err:
                result['bad_packets'] += 1
                diagnostic(dict(rejected_packet=str(err)))
                first_error = first_error or err

        result['missing_samples'] = rx.missing_samples
        if with_imu:
            result['imu_missing_samples'] = imu_rx.missing_samples
        result['queue_overflow'] = overflow
        if overflow:
            first_error = first_error or RuntimeError(f'主机接收队列溢出 {overflow} 次')
        if first_error is not None:
            raise first_error

    try:
        diagnostic(dict(initial_meta=meta, initial_status=initial_status))
        if mode is None:
            _init_stream_pipeline(meta)
        elif is_probe:
            attempted = True
            await asyncio.wait_for(client.write_gatt_char(CONTROL, PROBE_COMMAND, response=True), 10)
            probe_deadline = time.monotonic() + max(3.0, seconds)
            probed_meta = meta
            while time.monotonic() < probe_deadline:
                if not getattr(client, 'is_connected', True):
                    raise RuntimeError('PRB1 探测过程中 BLE 连接中断或重连（严禁跨连接拼接）')
                await asyncio.sleep(min(0.05, poll_seconds))
                raw_m = bytes(await asyncio.wait_for(client.read_gatt_char(META), 10))
                probed_meta = validate_c08b_metadata(raw_m, expected)
                st_b = bytes(await asyncio.wait_for(client.read_gatt_char(STATUS), 10))
                final_status = decode_status(st_b)
                if final_status['fault']:
                    raise RuntimeError(f'PRB1 子板探测触发设备故障码 {final_status["fault"]}')
                if probed_meta['afe'] in ('ADS1298_DUAL', 'ADS1298_SINGLE', 'ADS1292') and not final_status['active']:
                    break
            if probed_meta['afe'] not in ('ADS1298_DUAL', 'ADS1298_SINGLE', 'ADS1292'):
                raise RuntimeError(f'PRB1 子板探测超时未识别出有效 AFE（afe={probed_meta["afe"]}）')
            _init_stream_pipeline(probed_meta)
            result['stop_confirmed'] = not final_status['active']
            diagnostic(dict(probed_meta=probed_meta, post_probe_status=final_status))
        else:
            await asyncio.wait_for(client.start_notify(DATA, lambda h, v: on_notify(h, v, 'adc')), 10)
            subscriptions.append(DATA)
            if with_imu:
                await asyncio.wait_for(client.start_notify(IMU_DATA, lambda h, v: on_notify(h, v, 'imu')), 10)
                subscriptions.append(IMU_DATA)
            attempted = True
            target_fs = fs_hz if fs_hz is not None else meta['fs_Hz']
            if is_synth:
                ctrl_payload = b'SYN1' + struct.pack('<HB', target_fs, synth_channels)
            elif fs_hz is not None:
                ctrl_payload = ALL_COMMANDS[mode] + struct.pack('<H', fs_hz)
            else:
                ctrl_payload = ALL_COMMANDS[mode]
            await asyncio.wait_for(client.write_gatt_char(CONTROL, ctrl_payload, response=True), 10)

            # 等待第 1 包通知入队（L432 上电探测最长约 1.4 s），收到首包后先重读 META 锁定真实子板协议再解码！
            start_deadline = time.monotonic() + max(4.0, seconds)
            while not first_data and time.monotonic() < start_deadline:
                if not getattr(client, 'is_connected', True):
                    raise RuntimeError('等待首包期间 BLE 连接中断或重连（严禁跨连接拼接数据）')
                await asyncio.sleep(min(0.02, poll_seconds))
            if not first_data:
                st_bytes = bytes(await asyncio.wait_for(client.read_gatt_char(STATUS), 10))
                final_status = decode_status(st_bytes)
                raise RuntimeError(f'启动后未收到数据包（fault={final_status["fault"]}）')

            raw_active_meta = bytes(await asyncio.wait_for(client.read_gatt_char(META), 10))
            probed = validate_c08b_metadata(raw_active_meta, expected)
            if mode in REAL_COMMANDS and probed['afe'] not in ('ADS1298_DUAL', 'ADS1298_SINGLE', 'ADS1292'):
                raise ValueError(f'启动真实采集后固件仍未识别出有效 AFE 子板（afe={probed["afe"]}）')
            _init_stream_pipeline(probed)
            diagnostic(dict(active_meta=probed))
            drain()

            run_deadline = first_data[0] + seconds
            while time.monotonic() < run_deadline:
                if not getattr(client, 'is_connected', True):
                    drain()
                    raise RuntimeError('采集过程中 BLE 连接中断或重连（严禁跨连接拼接数据）')
                await asyncio.sleep(min(poll_seconds, max(0.01, run_deadline - time.monotonic())))
                drain()
                if not getattr(client, 'is_connected', True):
                    raise RuntimeError('采集过程中 BLE 连接中断或重连（严禁跨连接拼接数据）')
                mid_status = decode_status(bytes(await asyncio.wait_for(client.read_gatt_char(STATUS), 10)))
                final_status = mid_status
                if mid_status['fault']:
                    raise RuntimeError(f'采集中触发设备故障码 {mid_status["fault"]}（fault={mid_status["fault"]}）')
                if not mid_status['active']:
                    raise RuntimeError(f'采集中设备意外退出运行态（fault={mid_status["fault"]}）')
            if not getattr(client, 'is_connected', True):
                raise RuntimeError('采集过程中 BLE 连接中断或重连（严禁跨连接拼接数据）')

            # 发 STOP 前必须先核对 STATUS：固件收到 STOP 会复位非持续性锁存故障码，先发 STOP 会静默吞没中途故障！
            pre_stop = decode_status(bytes(await asyncio.wait_for(client.read_gatt_char(STATUS), 10)))
            final_status = pre_stop
            if pre_stop['fault']:
                raise RuntimeError(f'采集中触发设备故障码 {pre_stop["fault"]}（fault={pre_stop["fault"]}）')
            if not pre_stop['active']:
                raise RuntimeError(f'采集中设备意外退出运行态（fault={pre_stop["fault"]}）')

            await asyncio.wait_for(client.write_gatt_char(CONTROL, STOP_COMMAND, response=True), 10)
            for _ in range(10):
                await asyncio.sleep(0.02)
                drain()
                if not getattr(client, 'is_connected', True):
                    raise RuntimeError('收尾停机期间 BLE 连接中断或重连（严禁跨连接拼接数据）')
                st_bytes = bytes(await asyncio.wait_for(client.read_gatt_char(STATUS), 10))
                final_status = decode_status(st_bytes)
                if not final_status['active']:
                    result['stop_confirmed'] = True
                    break
            drain()
            if not result['stop_confirmed']:
                raise RuntimeError('发送 STOP 后设备仍处于 active 状态')
            if final_status['fault']:
                raise RuntimeError(f'采集中触发设备故障码 {final_status["fault"]}（fault={final_status["fault"]}）')
            if result['valid_samples'] <= 0:
                raise RuntimeError('未收到任何有效采样')
        result['state'] = '已完成（已实现未验收）'
    except Exception as exc:
        failure = exc
        result['state'] = f'失败：{exc}'
        if attempted and not is_probe:
            try:
                await asyncio.wait_for(client.write_gatt_char(CONTROL, STOP_COMMAND, response=True), 3)
            except Exception as stop_err:
                diagnostic(dict(stop_cleanup_error=str(stop_err)))
    finally:
        for char_uuid in reversed(subscriptions):
            try:
                await asyncio.wait_for(client.stop_notify(char_uuid), 3)
            except Exception as unsub_err:
                diagnostic(dict(unsubscribe_error=str(unsub_err), uuid=char_uuid))
        if archive is None:
            _init_stream_pipeline(active_meta)
        diagnostic(dict(final_status=final_status, summary=result))
        diag.close()
        archive.close()
        (output / 'summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')

    if failure is not None:
        raise failure
    return result


async def reg_op_c08b(
    client,
    op,
    chip='both',
    addr=0,
    val=0,
    allow_real=False,
    expected=None,
    poll_seconds=0.05,
    timeout=5.0,
):
    """经 BLE GATT CONTROL/META/STATUS 执行 C08B 在线寄存器读(rreg)、安全写核(wreg)或清空覆盖(clro)。"""
    if op not in ('rreg', 'wreg', 'clro'):
        raise ValueError(f'未知寄存器操作 {op!r}；可用 rreg / wreg / clro')
    if not math.isfinite(poll_seconds) or poll_seconds <= 0 or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('轮询间隔与超时必须为正有限数')

    chip_id_to_name = {0: 'u1', 1: 'u2', 2: 'both'}
    if op == 'rreg':
        ctrl_payload = encode_rreg_cmd(chip, addr)
        chip_name = chip_id_to_name[ctrl_payload[4]]
    elif op == 'wreg':
        ctrl_payload = encode_wreg_cmd(chip, addr, val)
        chip_name = chip_id_to_name[ctrl_payload[4]]
    else:
        ctrl_payload = CLEAR_OVERRIDES_COMMAND
        chip_name = 'both'

    if op in ('rreg', 'wreg') and (not allow_real or expected is None):
        raise ValueError('在线寄存器读写 RREG/WREG 需显式传入 allow_real=True 与 expected build_id（仅限离体台架）')

    service = client.services.get_service(SERVICE)
    required_chars = {DATA, META, STATUS, CONTROL}
    if service is None or not required_chars.issubset({str(c.uuid).lower() for c in service.characteristics}):
        raise ValueError('设备缺少完整 C08B V12 BLE 服务特征')

    raw_meta = bytes(await asyncio.wait_for(client.read_gatt_char(META), 10))
    meta = validate_c08b_metadata(raw_meta, expected)
    raw_status = bytes(await asyncio.wait_for(client.read_gatt_char(STATUS), 10))
    initial_status = decode_status(raw_status)
    if initial_status['bench_measured'] != meta['bench_measured']:
        raise ValueError('META 与 STATUS 的台架锁状态不一致')
    if initial_status['active']:
        raise ValueError('设备正在流式采集中，请先停机再执行寄存器操作')

    if op in ('rreg', 'wreg'):
        if not meta['bench_measured']:
            raise ValueError('固件台架锁未解开（bench_measured=false），拒绝发送 RREG/WREG 命令')
        if meta['afe'] == 'UNKNOWN':
            raise ValueError('固件报告子板状态 UNKNOWN，拒绝执行 RREG/WREG')
        if initial_status['fault'] == 3:
            raise ValueError('固件处于 USB VBUS/OE_N 硬件互锁状态（fault=3），拒绝执行 RREG/WREG')
        if meta['afe'] in ('ADS1298_DUAL', 'ADS1298_SINGLE', 'ADS1292'):
            if meta['afe'] != 'ADS1298_DUAL' and chip_name == 'u2':
                raise ValueError(f'{meta["afe"]} 单芯片子板不支持读写 U2')
            if op == 'rreg' and meta['afe'] == 'ADS1292' and addr > 0x0B:
                raise ValueError(f'ADS1292 寄存器地址超出 0x00..0x0B：0x{addr:02X}')
            if op == 'wreg':
                targets = [1] if chip_name == 'u2' else ([0] if (chip_name == 'u1' or meta['afe'] != 'ADS1298_DUAL') else [0, 1])
                for c in targets:
                    ok, _vm = validate_c08b_reg_write_host(meta['afe'], c, addr, val)
                    if not ok:
                        raise ValueError(
                            f'主机安全掩码拦截危险寄存器写入：afe={meta["afe"]} chip=u{c + 1} addr=0x{addr:02X} val=0x{val:02X}'
                        )

    prev_seq = (meta.get('last_reg') or {}).get('seq')
    await asyncio.wait_for(client.write_gatt_char(CONTROL, ctrl_payload, response=True), 10)
    deadline = time.monotonic() + max(0.2, timeout)
    cur_meta = meta
    cur_status = initial_status
    while time.monotonic() < deadline:
        if not getattr(client, 'is_connected', True):
            raise RuntimeError(f'{op.upper()} 执行期间 BLE 连接中断或重连')
        await asyncio.sleep(min(0.05, poll_seconds))
        raw_m = bytes(await asyncio.wait_for(client.read_gatt_char(META), 10))
        cur_meta = validate_c08b_metadata(raw_m, expected)
        st_b = bytes(await asyncio.wait_for(client.read_gatt_char(STATUS), 10))
        cur_status = decode_status(st_b)
        if cur_status['fault']:
            raise RuntimeError(f'{op.upper()} 触发设备故障码 {cur_status["fault"]}')
        if op == 'clro':
            if not cur_status['active'] and cur_meta.get('reg_overrides', 0) == 0 and 'last_reg' not in cur_meta:
                return dict(
                    state='已完成（已实现未验收）',
                    op='clro',
                    afe=cur_meta['afe'],
                    protocol=cur_meta['protocol'],
                    active_channels=cur_meta['active_channels'],
                    build_id=cur_meta['build_id'],
                    reg_overrides=0,
                    stop_confirmed=True,
                    physical_device_verified=False,
                )
        else:
            lr = cur_meta.get('last_reg')
            if (
                not cur_status['active']
                and cur_meta['afe'] in ('ADS1298_DUAL', 'ADS1298_SINGLE', 'ADS1292')
                and lr is not None
                and lr.get('seq') != prev_seq
                and lr.get('addr') == addr
            ):
                if op == 'wreg':
                    targets = [1] if chip_name == 'u2' else ([0] if (chip_name == 'u1' or cur_meta['afe'] != 'ADS1298_DUAL') else [0, 1])
                    for c in targets:
                        ok, vm = validate_c08b_reg_write_host(cur_meta['afe'], c, addr, val)
                        got_v = lr['u1' if c == 0 else 'u2']
                        if not ok or (got_v & vm) != (val & vm):
                            raise RuntimeError(
                                f'WREG 回读校验不一致：chip=u{c + 1} addr=0x{addr:02X} 写 0x{val:02X} 读回 0x{got_v:02X}'
                            )
                return dict(
                    state='已完成（已实现未验收）',
                    op=op,
                    chip=chip_name,
                    addr=addr,
                    afe=cur_meta['afe'],
                    protocol=cur_meta['protocol'],
                    active_channels=cur_meta['active_channels'],
                    build_id=cur_meta['build_id'],
                    reg_overrides=cur_meta.get('reg_overrides', 0),
                    last_reg=lr,
                    stop_confirmed=True,
                    physical_device_verified=False,
                )

    raise RuntimeError(f'{op.upper()} 超时未收到固件寄存器应答（afe={cur_meta["afe"]}）')


def replay_c08b(directory, allow_real=False):
    """离线回放 C08B RawArchive 目录，返回有效采样矩阵 (µV) 与边界/丢样统计。"""
    directory = Path(directory)
    meta = json.loads((directory / 'metadata.json').read_text())
    adc = meta['adc_profile']
    proto = adc.get('transport_protocol', PROTO_V1_8CH)
    active_ch = adc.get('active_channels', adc.get('channels', 8))
    vref_mV = adc.get('vref_mV', int(round(adc.get('vref_V', 2.4) * 1000)))
    gain = adc.get('gain', 6)
    uv_scale = (vref_mV * 1e3) / (gain * (2 ** 23 - 1))

    codec = load_codec()
    decoder = decode_16ch if proto == PROTO_V4_16CH else codec.decode
    rx = codec.Receiver(allow_real=allow_real, decoder=decoder)
    rows = []
    bad_status = 0

    for line in (directory / 'events.jsonl').read_text().splitlines():
        event = json.loads(line)
        if event == {'disconnect': True}:
            rx.disconnect()
            continue
        pkt = rx.receive(bytes.fromhex(event['packet_hex']), event['mtu'])
        for f in pkt.frames:
            if not frame_status_valid(f, proto):
                bad_status += 1
                continue
            counts = decode_frame_16ch(f)[2] if proto == PROTO_V4_16CH else codec.decode_frame(f)[1]
            rows.append(counts[:active_ch])

    uv = np.asarray(rows, dtype=np.float64) * uv_scale if rows else np.zeros((0, active_ch), dtype=np.float64)
    imu_summary = None
    imu_events = directory / 'imu-events.jsonl'
    if imu_events.exists() and imu_events.read_text().strip():
        imu_rx = codec.Receiver(allow_real=allow_real, decoder=v12_imu.decode)
        imu_rows = []
        for line in imu_events.read_text().splitlines():
            ev = json.loads(line)
            if ev == {'disconnect': True}:
                imu_rx.disconnect()
                continue
            ipkt = imu_rx.receive(bytes.fromhex(ev['packet_hex']), ev['mtu'])
            dec = v12_imu.sample(ipkt.frames[0])
            imu_rows.append((*dec['gyro_raw'], *dec['accel_raw']))
        imu_summary = dict(
            samples=imu_rx.accepted_samples,
            missing_samples=imu_rx.missing_samples,
            sessions=imu_rx.sessions,
            raw=np.asarray(imu_rows, dtype=np.int16),
        )

    return dict(
        uv=uv,
        samples=len(uv),
        accepted_samples=rx.accepted_samples,
        missing_samples=rx.missing_samples,
        bad_status_frames=bad_status,
        sessions=rx.sessions,
        boundaries=list(rx.boundaries),
        protocol=proto,
        active_channels=active_ch,
        imu=imu_summary,
        calibration_verified=False,
        hardware_verified=False,
    )


def synth_c08b_packets(uv, profile=None, seq0=0, t0_us=1000, codec=None, reconfigure=False):
    """将 (n, active_ch) µV 矩阵按 C08B 2/8/16ch 规格编码为带 SYNTHETIC 标记的 F01 v1/v4 包。"""
    codec = codec or _CODEC
    arr = np.asarray(uv, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError('uv 必须是二维矩阵 (n, ch)')
    profile = profile or C08BAdcProfile.for_n_channels(arr.shape[1])
    if arr.shape[1] != profile.active_channels:
        raise ValueError(f'输入通道数 {arr.shape[1]} 与 profile.active_channels={profile.active_channels} 不符')

    counts = np.clip(np.round(arr / profile.uv_per_count), -0x800000, 0x7FFFFF).astype(np.int64)
    start_bits = SESSION_START | (RECONFIGURE if reconfigure else 0)
    if profile.transport_protocol == PROTO_V4_16CH:
        step = MAX_FRAMES_16CH
        for i in range(0, len(counts), step):
            frames = tuple(encode_frame_16ch(row) for row in counts[i:i + step])
            seq = seq0 + i
            flags = SYNTHETIC | (start_bits if seq == 0 else 0)
            ts = t0_us + seq * 1_000_000 // profile.fs_Hz
            yield encode_16ch(Packet(seq, ts, flags, frames))
    else:
        step = MAX_FRAMES_8CH
        for i in range(0, len(counts), step):
            batch = counts[i:i + step]
            if profile.active_channels < 8:
                pad = np.zeros((len(batch), 8 - profile.active_channels), dtype=np.int64)
                batch = np.concatenate([batch, pad], axis=1)
            frames = tuple(
                ADS_STATUS_OK + b''.join(int(v).to_bytes(3, 'big', signed=True) for v in row)
                for row in batch
            )
            seq = seq0 + i
            flags = SYNTHETIC | (start_bits if seq == 0 else 0)
            ts = t0_us + seq * 1_000_000 // profile.fs_Hz
            yield codec.encode(Packet(seq, ts, flags, frames))


def pack_c08b_imu_packet(seq, timestamp_us, raw6, flags=SYNTHETIC, read_latency_us=120):
    """构造与 firmware/c08b-stream c08b_pack_imu_pkt / v12_imu.decode 一致的 36B IMU 包。"""
    if len(raw6) != 6:
        raise ValueError('IMU 样本需包含 6 轴 int16 (gx, gy, gz, ax, ay, az)')
    hdr = HEADER.pack(1, 2, 1, flags, seq, timestamp_us)
    body = struct.pack('<6hBBBB I', *[int(x) for x in raw6], 0x03, 0, 0, 0, int(read_latency_us))
    return hdr + body


class C08BRig:
    """C08B 2/8/16 通道统一数据源，直接输出 float32 µV 与 6 轴 int16 IMU 给 AcqHandler。"""

    gyro_scale = C08B_IMU_PROFILE['gyro_dps_per_count'] * math.pi / 180.0
    acc_scale = C08B_IMU_PROFILE['accel_g_per_count'] * 9.80665

    def __init__(self, n_channels=16, fs_Hz=1000, allow_real=False, profile=None, raw_dir=None):
        self.profile = profile or C08BAdcProfile.for_n_channels(n_channels, fs_Hz=fs_Hz)
        if self.profile.active_channels != n_channels:
            raise ValueError('profile.active_channels 与 n_channels 不一致')
        self.n_channels = n_channels
        self.fs_Hz = self.profile.fs_Hz
        self.kind = f'c08b-{n_channels}ch'
        self.codec = load_codec()
        decoder = decode_16ch if self.profile.transport_protocol == PROTO_V4_16CH else self.codec.decode
        self.rx = self.codec.Receiver(allow_real=allow_real, decoder=decoder)
        self.imu_rx = self.codec.Receiver(allow_real=allow_real, decoder=v12_imu.decode)
        self.archive = _open_archive(raw_dir, self.profile, self.codec, allow_real) if raw_dir is not None else None
        if self.archive is not None:
            self.archive.enable_imu(C08B_IMU_PROFILE)
        self.subscribers = []
        self.frame_subscribers = []
        self.imu_subscribers = []
        self.chunk_subscribers = []
        self.boundary_subscribers = []
        self.bad_status = []
        self.seq = 0
        self.streaming = False
        self.link_since = None
        self.last_frame_at = None
        self.replay = 'C08B' if not allow_real else None
        self.banner = f'C08B {n_channels}ch 协议 v{self.profile.transport_protocol}（候选）'

    def open(self):
        self.streaming = True

    def subscribe(self):
        q = queue.Queue(maxsize=2000)
        self.subscribers.append(q)
        self.open()
        return q

    def unsubscribe(self, q):
        if q in self.subscribers:
            self.subscribers.remove(q)

    def take(self, *a, **k):
        raise ValueError('C08B 硬件锁关闭：尚未完成实物供电与时序验收，当前仅合成流预览，禁止写入训练集')

    def feed_packet(self, data, mtu=247):
        host_ns = time.monotonic_ns()
        if self.archive is not None:
            self.archive.write(dict(packet_hex=bytes(data).hex(), mtu=mtu))
        before = self.rx.missing_samples
        p = self.rx.receive(data, mtu)
        if p.flags & RECONFIGURE:
            ev = dict(self.rx.boundaries[-1])
            for cb in list(self.boundary_subscribers):
                cb(ev)
        self.seq = (self.seq + (self.rx.missing_samples - before)) & 0xFFFFFFFF

        proto = self.profile.transport_protocol
        good_rows = []
        seq_u8 = []
        for i, f in enumerate(p.frames):
            if not frame_status_valid(f, proto):
                self.bad_status.append(p.sequence + i)
                self.seq = (self.seq + 1) & 0xFFFFFFFF
                continue
            counts = decode_frame_16ch(f)[2] if proto == PROTO_V4_16CH else self.codec.decode_frame(f)[1]
            good_rows.append(counts[:self.n_channels])
            seq_u8.append(self.seq & 0xFF)
            self.seq = (self.seq + 1) & 0xFFFFFFFF

        if not good_rows:
            return
        now_wall = time.time()
        if self.link_since is None:
            self.link_since = now_wall
        self.last_frame_at = time.monotonic()
        emg_uv = (np.asarray(good_rows, dtype=np.float64) * self.profile.uv_per_count).astype(np.float32)
        imu_empty = np.zeros((0, 6), dtype=np.int16)
        seq_arr = np.asarray(seq_u8, dtype=np.uint8)
        kinds_arr = np.ones(len(seq_u8), dtype=np.uint8)
        for cb in list(self.chunk_subscribers):
            cb(emg_uv, imu_empty, seq_arr, kinds_arr, host_ns)
        for cb in list(self.frame_subscribers):
            cb(emg_uv)

    def feed_imu_packet(self, data, mtu=247):
        host_ns = time.monotonic_ns()
        if self.archive is not None:
            self.archive.write_imu(dict(packet_hex=bytes(data).hex(), mtu=mtu))
        p = self.imu_rx.receive(data, mtu)
        dec = v12_imu.sample(p.frames[0])
        imu_arr = np.asarray([[*dec['gyro_raw'], *dec['accel_raw']]], dtype=np.int16)
        emg_empty = np.zeros((0, self.n_channels), dtype=np.float32)
        seq_arr = np.asarray([self.seq & 0xFF], dtype=np.uint8)
        self.seq = (self.seq + 1) & 0xFFFFFFFF
        kinds_arr = np.asarray([2], dtype=np.uint8)
        for cb in list(self.chunk_subscribers):
            cb(emg_empty, imu_arr, seq_arr, kinds_arr, host_ns)
        for cb in list(self.imu_subscribers):
            cb(imu_arr)

    def disconnect(self):
        if self.archive is not None:
            self.archive.write({'disconnect': True})
        boundary = dict(
            reason='disconnect',
            previous_timestamp_us=self.rx.last_timestamp,
            next_timestamp_us=None,
            missing_samples=None,
        )
        self.rx.disconnect()
        self.imu_rx.disconnect()
        for cb in list(self.boundary_subscribers):
            cb(boundary)

    def close_capture(self):
        if self.archive is not None:
            self.archive.close()
            self.archive = None

    def status(self):
        return dict(
            port='c08b',
            kind='wl8',
            n_channels=self.n_channels,
            fs_Hz=self.fs_Hz,
            banner=self.banner,
            streaming=self.streaming,
            link='streaming' if self.streaming else 'waiting-band',
            link_since=self.link_since,
            replay=self.replay,
            c08b=dict(
                n_channels=self.n_channels,
                protocol=self.profile.transport_protocol,
                accepted_samples=self.rx.accepted_samples,
                missing_samples=self.rx.missing_samples,
                malformed=self.rx.malformed,
                reordered=self.rx.reordered,
                sessions=self.rx.sessions,
                bad_status_frames=len(self.bad_status),
                imu_samples=self.imu_rx.accepted_samples,
                adc_profile=asdict(self.profile),
                calibration_verified=False,
                hardware_verified=False,
            ),
        )


class SynthC08BRig(C08BRig):
    """合成 C08B 2/8/16ch + 6 轴 IMU 数据源：经真实 F01 v1/v4 与 v12_imu 编码器出包后再解码。"""

    def __init__(self, n_channels=16, fs_Hz=1000, seed=1, with_imu=True):
        super().__init__(n_channels=n_channels, fs_Hz=fs_Hz, allow_real=False)
        self.rng = np.random.default_rng(seed)
        self.with_imu = with_imu
        self.replay = 'C08B-SYNTH'
        self.banner = f'C08B {n_channels}ch 协议 v{self.profile.transport_protocol} FAKE · 合成数据，非实物'

    def open(self):
        if self.streaming:
            return
        self.streaming = True
        threading.Thread(target=self._play, daemon=True).start()

    def _play(self):
        block = max(8, self.fs_Hz // 50)  # 约 20 ms 一批
        n = 0
        imu_seq = 0
        t0 = time.monotonic()
        ch_idx = np.arange(self.n_channels, dtype=np.float64)
        base_sigma = 6.5 + 2.5 * np.sin(ch_idx * 1.1)
        while self.streaming:
            t_sec = (n + np.arange(block, dtype=np.float64)) / self.fs_Hz
            # 每 2.4 秒做一次平滑前臂局部肌群激活（0.9 s 收缩包络 + 1.5 s 放松底噪），模拟环腕电极空间分布差异
            phase = np.mod(t_sec, 2.4)
            env = np.where(phase < 0.9, np.sin(np.pi * np.clip(phase / 0.9, 0.0, 1.0)) ** 1.6, 0.0)
            cycle = int(n // int(2.4 * self.fs_Hz))
            center = (cycle * 0.37 * self.n_channels) % max(1, self.n_channels)
            dist = np.minimum(np.abs(ch_idx - center), self.n_channels - np.abs(ch_idx - center))
            width = max(0.75, self.n_channels * 0.18)
            spatial = np.exp(-0.5 * (dist / width) ** 2)
            sigma_mat = base_sigma[None, :] + (88.0 * env[:, None]) * spatial[None, :]
            carrier = 0.65 * self.rng.normal(0.0, 1.0, (block, self.n_channels)) + 0.35 * np.sin(
                2.0 * math.pi * (95.0 * t_sec[:, None] + ch_idx[None, :] * 0.43)
            ) * self.rng.normal(0.8, 0.35, (block, self.n_channels))
            uv = carrier * sigma_mat
            for pkt in synth_c08b_packets(uv, profile=self.profile, seq0=n, t0_us=1000, codec=self.codec):
                if not self.streaming:
                    return
                self.feed_packet(pkt)
            n += block

            if self.with_imu:
                target_imu = (n * 104) // self.fs_Hz
                while imu_seq < target_imu and self.streaming:
                    ts_us = 1000 + (imu_seq * 1_000_000) // 104
                    flags = SYNTHETIC | (SESSION_START if imu_seq == 0 else 0)
                    raw6 = (
                        int(30 * math.sin(imu_seq * 0.1)),
                        int(20 * math.cos(imu_seq * 0.1)),
                        -10,
                        0,
                        0,
                        4096,
                    )
                    self.feed_imu_packet(pack_c08b_imu_packet(imu_seq, ts_us, raw6, flags=flags))
                    imu_seq += 1

            time.sleep(max(0.0, t0 + n / self.fs_Hz - time.monotonic()))


async def run_dongle_c08b(
    port,
    output,
    seconds=5.0,
    mode=None,
    allow_real=False,
    expected=None,
    with_imu=False,
    synth_channels=16,
    fs_hz=None,
    open_ser=None,
    reconnect_timeout=15.0,
):
    """经 XIAO / ESP32-C6 USB 接收器（dongle_c08b 档，MAKO-DONGLE）建立全新 BLE 会话并采集 YUANLI-C08B。"""
    import v12_dongle  # 按需加载，保持纯离线编解码零串口耦合

    if open_ser is None:
        import serial
        open_ser = lambda p: serial.Serial(p, 115200, timeout=0.05)

    out_path = Path(output)
    ser, client = await v12_dongle.open_ready_dongle(port, open_ser)
    try:
        await asyncio.sleep(0.05)
        before = (client.link or {}).get('connects', 0)
        await client._cmd(ord('D'))
        deadline = time.monotonic() + reconnect_timeout
        while time.monotonic() < deadline:
            await client._cmd(ord('Q'))
            if client.ready and (client.link or {}).get('connects', 0) > before:
                break
            await asyncio.sleep(min(0.05, max(0.005, reconnect_timeout / 100.0)))
        if not (client.ready and (client.link or {}).get('connects', 0) > before):
            raise RuntimeError(
                f'接收器在 {reconnect_timeout:.1f}s 内未连上 YUANLI-C08B（请确认接收器已刷 dongle_c08b 且手环正在广播）'
            )
        client.start_connects = client.link['connects']
        try:
            res = await capture_c08b(
                client,
                out_path,
                seconds=seconds,
                mode=mode,
                allow_real=allow_real,
                expected=expected,
                with_imu=with_imu,
                synth_channels=synth_channels,
                fs_hz=fs_hz,
            )
            await client._cmd(ord('Q'))
            await asyncio.sleep(0.05)
            if not client.is_connected:
                summary_file = out_path / 'summary.json'
                if summary_file.exists():
                    res['ok'] = False
                    res['aborted_reason'] = 'dongle_tail_disconnected_or_reconnected'
                    summary_file.write_text(json.dumps(res, ensure_ascii=False, indent=2) + '\n')
                raise RuntimeError('C08B BLE 收尾链路查询发现中途断连或重连，本段采集作废（禁止重连拼接佩戴段）')
            res['transport'] = 'xiao_dongle'
            summary_file = out_path / 'summary.json'
            if summary_file.exists():
                summary_file.write_text(json.dumps(res, ensure_ascii=False, indent=2) + '\n')
            return res
        finally:
            query_error = None
            try:
                await client._cmd(ord('Q'))
                await asyncio.sleep(0.05)
            except Exception as err:
                query_error = str(err)
            if out_path.is_dir():
                evidence = dict(
                    link=client.link,
                    history=client.link_history,
                    junk_bytes=client.parser.junk,
                    final_query_error=query_error,
                )
                (out_path / 'dongle.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    finally:
        client.close()
        try:
            ser.close()
        except OSError:
            pass


async def run_dongle_reg_c08b(
    port,
    op,
    chip='both',
    addr=0,
    val=0,
    allow_real=False,
    expected=None,
    open_ser=None,
    connect_timeout=10.0,
    timeout=5.0,
):
    """经 MAKO-DONGLE USB 接收器 0xA5 串口帧执行在线 RREG / WREG / CLRO 寄存器操作。"""
    import v12_dongle

    if open_ser is None:
        import serial
        open_ser = lambda p: serial.Serial(p, 115200, timeout=0.05)

    ser, client = await v12_dongle.open_ready_dongle(port, open_ser)
    try:
        deadline = time.monotonic() + connect_timeout
        while time.monotonic() < deadline:
            await client._cmd(ord('Q'))
            if client.ready and client.link is not None:
                break
            await asyncio.sleep(min(0.05, max(0.005, connect_timeout / 100.0)))
        if not (client.ready and client.link is not None):
            raise RuntimeError(
                f'接收器在 {connect_timeout:.1f}s 内未就绪连接 YUANLI-C08B（请确认接收器已刷 dongle_c08b 且手环正在广播）'
            )
        client.start_connects = client.link['connects']
        res = await reg_op_c08b(
            client,
            op,
            chip=chip,
            addr=addr,
            val=val,
            allow_real=allow_real,
            expected=expected,
            timeout=timeout,
        )
        await client._cmd(ord('Q'))
        await asyncio.sleep(0.02)
        if not client.is_connected:
            raise RuntimeError(f'{op.upper()} 收尾链路查询发现中途断连或重连')
        res['transport'] = 'xiao_dongle'
        res['dongle_junk_bytes'] = client.parser.junk
        return res
    finally:
        client.close()
        try:
            ser.close()
        except OSError:
            pass


async def run_ble_c08b(
    address,
    output,
    seconds=5.0,
    mode=None,
    allow_real=False,
    expected=None,
    with_imu=False,
    synth_channels=16,
    fs_hz=None,
):
    """经 BleakClient 直连 YUANLI-C08B（注：macOS 会话若受 TCC 蓝牙限制请改用 --port 接收器通道）。"""
    from bleak import BleakClient

    async with BleakClient(address) as client:
        res = await capture_c08b(
            client,
            output,
            seconds=seconds,
            mode=mode,
            allow_real=allow_real,
            expected=expected,
            with_imu=with_imu,
            synth_channels=synth_channels,
            fs_hz=fs_hz,
        )
        res['transport'] = 'bleak_direct'
        summary_file = Path(output) / 'summary.json'
        if summary_file.exists():
            summary_file.write_text(json.dumps(res, ensure_ascii=False, indent=2) + '\n')
        return res


async def run_ble_reg_c08b(
    address,
    op,
    chip='both',
    addr=0,
    val=0,
    allow_real=False,
    expected=None,
    timeout=5.0,
):
    """经 BleakClient 直连 YUANLI-C08B 执行在线 RREG / WREG / CLRO 寄存器操作。"""
    from bleak import BleakClient

    async with BleakClient(address) as client:
        res = await reg_op_c08b(
            client,
            op,
            chip=chip,
            addr=addr,
            val=val,
            allow_real=allow_real,
            expected=expected,
            timeout=timeout,
        )
        res['transport'] = 'bleak_direct'
        return res


def _self_check():
    for n_ch, proto in ((16, PROTO_V4_16CH), (8, PROTO_V1_8CH), (2, PROTO_V1_8CH)):
        prof = C08BAdcProfile.for_n_channels(n_ch, fs_Hz=1000)
        rig = C08BRig(n_channels=n_ch, fs_Hz=1000)
        got = []
        rig.chunk_subscribers.append(lambda emg, imu, seq, kinds, ns: got.append(emg))
        uv = np.linspace(-120.0, 120.0, 16 * n_ch, dtype=np.float64).reshape(16, n_ch)
        for pkt in synth_c08b_packets(uv, profile=prof):
            assert len(pkt) <= 232
            rig.feed_packet(pkt)
        out = np.concatenate(got, axis=0)
        assert out.shape == (16, n_ch)
        assert np.max(np.abs(out - uv)) < 0.1, f'{n_ch}ch 往返误差过大'
        st = rig.status()
        assert st['kind'] == 'wl8' and st['n_channels'] == n_ch and st['fs_Hz'] == 1000
        assert st['c08b']['protocol'] == proto
    assert parse_rreg_spec('CH1SET') == ('both', 0x05)
    assert parse_rreg_spec('u2:0x03') == ('u2', 0x03)
    assert parse_wreg_spec('both:CH1SET=0x60') == ('both', 0x05, 0x60)
    assert encode_rreg_cmd('u1', 0x05) == b'RREG\x00\x05'
    assert encode_wreg_cmd('both', 0x05, 0x60) == b'WREG\x02\x05\x60'
    assert validate_c08b_reg_write_host('ADS1298_DUAL', 0, 0x03, 0xC4) == (True, 0xFE)
    assert not validate_c08b_reg_write_host('ADS1298_DUAL', 0, 0x03, 0xCC)[0]
    assert not validate_c08b_reg_write_host('ADS1298_DUAL', 0, 0x03, 0xD4)[0]
    assert not validate_c08b_reg_write_host('ADS1298_DUAL', 1, 0x03, 0xC4)[0]
    assert not validate_c08b_reg_write_host('ADS1298_DUAL', 0, 0x05, 0x02)[0]
    print('c08b_stream --check: 2ch / 8ch / 16ch 编解码与寄存器安全掩码冒烟通过')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='运行 2/8/16ch 编解码与寄存器安全掩码快速自检')
    parser.add_argument('--replay', type=Path, help='离线回放 C08B RawArchive 目录')
    parser.add_argument('--port', help='MAKO-DONGLE (dongle_c08b 档) USB 串口路径，如 /dev/cu.usbmodemXXX')
    parser.add_argument('--address', help='BLE 设备地址或 UUID（直连模式）')
    parser.add_argument('--out', type=Path, help='新采集归档输出目录（寄存器单次命令可选 JSON 输出路径）')
    parser.add_argument(
        '--mode',
        choices=('status', *ALL_COMMANDS.keys()),
        default='status',
        help='采集模式：status 只读诊断 / synth 双核无电合成流 / probe 只读探测 / test|short|rld_diag|rld|external 台架实采',
    )
    parser.add_argument('--seconds', type=float, default=5.0, help='采集时长（秒）')
    parser.add_argument('--fs-hz', type=int, choices=(500, 1000, 2000), default=None, help='在线指定流式采样率（500 / 1000 / 2000 Hz）')
    parser.add_argument('--synth-channels', type=int, choices=(2, 8, 16), default=16, help='SYN1 合成流通道档位')
    parser.add_argument('--with-imu', action='store_true', help='同时订阅并归档 6 轴 IMU_DATA 流')
    parser.add_argument('--rreg', help='在线读取 ADS 寄存器（如 0x00、CONFIG3、u1:CH1SET；需配合 --allow-real 与 --expected）')
    parser.add_argument('--wreg', help='在线安全写入并回读核验 ADS 寄存器（如 both:CH1SET=0x60；需配合 --allow-real 与 --expected）')
    parser.add_argument('--clear-reg-overrides', action='store_true', help='清空运行期全部 ADS 寄存器覆盖项（CLRO）')
    parser.add_argument('--expected', help='真实采集、PRB1 探测或 RREG/WREG 要求的 16 位十六进制固件 build_id')
    parser.add_argument('--allow-real', action='store_true', help='离体台架真实采集/寄存器读写或真实归档回放显式放行开关')
    args = parser.parse_args()
    if args.check:
        _self_check()
        return 0
    if args.replay is not None:
        res = replay_c08b(args.replay, allow_real=args.allow_real)
        res_out = {k: v for k, v in res.items() if k != 'uv'}
        if res_out.get('imu') is not None:
            res_out['imu'] = {k: v for k, v in res_out['imu'].items() if k != 'raw'}
        print(json.dumps(res_out, ensure_ascii=False, indent=2))
        return 0
    if args.port or args.address:
        if args.port and args.address:
            parser.error('--port 与 --address 只能二选一')
        reg_ops = sum((args.rreg is not None, args.wreg is not None, bool(args.clear_reg_overrides)))
        if reg_ops > 1:
            parser.error('--rreg、--wreg 与 --clear-reg-overrides 单次只能三选一')
        if reg_ops == 1:
            if args.rreg is not None:
                op, (chip, addr), val = 'rreg', parse_rreg_spec(args.rreg), 0
            elif args.wreg is not None:
                op = 'wreg'
                chip, addr, val = parse_wreg_spec(args.wreg)
            else:
                op, chip, addr, val = 'clro', 'both', 0, 0
            if args.port:
                res = asyncio.run(run_dongle_reg_c08b(
                    args.port, op, chip=chip, addr=addr, val=val,
                    allow_real=args.allow_real, expected=args.expected,
                ))
            else:
                res = asyncio.run(run_ble_reg_c08b(
                    args.address, op, chip=chip, addr=addr, val=val,
                    allow_real=args.allow_real, expected=args.expected,
                ))
            if args.out is not None:
                if args.out.exists():
                    raise FileExistsError(f'输出路径已存在：{args.out}')
                args.out.write_text(json.dumps(res, ensure_ascii=False, indent=2) + '\n')
            print(json.dumps(res, ensure_ascii=False, indent=2))
            return 0
        if args.out is None:
            parser.error('在线采集或状态读取必须指定 --out <新归档目录>')
        capture_mode = None if args.mode == 'status' else args.mode
        if args.port:
            res = asyncio.run(run_dongle_c08b(
                args.port,
                args.out,
                seconds=args.seconds,
                mode=capture_mode,
                allow_real=args.allow_real,
                expected=args.expected,
                with_imu=args.with_imu,
                synth_channels=args.synth_channels,
                fs_hz=args.fs_hz,
            ))
        else:
            res = asyncio.run(run_ble_c08b(
                args.address,
                args.out,
                seconds=args.seconds,
                mode=capture_mode,
                allow_real=args.allow_real,
                expected=args.expected,
                with_imu=args.with_imu,
                synth_channels=args.synth_channels,
                fs_hz=args.fs_hz,
            ))
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    parser.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())

"""设备层入口（EMG_UNIVERSAL_APP §2.1 / EMG_STUDIO_V2_PLAN B.1）：

    desc = device_desc.load('fake')
    rig  = build_rig(desc)             # 现有 Wl8Rig / FakeWl8Rig / ReplayWl8Rig / SynthV12Rig / Cheez Rig，按描述挑
    acq  = AcqHandler(rig, desc)       # 统一 open / start / stop / status / subscribe / record

黑客松阶段只「包」不「拆」：旧 Rig 类原样保留，AcqHandler 把它们的订阅链路翻译成统一块。
"""
from .acq import AcqHandler, Block, build_rig

__all__ = ['AcqHandler', 'Block', 'build_rig']

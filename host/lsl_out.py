"""LSL 出流（可选）：有 pylsl 才能开；没有就 available() = False，接口照常返回 {'ok': False, 'why': ...}。
不做 LSL 入流——OpenSignals 也只出不入。"""
try:
    import pylsl
except ImportError:
    pylsl = None


def available():
    return pylsl is not None


class Outlet:
    def __init__(self, desc, name=None):
        if pylsl is None:
            raise RuntimeError('没有 pylsl：pip install pylsl 后再开 LSL')
        info = pylsl.StreamInfo(name or f'yuanli-{desc.id}', 'EMG', desc.n_channels, desc.fs_Hz, 'float32', f'yuanli-{desc.id}')
        chs = info.desc().append_child('channels')
        for c in desc.channels:
            ch = chs.append_child('channel')
            ch.append_child_value('label', c['label'])
            ch.append_child_value('unit', 'microvolts')
            ch.append_child_value('type', c.get('sensor', 'EMG'))
        self.outlet = pylsl.StreamOutlet(info, chunk_size=32)
        self.name = info.name()
        self.pushed = 0

    def push(self, block):
        self.outlet.push_chunk(block.uv.astype('float32').tolist())
        self.pushed += len(block.uv)

    def close(self):
        self.outlet = None

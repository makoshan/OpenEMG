"""LSL 出流门禁：没有 pylsl 打印 SKIP 且 available()=False、Outlet 构造必失败；有 pylsl 则开流推 1 块、本机 resolve 到流名。"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import device_desc as dd
import lsl_out
from rig import Block


def main():
    desc = dd.load('fake')
    if not lsl_out.available():
        try:
            lsl_out.Outlet(desc)
            raise AssertionError('没有 pylsl 却建了 Outlet')
        except RuntimeError as e:
            print(f'  红 ✓ 无 pylsl 时拒绝: {e}')
        print('check_lsl: SKIP（环境无 pylsl；available()=False，接口照常拒绝）')
        return
    o = lsl_out.Outlet(desc, name='yuanli-check')
    b = Block('fake', np.zeros((64, 8), np.float32), np.zeros((64, 8), np.int32), np.arange(64, dtype=np.uint32), np.zeros(1, np.int64))
    o.push(b)
    found = [s.name() for s in lsl_out.pylsl.resolve_byprop('name', 'yuanli-check', timeout=3)]
    assert 'yuanli-check' in found and o.pushed == 64, found
    o.close()
    print(f'check_lsl: 开流 yuanli-check 推 64 帧，本机 resolve 到 {found}')


if __name__ == '__main__':
    main()

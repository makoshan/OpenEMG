"""只修补F04构建副本，绝不写回共享PlatformIO包。"""
import hashlib

BLUEFRUIT_SHA256 = '95f267709779cdbca963ae5872b0be7e9dcd16a01045c7fc09f684c150c256f1'


def patched_bluefruit(source):
    if hashlib.sha256(source).hexdigest() != BLUEFRUIT_SHA256:
        raise ValueError('SDK源码已变，必须重新审查断连路径，禁止模糊套补丁')
    before = b'''      delete _connection[conn_hdl];
      _connection[conn_hdl] = NULL;
    }
    break;

    case BLE_GAP_EVT_RSSI_CHANGED:'''
    after = before.replace(b'      _connection[conn_hdl] = NULL;',
                           b'      _connection[conn_hdl] = NULL;\n      conn = NULL; // F04: prevent role dispatch through a freed connection')
    if source.count(before) != 1:
        raise ValueError('断连补丁锚点不是唯一，停止构建')
    return source.replace(before, after)

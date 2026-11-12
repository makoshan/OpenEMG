"""`/studio` 预览页门禁：页面里每条 `/api/...` 调用（方法 + 路径）都要在服务端存在；`emg_web.py --device fake` 起服务后
`/studio` 返回这页、页面直接读的 GET 路由都 200。必失败：往页面文本里塞一条不存在的路由，契约检查必须报出来。"""
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import studio_api
from check_studio_api import Server, call

PAGE = HERE / 'emg_studio.html'
SERVICE_GET = {'/api/emg/state', '/api/emg/stream8'}          # emg_web.py 自己的路由，不在 studio_api.ROUTES


def page_calls(text):
    calls = {(m, p) for m, p in re.findall(r"send\('([A-Z]+)','(/api/[a-z0-9_/]+)", text)}
    calls |= {('GET', p) for p in re.findall(r"(?:get\(|EventSource\()[`']([^`'?$]+)", text) if p.startswith('/api/')}
    return calls


def missing(calls):
    return sorted(c for c in calls if c not in studio_api.ROUTES and not (c[0] == 'GET' and c[1] in SERVICE_GET))


def main():
    text = PAGE.read_text()
    calls = page_calls(text)
    assert len(calls) >= 14, f'只解析出 {len(calls)} 条调用，解析规则可能坏了：{sorted(calls)}'
    assert not missing(calls), f'页面调用了服务端没有的路由：{missing(calls)}'
    print(f'  页面 {len(calls)} 条 /api 调用全部在服务端存在')
    bad = missing(page_calls(text + "\nsend('POST','/api/take/rewind')"))
    assert bad == [('POST', '/api/take/rewind')], bad
    print('  红 ✓ 不存在的路由被报出：POST /api/take/rewind')

    with tempfile.TemporaryDirectory() as tmp, Server('--device', 'fake', '--data', tmp) as srv:
        code, body = call(srv.port, '/studio')
        assert code == 200 and b'EMG Studio' in body, (code, body[:80])
        for path in ('/api/emg/state?view=capture', '/api/device/state', '/api/files/list', '/api/dataset/list', '/api/train/runs'):
            code, _ = call(srv.port, path)
            assert code == 200, (path, code)
        print('  --device fake：/studio 与页面读的 5 条 GET 都是 200')
    print('check_studio_page: 页面路由契约 + 服务可达 通过，1 条必失败红')


if __name__ == '__main__':
    main()

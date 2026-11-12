"""原力手环当 AI 的确认键：Claude Code 的 PreToolUse 钩子（只管 Bash）。

流程：Claude Code 要跑一条命令 → 本钩子判断是不是「白名单里的低风险单条命令」→ 是就用耳机念出来，等手环手势：
  食指碰拇指（按住）= 同意 → 返回 allow；中指碰拇指 = 拒绝 → 返回 deny；20 秒没手势 / 手环没数据 → deny。
不在白名单的命令（含管道、重定向、删除、推送、sudo……）一律不表态（退出 0、不输出），回到 Claude Code 正常的弹窗询问。
官方协议：allow 不会绕过 settings 里的 deny 规则；钩子超时 = 不表态（https://code.claude.com/docs/en/hooks.md）。

识别：读采集服务 /api/emg/state 的 wl8.live.last（每 50 ms 一次的各类概率）。同意比拒绝要求更高把握（不对称）：
  同意：meta_index 概率 ≥ 0.85 连续 0.35 s；拒绝：meta_middle 概率 ≥ 0.6 连续 0.2 s。拿不准就继续等。
2026-10-05 离线：按住接触三类跨佩戴 87–100%（去掉离群的第 1 次佩戴，evidence/2026-10-05-meta-rewear.md）；唯一见过的错是「拒绝 → 同意」，所以同意门槛高。
日志只记时间、决定、原因和命令哈希（不记命令原文，免得命令里带的密钥进日志）。

演示开关（2026-10-06 加）：钩子写在仓库设置里会影响在本仓库工作的所有 Claude 会话，所以默认关闭——
开关文件不存在或已过期时直接不表态（不找服务、不念、不等）。演示时打开，到时自动失效：
  python3 host/ai_confirm.py --on 30   # 打开 30 分钟（最多 240）
  python3 host/ai_confirm.py --off     # 立刻关闭
  python3 host/ai_confirm.py --status
Run: python3 host/ai_confirm.py --check     # 回放自检，不碰手环、不出声
钩子：在 .claude/settings.local.json 的 hooks.PreToolUse 里 matcher "Bash" 指向本文件（timeout 30）

推到 Apple Watch（2026-10-16 加，参考 ghy196830-del/agent-watch-approve）：等确认时、以及 Stop 钩子（--stop）各推一条到自建 ntfy，
iPhone 的 ntfy App 收到后镜像到 Watch。只推项目名、命令类别、命令短哈希，不推命令原文。表上只负责「看到」，同意 / 拒绝仍用手势。
配置在 NTFY_ENV（NTFY_URL / NTFY_TOPIC / NTFY_TOKEN，chmod 600，不进仓库）；没配置或推送失败都不影响确认。同样受演示开关控制。
不戴手环演示：先开 host/gesture_sim.py（a 同意 / d 拒绝），它把地址写进 SERVICE_FILE，本钩子优先用它。
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

APPROVE, REJECT = ('_index', .85, .35), ('_middle', .6, .2)      # (类别后缀, 概率门槛, 连续秒数)：meta_index / mouse_index 都算食指
WAIT_S, STALE_S, POLL_S = 20., 3., .05
ARM_S = .15                                                                  # 连续这么久低于门槛才算「松开」，单帧掉概率不算
LOG = Path.home() / '.local/state/yuanli/ai_confirm.log'
SERVICE_FILE = Path.home() / '.local/state/yuanli/service.url'                # 手势模拟器运行时写的地址
NTFY_ENV = Path.home() / '.config/yuanli/ntfy.env'
SWITCH = Path.home() / '.local/state/yuanli/ai_confirm.on'                  # 演示开关：文件内容是到期时间（秒）；没有、读不懂、过期 = 关
SAFE = [r'npm (test|run (test|lint|check|build))', r'(python3?|uv run python) [\w./-]+\.py --check', r'pytest( [\w./:-]+)*',
        r'git (status|diff|log)( [\w./=-]+)*', r'ls( -[a-zA-Z]+)?( [\w./-]+)*', r'(cat|head|tail|wc) [\w./-]+']
CATEGORY = ['npm 检查', '脚本自检', 'pytest', 'git 只读', '列目录', '读文件']        # 与 SAFE 一一对应，推送只发类别
UNSAFE = re.compile(r'[;&|<>`$\\]|\brm\b|\bsudo\b|\bgit push\b|\bcurl\b|\bwget\b|\bchmod\b|\bmv\b'
                    r'|\.env\b|\.pem\b|id_rsa|\.ssh\b|credential|secret|token')     # 敏感文件：cat .env 能过白名单，会把密钥读进对话


def enabled(now=None, path=None):
    """到期时间要在「现在」和「现在 + 240 分钟」之间才算开：手写 inf 或很远的时间也算关（独立复核指出）。"""
    now = time.time() if now is None else now
    try: return now < float((path or SWITCH).read_text().strip()) <= now + 240 * 60 + 60
    except (OSError, ValueError): return False


def switch(args, path=None):
    """--on [分钟] / --off / --status；返回给人看的一行。"""
    path = path or SWITCH
    if args[0] == '--on':
        minutes = min(240., max(1., float(args[1]) if len(args) > 1 else 30.))
        path.parent.mkdir(parents=True, exist_ok=True); path.write_text(str(time.time() + minutes * 60))
        return f'确认键已打开 {minutes:.0f} 分钟，到 {time.strftime("%H:%M", time.localtime(time.time() + minutes * 60))} 自动关闭'
    if args[0] == '--off':
        path.unlink(missing_ok=True); return '确认键已关闭'
    if enabled(path=path): return f'确认键打开中，到 {time.strftime("%H:%M", time.localtime(float(path.read_text())))} 自动关闭'
    return '确认键关闭（钩子不表态，Claude Code 照常询问）'


def eligible(cmd):
    """只有白名单里的单条命令才走手环；任何管道 / 重定向 / 删除类字眼都不碰（交回正常询问）。"""
    c = cmd.strip()
    return bool(c) and not UNSAFE.search(c) and any(re.fullmatch(p, c) for p in SAFE)


def decide(samples, start, now):
    """samples：[(t, {类别: 概率})] 按时间排序，只看 start 之后的。返回 'allow' / 'deny' / None（还没定）。
    连续满足要求的样本跨度 ≥ 规定秒数才算；中间断一次就重新计。
    必须先在 start 之后见到「没按」才上膛：上一条确认还捏着没松的手指不能顺带批下一条（2026-10-16 模拟器端到端测出连批）。"""
    run = {APPROVE[0]: None, REJECT[0]: None}
    low = {APPROVE[0]: None, REJECT[0]: None}
    armed = {APPROVE[0]: False, REJECT[0]: False}
    for t, probs in samples:
        if t < start: continue
        for lab, th, need in (REJECT, APPROVE):                              # 先看拒绝：两边同时满足时宁可拒绝
            if max((v for k, v in probs.items() if k.endswith(lab)), default=0) >= th:
                low[lab] = None
                if not armed[lab]: continue
                run[lab] = run[lab] if run[lab] is not None else t
                if t - run[lab] >= need: return 'deny' if lab == REJECT[0] else 'allow'
            else:
                run[lab] = None
                low[lab] = low[lab] if low[lab] is not None else t
                if t - low[lab] >= ARM_S: armed[lab] = True
    return None


def category(cmd):
    return next((CATEGORY[i] for i, p in enumerate(SAFE) if re.fullmatch(p, cmd.strip())), '其他')


def read_env(text):
    """KEY=VALUE 每行一项；跳过空行和 # 注释，去掉两边空格和引号。"""
    cfg = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k, v = line.split('=', 1); cfg[k.strip()] = v.strip().strip('\'"')
    return cfg


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None                      # 跳转一律当失败：免得带着令牌跟到别处


_OPEN = urllib.request.build_opener(_NoRedirect).open


def note(msg):
    """推送失败原因写进确认日志（不带令牌、不带命令）。"""
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open('a') as f: f.write(json.dumps({'t': time.strftime('%F %T'), 'push': msg}, ensure_ascii=False) + '\n')
    except OSError: pass


def push(title, message, cfg=None, opener=None):
    """推一条到自建 ntfy（JSON 发布，中文不走 HTTP 头）。返回是否发出；失败只记原因，不影响确认。"""
    try:
        if cfg is None:
            if not NTFY_ENV.exists(): return False                            # 没配置：静默不推
            cfg = read_env(NTFY_ENV.read_text())
        url, topic, token = (cfg.get(k, '') for k in ('NTFY_URL', 'NTFY_TOPIC', 'NTFY_TOKEN'))
        if not (url.startswith('https://') and topic and token): note('配置不全或不是 https'); return False
        body = {'topic': topic, 'title': title, 'message': message, 'priority': 4, 'tags': ['watch']}
        (opener or _OPEN)(urllib.request.Request(url.rstrip('/'), data=json.dumps(body, ensure_ascii=False).encode(), method='POST',
                                                 headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token,
                                                          'User-Agent': 'yuanli-ai-confirm/1'}), timeout=8)   # Cloudflare 浏览器完整性检查会拦 Python-urllib（1010）
        return True
    except Exception as e: note(f'推送失败：{type(e).__name__}'); return False


def project_name(ev):
    return Path(os.environ.get('CLAUDE_PROJECT_DIR') or ev.get('cwd') or os.getcwd()).name


def find_service():
    """App 起的采集服务端口是随机的：按进程名找 emg8-server.py / emg_web.py 正在监听的端口，再用 /api/emg/state 确认是八通道。"""
    if os.environ.get('YUANLI_SERVICE'): return os.environ['YUANLI_SERVICE']
    try:                                                                       # 手势模拟器在跑就用它；文件残留但服务已停则继续找真服务
        st, sim = SERVICE_FILE.stat(), SERVICE_FILE.read_text().strip()
        u = urllib.parse.urlsplit(sim)
        if (st.st_uid == os.getuid() and not st.st_mode & 0o077 and u.scheme == 'http' and u.hostname == '127.0.0.1'
                and u.port and not u.username and not u.password and u.path in ('', '/')
                and (json.load(urllib.request.urlopen(sim + '/api/emg/state', timeout=2)).get('rig') or {}).get('kind') == 'wl8'):
            return sim
    except Exception: pass
    out = subprocess.run(['lsof', '-nP', '-iTCP', '-sTCP:LISTEN', '-Fpcn'], capture_output=True, text=True).stdout
    pid, ports = '', []
    for line in out.splitlines():
        if line.startswith('p'): pid = line[1:]
        if line.startswith('n') and ':' in line and pid:
            cmd = subprocess.run(['ps', '-o', 'command=', '-p', pid], capture_output=True, text=True).stdout
            if 'emg8-server.py' in cmd or 'emg_web.py' in cmd: ports.append(line.rsplit(':', 1)[1])
    for p in ports:
        try:
            st = json.load(urllib.request.urlopen(f'http://127.0.0.1:{p}/api/emg/state', timeout=2))
            if (st.get('rig') or {}).get('kind') == 'wl8': return f'http://127.0.0.1:{p}'
        except Exception: pass
    return None


def live_samples(base):
    """确保实时识别在跑（没跑就用最新模型启动），返回一个取样函数：每次调用返回 (t, probs) 或 None。"""
    st = json.load(urllib.request.urlopen(base + '/api/emg/state', timeout=2))
    if not (st.get('wl8') or {}).get('live'):
        proj = (st.get('project') or {}).get('id', '')
        req = urllib.request.Request(base + '/api/emg/wl8/live', data=json.dumps({'action': 'start'}).encode(), method='POST',
                                     headers={'Content-Type': 'application/json', 'X-Mako-Collector': '1', 'X-Mako-Project': proj})
        urllib.request.urlopen(req, timeout=5)
    def one():
        last = ((json.load(urllib.request.urlopen(base + '/api/emg/state', timeout=2)).get('wl8') or {}).get('live') or {}).get('last')
        return None if not last else (float(last['t']), dict(last.get('probs') or {}))
    return one


def wait_gesture(sample, clock=time.time, sleep=time.sleep):
    """念完之后开始计时：返回 (决定, 原因)。手环数据超过 STALE_S 没更新就拒绝。"""
    start, seen, last_new = clock(), [], clock()
    while clock() - start < WAIT_S:
        s = sample()
        if s and (not seen or s[0] > seen[-1][0]): seen.append(s); last_new = clock()
        if clock() - last_new > STALE_S: return 'deny', '手环没有数据（超过 3 秒没更新）'
        d = decide(seen, start, clock())
        if d: return d, '手环：食指碰拇指（同意）' if d == 'allow' else '手环：中指碰拇指（拒绝）'
        sleep(POLL_S)
    return 'deny', f'{WAIT_S:.0f} 秒内没等到手势'


def say(text):
    if not os.environ.get('YUANLI_MUTE'): subprocess.run(['say', '-v', 'Tingting', text], timeout=15)


def log(decision, reason, cmd):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open('a') as f: f.write(json.dumps({'t': time.strftime('%F %T'), 'decision': decision, 'reason': reason, 'cmd_sha8': hashlib.sha256(cmd.encode()).hexdigest()[:8]}, ensure_ascii=False) + '\n')


def post(base, path, body):
    """向采集服务发一条通知（带本工程头）。失败不影响确认本身。"""
    if not base: return
    try:
        st = json.load(urllib.request.urlopen(base + '/api/emg/state', timeout=2))
        req = urllib.request.Request(base + path, data=json.dumps(body).encode(), method='POST',
                                     headers={'Content-Type': 'application/json', 'X-Mako-Collector': '1', 'X-Mako-Project': (st.get('project') or {}).get('id', '')})
        urllib.request.urlopen(req, timeout=2)
    except Exception: pass


def simulated(base):
    try: return bool((json.load(urllib.request.urlopen(base + '/api/emg/state', timeout=2)).get('rig') or {}).get('simulated'))
    except Exception: return False


def hold_mouse(base, what):
    """让采集服务暂停 / 恢复手势鼠标（host/wl8_actions.py）。"""
    post(base, '/api/emg/wl8/action', {'action': what, 'seconds': WAIT_S + 5})


def tell_app(base, body):
    """App「AI 授权」卡：开始等确认（pending，带命令）/ 判完（done，带决定、原因、毫秒）。"""
    post(base, '/api/emg/wl8/ai', body)


def main(stdin=sys.stdin, stdout=sys.stdout, sample=None, base=None, on=None):
    ev = json.load(stdin)
    cmd = (ev.get('tool_input') or {}).get('command', '')
    if not (enabled() if on is None else on): return 0                           # 演示开关没开：不表态，不找服务、不念
    if ev.get('tool_name') != 'Bash' or not eligible(cmd): return 0                # 不表态：正常询问
    if sample is None:
        base = find_service()
        if not base: log('none', '没找到采集服务', cmd); return 0                   # 手环服务不在：不表态，回到弹窗
        try: sample = live_samples(base)
        except Exception as e: log('none', f'启动实时识别失败：{type(e).__name__}', cmd); return 0
    # 先暂停手势鼠标再念：念提示要好几秒，提前做的「食指同意」不能顺带点一下左键
    hold_mouse(base, 'pause')
    decision, reason = 'deny', '钩子出错'
    try:
        tell_app(base, {'action': 'pending', 'cmd': cmd, 'timeout': WAIT_S})
        sha8 = hashlib.sha256(cmd.encode()).hexdigest()[:8]                     # 后台推送，不占 20 s 等待（钩子总超时 30 s）
        threading.Thread(target=push, args=('原力手环 · 待确认', f'{project_name(ev)} · {category(cmd)} · {sha8}\n食指同意 / 中指拒绝（{WAIT_S:.0f} 秒）'), daemon=True).start()
        say(f'Claude 要运行：{cmd[:60]}。食指同意，中指拒绝')
        t0 = time.time()
        decision, reason = wait_gesture(sample)
        if base and simulated(base): reason = reason.replace('手环：', '模拟器：')        # 审计日志分得清真手环还是模拟器
        tell_app(base, {'action': 'done', 'decision': decision, 'reason': reason, 'ms': round((time.time() - t0) * 1000)})
    finally: hold_mouse(base, 'resume')
    log(decision, reason, cmd)
    json.dump({'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': decision, 'permissionDecisionReason': reason}}, stdout, ensure_ascii=False)
    return 0


def stop_hook(stdin=sys.stdin, on=None, send=None):
    """Stop 钩子：Claude 一轮结束推「任务完成」。不输出、不阻止停止；演示开关关着就什么都不做。"""
    ev = json.load(stdin)
    if not (enabled() if on is None else on): return False
    return (send or push)('原力手环 · 任务完成', f'{project_name(ev)} · Claude 本轮已结束，回来验收')


def check():
    import io, tempfile
    os.environ['YUANLI_MUTE'] = '1'
    globals()['NTFY_ENV'] = Path('/nonexistent/ntfy.env')                    # 自检绝不往真手机推
    globals()['LOG'] = Path(tempfile.mkdtemp()) / 'ai_confirm.log'            # 也不写真实日志
    assert eligible('npm test') and eligible('git status') and eligible('python3 host/wl8.py --check')
    for bad in ('rm -rf build', 'git push origin main', 'npm test && rm x', 'cat a | sh', 'ls > out', 'curl x', 'sudo ls', 'npm install', 'echo $KEY'):
        assert not eligible(bad), bad
    for secret in ('cat .env', 'cat firmware/.env', 'head key.pem', 'cat ~/.ssh/id_rsa', 'ls .ssh', 'cat aws_credentials'):   # 这些能过白名单，只靠敏感词拦
        assert not eligible(secret), ('敏感文件被手环放行', secret)
    p = lambda i, m: {'meta_index': i, 'meta_middle': m, 'meta_rest': 1 - i - m}
    loose = [(k * .05, {'mouse_rest': 1}) for k in range(5)]                  # 先松开 0.2 s（上膛要 ARM_S）
    assert decide(loose + [(.25 + k * .05, {'mouse_index': .9, 'mouse_middle': 0, 'mouse_rest': .1}) for k in range(9)], 0, 1) == 'allow', '鼠标八类组的食指没认成同意'
    assert decide(loose + [(.25 + k * .05, {'mouse_index': 0, 'mouse_middle': .7, 'mouse_left': .3}) for k in range(6)], 0, 1) == 'deny', '鼠标八类组的中指没认成拒绝'
    hold = lambda probs, secs, t0=0.: [(t0 + k * .05, p(0, 0)) for k in range(5)] + [(t0 + .25 + k * .05, probs) for k in range(int(secs / .05) + 1)]
    assert decide(hold(p(.9, 0), .4), 0, 1) == 'allow'
    assert decide(hold(p(.8, 0), 2), 0, 3) is None, '同意把握 0.8 低于门槛却放行了'
    assert decide(hold(p(.9, 0), .2), 0, 1) is None, '只按了 0.2 秒就放行了'
    assert decide(hold(p(0, .7), .25), 0, 1) == 'deny'
    flick = [(k * .05, p(.9 if k % 4 else 0, 0)) for k in range(40)]            # 每 4 帧断一次：不连续，不算
    assert decide(flick, 0, 2) is None, '断断续续的食指被当成同意'
    assert decide(hold(p(.9, 0), 1, t0=-2), 0, 1) is None, '念完之前的手势被算进去了'
    both = [(k * .05, p(0, 0)) for k in range(5)] + [(.25 + k * .05, {'meta_index': .9, 'meta_middle': .65 if k >= 3 else 0}) for k in range(12)]   # 同意、拒绝同时到线
    assert decide(both, 0, 1) == 'deny', '同意和拒绝同时满足时没有选拒绝'
    carried = [(k * .05, p(.95, 0)) for k in range(-10, 40)]                    # 上一条的食指一直没松，跨过本条开始时刻
    assert decide(carried, 0, 2) is None, '没松开的食指顺带批了下一条'
    assert decide(carried + [(2 + k * .05, p(0, 0)) for k in range(5)] + [(2.25 + k * .05, p(.95, 0)) for k in range(9)], 0, 3) == 'allow', '松开再捏应当算同意'
    dropout = [(k * .05, p(.8 if k % 10 == 3 else .95, 0)) for k in range(-10, 60)]   # 一直捏着，偶尔掉一帧到门槛下
    assert decide(dropout, 0, 3) is None, '捏着时掉一帧就上膛，连批了下一条'
    assert read_env('# NTFY_TOKEN=old\nNTFY_URL = https://x\nNTFY_TOPIC="t"\nNTFY_TOKEN=\'new\'\n\n') == {'NTFY_URL': 'https://x', 'NTFY_TOPIC': 't', 'NTFY_TOKEN': 'new'}
    # wait_gesture：用假时钟跑完整流程
    def run(stream):
        clock = [100.]; it = iter(stream)
        def sample():
            try: s = next(it); return (clock[0], s) if s is not None else None
            except StopIteration: return None
        return wait_gesture(sample, clock=lambda: clock[0], sleep=lambda d: clock.__setitem__(0, clock[0] + d))
    assert run([p(0, 0)] * 10 + [p(.95, 0)] * 12)[0] == 'allow'
    assert run([p(0, 0)] * 10 + [p(0, .9)] * 8)[0] == 'deny'
    assert run([p(0, 0)] * 2000) == ('deny', '20 秒内没等到手势')
    assert run([p(0, 0)] * 3)[1].startswith('手环没有数据'), '数据停了没有拒绝'
    # main：钩子协议（stdin → stdout JSON）
    def hook(cmd, stream):
        out = io.StringIO(); it = iter(stream); clock = [time.time()]
        it = iter([p(0, 0)] * 5 + list(stream))                                 # 念完时手是松的
        def sample():
            clock[0] += .05
            try: return (clock[0], next(it))
            except StopIteration: return (clock[0], p(0, 0))
        rc = main(io.StringIO(json.dumps({'tool_name': 'Bash', 'tool_input': {'command': cmd}})), out, sample, on=on)
        return rc, out.getvalue()
    on = True
    rc, out = hook('rm -rf /', [p(.99, 0)] * 50); assert rc == 0 and out == '', '危险命令被手环放行了（应该不表态）'
    rc, out = hook('npm test', [p(.99, 0)] * 50); d = json.loads(out)['hookSpecificOutput']
    assert d['hookEventName'] == 'PreToolUse' and d['permissionDecision'] == 'allow', d
    on = False; rc, out = hook('npm test', [p(.99, 0)] * 50); assert rc == 0 and out == '', '演示开关关着，钩子却表态了'
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:                                    # 开关文件：没有 / 过期 / 乱写 = 关；未到期 = 开；--off 删掉
        sw = Path(tmp) / 'on'
        assert not enabled(path=sw)
        sw.write_text(str(time.time() - 1)); assert not enabled(path=sw), '过期的开关还算开着'
        sw.write_text('乱写'); assert not enabled(path=sw)
        for far in ('inf', str(time.time() + 86400)): sw.write_text(far); assert not enabled(path=sw), ('手写的超长到期时间让开关一直开着', far)
        assert '30 分钟' in switch(['--on'], sw) and enabled(path=sw)
        assert '240 分钟' in switch(['--on', '9999'], sw), '打开时长没有上限'
        switch(['--off'], sw); assert not enabled(path=sw) and '关闭' in switch(['--status'], sw)
    # 顺序：先暂停手势鼠标、再念、等手势、最后恢复；念的时候鼠标必须已经停了
    calls, g = [], globals()
    real = g['hold_mouse'], g['say'], g['wait_gesture'], g['log'], g['tell_app']
    g['hold_mouse'] = lambda base, what: calls.append(('mouse', base, what))
    g['say'] = lambda text: calls.append(('say',))
    g['wait_gesture'] = lambda sample: (calls.append(('wait',)), ('deny', '测试'))[1]
    g['log'] = lambda *a: None                                              # 自检不写真实日志
    g['tell_app'] = lambda base, body: calls.append(('app', body['action'], body.get('decision')))
    try: main(io.StringIO(json.dumps({'tool_name': 'Bash', 'tool_input': {'command': 'npm test'}})), io.StringIO(), lambda: None, base='http://svc', on=True)   # 合并：本地的 App 授权卡上报 + 远端的演示开关参数
    finally: g['hold_mouse'], g['say'], g['wait_gesture'], g['log'], g['tell_app'] = real
    assert calls == [('mouse', 'http://svc', 'pause'), ('app', 'pending', None), ('say',), ('wait',), ('app', 'done', 'deny'), ('mouse', 'http://svc', 'resume')], calls
    sent = []
    fake = lambda req, timeout: sent.append((req.full_url, dict(req.header_items()), json.loads(req.data)))
    cfg = {'NTFY_URL': 'https://ntfy.example', 'NTFY_TOPIC': 't', 'NTFY_TOKEN': 'tk'}
    assert push('标题', '正文', cfg, fake) and sent[-1][0] == 'https://ntfy.example' and sent[-1][1]['Authorization'] == 'Bearer tk'
    assert not sent[-1][1].get('User-agent', '').startswith('Python-urllib'), '用了默认 UA，过 Cloudflare 会被 1010 拦'
    assert sent[-1][2] == {'topic': 't', 'title': '标题', 'message': '正文', 'priority': 4, 'tags': ['watch']}, sent[-1]
    assert not push('x', 'y', {**cfg, 'NTFY_URL': 'http://ntfy.example'}, fake), '明文 http 也推了（令牌会裸奔）'
    assert not push('x', 'y', {}, fake) and not push('x', 'y', cfg, lambda *a, **k: 1 / 0), '没配置 / 网络错要返回 False 不抛'
    assert '推送失败：ZeroDivisionError' in LOG.read_text() and 'tk' not in LOG.read_text(), '失败原因没记或记了令牌'
    with tempfile.TemporaryDirectory() as tmp:                                    # 模拟器地址文件：权限 / 主机核对
        g = globals(); real_file = g['SERVICE_FILE']; g['SERVICE_FILE'] = Path(tmp) / 'service.url'
        import gesture_sim; s2, ok_base = gesture_sim.serve(gesture_sim.Sim())
        try:
            for url, mode, want in [(ok_base, 0o600, ok_base), (ok_base, 0o644, None),
                                    ('http://127.0.0.1:80@evil.example', 0o600, None), (ok_base.replace('127.0.0.1', 'localhost'), 0o600, None)]:
                g['SERVICE_FILE'].write_text(url); os.chmod(g['SERVICE_FILE'], mode)
                os.environ.pop('YUANLI_SERVICE', None)
                got_base = find_service()                                              # 反例可能退回找到真采集服务，只要求不是伪造地址
                assert got_base == want if want else got_base != url, (url, oct(mode), got_base)
            assert simulated(ok_base), '模拟器没被识别出来'
        finally: s2.shutdown(); g['SERVICE_FILE'] = real_file
    assert [category(c) for c in ('npm run build', 'git log -3', 'cat README.md', 'make')] == ['npm 检查', 'git 只读', '读文件', '其他']
    assert len(CATEGORY) == len(SAFE)
    got = []
    assert stop_hook(io.StringIO('{"cwd": "/x/原力手环"}'), on=True, send=lambda t, m: got.append((t, m)) or True) and got == [('原力手环 · 任务完成', '原力手环 · Claude 本轮已结束，回来验收')], got
    assert not stop_hook(io.StringIO('{}'), on=False, send=lambda t, m: got.append(1)) and len(got) == 1, '开关关着 Stop 也推了'
    # 待确认推送只带项目名 / 类别 / 短哈希，不带命令原文
    pushed, g = [], globals(); real = g['push'], g['hold_mouse'], g['say'], g['wait_gesture'], g['log'], g['tell_app']
    g['push'] = lambda t, m: pushed.append((t, m)); g['hold_mouse'] = g['tell_app'] = lambda *a: None; g['say'] = g['log'] = lambda *a: None
    g['wait_gesture'] = lambda sample: ('deny', '测试')
    try: main(io.StringIO(json.dumps({'tool_name': 'Bash', 'tool_input': {'command': 'git log --oneline'}, 'cwd': '/p/demo'})), io.StringIO(), lambda: None, base='http://svc', on=True)
    finally: g['push'], g['hold_mouse'], g['say'], g['wait_gesture'], g['log'], g['tell_app'] = real
    time.sleep(.1)
    assert pushed and pushed[0][0] == '原力手环 · 待确认' and 'git 只读' in pushed[0][1] and hashlib.sha256(b'git log --oneline').hexdigest()[:8] in pushed[0][1], pushed
    assert 'oneline' not in pushed[0][1], '推送里带了命令原文'
    print('ai_confirm check passed: 白名单（9 种危险命令、6 种敏感文件不碰）、同意要 0.85 且连续 0.35 s、拒绝 0.6 且 0.2 s、断续不算、念完前的手势不算、'
          '同时满足选拒绝、没松开 / 掉帧的手势不连批、超时拒绝、数据停了拒绝、钩子输出符合协议、危险命令不表态、先暂停手势鼠标再念、演示开关默认关 / 过期失效 / 上限 240 分钟、'
          '推送只带项目名 / 类别 / 短哈希、只走 https、失败记原因不记令牌、配置按行解析、模拟器地址核对权限和主机、Stop 受开关控制')


if __name__ == '__main__':
    if '--check' in sys.argv: check(); sys.exit()
    if len(sys.argv) > 1 and sys.argv[1] in ('--on', '--off', '--status'): print(switch(sys.argv[1:])); sys.exit()
    if '--stop' in sys.argv: stop_hook(); sys.exit()
    sys.exit(main())

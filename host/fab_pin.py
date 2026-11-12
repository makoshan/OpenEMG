"""制造包来源按文件内容绑定，不按提交号。

旧做法 make_fab 用 `git show <提交号>:板文件` 取源板，推送前一变基提交号就变，记下的号成了孤儿提交。
这里记每个文件的 git blob 号（文件内容的编号）和 SHA-256：内容不变 blob 号就不变，变基不影响取回。
照 MOSS Core V0.7 的 CHECKS.json：哈希对不上就拒绝复用旧检查结果。

  python3 host/fab_pin.py pin OUT.json 文件...       记录已提交文件的 blob/SHA-256（工作区有未提交改动就拒绝）
  python3 host/fab_pin.py fetch PIN.json 目录         按 blob 号取回源文件并核 SHA-256（替代 git show 提交号:路径）
  python3 host/fab_pin.py verify PIN.json [目录]      重算哈希，有一个不符就退出 1（复用 DRC/自检结果前跑）
  python3 host/fab_pin.py pushed PIN.json [--ref origin/main]  确认每个 blob 在主干某个提交里，推送后跑
  python3 host/fab_pin.py --check                     临时仓库里的正反例
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def git(*args, cwd, data=False):
    r = subprocess.run(['git', *args], cwd=cwd, capture_output=True)
    if r.returncode:
        raise ValueError(f'git {" ".join(args)} 失败：{r.stderr.decode().strip()}')
    return r.stdout if data else r.stdout.decode().strip()


def root_of(cwd='.'):
    return Path(git('rev-parse', '--show-toplevel', cwd=cwd))


def pin(files, cwd='.'):
    root = root_of(cwd)
    out = {}
    for f in files:
        p = Path(f).absolute()
        rel = (p.parent.resolve() / p.name).relative_to(root).as_posix()   # 只解析目录：软链文件记它自己的路径
        blob = git('rev-parse', f'HEAD:{rel}', cwd=root)
        body = (root / rel).read_bytes()
        # 工作区要和 HEAD 一致，否则记下的 blob 不是你出包用的那份
        if hashlib.sha256(body).hexdigest() != hashlib.sha256(git('cat-file', 'blob', blob, cwd=root, data=True)).hexdigest():
            raise ValueError(f'{rel} 有未提交改动，先提交再绑定')
        out[rel] = dict(blob=blob, sha256=hashlib.sha256(body).hexdigest(), bytes=len(body))
    return check_names(out)


def check_names(m):
    if not m:
        raise ValueError('空清单不能作为来源')
    # fetch 平铺到一个目录，同名文件会互相覆盖
    names = [Path(r).name for r in m]
    if len(set(names)) != len(names):
        raise ValueError(f'清单里有同名文件：{sorted({n for n in names if names.count(n) > 1})}')
    return m


def load(path):
    m = json.loads(Path(path).read_text())
    m = m.get('files', m)   # 允许嵌在 SOURCE.json 的 files 字段里
    if not m or any(len(v.get('sha256', '')) != 64 or len(v.get('blob', '')) < 40 for v in m.values()):
        raise ValueError('清单为空或缺 blob/sha256')
    return check_names(m)


def fetch(m, dest, cwd='.'):
    root, dest = root_of(cwd), Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for rel, v in m.items():
        body = git('cat-file', 'blob', v['blob'], cwd=root, data=True)
        if hashlib.sha256(body).hexdigest() != v['sha256']:
            raise ValueError(f'{rel} blob 内容与记录的 SHA-256 不符')
        (dest / Path(rel).name).write_bytes(body)


def differences(m, directory=None, cwd='.'):
    """directory 为空时比仓库里的原路径，否则比取回目录里的同名文件。"""
    base = root_of(cwd)
    bad = []
    for rel, v in m.items():
        p = Path(directory) / Path(rel).name if directory else base / rel
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != v['sha256']:
            bad.append(rel)
    return bad


def unpushed(m, ref='origin/main', cwd='.'):
    root = root_of(cwd)
    missing = []
    for rel, v in m.items():
        commits = git('log', '--format=%H', ref, '--', rel, cwd=root).split()
        if not any(git('rev-parse', f'{c}:{rel}', cwd=root) == v['blob'] for c in commits if git('ls-tree', c, '--', rel, cwd=root)):
            missing.append(rel)
    return missing


def check():
    with tempfile.TemporaryDirectory(prefix='fab-pin-check-') as tmp:
        t = Path(tmp)
        run = lambda *a: git(*a, cwd=t)
        run('init', '-q'); run('config', 'user.email', 'x@x'); run('config', 'user.name', 'x')
        (t / 'board.kicad_pcb').write_text('v1\n'); run('add', '.'); run('commit', '-qm', 'board')
        run('branch', 'main-remote')   # 充当 origin/main
        (t / 'note').write_text('n'); run('add', 'note'); run('commit', '-qm', 'note')
        old = run('rev-parse', 'HEAD')
        m = pin([t / 'board.kicad_pcb'], cwd=t)
        # 模拟推送前变基：改写提交并清掉旧提交对象，旧提交号成真孤儿
        run('commit', '-q', '--amend', '-m', 'note rebased')
        assert run('rev-parse', 'HEAD') != old
        run('reflog', 'expire', '--expire=now', '--all'); run('gc', '-q', '--prune=now')
        try:
            run('show', f'{old}:board.kicad_pcb')
        except ValueError:
            pass
        else:
            raise AssertionError('旧提交没清掉，变基反例无效')
        out = t / 'fetched'
        fetch(m, out, cwd=t)
        assert (out / 'board.kicad_pcb').read_text() == 'v1\n', '变基后按 blob 取回失败'
        assert differences(m, out, cwd=t) == [] and differences(m, cwd=t) == []
        assert unpushed(m, 'main-remote', cwd=t) == []
        # 反例：取回文件被改、仓库文件被改
        (out / 'board.kicad_pcb').write_text('v2\n')
        assert differences(m, out, cwd=t) == ['board.kicad_pcb'], '改过的取回文件没查出'
        (t / 'board.kicad_pcb').write_text('v2\n')
        assert differences(m, cwd=t) == ['board.kicad_pcb'], '改过的仓库文件没查出'
        # 反例：未提交改动不许绑定
        try:
            pin([t / 'board.kicad_pcb'], cwd=t)
        except ValueError:
            pass
        else:
            raise AssertionError('未提交改动被绑定')
        # 反例：新内容只在本地提交、没进主干
        run('commit', '-qam', 'v2')
        m2 = pin([t / 'board.kicad_pcb'], cwd=t)
        assert unpushed(m2, 'main-remote', cwd=t) == ['board.kicad_pcb'], '未推送的 blob 没查出'
        # 反例：记录的哈希被篡改
        m2['board.kicad_pcb']['sha256'] = '0' * 64
        try:
            fetch(m2, out, cwd=t)
        except ValueError:
            pass
        else:
            raise AssertionError('哈希不符的 blob 被取回')
        same = {'a/b.kicad_pcb': dict(m2['board.kicad_pcb']), 'c/b.kicad_pcb': dict(m2['board.kicad_pcb'])}
        for bad in ({}, {'x': {'blob': 'a', 'sha256': 'b'}}, same):
            p = t / 'bad.json'; p.write_text(json.dumps(bad))
            try:
                load(p)
            except ValueError:
                pass
            else:
                raise AssertionError('坏清单未被拒绝')
    print('PASS: 旧提交清掉后按 blob 取回、同名文件、取回/仓库改动、未提交绑定、未推送、哈希篡改、空清单均判对')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('cmd', nargs='?', choices=['pin', 'fetch', 'verify', 'pushed'])
    ap.add_argument('args', nargs='*')
    ap.add_argument('--ref', default='origin/main')
    a = ap.parse_args()
    if a.check:
        check(); return 0
    try:
        if a.cmd == 'pin':
            out, m = Path(a.args[0]), pin(a.args[1:])   # 先算完再建文件，失败不留空清单
            with out.open('x') as fh:   # 不覆盖已有清单
                json.dump(m, fh, ensure_ascii=False, indent=1); fh.write('\n')
            print('已绑定', len(a.args) - 1, '个文件 →', out); return 0
        m = load(a.args[0])
        if a.cmd == 'fetch':
            fetch(m, a.args[1]); print('已取回并核对', len(m), '个文件'); return 0
        bad = differences(m, a.args[1] if len(a.args) > 1 else None) if a.cmd == 'verify' else unpushed(m, a.ref)
        print(('哈希不符：' if a.cmd == 'verify' else f'不在 {a.ref}：') + ', '.join(bad) if bad else f'{a.cmd} 通过（{len(m)} 个文件）')
        return 1 if bad else 0
    except (OSError, ValueError, IndexError) as e:
        print('未通过：', e, file=sys.stderr); return 2


if __name__ == '__main__':
    sys.exit(main())

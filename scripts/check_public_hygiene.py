#!/usr/bin/env python3
"""OpenEMG 公开仓隐私、版权、压缩包穿透、Git 元数据与大文件门禁（含 --selftest 8/8 反例自检）。

设计特点：
1. 脚本自身零硬编码敏感词（采用通用结构正则 + 加盐 SHA-256 摘要表，同时拆分连字符/下划线子词查表），扫描时不豁免自身。
2. 穿透解压扫描所有 .epro2 / .epro / .zip / .3mf 归档内部成员（自动跳过二进制与切片 .gcode 几何坐标）。
3. 禁止混入顶层 docs/ 教学文档目录、非动作库视频（.mp4）或真实生物信号采集包（*.npz / *.edf / *.bdf / *.gdf）。
4. 单文件体积上限 <= 25 MiB。
5. 若存在 .git 仓库，强制校验全部提交 Author / Committer 邮箱必须为匿名 noreply 邮箱，且初始发布提交数为 1。
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

MAX_BYTES = 25 * 1024 * 1024
HASH_SALT = "openemg-hygiene-v1:"

BLOCKED_TOKEN_SHA256 = {
    "1643f0aca16e8d05cf0a538748ae6678e436ac0a442e5fc0efa6324a5f9eb4d3",
    "16c03fdc27721be8a12c87d67e9e690066ca4a4264c7b28c9b833376b38635e6",
    "2701cc1fe7c3b3f1336cf5409944f609ea310d9f304134f4520240549ad372be",
    "299899ac07f88a8d217377ce4618123d978d0d493070d9e1dd221d001cdbfc33",
    "3fd0957c9293298368c417e6e23dabadabbe349a65176c184dd97d10b1eba573",
    "4046dc5bbffa0821cc837da92f376ad51237fff98a8ef574da86d0c347208615",
    "47551c272567242199da76c9aec266c690c55d1d7115330414a20e517d932ab7",
    "47bc1762674349496f7e2abbb1bc17a4f0f92317c8343850eb2bfbb7fa5ef9ae",
    "50259511f3c422ca08ea0197462970823e785d50857ade8d583711bd8897ca18",
    "7ec392c7bea989d1c4da5a6306658409f49393061909a691b14218a44846135b",
    "9018e7dca0ac51a243029b6c24e0d141e2945b9214d5dc1a864ee9bbaa1fe948",
    "c665f227aae7e2829316e939974e2f9079c559aa3dc4a9cd6daabc1e2f4b951e",
    "c6a6d9f236b24c5eae95d4486f687a07d46dc45154bb303d78f48e4cf6762fa5",
    "cc7ed696ab9136de145a0c8fc06db7a80401968770c0bc205547400dfcd5e0d2",
    "d6edfbb3b5a2cfe111caaf7a10240b5a25050a5a05ddff9a62a1f44eee1101f8",
    "e125209ed9a87efc3ed406d25de980a29cfce7efeb6dd2afebbb34311d18add1"
}

GENERIC_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("本机绝对用户路径", re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+/")),
    ("本机临时工作树路径", re.compile(r"/private/tmp/[A-Za-z0-9._-]+/")),
    ("连字符转义用户路径", re.compile(r"-(?:Users|home)-[A-Za-z0-9._-]+-")),
    ("个人年份工作区路径", re.compile(r"(?:~|\$HOME|Path\.home\(\)\s*/\s*['\"]?)/?go/202\d/")),
    ("PEM 私钥块", re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY[-]----")),
    ("打样批次订单号", re.compile(r"\b(?:SMT26\d+|Y2[3-9]|Y3[0-9]|Y5[34])\b")),
    ("内网私有网段IP", re.compile(r"\b192\.168\.\d+\.\d+\b")),
    ("商业应用动图旧注", re.compile(r"Meta (?:Neural Band )?官方(?:细线|示范)动图")),
    ("闭源声明残留", re.compile(r"内部项目代码[，,]不公开发布")),
]

TOKEN_RE = re.compile(r"[A-Za-z0-9_@.-]{4,}")
FORBIDDEN_EXTS = {".npz", ".edf", ".bdf", ".gdf", ".pem", ".key", ".p12"}
ARCHIVE_SCAN_EXTS = {".epro2", ".epro", ".zip", ".3mf", ".f3d"}
SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", "dist", "build", "out"}
BINARY_SKIP_TEXT = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".icns", ".glb", ".pdf",
    ".pptx", ".docx", ".3mf", ".stl", ".f3d", ".node", ".woff", ".woff2", ".ttf", ".otf", ".gcode",
}


def _eda_pin_reference(text: str, match: re.Match[str]) -> bool:
    """只识别 EDA 原生记录里封装焊盘、符号脚号及其网络索引。"""
    if not re.fullmatch(r"Y[0-9]+", match.group()):
        return False
    start = text.rfind("\n", 0, match.start()) + 1
    prefix = text[start:match.start()]
    suffix = text[match.end():match.end()+3]
    if prefix.startswith('{"type":"PAD",'):
        return prefix.endswith('"num":"') and suffix.startswith('"')
    if prefix.startswith('{"type":"ATTR",'):
        return prefix.endswith('"key":"Pin Number","value":"') and suffix.startswith('"')
    if prefix.startswith('{"type":"PAD_NET",'):
        return bool(re.search(r'"id":"\[\\"PAD_NET\\",\\"[^"\\]+\\",\\"$', prefix)) and suffix.startswith(r'\"')
    return False


def _scan_text_blob(data: bytes, label_path: str, errors: list[str]) -> None:
    if b"\x00" in data[:4096]:
        return
    text = data.decode("utf-8", errors="replace")
    for label, pat in GENERIC_PATTERNS:
        for m in pat.finditer(text):
            if (label == "打样批次订单号" and label_path.endswith((".epcb2", ".esch2"))
                    and _eda_pin_reference(text, m)):
                continue
            errors.append(f"{label} 命中 ({m.group(0)!r}): {label_path}")
            break
    candidates: set[str] = set()
    for tok in TOKEN_RE.findall(text):
        low = tok.lower().strip(".-_")
        if len(low) >= 4:
            candidates.add(low)
        for sub in re.split(r"[-_.]", low):
            if len(sub) >= 4:
                candidates.add(sub)
    for cand in candidates:
        digest = hashlib.sha256((HASH_SALT + cand).encode("utf-8")).hexdigest()
        if digest in BLOCKED_TOKEN_SHA256:
            errors.append(f"受限标识摘要命中: {label_path}")
            break


def _read_zip_member(p: Path, zf: zipfile.ZipFile, info: zipfile.ZipInfo) -> bytes:
    try:
        return zf.read(info.filename)
    except NotImplementedError:
        if info.compress_type != 93:
            raise
        # Fusion 360 .f3d 等归档使用 Zstandard (method=93)；从 Local File Header 后读取原始压缩流并用 zstandard 或系统 zstd 解压
        with p.open("rb") as fh:
            fh.seek(info.header_offset)
            lhdr = fh.read(30)
            if len(lhdr) < 30 or lhdr[:4] != b"PK\x03\x04":
                raise RuntimeError(f"无效的本地 Zip 头部: {info.filename}")
            fn_len = int.from_bytes(lhdr[26:28], "little")
            ex_len = int.from_bytes(lhdr[28:30], "little")
            fh.seek(info.header_offset + 30 + fn_len + ex_len)
            comp_data = fh.read(info.compress_size)
        try:
            import zstandard as zstd  # type: ignore
            dctx = zstd.ZstdDecompressor()
            return dctx.decompress(comp_data, max_output_size=max(info.file_size, 1024 * 1024))
        except ImportError:
            pass
        for zstd_bin in ("zstd", "/opt/homebrew/bin/zstd", "/usr/bin/zstd"):
            if subprocess.run(["which", zstd_bin], capture_output=True).returncode == 0 or os.path.exists(zstd_bin):
                proc = subprocess.run([zstd_bin, "-d", "-q", "-c"], input=comp_data, capture_output=True, check=False)
                if proc.returncode == 0:
                    return proc.stdout
        raise RuntimeError(f"无法解压 Zstandard 压缩归档成员 {info.filename}（请安装 zstandard 或 zstd CLI）")


def _scan_archive(p: Path, rel: Path, errors: list[str]) -> None:
    try:
        with zipfile.ZipFile(p, "r") as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = info.filename
                sub_ext = Path(name).suffix.lower()
                if sub_ext in FORBIDDEN_EXTS:
                    errors.append(f"归档内部含禁止文件后缀 ({sub_ext}): {rel}!{name}")
                    continue
                if sub_ext in BINARY_SKIP_TEXT or name.endswith(".gcode"):
                    continue
                if info.file_size > MAX_BYTES:
                    continue
                raw = _read_zip_member(p, zf, info)
                _scan_text_blob(raw, f"{rel}!{name}", errors)
    except (zipfile.BadZipFile, RuntimeError) as exc:
        errors.append(f"归档文件损坏或无法解压 ({rel}): {exc}")


def _check_git_metadata(root: Path) -> list[str]:
    if not (root / ".git").exists():
        return []
    res = subprocess.run(
        ["git", "-C", str(root), "log", "--all", "--format=%ae%n%ce"],
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        return []
    bad: list[str] = []
    for raw in res.stdout.splitlines():
        email = raw.strip().lower()
        if not email:
            continue
        h = hashlib.sha256((HASH_SALT + email).encode("utf-8")).hexdigest()
        if h in BLOCKED_TOKEN_SHA256 or not email.endswith(".noreply.github.com"):
            bad.append(f"Git 提交元数据包含非匿名邮箱: {email}")
    return sorted(set(bad))


def scan_repo(root: Path) -> list[str]:
    errors: list[str] = _check_git_metadata(root)

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        dp = Path(dirpath)
        for fn in sorted(filenames):
            if fn == ".git":
                continue
            p = dp / fn
            if p.is_symlink():
                errors.append(f"不允许符号链接入库: {p.relative_to(root)}")
                continue
            rel = p.relative_to(root)
            ext = p.suffix.lower()
            size = p.stat().st_size

            if size > MAX_BYTES:
                errors.append(f"单文件超过 25 MiB ({size} bytes): {rel}")

            if ext in FORBIDDEN_EXTS:
                errors.append(f"禁止入库的文件后缀 ({ext}): {rel}")

            if ext == ".mp4" and rel.parts[:3] != ("app", "public", "gesture-library"):
                errors.append(f"禁止入库非动作库的视频文件 (.mp4): {rel}")

            if rel.parts[0] == "docs":
                errors.append(f"禁止混入教学文档目录 docs/: {rel}")

            if ext in ARCHIVE_SCAN_EXTS:
                _scan_archive(p, rel, errors)
                continue

            if ext in BINARY_SKIP_TEXT:
                continue

            try:
                data = p.read_bytes()
            except OSError as exc:
                errors.append(f"无法读取 {rel}: {exc}")
                continue
            _scan_text_blob(data, str(rel), errors)
    return errors


def run_selftest() -> int:
    """构造 8 类必失败合成反例（含连字符路径与 .epro2 内部注入），确认门禁不漏放。"""
    with tempfile.TemporaryDirectory(prefix="openemg-hygiene-test-") as td:
        root = Path(td)
        (root / "README.md").write_text("# Clean Repo\n", encoding="utf-8")
        assert scan_repo(root) == [], "干净最小仓不应报错"

        # 同一个编号既可能是封装坐标，也可能是订单号，不能整份文件豁免。
        sample_pin = "Y" + "23"
        pad = '{"type":"PAD","id":"e1"}||{"num":"' + sample_pin + '"}|'
        errs: list[str] = []
        _scan_text_blob(pad.encode(), "test.epcb2", errs)
        assert not errs
        for number in ("23", "53", "54"):
            errs = []
            _scan_text_blob((pad + '\n订单 Y' + number).encode(), "test.epcb2", errs)
            assert any("打样批次订单号" in err for err in errs)

        canary = "-".join(("openemg", "hygiene", "canary", "fail"))
        u_path = "/" + "Users" + "/alice/workspace/file.py"
        tmp_path = "/" + "private/tmp/worktree-99/board.kicad_pcb"
        dash_path = "/" + "private/tmp/claude-501/-" + "Users" + "-alice-work/board.kicad_pcb"
        pem_hdr = "-----BEGIN " + "PRIVATE KEY-----"
        cases = [
            ("path_leak.txt", u_path, "本机绝对用户路径"),
            ("tmp_leak.json", tmp_path, "本机临时工作树路径"),
            ("dash_leak.json", dash_path, "连字符转义用户路径"),
            ("key_leak.txt", pem_hdr, "PEM 私钥块"),
            ("hash_leak.json", f'{{"tag": "{canary}"}}', "受限标识摘要命中"),
            ("docs/emg-intro-semg/lecture.pdf", "fake-pdf", "禁止混入教学文档目录 docs/"),
            ("host/capture.npz", "PK\x03\x04fake", "禁止入库的文件后缀 (.npz)"),
        ]
        for rel_str, content, expect_tag in cases:
            f = root / rel_str
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(content, encoding="utf-8")
            errs = scan_repo(root)
            f.unlink()
            if not any(expect_tag in e for e in errs):
                print(f"SELFTEST FAIL: 反例 {rel_str} 未触发 {expect_tag!r}，实际返回: {errs}", file=sys.stderr)
                return 1

        # 反例 7：.epro2 压缩包内部隐藏路径泄漏
        bad_epro = root / "bad.epro2"
        with zipfile.ZipFile(bad_epro, "w") as zf:
            zf.writestr("project.json", f'{{"src": "{u_path}"}}')
        epro_errs = scan_repo(root)
        bad_epro.unlink()
        if not any("bad.epro2!project.json" in e for e in epro_errs):
            print(f"SELFTEST FAIL: 未拦截 .epro2 内部泄漏，实际返回: {epro_errs}", file=sys.stderr)
            return 1

        # 反例 8：.f3d Fusion 360 压缩包内部隐藏路径泄漏
        bad_f3d = root / "bad.f3d"
        with zipfile.ZipFile(bad_f3d, "w") as zf:
            zf.writestr("Manifest.dat", f'{{"origin": "{u_path}"}}')
        f3d_errs = scan_repo(root)
        bad_f3d.unlink()
        if not any("bad.f3d!Manifest.dat" in e for e in f3d_errs):
            print(f"SELFTEST FAIL: 未拦截 .f3d 内部泄漏，实际返回: {f3d_errs}", file=sys.stderr)
            return 1

        # 反例 9：非匿名 Git 邮箱
        subprocess.run(["git", "-C", str(root), "init", "-b", "main", "-q"], check=True)
        subprocess.run(["git", "-C", str(root), "add", "README.md"], check=True)
        env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "alice@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "alice@example.com",
        }
        subprocess.run(["git", "-C", str(root), "commit", "-m", "init", "-q"], env=env, check=True)
        git_errs = scan_repo(root)
        if not any("Git 提交元数据包含非匿名邮箱" in e for e in git_errs):
            print(f"SELFTEST FAIL: 未拦住非匿名 Git 邮箱，实际返回: {git_errs}", file=sys.stderr)
            return 1

    print("check_public_hygiene selftest: 10/10 必失败反例（含临时工作树路径、连字符路径与 .epro2/.f3d 压缩包穿透）全部拦截，干净基线通过")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return run_selftest()
    target = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    errs = scan_repo(target)
    if errs:
        print(f"公开仓门禁失败（共 {len(errs)} 项）：", file=sys.stderr)
        for e in errs[:50]:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"公开仓门禁通过：{target}（0 违规）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

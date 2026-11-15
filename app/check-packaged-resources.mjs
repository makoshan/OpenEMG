// 打包态 Resources 目录同构门禁（开发态 + Linux CI + macOS 打包共用）：
// 在脱离仓库树的系统临时目录中构造 Contents/Resources/{host,firmware}，
// 验证采集服务导入链（emg_web -> studio_api -> rig -> c08b_stream / v12 / v12_ble）
// 与首板自检解码器（studio_api._bringup_decoder）零仓库依赖可加载；并配 2 条缺文件必败反例。
import { execFileSync } from 'node:child_process';
import { cpSync, existsSync, mkdtempSync, mkdirSync, readFileSync, rmSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const appDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(appDir, '..');
const rawPy = process.env.YUANLI_PY
  || (existsSync(path.join(appDir, 'build/python/bin/python3'))
      ? path.join(appDir, 'build/python/bin/python3')
      : 'python3');
const py = (rawPy.includes('/') || rawPy.includes('\\')) ? path.resolve(rawPy) : rawPy;

// 1. 静态核对 pack.mjs extraResource 与 package-provenance.mjs 清单目录一致包含 firmware/host/python
const packSrc = readFileSync(path.join(appDir, 'scripts/pack.mjs'), 'utf8');
const provSrc = readFileSync(path.join(appDir, 'scripts/package-provenance.mjs'), 'utf8');
for (const req of ['build/python', 'build/host', 'build/firmware']) {
  if (!packSrc.includes(`'${req}'`)) throw Error(`pack.mjs extraResource 漏打 ${req}`);
}
for (const dir of ['app', 'firmware', 'host', 'python']) {
  if (!provSrc.includes(`'${dir}'`)) throw Error(`package-provenance.mjs hashes() 漏校验 ${dir}`);
}

const tmpRoot = mkdtempSync(path.join(os.tmpdir(), 'openemg-res-gate-'));
try {
  const resDir = path.join(tmpRoot, 'Resources');
  const hostDst = path.join(resDir, 'host');
  const fwDst = path.join(resDir, 'firmware');
  mkdirSync(hostDst, { recursive: true });

  // 按 bundle-python.sh 同口径复制 host 运行时代码（排除 research / check_* / .venv* / v12-captures）
  cpSync(path.join(repoRoot, 'host'), hostDst, {
    recursive: true,
    filter: (src) => {
      const rel = path.relative(path.join(repoRoot, 'host'), src);
      if (!rel) return true;
      const parts = rel.split(path.sep);
      if (parts[0] === 'research' || parts[0] === 'v12-captures' || parts[0].startsWith('.venv')) return false;
      if (parts.includes('__pycache__')) return false;
      const base = path.basename(src);
      if (base.startsWith('check_')) return false;
      return true;
    },
  });

  // 按 bundle-python.sh 同口径复制 host 跨兄弟目录引用的 firmware 纯 Python 解码器
  const codecDst = path.join(fwDst, 'offline-f01/codec.py');
  const bringupDst = path.join(fwDst, 'c08b-bringup/tools/decode_bringup.py');
  mkdirSync(path.dirname(codecDst), { recursive: true });
  mkdirSync(path.dirname(bringupDst), { recursive: true });
  cpSync(path.join(repoRoot, 'firmware/offline-f01/codec.py'), codecDst);
  cpSync(path.join(repoRoot, 'firmware/c08b-bringup/tools/decode_bringup.py'), bringupDst);

  const runPy = (code) => execFileSync(py, ['-I', '-B', '-c', code], {
    cwd: tmpRoot,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  }).trim();

  // 2. 正例：在完全脱离仓库的临时 Resources/ 中导入全链路并解码示例广播
  const okOut = runPy(`
import json, sys
sys.path.insert(0, ${JSON.stringify(hostDst)})
import emg_web, studio_api, c08b_stream, v12, v12_ble
assert c08b_stream.SYNTHETIC == 1
assert v12.load_codec().FRAME_BYTES == 27
assert v12_ble.load_codec().FRAME_BYTES == 27
dec = studio_api._bringup_decoder()
r = dec.decode_any_hex(dec.sample_hex("16ch"))
pin = dec.channel_pinout("c08b-16ch")
assert r["verdict"] == "PASS" and r["afe_channels"] == 16 and r["done_mask_hex"] == "0x03FF" and len(pin["rows"]) == 16
print(json.dumps({"ok": True, "afe_channels": r["afe_channels"], "verdict": r["verdict"], "pinout_rows": len(pin["rows"])}))
`);
  const parsed = JSON.parse(okOut);
  if (!parsed.ok) throw Error('正例未通过: ' + okOut);

  // 3. 必败反例 A：缺 firmware/offline-f01/codec.py 必须报 FileNotFoundError（防偷读原仓）
  rmSync(codecDst);
  let caughtCodec = false;
  try {
    runPy(`import sys; sys.path.insert(0, ${JSON.stringify(hostDst)}); import c08b_stream`);
  } catch (e) {
    if (String(e.stderr || e.message).includes('FileNotFoundError')) caughtCodec = true;
  }
  if (!caughtCodec) throw Error('必败反例失效：删除 Resources/firmware/offline-f01/codec.py 后未报 FileNotFoundError');
  cpSync(path.join(repoRoot, 'firmware/offline-f01/codec.py'), codecDst);

  // 4. 必败反例 B：缺 firmware/c08b-bringup/tools/decode_bringup.py 必须报 FileNotFoundError
  rmSync(bringupDst);
  let caughtBringup = false;
  try {
    runPy(`import sys; sys.path.insert(0, ${JSON.stringify(hostDst)}); import studio_api; studio_api._bringup_decoder()`);
  } catch (e) {
    if (String(e.stderr || e.message).includes('FileNotFoundError')) caughtBringup = true;
  }
  if (!caughtBringup) throw Error('必败反例失效：删除 Resources/firmware/c08b-bringup/tools/decode_bringup.py 后未报 FileNotFoundError');

  console.log('check-packaged-resources: PASS (Resources/{host,firmware} 离线隔离导入 + 2 条缺文件必败反例通过)');
} finally {
  rmSync(tmpRoot, { recursive: true, force: true });
}

// 云端上传端到端：真平台（vibe-hw platform/server.mjs，本机 sqlite + 文件版 R2）+ electron/cloud.cjs。用合成录音，不碰真实肌电。
// 用法：npm run check:cloud            （需通过 VIBE_HW=<平台服务端目录> 指定本地测试服务端）
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import { createRequire } from 'node:module';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';

const require = createRequire(import.meta.url);
const { createCloud, CONSENT_VERSION } = require('./electron/cloud.cjs');
const VIBE = process.env.VIBE_HW ?? '';
if (!VIBE || !fs.existsSync(path.join(VIBE, 'platform', 'wl8.mjs'))) { console.log('SKIP：未配置本地平台测试服务端（设 VIBE_HW=<目录> 可启用）'); process.exit(0); }

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'yuanli-cloud-'));
const platData = path.join(tmp, 'platform'), proj = path.join(tmp, 'project'), stateFile = path.join(tmp, 'userData', 'cloud.json');
let fails = 0; const check = (ok, name) => { console.log(`${ok ? 'PASS' : 'FAIL'} ${name}`); if (!ok) fails++; };
const port = await new Promise((ok) => { const s = net.createServer().listen(0, '127.0.0.1', () => { const p = s.address().port; s.close(() => ok(p)); }); });
const base = `http://127.0.0.1:${port}`;

let server = null;
const up = () => new Promise((ok, no) => {
  server = spawn(process.execPath, ['--no-warnings', 'platform/server.mjs'], { cwd: VIBE, env: { ...process.env, PORT: String(port), PLATFORM_DATA: platData }, stdio: ['ignore', 'pipe', 'pipe'] });
  let log = ''; const on = (d) => { log += d; if (log.includes('platform on')) ok(); };
  server.stdout.on('data', on); server.stderr.on('data', on); server.on('exit', (c) => no(new Error(`平台退出 ${c}：${log}`)));
});
const down = () => new Promise((ok) => { server.once('exit', ok); server.kill(); });

// 合成录音：npz 只需 zip 头（平台只验格式）；json 带串口路径，用来证明它不会被上传
let n = 0;
function take(label, donning, set = 'emg-wl8-data') {
  const dir = path.join(proj, set, label); fs.mkdirSync(dir, { recursive: true });
  const stem = path.join(dir, `${label}-${++n}`), body = Buffer.concat([Buffer.from([0x50, 0x4b, 0x03, 0x04]), Buffer.from(`take-${n}-`.repeat(50))]);
  fs.writeFileSync(stem + '.npz', body);
  fs.writeFileSync(stem + '.json', JSON.stringify({ label, donning, seconds: 2, session: '左手 · 校准', port: '/dev/cu.wchusbserialSECRET123' }));
  return body;
}
const r2Files = () => { const d = path.join(platData, 'r2'); const walk = (x) => fs.existsSync(x) ? fs.readdirSync(x, { withFileTypes: true }).flatMap((e) => e.isDirectory() ? walk(path.join(x, e.name)) : [path.join(x, e.name)]) : []; return walk(d); };
const me = async (token) => (await fetch(base + '/v1/wl8/me', { headers: { 'x-subject-token': token } })).json();

try {
  await up();
  const cloud = createCloud({ stateFile, dataRoot: proj, base });
  const bodies = [take('ai_rest', 1), take('ai_up', 1), take('ai_rest', 2, 'emg-wl8-data-rewear')];

  let s = await cloud.sync();
  check(!s.consented && s.pending === 3 && r2Files().length === 0, '没同意：3 条只在本机，一条都不传');
  await cloud.consent(CONSENT_VERSION).then(() => check(true, '同意当前版本 → 拿到匿名令牌'));
  const token = JSON.parse(fs.readFileSync(stateFile, 'utf8')).token;
  check((fs.statSync(stateFile).mode & 0o777) === 0o600, '令牌文件权限 600');

  s = await cloud.sync();
  check(s.uploaded === 3 && s.pending === 0 && !s.lastError, '联网同步：3 条全传上');
  const files = r2Files();
  check(files.length === 3 && files.every((f) => f.endsWith('.npz')), '平台只收到 3 个 npz，没有 json');
  check(files.every((f) => !fs.readFileSync(f).includes('SECRET123')), '串口序列号没有出本机');
  check(bodies.every((b) => files.some((f) => fs.readFileSync(f).equals(b))), '平台上的字节和本机录音一致');
  const m1 = await me(token);
  check(m1.labels.find((l) => l.label === 'ai_rest')?.n === 2 && m1.labels.find((l) => l.label === 'ai_rest')?.donnings === 2, '重戴集也传了：ai_rest 2 条 2 次佩戴');

  // 断网：录 2 条 → 同步失败但不丢 → 联网后补传
  await down();
  take('ai_left', 2); take('ai_right', 2);
  s = await cloud.sync();
  check(s.pending === 2 && s.uploaded === 3 && s.lastError.startsWith('连不上'), '断网：新录 2 条留在待传，报「连不上」');
  await up();
  s = await cloud.sync();
  check(s.uploaded === 5 && s.pending === 0 && !s.lastError, '联网后补传 2 条');

  // 重传不重复：把本地账本的 done 清掉再同步，平台按 id 认出是重传
  const st = JSON.parse(fs.readFileSync(stateFile, 'utf8')); for (const t of Object.values(st.takes)) delete t.done; fs.writeFileSync(stateFile, JSON.stringify(st));
  const again = createCloud({ stateFile, dataRoot: proj, base });
  s = await again.sync();
  const total = (await me(token)).labels.reduce((a, l) => a + l.n, 0);
  check(s.uploaded === 5 && total === 5 && r2Files().length === 5, '账本丢了 done 再同步：平台仍是 5 条，不重复');

  // 坏文件：npz 不是 zip → 平台 422，标成被拒，不再每轮重试
  const bad = path.join(proj, 'emg-wl8-data', 'ai_up', 'broken'); fs.writeFileSync(bad + '.npz', 'not zip'); fs.writeFileSync(bad + '.json', JSON.stringify({ label: 'ai_up', donning: 1 }));
  s = await again.sync();
  check(s.rejected === 1 && s.pending === 0 && s.uploaded === 5, '坏文件被平台拒：记为被拒 1 条，不算待传');

  // 平台还没上线这组接口（404）：不能把录音标成被拒，下轮要接着传
  const fake404 = createCloud({ stateFile: path.join(tmp, 'userData', 'c404.json'), dataRoot: proj, base, fetch: async (u, i) => (String(u).includes('/takes/') ? new Response('{"error":"没有这个路径"}', { status: 404 }) : fetch(u, i)) });
  await fake404.consent(CONSENT_VERSION);
  s = await fake404.sync();
  check(s.rejected === 0 && s.pending === 6 && s.lastError.includes('404'), '平台回 404：录音留在待传，不标成被拒');
  await fake404.revoke();

  // 撤回做到一半（平台已打删除标记、R2 还没删完）：下一轮同步碰到 401 要补删，不能直接把本地令牌丢掉
  const half = createCloud({ stateFile: path.join(tmp, 'userData', 'half.json'), dataRoot: proj, base, fetch: async (u, i) => (i?.method === 'PUT' ? new Response('{"error":"没有用户令牌，或已删除"}', { status: 401 }) : String(u).endsWith('/v1/wl8/me') && i?.method === 'DELETE' && !half.allowDelete ? new Response('{"error":"内部错误"}', { status: 500 }) : fetch(u, i)) });
  await half.consent(CONSENT_VERSION);
  s = await half.sync();
  check(s.consented && s.lastError.includes('再点一次'), '撤回做到一半：同步碰到 401 时补删失败 → 令牌留着，提示再点撤回');
  half.allowDelete = true;
  s = await half.revoke();
  check(!s.consented, '再点一次撤回 → 平台删完，本地令牌清掉');

  // 撤回同意：平台删光、本地令牌清掉，旧令牌失效
  s = await again.revoke();
  check(!s.consented && r2Files().length === 0, '撤回同意：平台上的录音全删了');
  check((await fetch(base + '/v1/wl8/me', { headers: { 'x-subject-token': token } })).status === 401, '旧令牌失效');
  check(fs.readdirSync(path.join(proj, 'emg-wl8-data', 'ai_rest')).length === 2, '本机录音一条没动');
} catch (e) { console.error(e); fails++; }
if (server && server.exitCode === null) server.kill();
fs.rmSync(tmp, { recursive: true, force: true });
console.log(fails ? `${fails} 项失败` : '云端上传端到端全部通过');
process.exit(fails ? 1 : 0);

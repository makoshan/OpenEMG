// 用合成媒体检查录制页面，不打开摄像头或连接设备。
import { build } from 'vite';
import { existsSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
const root = path.dirname(fileURLToPath(import.meta.url));
const temp = mkdtempSync(path.join(tmpdir(), 'yuanli-filter-ui-'));
const evDir = path.join(root, '../evidence/2026-10-15-filter-boundary');
try {
  await build({root, base:'./', build:{outDir:path.join(temp,'dist'), rollupOptions:{input:path.join(root,'check-filter-ui.html')}}});
  const result = spawnSync(createRequire(import.meta.url)('electron'), [path.join(root,'check-filter-ui.cjs')], {
    stdio:'inherit', env:{...process.env, FILTER_TEST_SCREEN:path.join(existsSync(evDir) ? evDir : temp, 'calibration-test.png'), FILTER_TEST_USERDATA:path.join(temp,'user'), FILTER_TEST_HTML:path.join(temp,'dist/check-filter-ui.html')}, timeout:30000,
  });
  process.exitCode = result.status ?? 1;
} finally { rmSync(temp, {recursive:true, force:true}); }

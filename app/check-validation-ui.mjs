// 用合成媒体检查录制页面，不打开摄像头或连接设备。
import { build } from 'vite';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
const root = path.dirname(fileURLToPath(import.meta.url));
const temp = mkdtempSync(path.join(tmpdir(), 'yuanli-validation-ui-'));
try {
  await build({root, base:'./', build:{outDir:path.join(temp,'dist'), rollupOptions:{input:path.join(root,'check-validation-ui.html')}}});
  const result = spawnSync(createRequire(import.meta.url)('electron'), [path.join(root,'check-validation-ui.cjs')], {
    stdio:'inherit', env:{...process.env, VALIDATION_TEST_USERDATA:path.join(temp,'user'), VALIDATION_TEST_HTML:path.join(temp,'dist/check-validation-ui.html')}, timeout:50000,
  });
  process.exitCode = result.status ?? 1;
} finally { rmSync(temp, {recursive:true, force:true}); }

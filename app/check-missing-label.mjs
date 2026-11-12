// 训练页「还缺…」提示用中文类别名：抓握组没有 gestures，也要显示「放松、捏合、握拳」而不是 rest、pinch、fist。
// profiles.ts 导入 JSON，node 不能直接跑：先用 vite 打成临时模块再断言。
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { build } from 'vite';
const root = path.dirname(fileURLToPath(import.meta.url));
const out = mkdtempSync(path.join(tmpdir(), 'yuanli-missing-label-'));
try {
  await build({ root, logLevel: 'error', configFile: false, build: { outDir: out, emptyOutDir: true, lib: { entry: path.join(root, 'src/emg8/profiles.ts'), formats: ['es'], fileName: 'profiles' } } });
  const { PROFILES, LABEL_CN, trainingBlock, validationHint } = await import(pathToFileURL(path.join(out, 'profiles.js')).href);
  const st = { project: { id: 'p' }, rig: { kind: 'wl8' }, tiers: [...PROFILES.grasp.labels, ...PROFILES['ghost-seals'].labels], counts: { train: { wl8: { rest: 3 } }, rewear: { wl8: {} } } };
  assert.equal(trainingBlock(st, PROFILES.grasp, 'p'), '每类至少 3 条训练数据，还缺 捏合、握拳');
  const seals = trainingBlock(st, PROFILES['ghost-seals'], 'p');   // 有 gestures 的组仍用组里的名字（破邪印等），不被基础名盖掉
  assert.match(seals, /还缺 放松、破邪印、道指、五雷诀$/, seals);
  const thumb = { ...PROFILES['thumb-four'], minRewear: 3 };
  assert.match(validationHint({ counts: { rewear: { wl8: {} } } }, thumb), /还缺 [^a-z_]+$/, '拇指组重戴提示不能出现英文 id');
  assert.equal(LABEL_CN.rest, '放松'); assert.equal(LABEL_CN.seal_poxie, '破邪印');
  console.log('缺数提示中文名检查通过：抓握「还缺 捏合、握拳」，结印仍用组内名字，重戴提示无英文 id');
} finally { rmSync(out, { recursive: true, force: true }); }

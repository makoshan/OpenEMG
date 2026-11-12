// 动作库素材门：每个动作左右手各有 jpg + mp4，且地址是相对路径（App 用 file:// 打开，/ 开头会指到磁盘根目录）。
// 用法：node check-gesture-library.mjs [dist目录]   不给目录查 public/，给了查构建产物
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
const root = process.argv[2] ? path.resolve(process.argv[2]) : path.join(here, 'public');
const src = readFileSync(path.join(here, 'src/emg8/gesture-library.tsx'), 'utf8');
const gestures = [...src.matchAll(/\{ id: (\d+), name: '[^']+', slug: '([\w-]+)' \}/g)].map((m) => [m[1].padStart(2, '0'), m[2]]);
const tmpl = src.match(/const asset = [^`]*`([^`]*)`/)?.[1];
const missing = [];
if (gestures.length !== 16) missing.push(`动作表应有 16 个，解析到 ${gestures.length} 个`);
if (!tmpl?.startsWith('gesture-library/')) missing.push(`素材地址必须是相对路径 gesture-library/…（本脚本按这个目录查文件）：${tmpl}`);
for (const hand of ['left', 'right']) for (const [id, slug] of gestures) for (const ext of ['jpg', 'mp4']) {
  const f = path.join(root, 'gesture-library', hand, `${id}-${slug}.${ext}`);
  if (!existsSync(f)) missing.push(path.relative(here, f));
}
if (missing.length) { console.error('动作库素材检查失败：\n' + missing.join('\n')); process.exit(1); }
console.log(`动作库素材检查通过：${gestures.length} 个动作 × 左右手 × jpg/mp4，相对路径（${path.relative(here, root) || '.'}）`);

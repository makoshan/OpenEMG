// 构建产物拷进 OpenEMG App（app/game/tianjie/）：App 的游戏窗口只读那里。先 npm run build，再跑这个。
// 只覆盖 dist 里有的文件，保留 app/game/tianjie/SOURCE.md。
import { cpSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
const dist = fileURLToPath(new URL('../dist/', import.meta.url));
const app = fileURLToPath(new URL('../../../app/game/tianjie/', import.meta.url));
if (!existsSync(dist + 'game.js')) { console.error('先 npm run assets -- <素材目录> && npm run build'); process.exit(1); }
cpSync(dist, app, { recursive: true });
console.log('已拷到', app);

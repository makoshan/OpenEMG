// 打成 out/OpenEMG-darwin-arm64/OpenEMG.app：页面 dist/、主进程 electron/，Resources 里放自带 Python、host/、手势算法。
// 不用 asar：采集入口 emg8-server.py 由外部 Python 读取，读不了 asar 包里的文件。
import { execFileSync } from 'node:child_process';
import { record } from './package-provenance.mjs';
const commit = execFileSync('git', ['rev-parse', 'HEAD'], {encoding:'utf8'}).trim();
if (execFileSync('git', ['status', '--porcelain', '--untracked-files=all'], {encoding:'utf8'}).trim()) throw Error('正式包必须从已提交的干净源码构建');
import { packager } from '@electron/packager';

const [appPath] = await packager({
  dir: '.', out: 'out', overwrite: true, asar: false, platform: 'darwin', arch: 'arm64',
  extendInfo: { NSCameraUsageDescription: '仅在你开启预览时使用所选摄像头；点击开始录制后才保存手部视频，用于核对动作起止，视频只存本机。' },
  // bundle id 不随改名换：换了辅助功能、摄像头授权要重给
  name: 'OpenEMG', appBundleId: 'org.openemg.desktop', appCategoryType: 'public.app-category.healthcare-fitness',
  icon: 'icon/icon.icns',   // 源图 icon/icon.svg；改图后跑 scripts/render-icon.cjs + iconutil 重出
  extraResource: ['build/python', 'build/host'],
  // 主进程只用 Node 自带模块，node_modules 一个都不带；页面已打进 dist/
  ignore: [/^\/(src|build|out|scripts|node_modules|icon|public)(\/|$)/, /^\/(check-[\w-]+\.(mjs|cjs|tsx|html)|vite\.config\.js|index\.html|README\.md|package-lock\.json)$/,
    /__pycache__/, /\.c$/],
});
// 门：包里任何软链都可能指回本机（packager 复制时会改写成绝对路径），有就失败
record(appPath + '/OpenEMG.app/Contents/Resources', commit);
const links = execFileSync('find', [appPath, '-type', 'l', '-path', '*/Contents/Resources/*']).toString().trim();
if (links) { console.error(`Resources 里有软链，别的 Mac 上会断：\n${links}`); process.exit(1); }
console.log(appPath);

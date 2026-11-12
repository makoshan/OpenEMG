// 重出图标：RESVG=<@resvg/resvg-js 目录，vibe-hw 的 node_modules 里有> node scripts/render-icon.cjs icon/icon.svg build/icon.iconset && iconutil -c icns build/icon.iconset -o icon/icon.icns
const { Resvg } = require(process.env.RESVG);
const fs = require('node:fs'), path = require('node:path');
const [svg, out] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const src = fs.readFileSync(svg);
for (const s of [16, 32, 128, 256, 512]) for (const k of [1, 2]) {
  const png = new Resvg(src, { fitTo: { mode: 'width', value: s * k } }).render().asPng();
  fs.writeFileSync(path.join(out, `icon_${s}x${s}${k === 2 ? '@2x' : ''}.png`), png);
}

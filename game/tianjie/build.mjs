import { build } from 'esbuild';
import { copyFile, rm } from 'node:fs/promises';
await build({entryPoints:['src/main.mjs'],bundle:true,format:'esm',outfile:'dist/game.js',minify:true,target:'es2022',legalComments:'eof'});
await copyFile('src/index.html','dist/index.html');await copyFile('src/style.css','dist/style.css');
for(const name of ['app.mjs','engine.mjs']) await rm('dist/'+name,{force:true});
console.log('3D PVE build complete.');

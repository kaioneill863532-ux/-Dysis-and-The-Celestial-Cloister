import {readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {build} from 'esbuild';

const root=resolve(import.meta.dirname,'..','prototype','rotunda');
const entry=resolve(root,'main.js');
const [html,css,faces,license,result]=await Promise.all([
 readFile(resolve(root,'index.html'),'utf8'),
 readFile(resolve(root,'style.css'),'utf8'),
 readFile(resolve(root,'fonts/faces.css'),'utf8'),
 readFile(resolve(root,'fonts/OFL.txt'),'utf8'),
 build({entryPoints:[entry],bundle:true,write:false,format:'iife',minify:true,target:'es2022',legalComments:'inline'}),
]);
let inlineFaces=faces;
for(const match of faces.matchAll(/url\('\.\/([^']+)'\)/g)){
 const encoded=(await readFile(resolve(root,'fonts',match[1]))).toString('base64');
 inlineFaces=inlineFaces.replaceAll(match[0],`url('data:font/woff2;base64,${encoded}')`);
}
const js=result.outputFiles[0].text;
const standalone=html
 .replace('<link rel="stylesheet" href="./fonts/faces.css">',`<style>${inlineFaces}\n/* Noto Serif SC font license\n${license}\n*/</style>`)
 .replace('<link rel="stylesheet" href="./style.css">',`<style>${css}</style>`)
 .replace('<script type="module" src="./main.js"></script>',`<script>${js.replaceAll('</script','<\\/script')}</script>`);
if(!standalone.includes('data:font/woff2;base64,')||!standalone.includes('<script>')||standalone.includes('src="./main.js"')||standalone.includes('href="./fonts/faces.css"'))throw new Error('Standalone substitution incomplete.');
await writeFile(resolve(root,'play.html'),standalone,'utf8');
console.log(`Built standalone rotunda: ${(Buffer.byteLength(standalone)/1024).toFixed(0)} KiB`);

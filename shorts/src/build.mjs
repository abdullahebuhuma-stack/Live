// Tek komutla video: seslendirme → ses tasarımı/miks → render.
// Kullanım: node src/build.mjs topics/<konu>.json [--preview]
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const topic = process.argv[2];
const preview = process.argv.includes('--preview');
if (!topic) { console.error('Kullanım: node src/build.mjs topics/<konu>.json [--preview]'); process.exit(1); }
const id = JSON.parse(fs.readFileSync(topic, 'utf8')).id;
const out = path.join('out', id);
const run = (cmd, args) => execFileSync(cmd, args, { stdio: 'inherit', env: { ...process.env, NODE_USE_ENV_PROXY: '1' } });

console.log('① Seslendirme ve zaman çizelgesi');
run('node', ['src/tts.mjs', topic, ...(preview ? ['--preview'] : [])]);
console.log('② Ses tasarımı, miks, master');
run('python3', ['src/audio.py', path.join(out, 'timeline.json')]);
console.log('③ Görüntü render');
run('node', ['src/render.mjs', out]);

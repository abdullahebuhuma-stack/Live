// Tek komutla video: seslendirme → ses tasarımı/miks → render.
// Kullanım:
//   node src/build.mjs topics/<konu>.json --voice <kayıt.wav | klasör>   (kendi sesiniz)
//   node src/build.mjs topics/<konu>.json                              (Google TTS)
//   node src/build.mjs topics/<konu>.json --preview                    (seslendirmesiz)
//   ek: --music <fon.mp3> [--music-db -6]  (fon müziği ve seviyesi dB; cihaz sesleri yalnızca DİNLE anlarında)
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const topic = process.argv[2];
const preview = process.argv.includes('--preview');
const vi = process.argv.indexOf('--voice');
const voice = vi > 0 ? process.argv[vi + 1] : null;
const mi = process.argv.indexOf('--music');
const music = mi > 0 ? process.argv[mi + 1] : null;
const mdi = process.argv.indexOf('--music-db');
const musicDb = mdi > 0 ? process.argv[mdi + 1] : '0';
if (!topic) { console.error('Kullanım: node src/build.mjs topics/<konu>.json [--preview]'); process.exit(1); }
const id = JSON.parse(fs.readFileSync(topic, 'utf8')).id;
const out = path.join('out', id);
const run = (cmd, args) => execFileSync(cmd, args, { stdio: 'inherit', env: { ...process.env, NODE_USE_ENV_PROXY: '1' } });

console.log('① Seslendirme ve zaman çizelgesi');
if (voice) run('python3', ['src/align.py', topic, voice]);
else run('node', ['src/tts.mjs', topic, ...(preview ? ['--preview'] : [])]);
console.log('② Ses tasarımı, miks, master');
run('python3', ['src/audio.py', path.join(out, 'timeline.json'), ...(music ? [music, musicDb] : [])]);
console.log('③ Görüntü render');
run('node', ['src/render.mjs', out]);

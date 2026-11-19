// Kare kare render → ffmpeg (H.264 + AAC, 1080x1920, 30 fps).
// Kullanım: node src/render.mjs out/<id> [--stills 1.5,8,20]  (stills: yalnızca PNG kareler)
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)('playwright');

const dir = path.resolve(process.argv[2]);
const stillsArg = process.argv.indexOf('--stills');
const stills = stillsArg > 0 ? process.argv[stillsArg + 1].split(',').map(Number) : null;

const tl = JSON.parse(fs.readFileSync(path.join(dir, 'timeline.json'), 'utf8'));
const env = JSON.parse(fs.readFileSync(path.join(dir, 'env.json'), 'utf8'));
const ev = JSON.parse(fs.readFileSync(path.join(dir, 'events.json'), 'utf8'));

const here = path.dirname(fileURLToPath(import.meta.url));
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
page.on('pageerror', (e) => console.error('Sayfa hatası:', e.message));
await page.goto('file://' + path.join(here, 'template.html'));
await page.evaluate(([a, b, c]) => window.init(a, b, c), [tl, env, ev]);

if (stills) {
  for (const t of stills) {
    const url = await page.evaluate((t) => window.renderAt(t, 0.92), t);
    const f = path.join(dir, `still-${String(t).replace('.', '_')}.jpg`);
    fs.writeFileSync(f, Buffer.from(url.split(',')[1], 'base64'));
    console.log(f);
  }
  await browser.close();
  process.exit(0);
}

const fps = tl.fps, total = Math.ceil(tl.duration * fps);
const outFile = path.join(dir, `${tl.id}${tl.preview ? '-onizleme' : ''}.mp4`);
const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
  '-i', path.join(dir, 'mix.wav'), '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
  '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', outFile], { stdio: ['pipe', 'inherit', 'inherit'] });

const t0 = Date.now();
for (let f = 0; f < total; f++) {
  const url = await page.evaluate((t) => window.renderAt(t, 0.93), f / fps);
  const buf = Buffer.from(url.slice(url.indexOf(',') + 1), 'base64');
  if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
  if (f % 150 === 0) process.stdout.write(`\r${f}/${total} kare  ${((Date.now() - t0) / 1000).toFixed(0)} sn`);
}
ff.stdin.end();
await new Promise((r) => ff.on('close', r));
await browser.close();
console.log(`\nHazır: ${outFile}`);

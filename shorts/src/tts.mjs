// Seslendirme + zaman çizelgesi.
// Kullanım: node src/tts.mjs topics/<konu>.json [--preview]
// --preview: Google TTS çağırmadan süreleri tahmin eder (seslendirmesiz önizleme).
// Anahtar: ortamın Network secrets bölümünde (X-Goog-Api-Key) ya da GOOGLE_TTS_API_KEY değişkeninde.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const topicPath = process.argv[2];
const preview = process.argv.includes('--preview');
if (!topicPath) { console.error('Kullanım: node src/tts.mjs topics/<konu>.json [--preview]'); process.exit(1); }

const topic = JSON.parse(fs.readFileSync(topicPath, 'utf8'));
const outDir = path.resolve('out', topic.id);
const voiceDir = path.join(outDir, 'voice');
const cacheDir = path.resolve('.cache', 'tts');
fs.mkdirSync(voiceDir, { recursive: true });
fs.mkdirSync(cacheDir, { recursive: true });

const SR = 44100;
const API = 'https://texttospeech.googleapis.com/v1beta1/text:synthesize';

const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

// Kelimeleri ayır, her kelimenin önüne <mark> koy; telaffuz için <sub alias> kullan.
function buildSsml(text, aliases) {
  const words = text.split(/\s+/).filter(Boolean);
  const parts = words.map((w, i) => {
    const m = w.match(/^(.*?)([.,:;!?]*)$/);
    const core = m[1], punct = m[2];
    const alias = aliases[core];
    const body = alias ? `<sub alias="${esc(alias)}">${esc(core)}</sub>` : esc(core);
    return `<mark name="w${i}"/>${body}${esc(punct)}`;
  });
  return { ssml: `<speak>${parts.join(' ')}<mark name="end"/></speak>`, words };
}

function wavInfo(buf) {
  // LINEAR16 yanıtı WAV başlığıyla gelir; "data" bloğunu bul.
  let off = 12, dataOff = -1, dataLen = 0, sr = SR;
  while (off < buf.length - 8) {
    const id = buf.toString('ascii', off, off + 4), len = buf.readUInt32LE(off + 4);
    if (id === 'fmt ') sr = buf.readUInt32LE(off + 12);
    if (id === 'data') { dataOff = off + 8; dataLen = Math.min(len, buf.length - off - 8); break; }
    off += 8 + len;
  }
  return { sr, duration: dataLen / 2 / sr, dataOff, dataLen };
}

// Sondaki sessizliği ölç (kelime bitişini doğru hesaplamak için).
function trailingSilence(buf, info) {
  const n = info.dataLen / 2;
  let i = n - 1;
  while (i > 0 && Math.abs(buf.readInt16LE(info.dataOff + i * 2)) < 300) i--;
  return (n - 1 - i) / info.sr;
}

async function synth(seg) {
  const v = topic.voice;
  const { ssml, words } = buildSsml(seg.text, topic.aliases || {});
  const body = {
    input: { ssml },
    voice: { languageCode: 'tr-TR', name: v.name },
    audioConfig: { audioEncoding: 'LINEAR16', sampleRateHertz: SR, speakingRate: v.speakingRate ?? 1, pitch: v.pitch ?? 0 },
    enableTimePointing: ['SSML_MARK'],
  };
  const key = crypto.createHash('sha1').update(JSON.stringify(body)).digest('hex').slice(0, 16);
  const cached = path.join(cacheDir, key + '.json');
  let res;
  if (fs.existsSync(cached)) {
    res = JSON.parse(fs.readFileSync(cached, 'utf8'));
  } else {
    const headers = { 'Content-Type': 'application/json' };
    if (process.env.GOOGLE_TTS_API_KEY) headers['X-Goog-Api-Key'] = process.env.GOOGLE_TTS_API_KEY;
    const r = await fetch(API, { method: 'POST', headers, body: JSON.stringify(body) });
    if (!r.ok) throw new Error(`Google TTS ${r.status}: ${(await r.text()).slice(0, 400)}`);
    res = await r.json();
    fs.writeFileSync(cached, JSON.stringify(res));
  }
  const audio = Buffer.from(res.audioContent, 'base64');
  const info = wavInfo(audio);
  const tail = trailingSilence(audio, info);
  const marks = Object.fromEntries((res.timepoints || []).map((tp) => [tp.markName, tp.timeSeconds]));
  const speechEnd = info.duration - tail;
  const wordTimes = words.map((w, i) => {
    const t0 = marks[`w${i}`];
    const t1 = marks[`w${i + 1}`] ?? Math.min(marks.end ?? speechEnd, speechEnd);
    return { w, t0, t1 };
  });
  // İşaret gelmediyse orantılı dağıt.
  if (wordTimes.some((x) => x.t0 == null)) return { audio, info, duration: speechEnd, words: proportional(words, speechEnd) };
  return { audio, info, duration: speechEnd, words: wordTimes };
}

function proportional(words, total) {
  const weight = words.map((w) => w.length + (/[.,:;!?]$/.test(w) ? 4 : 1));
  const sum = weight.reduce((a, b) => a + b, 0);
  let t = 0;
  return words.map((w, i) => { const d = (weight[i] / sum) * total; const o = { w, t0: t, t1: t + d * 0.92 }; t += d; return o; });
}

function estimate(seg) {
  const words = seg.text.split(/\s+/).filter(Boolean);
  const chars = seg.text.length;
  const duration = chars / 14.5 / (topic.voice.speakingRate ?? 1) * 1.08;
  return { duration, words: proportional(words, duration) };
}

const LEAD = { hook: 0.5, device: 0.75, outro: 0.45 };
const TAIL = { hook: 0.35, device: 2.1, outro: 1.6 };

let cursor = 0;
const segments = [];
for (const [i, seg] of topic.segments.entries()) {
  const r = preview ? estimate(seg) : await synth(seg);
  let voiceFile = null;
  if (!preview) {
    voiceFile = path.join(voiceDir, `${String(i).padStart(2, '0')}.wav`);
    fs.writeFileSync(voiceFile, r.audio);
  }
  const start = cursor;
  const voiceStart = start + LEAD[seg.kind];
  const voiceEnd = voiceStart + r.duration;
  const end = voiceEnd + TAIL[seg.kind];
  segments.push({ ...seg, start, voiceStart, voiceEnd, end, voiceFile,
    words: r.words.map((w) => ({ w: w.w, t0: +(voiceStart + w.t0).toFixed(3), t1: +(voiceStart + w.t1).toFixed(3) })) });
  console.log(`${seg.kind.padEnd(6)} ${seg.name ?? ''}`.padEnd(20), `${r.duration.toFixed(2)} sn`);
  cursor = end;
}

const timeline = { id: topic.id, series: topic.series, fps: 30, sr: SR, preview, duration: +cursor.toFixed(3), segments };
fs.writeFileSync(path.join(outDir, 'timeline.json'), JSON.stringify(timeline, null, 1));
console.log(`Toplam: ${cursor.toFixed(1)} sn ${preview ? '(ÖNİZLEME — seslendirme yok)' : ''}`);

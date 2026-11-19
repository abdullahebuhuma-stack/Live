"""Afro-Türk house remix (122 BPM) — orijinalin vokal stem'i üzerine sıfırdan yeni prodüksiyon.

Kullanım: python3 src/remix.py <stem klasörü (vocals/drums/bass/other.wav)> <çıkış klasörü>
Orijinal analiz: 128.0 BPM, ilk ölçü başı 0.887 sn, Mi minör. Vokal formant korunarak 122 BPM'e uyarlanır
(rubberband R3). Akorlar orijinalin her ölçüsündeki bas kökü + minör/majör tespitinden türetilir; aranjman
orijinalin enerji haritasını izler. Çıktılar: remix WAV, Ableton için ayrı stem'ler ve MIDI dosyaları.
"""
import json, os, subprocess, sys
import numpy as np, soundfile as sf, pyloudnorm as pyln, librosa, mido
from scipy.signal import butter, sosfilt, fftconvolve

sys.path.insert(0, os.path.dirname(__file__))
from audio import saw, svf_lp, lp, hp, bp, noise, fade, expdec  # mevcut sentez yardımcıları
TUNE_CENTS = -18.0  # orijinal kaydın akortu (bas ve vokal stem'inden ölçüldü)
def mtof(m):
    return 440.0 * 2 ** ((np.asarray(m, dtype=float) - 69 + TUNE_CENTS / 100) / 12)
import master as M  # true-peak limiter

SR = 44100
SRC_BPM, SRC_BAR0 = 128.0, 0.887
BPM = 122.0
BEAT = 60 / BPM; BAR = 4 * BEAT; STEP = BEAT / 4
K = SRC_BPM / BPM            # zaman uzama oranı
INTRO, OUTRO = 16, 16
rng = np.random.default_rng(122)
sec = lambda t: int(round(t * SR))

stem_dir, out_dir = sys.argv[1], sys.argv[2]
os.makedirs(os.path.join(out_dir, "ableton_stems"), exist_ok=True)
os.makedirs(os.path.join(out_dir, "midi"), exist_ok=True)


# ───────────── 1. orijinal analiz: ölçü başına kök, tip, enerji, vokal ─────────────
def load_mono(p, sr=22050):
    return librosa.load(p, sr=sr, mono=True)[0]

sr2 = 22050
vo, ba, ot, dr = (load_mono(os.path.join(stem_dir, f + ".wav")) for f in ("vocals", "bass", "other", "drums"))
src_bar = 4 * 60 / SRC_BPM
nbars = int((len(vo) / sr2 - SRC_BAR0) // src_bar)
Cb = librosa.feature.chroma_cqt(y=ba, sr=sr2, hop_length=512)
Co = librosa.feature.chroma_cqt(y=ot + 0.5 * vo, sr=sr2, hop_length=512)
fps = sr2 / 512
bars = []
for n in range(nbars):
    a, b = SRC_BAR0 + n * src_bar, SRC_BAR0 + (n + 1) * src_bar
    ia, ib = int(a * fps), int(b * fps)
    cb, co = Cb[:, ia:ib].mean(1), Co[:, ia:ib].mean(1)
    be = np.sqrt(np.mean(ba[int(a * sr2):int(b * sr2)] ** 2))
    root = int(np.argmax(cb if be > 0.01 else co))
    minor = co[(root + 3) % 12] >= co[(root + 4) % 12]
    seg = lambda x: np.sqrt(np.mean(x[int(a * sr2):int(b * sr2)] ** 2))
    bars.append({"root": root, "minor": bool(minor), "energy": float(seg(dr) + seg(ba) + seg(ot)), "vocal": float(seg(vo))})
# Mi minör (armonik) diyatonik tipler: Em, F#m, G, Am, B(majör, V), C, D — ölçüm gürültüsüne karşı sabitle
KEY_Q = {4: True, 6: True, 7: False, 9: True, 11: False, 0: False, 2: False}
for b_ in bars:
    if b_["root"] in KEY_Q: b_["minor"] = KEY_Q[b_["root"]]
# kök değişimini sakinleştir: tek ölçülük sapmaları komşulara eşitle
for n in range(1, nbars - 1):
    if bars[n - 1]["root"] == bars[n + 1]["root"] != bars[n]["root"] and bars[n]["energy"] > 0:
        bars[n]["root"], bars[n]["minor"] = bars[n - 1]["root"], bars[n - 1]["minor"]

vmax = max(b["vocal"] for b in bars)
first = next(i for i, b in enumerate(bars) if b["vocal"] > 0.15 * vmax) - 1
last = max(i for i, b in enumerate(bars) if b["vocal"] > 0.15 * vmax) + 1
used = list(range(max(first, 0), min(last + 1, nbars)))
E = np.array([bars[i]["energy"] for i in used])
q1, q2 = np.percentile(E, [30, 62])
levels = [0 if e < q1 else (1 if e < q2 else 2) for e in E]
# 4 ölçülük bloklara yuvarla (aranjman 4'lü cümlelerle hareket etsin)
for s in range(0, len(levels), 4):
    blk = levels[s:s + 4]; v = int(round(np.median(blk)))
    levels[s:s + 4] = [v] * len(blk)

NAMES = "C C# D D# E F F# G G# A A# B".split()
total_bars = INTRO + len(used) + OUTRO
plan = []  # remix ölçüsü başına: kök, tip, seviye
loop = [bars[i] for i in used[:4]]
for i in range(INTRO):
    plan.append({**loop[i % 4], "level": [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2][i], "intro": i})
for j, i in enumerate(used):
    plan.append({**bars[i], "level": levels[j]})
endloop = [bars[i] for i in used[-4:]]
for i in range(OUTRO):
    plan.append({**endloop[i % 4], "level": [2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0][i], "outro": i})
print(f"Orijinal: {nbars} ölçü, vokal ölçü {used[0]}–{used[-1]}. Remix: {total_bars} ölçü, {total_bars * BAR / 60:.2f} dk")
print("Akor haritası (ilk 16):", " ".join(NAMES[b["root"]] + ("m" if b["minor"] else "") for b in [bars[i] for i in used[:16]]))
print("Seviye haritası:", "".join(str(p["level"]) for p in plan))

N = sec(total_bars * BAR) + sec(4)
bt = lambda bar, step=0: bar * BAR + step * STEP
swing = lambda st: STEP * 0.08 if st % 2 else 0.0   # hafif 16'lık swing


# ───────────── 2. vokal: 122 BPM'e uyarlama + işleme ─────────────
tmp = os.path.join(out_dir, "_v_in.wav"); tmp2 = os.path.join(out_dir, "_v_st.wav")
vfull, vsr = sf.read(os.path.join(stem_dir, "vocals.wav"))
vfull = librosa.resample(vfull.T, orig_sr=vsr, target_sr=SR).T if vsr != SR else vfull
a0 = SRC_BAR0 + used[0] * src_bar
vcut = vfull[sec(a0): sec(SRC_BAR0 + (used[-1] + 1) * src_bar + 2)]
sf.write(tmp, vcut, SR, subtype="FLOAT")
subprocess.run(["rubberband", "-q", "-3", "-F", "-T", f"{BPM / SRC_BPM:.6f}", tmp, tmp2], check=True)
vst, _ = sf.read(tmp2); os.remove(tmp); os.remove(tmp2)
if vst.ndim == 1: vst = np.stack([vst, vst], 1)

voc_dry = np.zeros((N, 2)); i0 = sec(INTRO * BAR)
n = min(len(vst), N - i0); voc_dry[i0:i0 + n] = vst[:n]
vm = voc_dry.mean(1)
vproc = hp(vm, 140)
env = lp(np.abs(vproc), 15, 1); vproc = vproc / (1 + 3 * np.clip(env - 0.05, 0, None))  # yumuşak kompresör
# reverb (üretilmiş IR) + noktalı 8'lik delay
irn = sec(2.2); ir = noise(irn) * np.exp(-np.arange(irn) / (0.55 * SR)); ir = lp(ir, 5000)
ir2 = np.roll(ir, sec(0.013))
rev = np.stack([fftconvolve(vproc, ir)[:N], fftconvolve(vproc, ir2)[:N]], 1) * 0.045
dly = np.zeros(N); dt = sec(0.75 * BEAT); src = bp(vproc, 400, 5000) * 0.35
for k in range(1, 5):
    dly[dt * k:] += src[:N - dt * k] * (0.45 ** k)
voc = np.stack([vproc, vproc], 1) + rev + np.stack([dly * 0.8, np.roll(dly, sec(0.02)) * 1.0], 1)


# ───────────── 3. sesler ─────────────
def kick():
    n = sec(0.45); t = np.arange(n) / SR
    f = 46 + 120 * np.exp(-t / 0.022)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.2)
    x += hp(noise(n), 3000) * np.exp(-t / 0.002) * 0.25
    return fade(np.tanh(x * 1.7) * 0.9, 0.0005, 0.02)

def clap():
    n = sec(0.3); t = np.arange(n) / SR; nz = bp(noise(n), 1000, 4500); env = np.zeros(n)
    for d in (0, 0.009, 0.019):
        i = sec(d); env[i:] = np.maximum(env[i:], np.exp(-t[:n - i] / 0.007))
    return fade(nz * np.maximum(env, np.exp(-t / 0.09) * 0.5 * (t > 0.025)) * 1.8)

def shaker(acc):
    n = sec(0.07); t = np.arange(n) / SR
    env = np.minimum(1, t / 0.008) * np.exp(-t / 0.022)
    return fade(bp(noise(n), 5000, 12000) * env * (1.0 if acc else 0.55))

def conga(f0, slap=False):
    n = sec(0.35); t = np.arange(n) / SR
    f = f0 * (1 + 0.25 * np.exp(-t / 0.01))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (0.09 if slap else 0.16))
    x += bp(noise(n), 1500, 6000) * np.exp(-t / 0.006) * (0.5 if slap else 0.2)
    return fade(x * 0.8)

def rim():
    n = sec(0.06); t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * 1700 * t) * 0.6 + bp(noise(n), 2000, 8000) * 0.4) * np.exp(-t / 0.012)
    return fade(x * 0.6)

def ohat():
    n = sec(0.25); t = np.arange(n) / SR
    m = sum(np.sign(np.sin(2 * np.pi * f * t)) for f in (205, 304, 370, 523, 540, 800)) / 6
    return fade(bp(m * 0.5 + noise(n) * 0.5, 7000, 15000) * np.exp(-t / 0.07))

def sub(m, length):
    n = sec(length); t = np.arange(n) / SR; f = mtof(m)
    x = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
    x *= np.minimum(1, t / 0.004) * np.minimum(1, (length - t) / 0.02)
    return np.tanh(x * 1.4) * 0.8

def stab(notes, length, bright=1.0):
    n = sec(length); t = np.arange(n) / SR; x = np.zeros(n)
    for m in notes:
        f = mtof(m)
        x += saw(np.full(n, f * 1.004)) + saw(np.full(n, f * 0.996))
    cut = 600 + 2600 * bright * np.exp(-t / 0.12)
    y = svf_lp(x * 0.12, cut, 1.2)
    return fade(y * np.exp(-t / 0.5), 0.003, 0.03)

def pad(notes, length):
    n = sec(length); t = np.arange(n) / SR; L = np.zeros(n); R = np.zeros(n)
    for m in notes:
        f = mtof(m)
        L += saw(np.full(n, f * 1.006)); R += saw(np.full(n, f * 0.994))
    env = np.minimum(1, t / 0.6) * np.minimum(1, (length - t) / 0.6)
    return np.stack([lp(L, 1400) * env, lp(R, 1400) * env], 1) * 0.05

def marimba(m, vel=1.0):
    n = sec(0.5); t = np.arange(n) / SR; f = mtof(m)
    I = 2.2 * np.exp(-t / 0.02)
    x = np.sin(2 * np.pi * f * t + I * np.sin(2 * np.pi * f * 4 * t)) * np.exp(-t / 0.18)
    return fade(x * vel * 0.5, 0.001, 0.05)

def riser(length):
    n = sec(length); t = np.linspace(0, 1, n)
    return fade(svf_lp(noise(n), 300 + 8000 * t ** 2.2, 2.5) * t ** 2 * 0.4)

def voicing(root, minor):
    pcs = [0, 3, 7, 10, 14] if minor else ([0, 4, 7, 10] if root == 11 else [0, 4, 7, 11, 14])
    base = 48 + ((root - 48) % 12)
    if base > 55: base -= 12
    return [base + p for p in pcs]


# ───────────── 4. aranjman ─────────────
parts = {k: np.zeros(N) for k in ("kick", "clap", "perc", "shaker", "bass", "chords", "marimba", "fx")}
padbus = np.zeros((N, 2))
midi = {k: [] for k in ("kick", "clap", "perc", "bass", "chords", "marimba")}  # (başlangıç beat, süre beat, nota, vel)

def put(name, sig, t, g=1.0):
    i = sec(t)
    if i >= N or i < 0: return
    n = min(len(sig), N - i); parts[name][i:i + n] += sig[:n] * g

KICK, CLAP, RIM, OH = kick(), clap(), rim(), ohat()
CH, CL, CS = conga(320), conga(210), conga(320, True)
prev_level = 0
for b, p in enumerate(plan):
    lv, root, minor = p["level"], p["root"], p["minor"]
    intro, outro = p.get("intro"), p.get("outro")
    nxt = plan[b + 1]["level"] if b + 1 < len(plan) else 0
    notes = voicing(root, minor); bassn = 28 + ((root - 4) % 12) + (0 if (root - 4) % 12 < 8 else -12) + 12
    fill = nxt > lv  # sonraki ölçüde enerji artıyor: son vuruşu boşalt, riser
    for st in range(16):
        t = bt(b, st) + swing(st)
        if lv >= 1 and st % 4 == 0 and not (fill and st == 12):
            put("kick", KICK, t, 1.0); midi["kick"].append((b * 4 + st / 4, 0.25, 36, 110))
        if lv == 2 and st in (4, 12):
            put("clap", CLAP, t, 0.55); midi["clap"].append((b * 4 + st / 4, 0.25, 39, 100))
        # shaker her zaman (intro'nun ilk 2 ölçüsü hariç), break'te hafif
        if not (intro is not None and intro < 2) and not (outro is not None and outro >= 14):
            put("shaker", shaker(st % 4 == 2), t, 0.22 if lv == 0 else 0.32)
        if lv >= 1 or (intro is not None and intro >= 2):
            if st in (3, 6, 11, 14): put("perc", RIM, t, 0.35); midi["perc"].append((b * 4 + st / 4, 0.25, 37, 80))
        if lv >= 1:
            if st in (2, 10): put("perc", CH, t, 0.5); midi["perc"].append((b * 4 + st / 4, 0.25, 63, 90))
            if st in (7, 15): put("perc", CL, t, 0.55); midi["perc"].append((b * 4 + st / 4, 0.25, 64, 90))
            if st == 13 and b % 2: put("perc", CS, t, 0.45); midi["perc"].append((b * 4 + st / 4, 0.25, 62, 100))
        if lv == 2 and st in (2, 6, 10, 14):
            put("perc", OH, t, 0.22); midi["perc"].append((b * 4 + st / 4, 0.25, 46, 70))
    # bas: afro senkop (kök, kök, oktav, beşli, kök)
    if lv >= 1 and not (intro is not None and intro < 8):
        for st, off, ln in [(0, 0, 2), (3, 0, 2), (7, 12, 1), (10, 7, 2), (14, 0, 2)]:
            put("bass", sub(bassn + off, ln * STEP * 0.95), bt(b, st) + swing(st), 0.8)
            midi["bass"].append((b * 4 + st / 4, ln / 4 * 0.95, bassn + off, 100))
    # akorlar: stab (0, 6, 10) ya da break'te pad
    if lv >= 1 and not (intro is not None and intro < 12):
        for st, ln in [(0, 3), (6, 1.5), (10, 2)]:
            put("chords", stab(notes, ln * STEP, 0.6 + 0.4 * (lv == 2)), bt(b, st) + swing(st), 0.9)
            for m in notes: midi["chords"].append((b * 4 + st / 4, ln / 4, m, 90))
    if lv == 0 or (intro is not None and intro >= 8):
        pp = pad(notes, BAR + 0.3); i = sec(bt(b)); n = min(len(pp), N - i); padbus[i:i + n] += pp[:n]
    # marimba arpeji (tam enerji)
    if lv == 2:
        tones = [m + 12 for m in notes[:4]]
        for k, st in enumerate((0, 2, 3, 5, 6, 8, 10, 11, 13, 14)):
            m = tones[[0, 2, 1, 3, 2, 0, 3, 1, 2, 3][k] % len(tones)]
            put("marimba", marimba(m, 0.7 + 0.3 * (st % 4 == 0)), bt(b, st) + swing(st), 0.5)
            midi["marimba"].append((b * 4 + st / 4, 0.25, m, 90))
    if fill:
        put("fx", riser(BAR), bt(b), 0.5)
    prev_level = lv

# vokal chop teaser (intro 8–15. ölçüler): vokalin en güçlü ölçüsünden 8'lik dilimler
vbar = max(range(len(used)), key=lambda j: bars[used[j]]["vocal"])
vs = vm[sec((INTRO + vbar) * BAR): sec((INTRO + vbar + 1) * BAR)]
ch8 = [fade(vs[sec(k * 2 * STEP): sec(k * 2 * STEP + 1.8 * STEP)], 0.003, 0.02) for k in range(8)]
chops = np.zeros(N)
for b in range(8, 16):
    for k, src_i in enumerate([0, 0, 2, 0, 4, 4, 6, 2]):
        i = sec(bt(b, 2 * k)); s = ch8[src_i]; n = min(len(s), N - i); chops[i:i + n] += s[:n]
chops = bp(chops, 300, 6000) * 0.9

# sidechain: kick'ten türeyen ducking
kenv = lp(np.abs(parts["kick"]), 12, 1); duck = 1 - 0.65 * np.clip(kenv / (kenv.max() + 1e-9) * 2.5, 0, 1)
for k in ("bass", "chords", "marimba"): parts[k] *= duck
padbus *= duck[:, None]


# ───────────── 5. stereo miks ─────────────
def st(x, pan=0.0):
    a = (pan + 1) * np.pi / 4; return np.stack([x * np.cos(a), x * np.sin(a)], 1) * 1.414

mar_l = parts["marimba"]; mar = np.stack([mar_l, np.roll(mar_l, sec(0.012)) * 0.9], 1)
buses = {  # denge: kick ~-12, vokal ~-14, bas ~-15.5, perc ~-17, akor/pad ~-20, marimba ~-23.5 LUFS
    "kick": st(parts["kick"]) * 0.75,
    "clap": st(parts["clap"]) * 1.17,
    "perc": st(parts["perc"], -0.25) * 0.9,
    "shaker": st(parts["shaker"], 0.35) * 1.3,
    "bass": st(lp(parts["bass"], 250)) * 0.85,
    "chords": st(hp(parts["chords"], 150), 0.1) * 1.5 + st(np.roll(hp(parts["chords"], 150), sec(0.015)), -0.6) * 0.5,
    "pad": padbus * 1.6,
    "marimba": mar * 1.2,
    "fx": st(parts["fx"]) * 0.5,
    "vocal": voc * 0.41 + st(chops, -0.2) * 0.25,
}
mix = sum(buses.values())
for k_, v_ in buses.items():
    l_ = meter_ = pyln.Meter(SR).integrated_loudness(v_) if np.abs(v_).max() > 0 else -99
    print(f"  bus {k_:8} {l_:6.1f} LUFS  tepe {20*np.log10(np.abs(v_).max()+1e-9):6.1f} dBFS")
print(f"  toplam tepe/loudness farkı (crest) {20*np.log10(np.abs(mix).max()) - pyln.Meter(SR).integrated_loudness(mix):.1f} dB")
mix = sosfilt(butter(2, 25 / (SR / 2), "high", output="sos"), mix, axis=0)
end = sec(total_bars * BAR + 1.5); mix = mix[:end]
meter = pyln.Meter(SR)
TARGET = -11.0
for _ in range(4):
    y = mix * 10 ** ((TARGET - meter.integrated_loudness(mix)) / 20)
    pre = y.copy(); y, gr = M.tp_limit(y, -1.3)
    d = TARGET - meter.integrated_loudness(y)
    if abs(d) < 0.05: break
    mix = mix * 10 ** (d / 20)
grs = 20 * np.log10(np.maximum(np.abs(y).max(1), 1e-9) / np.maximum(np.abs(pre).max(1), 1e-9))[np.abs(pre).max(1) > 0.05]
print(f"limiter: zamanın %{100 * np.mean(grs < -1):.1f}'inde 1 dB'den, %{100 * np.mean(grs < -3):.1f}'inde 3 dB'den fazla kısıyor")
f = np.ones(len(y)); f[-sec(1.5):] = np.linspace(1, 0, sec(1.5)); y *= f[:, None]
outf = os.path.join(out_dir, "hayko_bitikals_afro_turk_remix_122bpm.wav")
sf.write(outf, y, SR, subtype="PCM_24")
print(f"{outf}: {meter.integrated_loudness(y):.1f} LUFS, true peak {M.true_peak(y):.2f} dBTP, limiter en fazla {gr:.1f} dB")

# ───────────── 6. Ableton paketi: stem + MIDI ─────────────
for k, v in buses.items():
    sf.write(os.path.join(out_dir, "ableton_stems", f"{k}.wav"), v[:end] * 0.5, SR, subtype="PCM_24")
sf.write(os.path.join(out_dir, "ableton_stems", "vocal_dry_122bpm.wav"), voc_dry[:end], SR, subtype="PCM_24")
for k, evs in midi.items():
    mf = mido.MidiFile(ticks_per_beat=480); tr = mido.MidiTrack(); mf.tracks.append(tr)
    tr.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(BPM)))
    tr.append(mido.MetaMessage("track_name", name=k))
    msgs = []
    for s_, d_, n_, v_ in evs:
        msgs.append((int(s_ * 480), 1, n_, v_)); msgs.append((int((s_ + d_) * 480), 0, n_, 0))
    msgs.sort(key=lambda m: (m[0], m[1]))
    last_t = 0
    for t_, on, n_, v_ in msgs:
        tr.append(mido.Message("note_on" if on else "note_off", note=int(n_), velocity=int(v_), time=t_ - last_t)); last_t = t_
    mf.save(os.path.join(out_dir, "midi", f"{k}.mid"))
json.dump({"bpm": BPM, "key": "E minor", "bars": total_bars, "levels": [p["level"] for p in plan],
           "chords": [NAMES[p["root"]] + ("m" if p["minor"] else "") for p in plan]},
          open(os.path.join(out_dir, "arrangement.json"), "w"), ensure_ascii=False)
print("Stem'ler:", ", ".join(sorted(os.listdir(os.path.join(out_dir, "ableton_stems")))))

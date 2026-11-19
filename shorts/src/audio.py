"""Ses tasarımı + miks + master.

Kullanım: python3 src/audio.py out/<id>/timeline.json
Çıktılar: mix.wav (−14 LUFS, −1 dBFS tavan), env.json (görseller için ses verisi), events.json (nota/step olayları)
Her cihazın imza sesi kendi sentez yöntemiyle koddan üretilir; hiçbir hazır sample kullanılmaz.
"""
import json, os, sys, wave
import numpy as np
from scipy.signal import butter, sosfilt
import pyloudnorm as pyln

SR = 44100
rng = np.random.default_rng(1970)


# ───────────────────────── yardımcılar ─────────────────────────
def mtof(m):
    return 440.0 * 2 ** ((np.asarray(m, dtype=float) - 69) / 12)


def sec(n):
    return int(round(n * SR))


def lp(x, fc, order=2):
    return sosfilt(butter(order, min(fc, SR * 0.45) / (SR / 2), 'low', output='sos'), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc / (SR / 2), 'high', output='sos'), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo / (SR / 2), min(hi, SR * 0.45) / (SR / 2)], 'band', output='sos'), x)


def place(buf, sig, t, gain=1.0):
    i = sec(t)
    if i >= len(buf):
        return
    if i < 0:
        sig, i = sig[-i:], 0
    n = min(len(sig), len(buf) - i)
    buf[i:i + n] += sig[:n] * gain


def expdec(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


def fade(x, a=0.003, r=0.01):
    x = x.copy()
    na, nr = min(sec(a), len(x)), min(sec(r), len(x))
    if na: x[:na] *= np.linspace(0, 1, na)
    if nr: x[-nr:] *= np.linspace(1, 0, nr)
    return x


def saw(freq):
    """PolyBLEP testere dişi (alias azaltılmış). freq: örnek başına frekans dizisi."""
    dt = np.asarray(freq) / SR
    ph = np.cumsum(dt) % 1.0
    y = 2 * ph - 1
    m = ph < dt
    t = ph[m] / dt[m]
    y[m] -= t + t - t * t - 1
    m = ph > 1 - dt
    t = (ph[m] - 1) / dt[m]
    y[m] -= t * t + t + t + 1
    return y


def square(freq):
    dt = np.asarray(freq) / SR
    ph = np.cumsum(dt)
    return np.sign(np.sin(2 * np.pi * ph)) * 0.8


def svf_lp(x, cutoff, q, drive=1.0):
    """TPT state-variable lowpass, örnek bazında değişen cutoff. Moog/303 filtre karakteri için."""
    cutoff = np.broadcast_to(np.clip(cutoff, 20, SR * 0.45), x.shape)
    g = np.tan(np.pi * cutoff / SR)
    k = 1.0 / q
    a1 = 1 / (1 + g * (g + k)); a2 = g * a1; a3 = g * a2
    y = np.empty_like(x)
    ic1 = ic2 = 0.0
    xin = np.tanh(x * drive) if drive != 1.0 else x
    for n in range(len(x)):
        v3 = xin[n] - ic2
        v1 = a1[n] * ic1 + a2[n] * v3
        v2 = ic2 + a2[n] * ic1 + a3[n] * v3
        ic1 = 2 * v1 - ic1
        ic2 = 2 * v2 - ic2
        y[n] = v2
    return y


def noise(n):
    return rng.uniform(-1, 1, n)


# ───────────────────────── davul sesleri ─────────────────────────
def kick808(length=0.9, tune=48):
    n = sec(length); t = np.arange(n) / SR
    f = tune + 95 * np.exp(-t / 0.028)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t / (length * 0.42))
    click = hp(noise(n), 3000) * np.exp(-t / 0.002) * 0.25
    return fade(np.tanh((body + click) * 1.6) * 0.9, 0.0005, 0.05)


def kick_punch(length=0.32):
    n = sec(length); t = np.arange(n) / SR
    f = 52 + 160 * np.exp(-t / 0.018)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.11)
    click = hp(noise(n), 2500) * np.exp(-t / 0.003) * 0.4
    return fade(np.tanh((body + click) * 2.2) * 0.85, 0.0005, 0.02)


def clap808(length=0.35):
    n = sec(length); t = np.arange(n) / SR
    nz = bp(noise(n), 900, 2600)
    env = np.zeros(n)
    for d in (0, 0.011, 0.022):
        i = sec(d); env[i:] = np.maximum(env[i:], np.exp(-(t[: n - i]) / 0.008))
    env = np.maximum(env, np.exp(-t / 0.12) * 0.55 * (t > 0.03))
    return fade(nz * env * 2.2)


def snare_mpc(length=0.28):
    n = sec(length); t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.05)
    nz = bp(noise(n), 1500, 9000) * np.exp(-t / 0.09)
    return fade(np.tanh((tone * 0.7 + nz * 1.1) * 1.5) * 0.8)


def hat(open_=False, bright=1.0):
    length = 0.42 if open_ else 0.06
    n = sec(length); t = np.arange(n) / SR
    # 808 tarzı: 6 kare dalga metalik küme + gürültü
    freqs = [205.3, 304.4, 369.6, 522.7, 540, 800]
    metal = sum(np.sign(np.sin(2 * np.pi * f * t)) for f in freqs) / 6
    x = bp(metal * 0.6 + noise(n) * 0.5, 6500 * bright, 15000)
    return fade(x * np.exp(-t / (0.16 if open_ else 0.018)) * 1.4)


def cowbell():
    n = sec(0.3); t = np.arange(n) / SR
    x = (np.sign(np.sin(2 * np.pi * 540 * t)) + np.sign(np.sin(2 * np.pi * 800 * t))) * 0.5
    x = bp(x, 600, 2800)
    env = np.exp(-t / 0.02) * 0.6 + np.exp(-t / 0.11) * 0.4
    return fade(x * env * 0.7)


# ───────────────────────── geçiş efektleri ─────────────────────────
def whoosh(length=0.55, rise=True):
    n = sec(length); t = np.linspace(0, 1, n)
    nz = noise(n)
    fc = 300 + 6000 * (t ** 2 if rise else (1 - t) ** 2)
    x = svf_lp(nz, fc, 2.5) - svf_lp(nz, fc * 0.4, 0.7) * 0.6
    env = np.sin(np.pi * t) ** 1.5
    return fade(x * env * 0.55)


def impact(length=1.2):
    n = sec(length); t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * np.cumsum(38 + 70 * np.exp(-t / 0.05)) / SR) * np.exp(-t / 0.35)
    crack = lp(noise(n), 5000) * np.exp(-t / 0.025) * 0.5
    tail = lp(noise(n), 900) * np.exp(-t / 0.4) * 0.12
    return fade(np.tanh((sub + crack + tail) * 1.3) * 0.8)


def riser(length):
    n = sec(length); t = np.linspace(0, 1, n)
    nz = noise(n)
    x = svf_lp(nz, 200 + 7000 * t ** 2.5, 3) * 0.5
    tone = saw(110 * 2 ** (t * 2)) * 0.12
    tone = lp(tone, 3000)
    return fade((x + tone) * t ** 2)


def tick():
    n = sec(0.03); t = np.arange(n) / SR
    return np.sin(2 * np.pi * 2200 * t) * np.exp(-t / 0.004) * 0.25


# ───────────────────────── cihaz motorları ─────────────────────────
# Her biri: (sinyal, olaylar). Olaylar görselleri sesle senkronlar.

def dev_moog(dur, t0):
    bpm = 108; s16 = 60 / bpm / 4
    out = np.zeros(sec(dur)); ev = []
    bass = [45, 45, 57, 45, 43, 45, 52, 50]  # A1 hattı, 8'lik
    lead = [(0, 69, 6), (6, 72, 2), (8, 76, 6), (14, 74, 2), (16, 72, 8), (24, 71, 4), (28, 67, 4)]
    steps = int(dur / s16) + 1
    for s in range(0, steps, 2):
        t = s * s16
        m = bass[(s // 2) % len(bass)]
        L = s16 * 1.9; n = sec(L); tt = np.arange(n) / SR
        f = mtof(m)
        osc = saw(np.full(n, f)) + saw(np.full(n, f * 1.004)) + saw(np.full(n, f * 0.996)) * 0.8 + square(np.full(n, f / 2)) * 0.5
        cut = 180 + 2200 * np.exp(-tt / 0.09)
        y = svf_lp(osc * 0.3, cut, 1.4, drive=1.6) * np.minimum(1, np.exp(-(tt - L * 0.8).clip(0) / 0.02))
        place(out, fade(y, 0.002, 0.01), t, 0.8)
        ev.append({"t": t0 + t, "type": "note", "midi": m, "dur": L})
    bar = s16 * 32
    for b in range(int(dur / bar) + 1):
        for st, m, ln in lead:
            t = b * bar + st * s16
            if t > dur: break
            L = ln * s16; n = sec(L); tt = np.arange(n) / SR
            vib = 1 + 0.006 * np.sin(2 * np.pi * 5.2 * tt) * np.clip((tt - 0.25) / 0.3, 0, 1)
            f = mtof(m) * vib
            osc = saw(f) + saw(f * 1.006) * 0.7
            y = svf_lp(osc * 0.25, 900 + 2400 * np.exp(-tt / 0.25), 1.1, drive=1.3)
            env = np.minimum(1, tt / 0.012) * np.exp(-tt / 2.5)
            place(out, fade(y * env, 0.005, 0.04), t, 0.45)
            ev.append({"t": t0 + t, "type": "note", "midi": m, "dur": L})
    return out, ev


def dev_808(dur, t0):
    bpm = 98; s16 = 60 / bpm / 4
    out = np.zeros(sec(dur)); ev = []
    K = [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0]
    C = [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0]
    H = [1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0]
    O = [0] * 14 + [1, 0]
    B = [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0]
    k, c, ho, hc, cb = kick808(), clap808(), hat(True), hat(False), cowbell()
    for s in range(int(dur / s16) + 1):
        t = s * s16; i = s % 16
        ev.append({"t": t0 + t, "type": "step", "i": i})
        if K[i]: place(out, k, t, 1.0); ev.append({"t": t0 + t, "type": "hit", "v": "kick"})
        if C[i]: place(out, c, t, 0.7); ev.append({"t": t0 + t, "type": "hit", "v": "clap"})
        if H[i]: place(out, hc, t, 0.35 if i % 4 else 0.45)
        if O[i]: place(out, ho, t, 0.3)
        if B[i] and (s // 16) % 2 == 1: place(out, cb, t, 0.4); ev.append({"t": t0 + t, "type": "hit", "v": "cowbell"})
    return out, ev


def dev_303(dur, t0):
    bpm = 126; s16 = 60 / bpm / 4
    #        nota, aksan, slide, gate
    pat = [(33, 1, 0, 1), (33, 0, 0, 1), (45, 0, 1, 1), (33, 0, 0, 0),
           (36, 1, 0, 1), (33, 0, 0, 1), (43, 0, 1, 1), (45, 1, 0, 1),
           (33, 0, 0, 1), (40, 0, 0, 0), (33, 1, 0, 1), (38, 0, 1, 1),
           (36, 0, 0, 1), (48, 1, 0, 1), (33, 0, 1, 1), (31, 0, 0, 1)]
    steps = int(dur / s16) + 1
    n = sec(dur)
    freq = np.zeros(n); amp = np.zeros(n); fenv = np.zeros(n); ev = []
    prev = mtof(33)
    for s in range(steps):
        m, acc, sl, gate = pat[s % 16]
        i0, i1 = sec(s * s16), min(n, sec((s + 1) * s16))
        if i0 >= n: break
        L = i1 - i0; tt = np.arange(L) / SR
        f = mtof(m)
        if sl:  # 303 slide: önceki notadan süzülerek gel
            freq[i0:i1] = prev + (f - prev) * (1 - np.exp(-tt / 0.03))
        else:
            freq[i0:i1] = f
        prev = f
        if gate:
            gl = int(L * (1.0 if sl else 0.62))
            amp[i0:i0 + gl] = np.minimum(1, tt[:gl] / 0.002) * (1.3 if acc else 0.9)
            fenv[i0:i1] = np.exp(-tt / (0.07 if acc else 0.16)) * (1.6 if acc else 1.0)
            ev.append({"t": t0 + s * s16, "type": "step", "i": s % 16, "midi": m, "acc": acc})
    amp = lp(amp, 300, 1)
    # Cutoff düğmesi segment boyunca açılıyor (klasik acid hareketi)
    knob = np.clip(np.linspace(0.12, 0.95, n) + 0.08 * np.sin(np.linspace(0, 6.0, n)), 0, 1)
    cutoff = 140 + 900 * knob ** 1.5 + 2600 * fenv * (0.35 + knob)
    osc = saw(freq)
    y = svf_lp(osc * amp * 0.5, cutoff, 7.5, drive=2.0)
    y = np.tanh(y * 1.8) * 0.75
    for k in range(0, n, sec(0.1)):
        ev.append({"t": t0 + k / SR, "type": "knob", "v": round(float(knob[k]), 3)})
    # Hafif kick ritmi (dört dörtlük) eşlik etsin
    kk = kick_punch(0.25)
    for b in range(int(dur / (s16 * 4)) + 1):
        place(y, kk, b * s16 * 4, 0.55)
    return y, ev


def fm_note(m, length, vel=1.0):
    n = sec(length); t = np.arange(n) / SR
    f = mtof(m)
    I = 1.7 * np.exp(-t / 0.5) + 0.25
    body = np.sin(2 * np.pi * f * t + I * np.sin(2 * np.pi * f * t))
    tineI = 2.8 * np.exp(-t / 0.035)
    tine = np.sin(2 * np.pi * f * t + tineI * np.sin(2 * np.pi * f * 14 * t)) * np.exp(-t / 0.25)
    env = np.minimum(1, t / 0.003) * np.exp(-t / 1.6)
    return fade((body * 0.75 + tine * 0.28 * vel) * env * vel, 0.002, 0.15)


def dev_dx7(dur, t0):
    bpm = 84; beat = 60 / bpm
    out = np.zeros(sec(dur)); ev = []
    chords = [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59, 62]]
    bassn = [41, 40, 38, 36]
    for b in range(int(dur / (beat * 4)) + 1):
        ch = chords[b % 4]; t = b * beat * 4
        for j, m in enumerate(ch):
            place(out, fm_note(m, beat * 4.2, 0.8), t + j * 0.018, 0.32)
        place(out, fm_note(bassn[b % 4], beat * 4, 0.6), t, 0.35)
        ev.append({"t": t0 + t, "type": "chord", "notes": ch, "dur": beat * 4})
        # ikinci vuruşta ince arpej
        for j, m in enumerate(ch[1:3]):
            place(out, fm_note(m + 12, beat * 1.5, 0.6), t + beat * (2.5 + j * 0.5), 0.18)
            ev.append({"t": t0 + t + beat * (2.5 + j * 0.5), "type": "note", "midi": m + 12, "dur": beat})
    # basit koro/genişlik hissi: modüle gecikme
    d = sec(0.012)
    wet = np.concatenate([np.zeros(d), out[:-d]])
    return out * 0.8 + wet * 0.35, ev


def dev_mpc(dur, t0):
    bpm = 90; s16 = 60 / bpm / 4; swing = 0.60
    out = np.zeros(sec(dur)); ev = []
    # "Sample": FM akorundan kesilmiş, filtrelenmiş, 12-bit'e indirgenmiş dilimler
    src = np.zeros(sec(4.0))
    for j, m in enumerate([57, 60, 64, 67]):
        place(src, fm_note(m, 3.5, 0.7), j * 0.01, 0.3)
    src = lp(src, 3800)
    src = np.round(src * 2047) / 2047  # 12-bit
    chops = [src[sec(0):sec(0.9)], src[sec(0.25):sec(0.9)], src[sec(0.5):sec(1.1)], src[sec(0.05):sec(0.45)]]
    chops = [fade(c, 0.002, 0.03) for c in chops]
    K = [1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0]
    S = [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0]
    CH = {0: 0, 3: 3, 6: 1, 8: 2, 11: 3, 14: 1}
    kk, sn = kick_punch(), snare_mpc()
    hc = hat(False, 0.8)
    for s in range(int(dur / s16) + 1):
        i = s % 16
        t = s * s16 + (s16 * (swing - 0.5) * 2 if i % 2 else 0)
        if K[i]: place(out, kk, t, 0.95); ev.append({"t": t0 + t, "type": "pad", "i": 12})
        if S[i]: place(out, sn, t, 0.8); ev.append({"t": t0 + t, "type": "pad", "i": 13})
        if i % 2 == 0 or i in (7, 15): place(out, hc, t, 0.22 + 0.1 * (i % 4 == 0)); ev.append({"t": t0 + t, "type": "pad", "i": 14})
        if (s // 16) % 2 == 0 and i in CH or (s // 16) % 2 == 1 and i in (0, 6, 8, 14):
            ci = CH.get(i, 0)
            place(out, chops[ci], t, 0.9); ev.append({"t": t0 + t, "type": "pad", "i": ci})
    # plak cızırtısı
    crackle = (rng.random(len(out)) > 0.9993) * rng.uniform(-0.25, 0.25, len(out))
    out += hp(crackle, 1500) + lp(noise(len(out)), 4000) * 0.004
    return out, ev


def pad_drone(dur, notes=(45, 52, 57, 60)):
    n = sec(dur); t = np.arange(n) / SR
    x = np.zeros(n)
    for m in notes:
        f = mtof(m)
        x += saw(np.full(n, f * 1.003)) + saw(np.full(n, f * 0.997))
    x = lp(x * 0.06, 900, 2)
    lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.25 * t)
    return fade(x * lfo, 0.4, 0.4)


DEVICES = {"moog": dev_moog, "tr808": dev_808, "tb303": dev_303, "dx7": dev_dx7, "mpc": dev_mpc}


# ───────────────────────── miks ─────────────────────────
def read_wav(path):
    with wave.open(path) as w:
        sr, ch = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float) / 32768
    if ch > 1: x = x.reshape(-1, ch).mean(1)
    if sr != SR:
        x = np.interp(np.arange(0, len(x) * SR / sr) * sr / SR, np.arange(len(x)), x)
    return x


def follow(x, att=0.005, rel=0.15):
    """Basit envelope follower (sidechain için)."""
    a = np.abs(x)
    a = lp(a, 20, 1)
    return np.clip(a, 0, None)


def limiter(x, ceiling=0.89, look=0.004, rel=0.08):
    from scipy.ndimage import maximum_filter1d, uniform_filter1d
    pk = maximum_filter1d(np.abs(x), size=sec(look) * 2 + 1)
    g = np.minimum(1.0, ceiling / np.maximum(pk, 1e-9))
    # yumuşak bırakma: minimumu koru, sonra düzle
    g = -maximum_filter1d(-g, size=sec(look) * 2 + 1)
    g = uniform_filter1d(g, size=sec(look))
    a = np.exp(-1 / (rel * SR))
    out = g.copy()
    for i in range(1, len(out)):  # release
        if out[i] > out[i - 1]:
            out[i] = out[i - 1] + (1 - a) * (out[i] - out[i - 1])
    return x * out


def main(tl_path):
    tl = json.load(open(tl_path))
    out_dir = os.path.dirname(tl_path)
    D = tl["duration"]; N = sec(D) + sec(0.5)
    music = np.zeros(N); sfx = np.zeros(N); voice = np.zeros(N)
    events = []
    devices_seen = []

    for i, seg in enumerate(tl["segments"]):
        s, ve, e = seg["start"], seg["voiceEnd"], seg["end"]
        if seg.get("voiceFile"):
            place(voice, read_wav(seg["voiceFile"]), seg["voiceStart"])
        if seg["kind"] == "hook":
            place(music, pad_drone(e - s + 0.4), s, 0.9)
            place(sfx, riser(e - s), s, 0.5)
        elif seg["kind"] == "device":
            dev = seg["device"]; devices_seen.append(dev)
            sig, ev = DEVICES[dev](e - s, s)
            # anlatım altında düşük, "DİNLE" anında tam ses
            n = len(sig); tt = np.arange(n) / SR + s
            gain = np.where(tt < ve, 0.42, 1.0)
            gain = lp(gain, 12, 1)
            gain *= np.clip((tt - s) / 0.05, 0, 1) * np.clip((e - tt) / 0.12, 0, 1)
            place(music, sig * gain, s)
            events += ev
            place(sfx, whoosh(0.55), s - 0.42, 0.7)
            place(sfx, impact(), s + 0.02, 0.75)
            for k in range(6):  # yıl sayacı tıkları
                place(sfx, tick(), s + 0.15 + k * 0.09, 0.6)
        elif seg["kind"] == "outro":
            place(sfx, whoosh(0.55), s - 0.42, 0.7)
            place(sfx, impact(), s + 0.02, 0.55)
            # final: 808 ritmi + DX7 akorları birlikte
            a, ev1 = dev_808(e - s, s)
            b, _ = dev_dx7(e - s, s)
            g = np.clip((e - (np.arange(len(a)) / SR + s)) / 1.2, 0, 1)
            place(music, (a * 0.55 + b * 0.8) * g, s, 0.6)
            events += [x for x in ev1 if x["type"] == "step"]

    # vokal işleme: low-cut + hafif kompresyon
    voice = hp(voice, 85)
    venv = follow(voice)
    vgain = 1 / (1 + 2.0 * np.clip(venv - 0.08, 0, None))
    voice = voice * vgain * 1.25

    # sidechain: konuşma varken müzik + efekt kısılır
    duck = 1 - 0.55 * np.clip(follow(voice) / 0.06, 0, 1)
    duck = lp(duck, 8, 1)
    music_bus = hp(music, 30) * duck
    mix = voice + music_bus * 0.85 + sfx * (0.6 + 0.4 * duck)

    # loudness: -14 LUFS, sonra limiter (−1 dBFS)
    meter = pyln.Meter(SR)
    loud = meter.integrated_loudness(mix)
    mix = mix * 10 ** ((-14 - loud) / 20)
    mix = limiter(mix, ceiling=10 ** (-1.2 / 20))
    loud2 = meter.integrated_loudness(mix)
    mix *= 10 ** ((-14 - loud2) / 20)
    mix = np.clip(mix, -0.891, 0.891)

    stereo = np.stack([mix, mix], 1)
    with wave.open(os.path.join(out_dir, "mix.wav"), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((stereo * 32767).astype(np.int16).tobytes())

    # ── görseller için ses verisi (kare başına) ──
    fps = tl["fps"]; nf = int(np.ceil(D * fps)) + 1
    vis = music_bus * 0.85 + sfx * 0.6
    win = 2048
    edges = np.geomspace(40, 12000, 25)
    freqs = np.fft.rfftfreq(win, 1 / SR)
    hann = np.hanning(win)
    frames = []
    for f in range(nf):
        c = sec(f / fps)
        a, b = max(0, c - win // 2), min(len(vis), c + win // 2)
        seg = np.zeros(win); seg[: b - a] = vis[a:b]
        sp = np.abs(np.fft.rfft(seg * hann))
        bands = []
        for k in range(24):
            m = (freqs >= edges[k]) & (freqs < edges[k + 1])
            v = sp[m].mean() if m.any() else 0
            bands.append(float(np.clip((20 * np.log10(v + 1e-9) + 10) / 50, 0, 1)))
        sc = vis[c: c + 1470: 15]
        sc = np.pad(sc, (0, 98 - len(sc)))[:98]
        vr = float(np.sqrt(np.mean(voice[max(0, c - 735): c + 735] ** 2))) if c < len(voice) else 0
        mr = float(np.sqrt(np.mean(vis[max(0, c - 735): c + 735] ** 2))) if c < len(vis) else 0
        frames.append({"m": round(min(1, mr * 4), 3), "v": round(min(1, vr * 5), 3),
                       "b": [round(x, 2) for x in bands], "s": [round(float(x) * 2.5, 3) for x in sc]})
    json.dump({"fps": fps, "frames": frames}, open(os.path.join(out_dir, "env.json"), "w"), separators=(",", ":"))
    events.sort(key=lambda x: x["t"])
    json.dump(events, open(os.path.join(out_dir, "events.json"), "w"), separators=(",", ":"))
    pk = 20 * np.log10(np.abs(mix).max() + 1e-9)
    print(f"mix.wav: {len(mix)/SR:.1f} sn, {meter.integrated_loudness(mix):.1f} LUFS, tepe {pk:.1f} dBFS, {len(events)} olay")


if __name__ == "__main__":
    main(sys.argv[1])

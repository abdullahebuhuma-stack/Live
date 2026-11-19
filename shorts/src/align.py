"""Kendi ses kaydınızı videoya hizalar (Google TTS yerine).

Kullanım:
  python3 src/align.py topics/<konu>.json <kayıt>
<kayıt> şunlardan biri olabilir:
  - tek dosya (wav/mp3/m4a/aiff...): tüm metni bir seferde okuyun, bölümler arasında ~1 sn sus.
  - klasör: bölüm başına bir dosya, alfabetik sırayla (01.wav, 02.wav, ...). Dosya sayısı = segment sayısı.

Kelime zamanları: duraklamalar noktalama işaretlerine eşlenir, her ifadenin içinde
süre kelimelere hece (ünlü) sayısına göre dağıtılır. Türkçede hece = ünlü sayısı.
Çıktı: out/<id>/timeline.json + out/<id>/voice/NN.wav (tts.mjs ile aynı biçim)
"""
import json, os, re, subprocess, sys, wave
import numpy as np
import pyloudnorm as pyln
from scipy.signal import butter, sosfilt

SR = 44100
HOP = 0.01  # 10 ms çerçeve
LEAD = {"hook": 0.5, "device": 0.75, "outro": 0.45}
TAIL = {"hook": 0.35, "device": 2.1, "outro": 1.6}
VOWELS = set("aeıioöuüAEIİOÖUÜâîû")


def load(path):
    """Her biçimi ffmpeg ile 44.1 kHz mono float'a çevirir."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(float) / 32768


def write(path, x):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def frames_db(x):
    n = int(HOP * SR)
    m = len(x) // n
    rms = np.sqrt(np.mean(x[: m * n].reshape(m, n) ** 2, axis=1) + 1e-12)
    return 20 * np.log10(rms)


def voiced_mask(db):
    floor = np.percentile(db, 10)
    peak = np.percentile(db, 95)
    thr = max(floor + 0.35 * (peak - floor), peak - 35)
    v = db > thr
    # 50 ms'den kısa sesli/sessiz kırıntıları temizle
    for val in (True, False):
        runs = runs_of(v, val)
        for a, b in runs:
            if b - a < 5:
                v[a:b] = not val
    return v


def runs_of(mask, val):
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i] == val:
            j = i
            while j < n and mask[j] == val: j += 1
            out.append((i, j)); i = j
        else:
            i += 1
    return out


def gaps(v):
    """Konuşma içindeki sessizlikler (baş/son hariç), çerçeve cinsinden."""
    s = runs_of(v, True)
    if not s: return [], None
    first, last = s[0][0], s[-1][1]
    g = [(a, b) for a, b in runs_of(v, False) if a > first and b < last]
    return g, (first, last)


def syllables(word, aliases):
    core = re.sub(r"[.,:;!?]+$", "", word)
    spoken = aliases.get(core, core)
    n = sum(ch in VOWELS for ch in spoken)
    n += 2 * sum(ch.isdigit() for ch in spoken)  # rakamlar kabaca 2 hece
    return max(1, n)


def word_times(words, t0, t1, aliases, pauses):
    """words'ü [t0,t1] aralığına dağıt; pauses: ifade sınırlarına konacak (başlangıç, bitiş) sn çiftleri."""
    # ifadeler = noktalama ile biten kelime grupları
    phrases, cur = [], []
    for w in words:
        cur.append(w)
        if re.search(r"[.,:;!?]$", w): phrases.append(cur); cur = []
    if cur: phrases.append(cur)
    # ifade sınırlarını duraklamalarla eşle: beklenen konuma (hece oranı) yakın ve uzun olanı seç, sıra korunur
    k = len(phrases) - 1
    chosen = []
    if k and len(pauses) >= k:
        tot = sum(syllables(w, aliases) for w in words)
        cum, exp = 0, []
        for ph in phrases[:-1]:
            cum += sum(syllables(w, aliases) for w in ph)
            exp.append(t0 + (t1 - t0) * cum / tot)
        P = sorted(pauses); m = len(P)
        cost = lambda i, j: abs((P[j][0] + P[j][1]) / 2 - exp[i]) - 0.8 * (P[j][1] - P[j][0])
        INF = float("inf")
        D = [[INF] * m for _ in range(k)]; B = [[-1] * m for _ in range(k)]
        for j in range(m): D[0][j] = cost(0, j)
        for i in range(1, k):
            best, bj = INF, -1
            for j in range(m):
                if j > 0 and D[i - 1][j - 1] < best: best, bj = D[i - 1][j - 1], j - 1
                if bj >= 0: D[i][j] = best + cost(i, j); B[i][j] = bj
        j = min(range(m), key=lambda j: D[k - 1][j])
        for i in range(k - 1, -1, -1):
            chosen.append(P[j]); j = B[i][j]
        chosen.reverse()
    spans = []
    if chosen:
        a = t0
        for ps, pe in chosen:
            spans.append((a, ps)); a = pe
        spans.append((a, t1))
    else:
        # duraklama bulunamazsa ifadeleri hece oranıyla tek aralığa yay
        tot = sum(syllables(w, aliases) for w in words)
        a = t0
        for ph in phrases:
            d = (t1 - t0) * sum(syllables(w, aliases) for w in ph) / tot
            spans.append((a, a + d)); a += d
    out = []
    for ph, (a, b) in zip(phrases, spans):
        syl = [syllables(w, aliases) for w in ph]
        tot = sum(syl); t = a
        for w, s in zip(ph, syl):
            d = (b - a) * s / tot
            out.append({"w": w, "t0": round(t, 3), "t1": round(t + d * 0.95, 3)})
            t += d
    return out


def split_single(x, n_seg):
    db = frames_db(x)
    v = voiced_mask(db)
    g, _ = gaps(v)
    if len(g) < n_seg - 1:
        sys.exit(f"Kayıtta {n_seg} bölümü ayıracak kadar duraklama bulunamadı. Bölümler arasında ~1 sn susun "
                 f"ya da her bölümü ayrı dosya olarak kaydedin.")
    cuts = sorted(sorted(g, key=lambda p: p[1] - p[0], reverse=True)[: n_seg - 1])
    short = [(b - a) * HOP for a, b in cuts if (b - a) * HOP < 0.45]
    if short:
        print(f"Uyarı: bazı bölüm araları çok kısa ({', '.join(f'{s:.2f}' for s in short)} sn); bölünme yanlış olabilir.")
    bounds, a = [], 0
    for ga, gb in cuts:
        mid = (ga + gb) // 2
        bounds.append((a, mid)); a = mid
    bounds.append((a, len(db)))
    n = int(HOP * SR)
    return [x[a * n: b * n] for a, b in bounds]


def trim(x):
    db = frames_db(x)
    v = voiced_mask(db)
    s = runs_of(v, True)
    if not s: sys.exit("Bir bölümde konuşma bulunamadı.")
    n = int(HOP * SR)
    a = max(0, s[0][0] - 3) * n
    b = min(len(db), s[-1][1] + 6) * n
    y = x[a:b].copy()
    f = min(len(y), int(0.008 * SR))
    y[:f] *= np.linspace(0, 1, f); y[-f:] *= np.linspace(1, 0, f)
    return y


def main(topic_path, rec):
    topic = json.load(open(topic_path))
    segs = topic["segments"]
    aliases = topic.get("aliases", {})
    out_dir = os.path.join("out", topic["id"]); vdir = os.path.join(out_dir, "voice")
    os.makedirs(vdir, exist_ok=True)

    if os.path.isdir(rec):
        files = sorted(f for f in os.listdir(rec) if not f.startswith("."))
        if len(files) != len(segs):
            sys.exit(f"Klasörde {len(files)} dosya var, {len(segs)} bölüm bekleniyor.")
        parts = [load(os.path.join(rec, f)) for f in files]
    else:
        parts = split_single(load(rec), len(segs))

    # temizlik: low-cut + tüm kaydı -16 LUFS'a getir
    sos = butter(2, 80 / (SR / 2), "high", output="sos")
    parts = [trim(sosfilt(sos, p)) for p in parts]
    meter = pyln.Meter(SR)
    allv = np.concatenate(parts)
    gain = 10 ** ((-16 - meter.integrated_loudness(allv)) / 20)
    pk = max(np.abs(p).max() for p in parts) * gain
    if pk > 0.95: gain *= 0.95 / pk
    parts = [p * gain for p in parts]

    cursor, timeline = 0.0, []
    n = int(HOP * SR)
    for i, (seg, x) in enumerate(zip(segs, parts)):
        f = os.path.join(vdir, f"{i:02d}.wav"); write(f, x)
        dur = len(x) / SR
        g, span = gaps(voiced_mask(frames_db(x)))
        pauses = [(a * HOP, b * HOP) for a, b in g if (b - a) * HOP >= 0.12]
        s0, s1 = span[0] * HOP, span[1] * HOP
        start = cursor; vs = start + LEAD[seg["kind"]]; ve = vs + dur; end = ve + TAIL[seg["kind"]]
        words = seg["text"].split()
        wt = word_times(words, s0, s1, aliases, pauses)
        for w in wt: w["t0"] = round(w["t0"] + vs, 3); w["t1"] = round(w["t1"] + vs, 3)
        timeline.append({**seg, "start": start, "voiceStart": vs, "voiceEnd": ve, "end": end, "voiceFile": f, "words": wt})
        print(f"{seg['kind']:6} {seg.get('name', ''):10} {dur:5.2f} sn  {len(pauses)} duraklama")
        cursor = end

    tl = {"id": topic["id"], "series": topic.get("series", ""), "fps": 30, "sr": SR, "preview": False,
          "duration": round(cursor, 3), "segments": timeline}
    json.dump(tl, open(os.path.join(out_dir, "timeline.json"), "w"), ensure_ascii=False, indent=1)
    print(f"Toplam: {cursor:.1f} sn")


if __name__ == "__main__":
    if len(sys.argv) < 3: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])

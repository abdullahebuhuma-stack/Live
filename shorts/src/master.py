"""Hazır stereo miks için hafif mastering: DC/subsonic temizliği, geniş EQ, 4x oversampling true-peak limiter.
Kullanım: python3 src/master.py <giriş> <çıkış.wav> <hedef LUFS> [tavan dBTP]"""
import sys, subprocess, numpy as np, soundfile as sf, pyloudnorm as pyln
from scipy.signal import butter, sosfilt, resample_poly
from scipy.ndimage import maximum_filter1d, uniform_filter1d
SR = 44100

def load(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(float).reshape(-1, 2)

def peq(x, f, g, q):  # RBJ peaking
    A = 10 ** (g / 40); w = 2 * np.pi * f / SR; a = np.sin(w) / (2 * q)
    b = [1 + a * A, -2 * np.cos(w), 1 - a * A]; d = [1 + a / A, -2 * np.cos(w), 1 - a / A]
    sos = np.array([[*np.divide(b, d[0]), 1, d[1] / d[0], d[2] / d[0]]])
    return sosfilt(sos, x, axis=0)

def tp_limit(x, ceil_db, look=0.0015, rel=0.12):
    c = 10 ** (ceil_db / 20)
    os_ = resample_poly(x, 4, 1, axis=0)
    pk = np.abs(os_).max(1).reshape(-1, 4).max(1)[: len(x)]
    pk = np.pad(pk, (0, len(x) - len(pk)))
    n = int(look * SR) * 2 + 1
    g = np.minimum(1, c / np.maximum(maximum_filter1d(pk, n), 1e-9))
    g = -maximum_filter1d(-g, n); g = uniform_filter1d(g, n)
    a = np.exp(-1 / (rel * SR)); out = g.copy()
    for i in range(1, len(out)):
        if out[i] > out[i - 1]: out[i] = out[i - 1] + (1 - a) * (out[i] - out[i - 1])
    return x * out[:, None], 20 * np.log10(out.min())

def true_peak(x):
    return 20 * np.log10(np.abs(resample_poly(x, 4, 1, axis=0)).max())

inp, outp, target = sys.argv[1], sys.argv[2], float(sys.argv[3])
ceil = float(sys.argv[4]) if len(sys.argv) > 4 else -1.0
x = load(inp)
x = x - x.mean(0)
x = sosfilt(butter(2, 18 / (SR / 2), 'high', output='sos'), x, axis=0)   # subsonik
x = peq(x, 280, -1.5, 0.8)    # alt-orta dolgunluğu
x = peq(x, 4000, 1.5, 0.7)    # varlık/anlaşılırlık
m = pyln.Meter(SR)
for _ in range(4):  # limiter sonrası loudness'i hedefe yakınsat
    y = x * 10 ** ((target - m.integrated_loudness(x)) / 20)
    y, gr = tp_limit(y, ceil - 0.3)
    diff = target - m.integrated_loudness(y)
    if abs(diff) < 0.05: break
    x = x * 10 ** (diff / 20)
y = y * 10 ** ((target - m.integrated_loudness(y)) / 20)
sf.write(outp, y, SR, subtype='PCM_24')
print(f"{outp}: {m.integrated_loudness(y):.1f} LUFS, true peak {true_peak(y):.2f} dBTP, en fazla limiter kazanç azaltımı {gr:.1f} dB")

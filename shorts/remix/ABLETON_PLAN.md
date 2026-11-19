# Bitikals: Afro-Türk House Remix v3 için Ableton Live 12 prodüksiyon planı

Bu plan, kullanıcının bilgisayarında Ableton Live 12'yi bilgisayar kontrolüyle (computer use) kullanacak Claude
oturumu için yazıldı. Kaynak dosyalar `hayko_bitikals_remix_ableton_paketi.zip` içinde: `stems/`, `midi/`, `BENIOKU.txt`.

## Sabitler

- Tempo **122 BPM**, 4/4, ton **Mi minör**, toplam **112 ölçü** (3:40)
- Orijinal kayıt **-18 cent** pes akortlu. Synth'lerde Detune/Fine -18 cent kullanın; Simpler/Sampler'da Detune -18 ct.
- Vokal: `stems/vocal_dry_122bpm.flac`. Zaten 122 BPM'e uyarlandı ve grid'e hizalandı. **Warp KAPALI.**
  Cümleleri yalnızca **tam ölçü** kaydırarak taşıyın (grid 1 Bar, Ctrl ile değil). Cümle içi kesirli başlangıçlar
  (pickup'lar) bilerek öyle; 16'lık veya 8'lik kaydırma vokali yeniden kaydırır.
- Kendi ürettiğim sentez stem'leri (kick, bass, chords...) **kullanılmayacak**. Yalnızca referans. Sesler Live kütüphanesinden seçilecek.

## Vokal cümleleri (vocal_dry_122bpm içindeki yerleri, ölçü.vuruş.16'lık)

| Kod | Başlangıç | Bitiş | Süre |
|---|---|---|---|
| V01 | 17.1.1 | 20.4.4 | 7.8 sn |
| V02 | 21.1.3 | 24.4.1 | 7.2 sn |
| V03 | 25.2.4 | 28.3.1 | 6.0 sn |
| V04 | 29.1.4 | 35.4.3 | 13.2 sn |
| V05 | 37.1.3 | 43.4.1 | 13.0 sn |
| V06 | 44.1.1 | 45.4.4 | 3.8 sn |
| V07 | 46.3.3 | 47.4.1 | 2.2 sn (kısa, hook/chop adayı) |
| V08 | 47.4.4 | 49.4.3 | 3.8 sn |
| V09 | 50.3.3 | 52.3.1 | 3.7 sn |
| V11 | 63.4.1 | 71.3.4 | 15.7 sn |
| V12 | 79.2.4 | 86.1.4 | 13.3 sn |
| V13 | 87.2.3 | 96.1.4 | 17.3 sn |
| V14 | 96.4.4 | 100.2.3 | 6.7 sn |
| V15 | 100.3.3 | 103.3.4 | 6.0 sn |
| V16 | 104.4.4 | 106.4.1 | 3.6 sn |

İş akışı: vokal dosyasını bir audio kanalına 1.1.1'den koyun. Her cümleyi Split (Ctrl+E) ile ayrı clip yapın. Sonra aşağıdaki yapıya göre **tam ölçü** kaydırarak yerleştirin; kullanılmayanları silin.

## Yapı (112 ölçü)

| Ölçü | Bölüm | Enerji | Vokal | Ne olur |
|---|---|---|---|---|
| 1–16 | Intro | düşük → orta | 13–16: V07 chop | 1–4 shaker + rim; 5 kick; 9 bas (HP filtreli); 13 akorlar LP filtreyle açılıyor; V07'den 8'lik chop |
| 17–32 | Verse 1 | orta | V01 @17, V02 @21, V03 @25, V08 @29 | kick, perc, bas, akor stab. Marimba ve clap yok |
| 33–40 | Build 1 | yükselen | V06 @37 | 33–36 kick devam, 37–40 kick ve sub çekilir, snare roll + riser; master HP ve LP build |
| 41–56 | Drop 1 | tam | V04 @41, V05 @49 | her şey + clap + marimba + open hat; 40.4'te yarım ölçü nefes (riser reverb kuyruğu) |
| 57–72 | Break | düşük | V11 @61 | kick ve bas yok, pad + akorlar LP'li, shaker; vokal büyük reverb'de; 72.4 throw |
| 73–80 | Build 2 | yükselen | V09 @77 | Build 1 ile aynı ama daha kısa roll (77–80); son akor B (V) tutulur |
| 81–96 | Drop 2 | tam + ek | V12 @81, V14 @89, V15 @93 | Drop 1 + ek perc katmanı (bongo), 89'dan sonra vokal chop çağrı-cevap |
| 97–112 | Outro | azalan | V16 @97 | 97–100 tam, 101 marimba ve clap çıkar, 105 akor ve bas çıkar, 109–112 perc + kick, son ölçüde reverb kuyruğu |

Akorlar: `midi/chords.mid` orijinal ölçü haritasından çıkarıldı ve vokalle uyumlu. Yeni yapıda vokal cümleleri taşındığı için
akorları da vokalle **aynı miktarda** taşıyın. Ya da bütün bölümlerde 4 ölçülük döngü kullanın: **Em – Em – C – B**
(break'te **Am – Em – C – B**). Build'lerin son ölçüsünde **B** tutulur, drop'ta **Em**'e çözülür.

## Kanallar, kütüphane sesleri ve FX

Live 12 tarayıcısında arama terimleriyle seçin (Core Library + Packs). Önerilen ilk seçim, beğenilmezse alternatifi deneyin.
Önce kulakla değil **seviye eşlenmiş A/B** ile karar verin.

| # | Kanal | Kütüphane (arama) | Kaynak MIDI | Cihaz zinciri |
|---|---|---|---|---|
| 1 | Kick | Drum Rack içinde "kick" → derin, kısa kuyruklu (909/organik) | `midi/kick.mid` | EQ Eight (HP 30 Hz), Saturator (Soft Sine, drive 3 dB) |
| 2 | Perc | Drum Rack: "conga", "bongo", "rim", "shaker" | `midi/perc.mid` (37 rim, 62 slap, 63 conga yüksek, 64 conga alçak, 46 open hat) | Drum Buss (Transients +, Crunch az), Auto Pan (az) |
| 3 | Shaker | "shaker" one-shot veya loop | 16'lık, 2. ve 4. 16'lık vurgulu | EQ Eight HP 400 Hz |
| 4 | Clap | "clap" (kuru, kısa) | `midi/clap.mid` | Send A biraz |
| 5 | Bass | Drift veya Operator "sub" preset | `midi/bass.mid` | Saturator (az), **Compressor sidechain ← Kick** (4:1, attack 1 ms, release 120 ms), Utility (mono < 120 Hz) |
| 6 | Chords | Electric (Rhodes) veya Wavetable "keys/stab" | `midi/chords.mid` | Auto Filter (LP, otomasyonlu), Chorus-Ensemble, sidechain ← Kick (2:1), Send B |
| 7 | Pad | Wavetable/Drift "pad" (yumuşak, geniş) | akorlar uzun nota | Auto Filter LP 2 kHz, sidechain ← Kick, Send A |
| 8 | Marimba | Collision veya Operator "mallet/marimba" | `midi/marimba.mid` | Echo send B (ping-pong), EQ HP 300 Hz |
| 9 | Vocal | audio: `vocal_dry_122bpm` | — | EQ Eight (HP 120, -2 dB @350 Hz geniş, +2 dB @4 kHz), Compressor (3:1, 4–6 dB GR), Saturator (Soft, az) |
| 10 | Vocal Chop | V07'nin kopyası, Simpler (Slice, 8'lik) | elle 8'lik desen | Auto Filter BP, Send B |
| 11 | FX | "riser", "impact", "reverse cymbal", "downlifter" | — | Send A |
| A | Return: Reverb | Hybrid Reverb (2.5 sn, pre-delay 20 ms, LP 6 kHz) | | |
| B | Return: Delay | Echo (sync, noktalı 1/8, ping-pong, feedback %35, filtre 400 Hz–5 kHz) | | |
| M | Master | EQ Eight (HP 25 Hz) → Glue Compressor (2:1, attack 10 ms, release A, GR 1–2 dB) → Limiter (True Peak, ceiling -1.0 dB) | | |

Başlangıç seviyeleri (fader, master'da limiter öncesi kabaca): kick -6, bas -9, vokal -8, perc -14, akor -16, pad -18, marimba -20, shaker -22 dBFS RMS.

## Otomasyon (Arrangement'ta A tuşu; değerler başlangıç noktası, kulakla doğrulayın)

| Ölçü | Kanal / parametre | Hareket |
|---|---|---|
| 1–16 | Chords Auto Filter LP Frequency | 13.1: 400 Hz → 16.4: 8 kHz (üstel) |
| 9–16 | Bass EQ Eight HP | 9.1: 200 Hz → 16.4: 30 Hz |
| 13–16 | Vocal Chop Auto Filter BP | 600 Hz → 3 kHz |
| 16.4 | Vocal send B | tek vuruş throw: -inf → -6 dB → -inf |
| her cümle sonu (V01–V05, V12–V15) | Vocal send B | son kelimede throw (yalnız son hece, 1 vuruş) |
| 33–40 | Master'a Auto Filter (HP) | 33.1: 20 Hz → 40.3: 300 Hz, 41.1'de 20 Hz (anında) |
| 37–40 | Kick ve Bass volume | 37.1'de -inf (sub boşluğu), 41.1'de geri |
| 37–40 | Snare roll (Drum Rack snare) | 37: dörtlük, 38: 8'lik, 39: 16'lık, 40: 32'lik; velocity 60→127 |
| 37–40 | Return A (reverb) Dry/Wet ve FX riser | reverb send 0 → -8 dB; riser volume -18 → -6 dB |
| 40.3–40.4 | Master volume | -1.5 dB → 41.1'de 0 dB (drop kontrastı) |
| 41.1 | FX impact + crash | tek vuruş |
| 41–56 | Vocal fader ride | cümle cümle ±1.5 dB (kompresörle değil) |
| 57–72 | Chords ve Pad Auto Filter LP | 57.1'de 1.2 kHz'e insin, 69–72'de 1.2 kHz → 5 kHz açılsın |
| 57–72 | Vocal send A | -12 dB → -6 dB (break'te geniş vokal) |
| 72.4 | Vocal send B | büyük throw (feedback geçici %55) |
| 73–80 | Build 1 ile aynı, roll 77'den başlar | son ölçüde akor B tutulur |
| 81.1 | Impact + downbeat | drop 2 |
| 89–96 | Vocal Chop | V07 dilimleri çağrı-cevap: vokal cümle aralarında 1 ölçü |
| 97–112 | Outro | 101: marimba ve clap volume -inf; 105: chords ve bass -inf; 109–112 master LP 20 kHz → 2 kHz |
| 112.4 | Return A | reverb kuyruğu kendiliğinden sönsün (cut yok) |

Kontrol listesi (otomasyon-incelikleri becerisi):
1. Her bölüm geçişinde neyin öne çıktığı tek cümleyle söylenebiliyor mu?
2. Build'lerin son 1–2 ölçüsünde 100 Hz altı azalıyor ve drop'ta geri geliyor mu?
3. Drop öncesi yarım ölçülük nefes kuyrukla dolu mu?
4. Throw'lar kuru vokali boğuyor mu?
5. Build, drop'tan daha yüksek değil mi? (kısa vadeli LUFS ile ölçün)

## Teslim

- Export: Master'ı 24-bit WAV, 44.1 kHz, Normalize kapalı, dither kapalı (32-bit ara dosya isteniyorsa float).
- Hedef: yaklaşık -10…-11 LUFS integrated, true peak ≤ -1.0 dBTP. Export sonrası dosyayı yeniden açıp ölçün.
- Live Set'i "Bitikals Afro-Türk Remix v3.als" olarak, **Collect All and Save** ile kaydedin (örnekler projeye kopyalanır).

## Bilinen sınırlar

- Vokal Demucs ile ayrıldı: sessiz yerlerde orijinal davul/gitar kalıntısı olabilir. Gerekirse Gate (threshold -40 dB, floor -20 dB).
- C bölümünden gelen cümleler (V12–V16) orijinalde serbest tempodaydı. Kayma duyulursa yalnızca o clip'i 16'lık kaydırın.
- Bu plandaki seçimler ölçüme ve kaynaklı kurallara dayanıyor. Sonuç dinlenmeden onaylanmış sayılmaz.

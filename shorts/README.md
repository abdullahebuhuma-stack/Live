# Shorts üretim hattı

TikTok, Reels ve Shorts için dikey (1080x1920, 30 fps) Türkçe bilgi videoları üretir. Her video şunları içerir:
3D motion graphics, karaoke altyazı, Google TTS seslendirme, koddan üretilmiş ses tasarımı ve -14 LUFS master.

## Tek komut

```bash
cd shorts
npm install                     # yalnızca fontlar
pip install numpy scipy pyloudnorm
node src/build.mjs topics/muzigi-degistiren-5-cihaz.json --voice kayit.wav  # kendi sesinizle
node src/build.mjs topics/muzigi-degistiren-5-cihaz.json                    # Google TTS ile
node src/build.mjs topics/muzigi-degistiren-5-cihaz.json --preview          # seslendirmesiz önizleme
```

Çıktı: `out/<id>/<id>.mp4`

## Kendi sesinizle kayıt

- Konu dosyasındaki `text` alanlarını sırayla, **tek dosyada** okuyun. Bölümler arasında **1–2 saniye susun**;
  sistem kaydı bu duraklamalardan bölümlere ayırır. İsterseniz her bölümü ayrı dosya kaydedip bir klasöre
  koyabilirsiniz (`01.wav`, `02.wav`...).
- Kaydı kuru gönderin: reverb, müzik ve kompresör olmasın. Low-cut, seviye (-16 LUFS), ducking ve master işlemlerini sistem yapıyor.
- WAV, MP3, M4A ya da AIFF olabilir. Telefon kaydı da olur.
- Kelime zamanları (`src/align.py`), kayıttaki duraklamaların noktalama işaretleriyle eşlenmesinden ve ifade içinde
  hece sayısına göre dağıtılmasından çıkar. Ekranda yazan metin `text` alanındaki metindir, okurken birebir aynısını söyleyin.

## Google TTS anahtarı (isteğe bağlı)

İki yoldan biriyle eklenir:
- Ortamın **Network secrets** bölümü: host `texttospeech.googleapis.com`, header `X-Goog-Api-Key`.
- Ya da `GOOGLE_TTS_API_KEY` ortam değişkeni.

Ses, `topics/*.json` içindeki `voice` alanından seçilir (varsayılan `tr-TR-Wavenet-E`). Yanlış okunan kelimeleri
`aliases` alanına yazarak düzeltin (ör. `"TR-808": "ti ar sekiz yüz sekiz"`). Aynı metin yeniden çağrılmaz, `.cache/tts` içinde saklanır.

## Hat

| Adım | Dosya | Ne yapar |
|---|---|---|
| ① | `src/align.py` | Kendi kaydınızı bölümlere ayırır, temizler ve kelime zamanlarını çıkarır |
| ① (alternatif) | `src/tts.mjs` | SSML ile kelime başına `<mark>` koyar, Google TTS'ten kelime zamanlarını alır ve zaman çizelgesini kurar |
| ② | `src/audio.py` | Cihaz seslerini sentezler, geçiş efektlerini ekler, vokali sidechain ile ducklar ve -14 LUFS / -1 dBFS master yapar |
| ③ | `src/render.mjs` + `src/template.html` | Canvas'ta 3D cihazları ve altyazıyı kare kare çizer, ffmpeg ile H.264 olarak kodlar |

### Ses tasarımı (sample yok, hepsi sentez)
- **Minimoog**: 3 detune testere dişi + sub, TPT SVF lowpass, filtre zarfı, vibratolu lead
- **TR-808**: pitch zarflı uzun kick, 3 darbeli clap, 6 kare dalgalı metalik hat, cowbell
- **TB-303**: rezonanslı filtre, aksan, slide ve segment boyunca açılan cutoff
- **DX7**: 2 operatörlü FM elektrik piyano (gövde + 14:1 oranlı tine)
- **MPC60**: %60 swing, 12-bit'e indirgenmiş akor chopları, plak cızırtısı

Görseller sesle senkron çalışır: 808 step LED'leri, MPC pad'leri, klavyede basılan notalar ve 303 cutoff düğmesi
`events.json`'dan, spektrum halkası ve osiloskop ise `env.json`'dan beslenir.

## Yeni video

`topics/` altına yeni bir JSON koyun. Segment türleri `hook`, `device` ve `outro`'dur. `device` alanı şunlardan biri olabilir:
`moog`, `tr808`, `tb303`, `dx7`, `mpc`. Yeni cihaz eklemek için `audio.py` içindeki `DEVICES` sözlüğüne ve
`template.html` içindeki `MODELS` nesnesine birer fonksiyon ekleyin.

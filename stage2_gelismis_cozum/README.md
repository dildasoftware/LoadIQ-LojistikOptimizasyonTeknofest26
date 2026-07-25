<div align="center">

# 🚛 LoadIQ — Gelişmiş Çözüm

### Yapay Zeka Destekli Lojistik Anahat Optimizasyonu

**TEKNOFEST 2026 · Hepsiburada Lojistik Optimizasyonu Yarışması · Takım NASİP**

[![Aşama](https://img.shields.io/badge/A%C5%9Fama-Geli%C5%9Fmi%C5%9F%20%C3%87%C3%B6z%C3%BCm-1c6f9a)](.)
[![Durum](https://img.shields.io/badge/Durum-Tamamland%C4%B1%20%C2%B7%20Feasible-2fa86a)](.)
[![Maliyet](https://img.shields.io/badge/Feasible%20Maliyet-22.106.411%20TL-127a72)](.)
[![Testler](https://img.shields.io/badge/Testler-32%2F32%20PASS-2fa86a)](./tests)
[![Checker](https://img.shields.io/badge/Checker-PASS%20%C2%B7%200%20ihlal-2fa86a)](./src/checker.py)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)

</div>

---

Transfer merkezleri arasındaki **desi** talebini saat dilimi bazında (09:00 / 17:00) tahmin eden ve bu talebi; elleçleme kapasitesi, tır kapasitesi, SLA cezası ve konsolidasyon gibi tüm operasyonel kısıtlara uyarak **minimum maliyetle** taşıyan uçtan uca bir planlama sistemidir. Sistem, planı üreten motordan **bağımsız** yazılmış bir doğrulayıcı (`checker.py`) ile kendi çıktısını sıfırdan denetler.

## 📋 İçindekiler

- [Nihai Sonuçlar](#-nihai-sonuçlar)
- [Problem Tanımı](#-problem-tanımı)
- [Sistem Mimarisi](#-sistem-mimarisi)
- [Metodoloji](#-metodoloji)
- [Proje Yapısı](#-proje-yapısı)
- [Kurulum](#-kurulum)
- [Çalıştırma](#-çalıştırma)
- [Test ve Doğrulama](#-test-ve-doğrulama)
- [İş Kuralları Uyumu](#-iş-kuralları-uyumu)
- [Teknoloji Yığını](#-teknoloji-yığını)
- [Dokümantasyon](#-dokümantasyon)
- [Takım](#-takım)

---

## 🏆 Nihai Sonuçlar

Tüm sayılar, `src/pipeline.py` çıktısının `src/checker.py` tarafından bağımsız doğrulanmasıyla üretilmiştir.

| Metrik | Değer |
|---|---|
| **Toplam plan maliyeti (feasible)** | **22.106.411 TL** |
| Araç maliyeti | 20.939.526 TL |
| SLA cezası | 1.166.885 TL (%5,3) |
| Uygunluk (feasibility) ihlali | **0** |
| Doğrulama | **checker PASS · 32/32 test** |
| Toplam araç seferi | 1.697 (98 kiralık · 1.599 spot) |
| Taşınan toplam desi | 6.613.772 |
| Talep tahmini doğruluğu | WAPE ≈ **%24,4** (P×E yöntemi) |

**Maliyet yolculuğu** (sadece-iyileştiren, checker-korumalı konsolidasyon):

```
Başlangıç planı        29,84M TL
  └─ Saat konsolidasyonu   → 24,08M TL   (371 birleştirme)
        └─ Milk-run + Feasibility → 22,11M TL   (215 birleştirme)

Toplam iyileşme: −7,73M TL  (−%25,9), tam feasible
```

---

## 🎯 Problem Tanımı

Türkiye genelinde **18 transfer merkezi** arasında, **289 aktif güzergahta** günde iki kez (09:00 ve 17:00) oluşan kargo talepleri (*desi* birimiyle) yönetilmelidir. Sistem iki resmi çıktı üretir:

1. **Talep Tahmini** (`outputs/Talep-tahmini.xlsx`) — her güzergah × gün × saat dilimi için beklenen desi miktarının istatistiksel tahmini.
2. **Taşıma Planı** (`outputs/Tasima-plani.xlsx`) — bu talebi zorunlu kiralık filo ve esnek spot araçlarla, tüm operasyonel kısıtlara uyarak minimum maliyetle karşılayan detaylı araç atama planı.

Gelişmiş çözüm aşaması, temel aşamadan farklı olarak **dakika çözünürlüğünde** çalışır; elleçleme süreleri, gece yarısı kapasite sıfırlanması, konsolidasyon senaryoları ve SLA ceza mekanizması gibi gerçek dünya kısıtlarını içerir.

---

## 🏗 Sistem Mimarisi

```
                 data/raw/*.xlsx  (8 resmi veri seti)
                        │
                        ▼
                  data_loader.py          ← okuma + doğrulama katmanı
                        │
          ┌─────────────┴──────────────┐
          ▼                            ▼
     forecast.py                  optimize.py
   (P×E talep tahmini)      (2 fazlı greedy + konsolidasyon)
          │                            │
          ▼                            ▼
 outputs/Talep-tahmini.xlsx   outputs/Tasima-plani.xlsx
                                       │
                                       ▼
                                  checker.py               ← BAĞIMSIZ doğrulayıcı
                              (12 kontrol, sıfırdan yeniden hesap)
                                       │
                                       ▼
                            PASS / FAIL + Maliyet Raporu
```

> **Tasarım kararı — neden ayrı bir `checker.py`?**
> Planı üreten kod (`optimize.py`) ile onu doğrulayan kod (`checker.py`) **bilinçli olarak** ayrıdır. Böylece üreticinin varsayımları ve kör noktaları doğrulayıcıya taşınmaz. `checker.py`, planı sıfırdan yeniden hesaplayarak kapasite, SLA cezası, maliyet doğruluğu, çıkış-hazırlık uygunluğu ve format uyumunu bağımsız olarak denetler. Bu, bir auto-grader mantığıyla çalışır.

---

## 🔬 Metodoloji

### 1. Talep Tahmini — P×E Yöntemi

Talep, iki bileşenin çarpımı olarak modellenir:

```
E[desi] = P(sevkiyat olur) × E[desi | sevkiyat olur]
```

Bu "P×E" modeli, cebirsel olarak **gün × saat dilimi ortalamasına** eşittir; ancak sıfır-şişkin (zero-inflated) talep yapısını doğru yakalar. Sızıntısız (leakage-free) geriye dönük test (backtest) ile 3 bağımsız hafta üzerinde **WAPE** metriğiyle doğrulanmıştır. `n` (bakılan geçmiş hafta sayısı) hiperparametresi süpürülmüş, maliyet–doğruluk dengesi gereği **n = 8** seçilmiştir.

**Neden ML değil?** Bir LightGBM modeli (`forecast_ml.py`) karşılaştırma için eğitildi ve kaybetti: **WAPE %32,5 (ML) — %24,4 (P×E)**. Karar, kanıta dayalı olarak istatistiksel P×E modeli lehine verildi; ML modeli metodolojik şeffaflık için repoda tutulmaktadır.

### 2. Optimizasyon — İki Fazlı Greedy + Konsolidasyon

1. **Faz 1 — Zorunlu kiralık ön-ataması:** Sözleşmeli kiralık filo, yalnızca 09:00 tamamlanmalı talebe atanır (17:00 yükü spot'a bırakılır — feasibility gereği).
2. **Faz 2 — Fayda esaslı spot seçimi:** Kalan talep, elleçleme ve tır kapasitesi korunarak maliyet–fayda esasıyla spot araçlara dağıtılır.
3. **Konsolidasyon (sadece-iyileştiren, checker-korumalı son-işlem):**
   - `konsolide_saat` — aynı rotadaki bitişik saat dilimlerini birleştirir.
   - `konsolide_milkrun` — aynı çıkıştan farklı varışlara giden düşük-dolu araçları tek bir A→B→C rotasında birleştirir.
   - Her adım yalnızca maliyeti **düşürürse** ve checker'dan geçerse kabul edilir; çözüm asla bozulmaz.

### 3. Feasibility Güvencesi

Kritik bir kısıt uygulanır: **bir araç, taşıdığı yükün talep hazırlık zamanından (09:00 / 17:00) önce yola çıkamaz.** Bu kural `checker.py` içinde bağımsız denetlenir (`CIKIS_HAZIRLIK`). Geliştirme sırasında, talebin ~%11,6'sını (767 bin desi) hazır olmadan sevk eden bir hata bu kontrol sayesinde yakalanıp giderilmiş; plan tam uygulanabilir (feasible) hâle getirilmiştir.

---

## 📁 Proje Yapısı

```
LoadIQ_KaynakKod/
├── NASIL_CALISTIRILIR.txt     # Jüri için hızlı çalıştırma kılavuzu
├── README.md                  # Bu dosya
├── requirements.txt           # Python bağımlılıkları
├── config/
│   └── rules.py               # Tüm sabit iş kuralları (tek kaynak)
├── src/
│   ├── time_utils.py          # Dakika bazlı süre/yuvarlama çekirdeği
│   ├── data_loader.py         # Veri okuma + doğrulama katmanı
│   ├── forecast.py            # Talep tahmin modeli (P×E)
│   ├── forecast_ml.py         # LightGBM karşılaştırma modeli
│   ├── optimize.py            # Taşıma planı optimizasyon motoru
│   ├── checker.py             # Bağımsız doğrulayıcı (auto-grader)
│   ├── pipeline.py            # Uçtan uca çalıştırıcı
│   ├── run_backtest.py        # Tahmin backtest (WAPE) betiği
│   ├── analyze_solution.py    # Çözüm analiz/raporlama yardımcısı
│   └── gen_forecast_n8.py     # n=8 tahmin üretim betiği
├── tests/                     # pytest test paketi (32 test)
├── data/raw/                  # 8 resmi girdi veri seti (değiştirilmez)
├── outputs/                   # Üretilen teslim dosyaları
├── docs/                      # İş kuralları spec + veri denetim raporu
└── dashboard/                 # Tek dosyalık görsel panel (SPA)
```

> **Not:** Teknik rapor, SRS ve sunum ayrı teslim kalemleridir; bu kaynak kod paketine dâhil edilmez (yalnızca çalışan kod, veri, testler ve dokümantasyon burada bulunur).

---

## ⚙️ Kurulum

Gereksinim: **Python 3.10+**

```bash
pip install -r requirements.txt
```

> **Not:** Windows'ta `python` yerine `py` komutu gerekebilir. Aşağıdaki komutlarda `python` yerine `py` kullanabilirsiniz.

---

## ▶️ Çalıştırma

**Uçtan uca pipeline** (talep tahmini + taşıma planı + bağımsız doğrulama):

```bash
python src/pipeline.py
```

Bu komut: ham veriyi yükler → talep tahminini okur → taşıma planını üretir (greedy + konsolidasyon) → `outputs/Tasima-plani.xlsx` dosyasını yazar → `checker.py` ile sıfırdan doğrular → **PASS/FAIL + maliyet özetini** ekrana basar. Beklenen sonuç: **PASS, 22.106.411 TL**.

**Yalnızca talep tahmini:**

```bash
python src/forecast.py
```

**Görsel panel (dashboard):** `dashboard/LoadIQ_Dashboard.html` dosyasına **çift tıklayın** — tek dosyadır, tüm veri gömülüdür, kendi kendine yeterlidir. Sunucu veya kurulum gerektirmez.

---

## ✅ Test ve Doğrulama

```bash
python -m pytest tests/ -v
```

| Test dosyası | Test sayısı | Kapsam |
|---|---|---|
| `test_time_utils.py` | 7 | Dakika yuvarlama, gece yarısı bölünmesi |
| `test_data_loader.py` | 6 | Veri okuma + tutarlılık doğrulaması |
| `test_checker.py` | 19 | Kapasite, SLA, maliyet, feasibility, format |
| **Toplam** | **32** | **Tamamı PASS** |

Bağımsız `checker.py`, üretilen planı 12 farklı kontrolle (kapasite ihlali, boş araç, kiralık filo, milk-run tutarlılığı, çıkış-hazırlık uygunluğu, SLA cezası, maliyet doğruluğu, format) sıfırdan denetler.

---

## 📜 İş Kuralları Uyumu

Yarışma şartnamesi, resmi Q&A ve duyurulardan derlenen **20 iş kuralının tamamına (20/20)** uyum sağlanmıştır. Tüm kurallar `config/rules.py` içinde tek kaynak olarak tanımlıdır ve `docs/is_kurallari_spec.md` altında belgelenmiştir. Öne çıkanlar: dakika bazlı süre hesabı, elleçleme kapasitesi ve gece yarısı sıfırlanması, tır kapasite limitleri, çıkış-hazırlık zamanı kısıtı, SLA cezası = geciken desi × ⌈gecikme saat⌉ × 0,4 TL.

---

## 🛠 Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| Dil | Python 3.10+ |
| Veri işleme | pandas, openpyxl, numpy |
| Optimizasyon | İki fazlı greedy + konsolidasyon sezgiseli |
| Tahmin (karşılaştırma) | LightGBM |
| Test | pytest |
| Görselleştirme | Chart.js + vanilla JS (tek dosya SPA) |

---

## 📚 Dokümantasyon

| Doküman | İçerik |
|---|---|
| `LoadIQ_Teknik_Rapor.pdf` | Yöntem, sonuçlar, grafikler, mühendislik kararları *(ayrı teslim kalemi)* |
| `LoadIQ_SRS.pdf` | Yazılım Gereksinim Spesifikasyonu *(ayrı teslim kalemi)* |
| [`docs/is_kurallari_spec.md`](./docs/is_kurallari_spec.md) | Tüm iş kurallarının tek kaynağı |
| [`docs/veri_denetim_raporu.md`](./docs/veri_denetim_raporu.md) | Veri setlerindeki tutarsızlıklar ve çözümleri |
| [`docs/sistem_tasarimi_ve_uygulama_plani.md`](./docs/sistem_tasarimi_ve_uygulama_plani.md) | Mimari tasarım ve uygulama yol haritası |

---

## 👥 Takım

**Takım NASİP** — TEKNOFEST 2026 · Lojistik & Ulaştırma Kategorisi

| Üye | Rol |
|---|---|
| **Dilara Bilişik** | Takım Kaptanı |
| **Fatma Elarid** | Takım Üyesi |
| **Meryem Tekeli** | Takım Üyesi |

📧 İletişim: bilbildilara77@gmail.com

<div align="center">

# 🚛 LoadIQ

### Yapay Zeka Destekli Lojistik Anahat Optimizasyonu

**TEKNOFEST 2026 · Hepsiburada Lojistik Optimizasyonu Yarışması**

[![Aşama](https://img.shields.io/badge/A%C5%9Fama-Geli%C5%9Fmi%C5%9F%20%C3%87%C3%B6z%C3%BCm-blue)](./stage2_gelismis_cozum)
[![Durum](https://img.shields.io/badge/Durum-Tamamland%C4%B1%20%C2%B7%20Feasible-success)](./stage2_gelismis_cozum)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Testler](https://img.shields.io/badge/Testler-32%2F32%20PASS-success)](./stage2_gelismis_cozum/tests)
[![Takım](https://img.shields.io/badge/Tak%C4%B1m-NAS%C4%B0P-lightgrey)](#-tak%C4%B1m)

</div>

---

## 📋 İçindekiler

- [Proje Hakkında](#-proje-hakkında)
- [Problem Tanımı](#-problem-tanımı)
- [Repo Yapısı](#-repo-yapısı)
- [Sistem Mimarisi](#-sistem-mimarisi-i̇kinci-aşama)
- [Hızlı Başlangıç](#-hızlı-başlangıç)
- [Proje Durumu](#-proje-durumu)
- [Teknoloji Yığını](#-teknoloji-yığını)
- [Dokümantasyon](#-dokümantasyon)
- [Takım](#-takım)

---

## 📖 Proje Hakkında

**LoadIQ**, TEKNOFEST 2026 kapsamında Hepsiburada tarafından düzenlenen
*Yapay Zeka Destekli Lojistik Anahat Optimizasyonu* yarışması için Takım
**NASİP** tarafından geliştirilen bir talep tahmini ve araç/rota
optimizasyon sistemidir.

Yarışma iki aşamalı ilerlemektedir:

| Aşama | Durum | Konum |
|---|---|---|
| **Birinci Aşama** — Temel İşlevli Çözüm | ✅ Tamamlandı (yarı final) | [`stage1_temel_cozum/`](./stage1_temel_cozum) |
| **İkinci Aşama** — Gelişmiş Çözüm | ✅ Tamamlandı · feasible plan (22.106.411 TL, checker PASS) | [`stage2_gelismis_cozum/`](./stage2_gelismis_cozum) |

Bu doküman, repoyu ilk kez inceleyen biri (jüri, mentor, yeni takım
üyesi) için genel bir harita niteliğindedir. Teknik detaylar için
[Dokümantasyon](#-dokümantasyon) bölümündeki bağlantılara bakınız.

---

## 🎯 Problem Tanımı

Türkiye genelinde **18 transfer merkezi** (depo) arasında, **289 aktif
güzergahta** günde iki kez (09:00 ve 17:00) oluşan kargo taleplerini
(*desi* birimiyle) yönetmek gerekmektedir. Sistem iki temel çıktı üretir:

1. **Talep Tahmini** — Önümüzdeki bir haftalık pencere için, her
   güzergah × gün × saat dilimi bazında beklenen desi miktarının
   istatistiksel tahmini.
2. **Taşıma Planı** — Bu talebi, zorunlu kiralık filo ve esnek spot
   araçlarla; elleçleme kapasitesi, tır kapasitesi ve SLA (teslimat
   süresi) cezası gibi gerçek operasyonel kısıtlara uyarak **minimum
   maliyetle** karşılayan detaylı bir araç atama planı.

İkinci aşamada problem, birinci aşamadan farklı olarak **dakika
çözünürlüğünde** çalışır; elleçleme süreleri, gece yarısı kapasite
sıfırlanması, konsolidasyon senaryoları ve SLA ceza mekanizması gibi
gerçek dünya operasyonuna çok daha yakın kısıtlar içerir.

---

## 🗂 Repo Yapısı

```
LoadIQ-LojistikOptimizasyonTeknofest26/
├── stage1_temel_cozum/          # Birinci Aşama (arşiv, tamamlandı)
│   ├── src/                     # Gün bazlı tahmin + optimizasyon kodu
│   ├── data/                    # Birinci aşama veri setleri
│   ├── tests/
│   └── README.md
│
├── stage2_gelismis_cozum/       # İkinci Aşama (AKTİF geliştirme)
│   ├── config/rules.py          # Tüm sabit iş kuralları (tek kaynak)
│   ├── data/raw/                # 8 resmi veri seti (talep, mesafe, kapasiteler...)
│   ├── src/
│   │   ├── time_utils.py        # Dakika bazlı süre/yuvarlama çekirdeği
│   │   ├── data_loader.py       # Veri okuma + doğrulama katmanı
│   │   ├── forecast.py          # Talep tahmin modeli (P×E yöntemi)
│   │   ├── optimize.py          # Taşıma planı optimizasyon motoru
│   │   └── checker.py           # Bağımsız doğrulayıcı (auto-grader)
│   ├── tests/                   # pytest test paketi
│   ├── outputs/                 # Üretilen teslim dosyaları
│   ├── docs/                    # Kural spesifikasyonu, denetim raporu, görev sözleşmesi
│   └── README.md
│
├── README.md                    # Bu dosya
└── .gitignore
```

---

## 🏗 Sistem Mimarisi (İkinci Aşama)

```
data/raw/*.xlsx
      │
      ▼
data_loader.py  ──►  forecast.py  ──►  outputs/Talep-tahmini.xlsx
      │                                        │
      │                                        ▼
      └──────────────────────────────►  optimize.py  ──►  outputs/Tasima-plani.xlsx
                                               │
                                               ▼
                                        checker.py
                                   (bağımsız doğrulama)
                                               │
                                               ▼
                                     PASS / FAIL + Maliyet Raporu
```

`checker.py`, sistemin `optimize.py`'den **bilinçli olarak bağımsız**
yazılmış modülüdür: üretilen planı sıfırdan yeniden hesaplayıp
(kapasite ihlali, SLA cezası, maliyet doğruluğu, format uyumu) doğrular.
Bu, tek bir modülün hem üretici hem denetleyici olmasından kaynaklanan
kör noktaları önlemek için bilinçli bir mühendislik kararıdır.

---

## 🚀 Hızlı Başlangıç

```bash
git clone https://github.com/dildasoftware/LoadIQ-LojistikOptimizasyonTeknofest26.git
cd LoadIQ-LojistikOptimizasyonTeknofest26/stage2_gelismis_cozum

pip install -r requirements.txt
python -m pytest tests/ -v
```

Talep tahminini incelemek için:

```bash
python src/forecast.py
```

---

## 📊 Proje Durumu

| Modül | Durum | Doğrulama |
|---|---|---|
| Veri denetimi (EDA) | ✅ Tamamlandı | [`docs/veri_denetim_raporu.md`](./stage2_gelismis_cozum/docs/veri_denetim_raporu.md) |
| Kanonik kural spesifikasyonu | ✅ Tamamlandı | [`docs/is_kurallari_spec.md`](./stage2_gelismis_cozum/docs/is_kurallari_spec.md) |
| `time_utils.py` — zaman/yuvarlama çekirdeği | ✅ Tamamlandı | 7/7 test PASS |
| `data_loader.py` — veri okuma/doğrulama | ✅ Tamamlandı | 6/6 test PASS |
| `checker.py` — bağımsız doğrulayıcı | ✅ Tamamlandı | 19/19 test PASS |
| `forecast.py` — talep tahmin modeli | ✅ Tamamlandı | Backtest WAPE ≈ %24 (P×E) |
| `optimize.py` — taşıma planı motoru | ✅ Tamamlandı | checker PASS · feasible 22.106.411 TL |
| Uçtan uca entegrasyon (`pipeline.py`) | ✅ Tamamlandı | `pipeline.py` → checker PASS, 0 uygunluk ihlali |

**Toplam:** 32/32 birim test yeşil (bkz. `stage2_gelismis_cozum/tests/`). Nihai feasible plan maliyeti **22.106.411 TL** (başlangıca göre −%25,9).

---

## 🛠 Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| Dil | Python 3.11+ |
| Veri işleme | pandas, openpyxl, numpy |
| Optimizasyon | Google OR-Tools (planlanan), greedy + lokal arama sezgiseli |
| Test | pytest |
| Sürüm kontrolü | Git / GitHub |

---

## 📚 Dokümantasyon

İkinci aşamaya dair tüm teknik detaylar [`stage2_gelismis_cozum/docs/`](./stage2_gelismis_cozum/docs) altında toplanmıştır:

| Doküman | İçerik |
|---|---|
| [`is_kurallari_spec.md`](./stage2_gelismis_cozum/docs/is_kurallari_spec.md) | Tüm iş kurallarının tek kaynağı (şartname + Q&A + duyurular derlenmiş) |
| [`veri_denetim_raporu.md`](./stage2_gelismis_cozum/docs/veri_denetim_raporu.md) | Veri setlerinde tespit edilen tutarsızlıklar ve çözümleri |
| [`sistem_tasarimi_ve_uygulama_plani.md`](./stage2_gelismis_cozum/docs/sistem_tasarimi_ve_uygulama_plani.md) | Mimari tasarım ve uygulama yol haritası |

---

## 👥 Takım

<div align="center">

**Takım NASİP**

TEKNOFEST 2026 · Lojistik & Ulaştırma Kategorisi

📧 bilbildilara77@gmail.com

</div>

---

<div align="center">
<sub>Bu depo yarışma teslim süreci boyunca gerekli görüldüğü şekilde güncellenmektedir.</sub>
</div>

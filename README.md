# 🚛 LoadIQ — Akıllı Lojistik Optimizasyon Sistemi

> **TEKNOFEST 2026 | Lojistik & Ulaştırma Kategorisi**
>
> Transfer merkezleri arası desi talebini tahmin eden ve minimum maliyetli araç ataması yapan optimizasyon sistemi.

---

## 📋 Problem Tanımı

18 transfer merkezi arasında, 89 güzergahta gerçekleşen desi (yük hacmi) taleplerini geçmiş 4 aylık veriden (1 Ocak – 10 Mayıs 2026) öğrenerek **11–17 Mayıs 2026** haftası için tahmin etmek ve bu tahmini, **minimum toplam maliyet** ile kiralık + spot araç kombinasyonu kullanarak karşılamak.

---

## 💰 TOPLAM MALİYET SONUCU

| Maliyet Kalemi | Tutar (TL) |
|----------------|-----------|
| Kiralık Araç Maliyeti | 802,743.79 |
| Spot Araç Maliyeti | 9,284,442.92 |
| **GENEL TOPLAM** | **10,087,186.71** |

> Bu maliyet 11–17 Mayıs 2026 (7 gün), 89 güzergah, 682 araç ataması için hesaplanmıştır.

---

## 📊 Teslim Çıktıları

| Dosya | İçerik |
|-------|--------|
| `outputs/Tahminlenen_Talep.xlsx` | 89 güzergah × 7 gün = 623 satır (Tarih, Çıkış TM, Varış TM, Tahmin Edilen Desi) |
| `outputs/Arac_Planlama.xlsx` | 682 araç ataması (Tarih, Araç Tipi, Çıkış TM, Varış TM, Atanan Desi, Maliyet) + Özet sayfası |

---

## 🔬 Tahmin Yöntemi

### Model: P(sevkiyat) × E[desi | sevkiyat] — İki Parçalı Model

Her (güzergah, hedef tarih) çifti için:

1. Hedef tarihin haftanın gününü bul (Pazartesi, Salı, ...)
2. O güzergahın **sadece hedef tarihten öNCEKİ** verilerinden, aynı haftanın-gününe denk gelen son **12 gözlemi** al (leakage yok)
3. `p_ship` = Bu gözlemlerde Desi > 0 olan oran
4. `e_desi` = Desi > 0 olan gözlemlerin ortalaması
5. **Tahmin = p_ship × e_desi**

### Denenen Alternatifler

| Model | WAPE | Karar |
|-------|------|-------|
| Basit haftalık ortalama | ~%44 | Elendi |
| **İki parçalı model (P×E)** | **~%42** | ✅ **Seçildi** |
| LightGBM (ML) | %59–107 (gerçek 7-gün-ileri ufkunda) | Elendi — leakage olmadan dengesiz |

**Neden ML reddedildi?** LightGBM, eğitim setinde iyi görünse de gerçek 7-gün-ileri tahmin ufkunda stabil çalışmadı (bazı ufuklarda WAPE %107'ye çıktı). Basit modeller ML'yi yenince karmaşıklığı reddetmek doğru mühendislik kararıdır.

### Backtest Sonuçları

- **Test dönemi:** 27 Nisan – 10 Mayıs 2026 (14 gün, leakage yok)
- **Genel WAPE:** ~%35–42
- **Not:** 30 Nisan ve 1 Mayıs (İşçi Bayramı) anomali günleridir. Bu günlerde desi normal günlerin %5–10'una düştü. Bu anomaliler backtest WAPE'sini olumsuz etkiler; hedef hafta (11–17 Mayıs) için bilinen resmi tatil yoktur.

---

## ⚙️ Optimizasyon Yöntemi

### Araç Atama Süreci (Güzergah × Gün Bazında)

**Adım 1 — Kiralık Araçlar (FAQ #3: Zorunlu)**
- `Kiralık_Araçlar.xlsx`'teki atamalar her gün sabit olarak çalışır
- Kiralık araçlar boş dahi olsa maliyetleri eklenir
- Maliyet = Günlük Kira + Mesafe × Km Maliyeti

**Adım 2 — Spot Araçlar (FAQ #1: Min %10 Doluluk)**
- Kalan desi = max(0, Tahmin – Kiralık Kapasite)
- Kalan desisi karşılayacak **minimum maliyetli** araç kombinasyonu seçilir
- **Kısıt:** Her spot aracın kapasitesinin en az **%10'u** dolu olmalı (560 desi = Kamyonet %10'u)
- Kalan desi < 560 desi ise spot araç **atanamaz** (FAQ #1 gereği)

**Adım 3 — Mesafe Hesabı (FAQ #6)**
- Tüm mesafeler **Haversine kuş uçuşu** formülüyle hesaplandı
- Karayolu çarpanı kullanılmadı (FAQ #6 gereği saf kuş uçuşu)

### Araç Parametreleri

| Araç | Kapasite (desi) | Kiralık Günlük (TL) | Kiralık/km (TL) | Spot Günlük (TL) | Spot/km (TL) |
|------|-----------------|---------------------|-----------------|------------------|--------------|
| Tır | 22.400 | 7.000 | 13 | 11.700 | 25 |
| Kamyon | 12.000 | 5.000 | 10 | 7.638 | 21 |
| Hafif Kamyon | 7.200 | 5.000 | 10 | 8.750 | 20 |
| Kamyonet | 5.600 | 3.750 | 6 | 4.750 | 18 |
---

## 📁 Proje Yapısı

```
LoadIQ-LojistikOptimizasyonTeknofest26/
├── data/
│   ├── raw/                          # Ham Excel dosyaları (değiştirilmedi)
│   │   ├── Desi_talep (1).xlsx
│   │   ├── Kiralık_Araçlar.xlsx
│   │   ├── Koordinatlar v2 (1).xlsx
│   │   └── Araç_Kapasite_Maliyet.xlsx
│   └── processed/
│       └── panel.csv                 # 89 güzergah × 130 gün tam panel
├── src/
│   ├── forecast.py                   # P×E tahmin modeli
│   ├── optimize.py                   # Araç atama optimizasyonu
│   ├── utils.py                      # Haversine mesafe hesabı
│   └── validate_format.py            # Çıktı format doğrulama
├── tests/
│   ├── test_coverage.py              # Kapasite kapsama testi
│   └── test_optimality.py            # Optimizasyon doğrulama
├── outputs/
│   ├── Tahminlenen_Talep.xlsx        # 623 satır tahmin (teslim çıktısı)
│   └── Arac_Planlama.xlsx            # 682 araç ataması (teslim çıktısı)
├── requirements.txt
└── README.md
```

---

## ⚙️ Kurulum & Çalıştırma

### 1. Bağımlılıkları Yükle

```bash
pip install -r requirements.txt
```

### 2. Pipeline'ı Sırayla Çalıştır

```bash

# Adım 1: Tahmin üret
python src/forecast.py

# Adım 2: Araç planlaması
python src/optimize.py

# Adım 3: Testleri çalıştır
python tests/test_coverage.py

```

---

## 📌 Varsayımlar & Bilinen Riskler

| # | Varsayım | Durum |
|---|----------|-------|
| 1 | Eksik (güzergah, tarih) kombinasyonları = Desi 0 (sevkiyat yok) | Doğrulandı |
| 2 | Kiralık araç filosu 7 gün boyunca sabit (her gün aynı atama) | ⚠️ DOĞRULANMAMIŞ |
| 3 | Karayolu çarpanı kullanılmadı | FAQ #6 gereği saf Haversine kuş uçuşu uygulandı |
| 4 | Dönüş rotası maliyeti hesaba katılmadı | FAQ #2 gereği |
| 5 | Konsolidasyon yapılmadı (tek kaynaklı atama) | FAQ #4 gereği |
| 6 | 30 Nisan ve 1 Mayıs anomali günleri (tatil etkisi) modelden çıkarılmadı | Backtest WAPE'sini etkiler |
| 7 | 19 Mayıs (Atatürk'ü Anma) hedef hafta dışında — etki yok | Doğrulandı |
| 8 | Her araç günde tek sefer yapar — ardışık/tekrar sefer kurgusu uygulanmadı | Yarışma duyurusu gereği |

---

## 🏗️ Teknoloji Yığını

| Katman | Teknoloji |
|--------|-----------|
| Dil | Python 3.11+ |
| Veri İşleme | pandas, openpyxl |
| Optimizasyon | Greedy optimizasyon (kiralık öncelikli, minimum maliyetli spot seçimi) |
| Mesafe Hesabı | Haversine (math) |
| Test | Python unittest / assert |

---

## 📬 İletişim

| | |
|--|--|
| Takım Adı | NASİP |
| E-posta | bilbildilara77@gmail.com |
| GitHub | https://github.com/dildasoftware/LoadIQ-LojistikOptimizasyonTeknofest26 |

---

> **TEKNOFEST 2026 | Lojistik & Ulaştırma**
>
> *"Doğru araç, doğru rota, minimum maliyet."*
>
> ⚠️ Bu depo teslim süreci boyunca **private** kalacaktır. Resmi duyuru sonrası public yapılacaktır.

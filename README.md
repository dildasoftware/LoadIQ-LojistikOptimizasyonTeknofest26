# 🚛 LoadIQ — Akıllı Yük Dağıtım & Rota Optimizasyon Sistemi

> **TEKNOFEST 2025 | Lojistik & Ulaştırma Kategorisi**
>
> Türkiye genelindeki transfer merkezleri arasında desi bazlı talep verilerini, araç kapasitelerini ve maliyet parametrelerini bütünleşik bir optimizasyon motoru üzerinden işleyerek **minimum toplam maliyet** ile **maksimum araç doluluk oranını** hedefleyen akıllı bir yük planlama sistemi.

---

## 📋 İçindekiler

* [Özellikler](#-özellikler)
* [Ekran Görüntüleri](#-ekran-görüntüleri)
* [Teknoloji Yığını](#-teknoloji-yığını)
* [Mimari Yapı](#-mimari-yapı)
* [Kurulum](#-kurulum)
* [Kullanım](#-kullanım)
* [Veri Modeli](#-veri-modeli)
* [Maliyet Hesaplama Mantığı](#-maliyet-hesaplama-mantığı)
* [Klasör Yapısı](#-klasör-yapısı)
* [Yol Haritası](#-yol-haritası)
* [Katkıda Bulunma](#-katkıda-bulunma)
* [Lisans](#-lisans)
* [İletişim](#-iletişim)

---

## ✨ Özellikler

### Çekirdek Fonksiyonlar

* **Desi Bazlı Yük Eşleştirme** — Çıkış/varış transfer merkezi çiftleri için gelen toplam desi talebini dinamik olarak okur ve araç kapasitelerine (Tır: 22.400 desi, Kamyon: 12.000, Hafif Kamyon: 7.200, Kamyonet: 5.600) göre optimal araç kombinasyonunu hesaplar
* **İkili Araç Filosu Desteği** — Kiralık araçlar (günlük + km başına maliyet) ve spot araçlar (sabit günlük + km başına maliyet) arasında gerçek zamanlı maliyet karşılaştırması yapar; her rota için en düşük maliyetli seçeneği seçer
* **Haversine Rota Hesabı** — 18 transfer merkezinin enlem/boylam koordinatlarından (Koordinatlar_v2.xlsx) iki nokta arasındaki gerçek kuş uçuşu mesafeyi hesaplar; karayolu katsayısı uygulanarak pratik mesafeye dönüştürür
* **Toplam Maliyet Çıktısı** *(TEKNOFEST zorunlu kriteri)* — Her rota için ayrı ayrı ve filonun tamamı için kümülatif toplam maliyet (TL) raporlanır
* **Coğrafi Görselleştirme** — Transfer merkezleri harita üzerinde işaretlenir; aktif rotalar ve araç atamaları görsel olarak sunulur

### Teknik Avantajlar

* Araç tipi/kapasite/maliyet parametreleri Excel'den okunur; **kod değiştirmeden** filoya yeni araç tipi eklenebilir
* Talep ve koordinat dosyaları modüler yapıda; bağımsız olarak güncellenebilir
* Kiralık araç atamalarının ön tanımlı listesi (Kiralık_Araçlar.xlsx) sisteme import edilebilir; planlı ve anlık atamalar ayrı takip edilir

---

## 📸 Ekran Görüntüleri

> *(Ekran görüntüleri projenin geliştirme sürecinde bu bölüme eklenecektir)*

| Bileşen                       | Açıklama                                                           |
| ----------------------------- | ------------------------------------------------------------------ |
| `screenshot_dashboard.png`    | Ana kontrol paneli — toplam maliyet özeti, araç doluluk oranları   |
| `screenshot_map.png`          | Türkiye haritası üzerinde transfer merkezi & rota görselleştirmesi |
| `screenshot_optimization.png` | Rota bazında araç atama & maliyet kırılımı tablosu                 |
| `screenshot_report.png`       | Dışa aktarılan Excel/PDF maliyet raporu örneği                     |

---

## 🛠️ Teknoloji Yığını

| Katman         | Teknoloji                | Açıklama                                                         |
| -------------- | ------------------------ | ---------------------------------------------------------------- |
| Backend        | Python 3.11+             | Çekirdek optimizasyon motoru                                     |
| Veri İşleme    | pandas, openpyxl         | Excel okuma/yazma, veri manipülasyonu                            |
| Optimizasyon   | SciPy / PuLP             | Doğrusal programlama tabanlı araç atama optimizasyonu            |
| Coğrafi Hesap  | geopy / math (Haversine) | Koordinat bazlı mesafe hesabı                                    |
| Görselleştirme | Folium / Plotly          | Harita & grafik çıktıları                                        |
| Arayüz         | Streamlit                | Etkileşimli web arayüzü                                          |
| Raporlama      | openpyxl, ReportLab      | Excel ve PDF rapor çıktısı                                       |
| Veri Formatı   | `.xlsx`                  | Araç parametreleri, koordinatlar, talep ve kiralık araç verileri |

---

## 🏗️ Mimari Yapı

```text
┌─────────────────────────────────────────────────────────────────┐
│                        VERİ KATMANI                             │
│                                                                 │
│  Arac_Kapasite_Maliyet.xlsx   Koordinatlar_v2.xlsx              │
│  (Araç tipleri, kapasite,     (18 transfer merkezi              │
│   kiralık & spot maliyetler)   enlem/boylam koordinatları)      │
│                                                                 │
│  Desi_talep.xlsx              Kiralik_Araclar.xlsx              │
│  (Çıkış→Varış bazlı           (Önceden atanmış kiralık          │
│   desi talep verileri)         araç listesi)                    │
└────────────────────┬────────────────────────────────────────────┘
                     │ pandas / openpyxl
┌────────────────────▼────────────────────────────────────────────┐
│                     HESAPLAMA KATMANI                           │
│                                                                 │
│  ┌─────────────────┐   ┌──────────────────┐                    │
│  │  Mesafe Motoru  │   │  Kapasite Motoru │                    │
│  │  (Haversine +   │   │ (Desi→Araç Tipi  │                    │
│  │ yol katsayısı)  │   │ eşleştirme)      │                    │
│  └────────┬────────┘   └────────┬─────────┘                    │
│           │                     │                              │
│  ┌────────▼─────────────────────▼─────────┐                    │
│  │      MALİYET OPTİMİZASYON MOTORU       │                    │
│  └────────────────────┬───────────────────┘                    │
└───────────────────────┼─────────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────────┐
│                      ÇIKTI KATMANI                              │
│                                                                 │
│ 📊 Streamlit Dashboard    🗺️ Folium Harita                     │
│ 📄 Excel Raporu           📋 PDF Maliyet Özeti                  │
│                                                                 │
│ ✅ TOPLAM MALİYET (TEKNOFEST zorunlu kriteri)                   │
└─────────────────────────────────────────────────────────────────┘
```

### Karar Akışı

1. Veri Yükleme
2. Mesafe Hesabı
3. Araç Atama
4. Maliyet Karşılaştırma
5. Raporlama

---

## ⚙️ Kurulum

### Ön Koşullar

* Python 3.11 veya üstü
* pip veya conda

### 1. Depoyu Klonlayın

```bash
git clone https://github.com/[KULLANICI_ADI]/loadiq.git
cd loadiq
```

### 2. Sanal Ortam Oluşturun

```bash
python -m venv .venv

source .venv/bin/activate
# veya
.venv\Scripts\activate
```

### 3. Bağımlılıkları Yükleyin

```bash
pip install -r requirements.txt
```

### 4. Veri Dosyalarını Yerleştirin

```text
data/
├── Arac_Kapasite_Maliyet.xlsx
├── Koordinatlar_v2.xlsx
├── Kiralik_Araclar.xlsx
└── Desi_talep.xlsx
```

### 5. Uygulamayı Başlatın

```bash
streamlit run app.py
```

---

## 🚀 Kullanım

```python
from loadiq.optimizer import LoadOptimizer

optimizer = LoadOptimizer(
    vehicles_path="data/Arac_Kapasite_Maliyet.xlsx",
    coordinates_path="data/Koordinatlar_v2.xlsx",
    demand_path="data/Desi_talep.xlsx",
    rentals_path="data/Kiralik_Araclar.xlsx"
)

results = optimizer.run()

print(f"Toplam Filo Maliyeti: {results.total_cost:,.2f} TL")
```

---

## 📊 Veri Modeli

### Araç Kapasite & Maliyet Parametreleri

| Araç Tipi    | Kapasite (desi) | Kiralık Günlük (TL) | Kiralık km (TL) | Spot Günlük (TL) | Spot km (TL) |
| ------------ | --------------- | ------------------- | --------------- | ---------------- | ------------ |
| Tır          | 22.400          | 7.000               | 13              | 11.700           | 25           |
| Kamyon       | 12.000          | 5.000               | 10              | 7.638            | 21           |
| Hafif Kamyon | 7.200           | 5.000               | 10              | 8.750            | 20           |
| Kamyonet     | 5.600           | 3.750               | 6               | 4.750            | 18           |

### Transfer Merkezleri

`Mersin · Kütahya · Kocaeli · Eskişehir · İstanbul · Bilecik · Balıkesir · Şanlıurfa · Tekirdağ · Sivas · Yalova · Manisa · Isparta · Mardin · Erzincan · Zonguldak · Karaman · Denizli`

---

## 💰 Maliyet Hesaplama Mantığı

### Kiralık Araç Maliyeti

```text
Maliyet_kiralık = Günlük_Kira + (Mesafe_km × km_Maliyet)
```

### Spot Araç Maliyeti

```text
Maliyet_spot = Günlük_Sabit + (Mesafe_km × km_Maliyet)
```

### Rota Toplam Maliyeti

```text
Maliyet_rota = min(Maliyet_kiralık, Maliyet_spot) × Araç_Sayısı
```

### Filo Toplam Maliyeti

```text
TOPLAM_MALİYET = Σ Maliyet_rota
```

---

## 📁 Klasör Yapısı

```text
loadiq/
├── data/
├── loadiq/
├── tests/
├── outputs/
├── app.py
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🗺️ Yol Haritası

### v1.0 — Temel Sistem

* [x] Veri yükleme
* [x] Haversine mesafe hesabı
* [x] Araç eşleştirme
* [x] Maliyet karşılaştırması
* [x] Toplam maliyet raporu

### v1.1 — Optimizasyon Katmanı

* [ ] Global araç dağıtımı optimizasyonu
* [ ] Çoklu rota birleştirme
* [ ] Çalışma saati ve müsaitlik kısıtları

### v1.2 — Gelişmiş Raporlama

* [ ] İnteraktif harita
* [ ] PDF raporlama
* [ ] Sunum dashboardu

### v2.0 — Platform Genişlemesi

* [ ] Çok günlü planlama
* [ ] API entegrasyonu
* [ ] Talep tahminleme
* [ ] Çok kullanıcılı sistem

---

## 🤝 Katkıda Bulunma

```bash
git checkout -b feature/ozellik-adi
git commit -m "feat: yeni özellik"
git push origin feature/ozellik-adi
```

---

## 📄 Lisans

Bu proje **MIT Lisansı** ile lisanslanmıştır.

---

## 📬 İletişim

|           |                     |
| --------- | ------------------- |
| Takım Adı | [TAKIM_ADI]         |
| Danışman  | [DANIŞMAN_ADI]      |
| E-posta   | [EMAIL_ADRESİ]      |
| GitHub    | [GITHUB_PROFIL_URL] |

---

<div align="center">

**TEKNOFEST 2025 | Lojistik & Ulaştırma**

*"Doğru araç, doğru rota, minimum maliyet."*



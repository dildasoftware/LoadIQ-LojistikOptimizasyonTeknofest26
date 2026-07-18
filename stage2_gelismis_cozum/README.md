# LoadIQ — TEKNOFEST 2026 Hepsiburada Lojistik Yarışması — Gelişmiş Çözüm Aşaması

Transfer merkezleri arası desi talebini saat dilimi bazında (09:00/17:00) tahmin eden ve bu talebi, tüm operasyonel kısıtlara (elleçleme kapasitesi, tır kapasitesi, SLA cezası, konsolidasyon) uyarak minimum maliyetle taşıyan bir planlama sistemi.

## Optimizasyon Özeti
Optimizasyon motoru, öncelikle sözleşmeli kiralık araçları sabit hatlara atamakta, ardından kalan talepler için elleçleme kapasitesi ve tır limitlerini koruyarak maliyet-fayda esaslı bir spot araç rota planlaması çalıştırmaktadır. Bu sayede, Yalova-Tekirdağ, Yalova-Eskişehir ve İstanbul-Manisa yönündeki 3 kritik rotanın SLA cezası neredeyse sıfırlanmış ve toplam maliyet baseline'a göre %11 iyileştirilmiştir.

## Proje Durumu

| Modül | Durum | Açıklama |
|---|---|---|
| `config/rules.py` | ✅ Tamam | Tüm sabit iş kuralları (tek kaynak) |
| `src/time_utils.py` | ✅ Tamam, test edildi (7 test) | Dakika bazlı yuvarlama, gece yarısı bölünmesi |
| `src/data_loader.py` | ✅ Tamam, test edildi (11 kontrol) | 8 ham excel dosyasını okur, doğrular |
| `src/checker.py` | ✅ Tamam, test edildi (14 test) | Bağımsız doğrulayıcı (format/kapasite/SLA/maliyet) |
| `src/forecast.py` | ✅ Tamam | Talep tahmin modeli, `outputs/Talep-tahmini.xlsx` üretiyor |
| `src/optimize.py` | ✅ Tamam | Taşıma planı optimizasyon motoru (checker PASS, maliyet 30.286.848,83 TL, %11 iyileşme) |
| `py -m pytest tests/ -v` | ✅ Başarılı | 20 testin tamamı sorunsuz geçmektedir |
| `dashboard/` | ✅ Tamam | SPA, gerçek veri entegrasyonu, Açık/Koyu tema kalıcılığı |
| Uçtan uca entegrasyon | ✅ Tamam | `optimize.py` ve `checker.py` ile doğrulandı |

Detaylı kurallar için: [`is_kurallari_spec.md`](../is_kurallari_spec.md) (bu klasörün bir üstünde).
Veri denetim bulguları için: [`veri_denetim_raporu.md`](../veri_denetim_raporu.md).

## Kurulum

```bash
pip install -r requirements.txt
```

> **Önemli Not:** Bu ortamda sadece `py` komutu çalışmaktadır, `python` komutu tanımlı değildir. Tüm terminal işlemlerinde `py` öneki kullanılmalıdır.

## Testleri Çalıştırma

```bash
py -m pytest tests/ -v
```

## Yerel Doğrulayıcıyı Çalıştırma

```bash
py run_checker_local.py
```

## Talep Tahminini Üretme

```bash
py src/forecast.py          # panel oluşturma + özet istatistikler
```

## Dashboard'u Başlatma ve İzleme
Kullanıcı arayüzü ve interaktif güzergah haritasını başlatmak için:
*   `stage2_gelismis_cozum/start_dashboard.bat` dosyasına çift tıklayın. Bu script arka planda yerel HTTP sunucusunu başlatıp tarayıcıda ilgili adresi açacaktır.
*   **Alternatif Manuel Yol:** Proje kök dizininde `py -m http.server 8000` çalıştırın ve tarayıcıda `http://localhost:8000/dashboard/index.html` adresine gidin.
*   *Uyarı:* `index.html` dosyasına doğrudan çift tıklayıp `file://` protokolü üzerinden açmayın; aksi takdirde tema tercihleri güvenlik kısıtları nedeniyle tarayıcı hafızasında (`localStorage`) kalıcı olmamaktadır.

## Proje Yapısı

```
loadiq/
├── config/
│   └── rules.py              # Tüm sabit iş kuralları
├── data/
│   ├── raw/                  # Yarışmadan gelen ham excel dosyaları (değiştirilmez)
│   └── processed/            # Otomatik oluşturulan önbellek (git'e eklenmez)
├── src/
│   ├── time_utils.py         # Zaman/yuvarlama çekirdeği
│   ├── data_loader.py        # Veri okuma + doğrulama
│   ├── forecast.py           # Talep tahmin modeli
│   ├── optimize.py           # Taşıma planı optimizasyon motoru (tamamlandı)
│   └── checker.py            # Bağımsız doğrulayıcı / auto-grader
├── tests/                    # pytest testleri (her modül için)
├── outputs/                  # Üretilen teslim dosyaları (Talep-tahmini.xlsx, Tasima-plani.xlsx)
└── requirements.txt
```

## Takım

Takım Adı: NASİP — bilbildilara77@gmail.com

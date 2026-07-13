# LoadIQ — TEKNOFEST 2026 Hepsiburada Lojistik Yarışması — Gelişmiş Çözüm Aşaması

Transfer merkezleri arası desi talebini saat dilimi bazında (09:00/17:00) tahmin eden ve bu talebi, tüm operasyonel kısıtlara (elleçleme kapasitesi, tır kapasitesi, SLA cezası, konsolidasyon) uyarak minimum maliyetle taşıyan bir planlama sistemi.

## Proje Durumu

| Modül | Durum | Açıklama |
|---|---|---|
| `config/rules.py` | ✅ Tamam | Tüm sabit iş kuralları (tek kaynak) |
| `src/time_utils.py` | ✅ Tamam, test edildi (7 test) | Dakika bazlı yuvarlama, gece yarısı bölünmesi |
| `src/data_loader.py` | ✅ Tamam, test edildi (11 kontrol) | 8 ham excel dosyasını okur, doğrular |
| `src/checker.py` | ✅ Tamam, test edildi (14 test) | Bağımsız doğrulayıcı (format/kapasite/SLA/maliyet) |
| `src/forecast.py` | ✅ Tamam | Talep tahmin modeli, `outputs/Talep-tahmini.xlsx` üretiyor |
| `src/optimize.py` | 🔲 Yapılıyor | Taşıma planı optimizasyon motoru |
| Uçtan uca entegrasyon | 🔲 Bekliyor | `optimize.py` bitince |

Detaylı kurallar için: [`is_kurallari_spec.md`](../is_kurallari_spec.md) (bu klasörün bir üstünde).
Veri denetim bulguları için: [`veri_denetim_raporu.md`](../veri_denetim_raporu.md).

## Kurulum

```bash
pip install -r requirements.txt
```

## Testleri Çalıştırma

```bash
python3 -m pytest tests/ -v
```

> Not: `tests/test_data_loader.py` büyük excel dosyasını okuduğu için ilk
> çalıştırmada birkaç saniye sürebilir (`data/processed/talep_cache.csv`
> önbelleği oluşturulduktan sonra hızlanır).

## Talep Tahminini Üretme

```bash
python3 src/forecast.py          # panel oluşturma + özet istatistikler
```

Tam tahmin dosyasını üretmek için `src/forecast.py` içindeki
`forecast_range(...)` fonksiyonunu 29 Haziran – 5 Temmuz aralığıyla
çağırıp `assign_talep_id` ile ID atayıp `to_excel(...)` ile kaydedin
(örnek kullanım için `if __name__ == "__main__"` bloğuna bakın).

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
│   ├── optimize.py           # (yapım aşamasında) Taşıma planı optimizasyonu
│   └── checker.py            # Bağımsız doğrulayıcı / auto-grader
├── tests/                    # pytest testleri (her modül için)
├── outputs/                  # Üretilen teslim dosyaları (Talep-tahmini.xlsx, Tasima-plani.xlsx)
└── requirements.txt
```

## Takım

Takım Adı: NASİP — bilbildilara77@gmail.com

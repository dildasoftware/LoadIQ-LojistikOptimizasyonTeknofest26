# LoadIQ — Gelişmiş Çözüm Aşaması: Sistem Tasarımı ve Uygulama Planı

Bu doküman şu ana kadar üretilenleri (veri denetimi, kanonik kural spesifikasyonu, zaman çekirdeği) tek bir uygulama planında birleştirir. Buradan itibaren birlikte bu plana göre ilerleyeceğiz — her adımın net bir "bitti" tanımı var, bir adım bitmeden bir sonrakine geçmeyeceğiz.

## 1. Amaç

29 Haziran 09:00 – 5 Temmuz 17:00 penceresi için:
1. Güzergah × gün × saat dilimi bazında desi talebi tahmin etmek (`Talep-tahmini.xlsx`)
2. Bu talebi, tüm kısıtlara (tır/elleçleme kapasitesi, SLA, kiralık filo zorunluluğu) uyarak minimum toplam maliyetle (araç maliyeti + SLA cezası) taşıyan bir plan üretmek (`Tasima-plani.xlsx`)
3. İkisinin de jüri tarafından reddedilmeyecek formatta, kısıt ihlali olmadan, doğrulanabilir şekilde teslim edilmesi

## 2. Genel Mimari

```
                     ┌─────────────────────┐
   Ham xlsx  ───────▶│   data_loader.py    │  Temizlik, tip doğrulama,
  (9 dosya)           │  + config/rules.py  │  sabit kısıtlar (Kocaeli hariç,
                     └──────────┬──────────┘  tır-yasaklı TM'ler, tatil günleri)
                                │
                                ▼
                     ┌─────────────────────┐
                     │    forecast.py      │  Saat dilimi bazlı (09:00/17:00)
                     │                      │  talep tahmini + backtest
                     └──────────┬──────────┘
                                │  Talep-tahmini.xlsx
                                ▼
                     ┌─────────────────────┐
                     │    optimize.py       │  Kiralık filo (sabit) + spot
                     │                      │  atama, greedy + lokal arama
                     └──────────┬──────────┘
                                │  Tasima-plani.xlsx
                                ▼
                     ┌─────────────────────┐
                     │    checker.py        │  BAĞIMSIZ doğrulama: kapasite
                     │  (auto-grader)       │  ihlali, maliyet/SLA yeniden
                     └──────────┬──────────┘  hesap, format uyumu
                                ▼
                       Denetim Raporu (PASS/FAIL + tahmini puan)
```

`time_utils.py` (zaman/yuvarlama) tüm modüller tarafından paylaşılan ortak çekirdektir — zaten yazıldı ve test edildi.

## 3. Modül Modül Tasarım

### 3.1 `config/rules.py` — Sabit Kurallar ve Kısıtlar
Denetim raporundan çıkan sabitler kod içinde tek yerde:
- `EXCLUDED_ROUTES`: Kocaeli'ye varışlı 17 çift
- `TIR_YASAK_TM`: Bilecik, Denizli, Isparta, Karaman, Kütahya, Sivas, Zonguldak
- `TIR_SPOT_YASAK_TM`: Balıkesir, Tekirdağ (kota zorunlu filoyla dolu)
- `TATIL_GUNLERI`: 1 Ocak, 20-21 Mart, 30 Nisan, 1 Mayıs, 27-31 Mayıs
- Maliyet/kapasite tabloları (xlsx'ten okunur, burada sadece iş kuralı sabitleri)

**Neden ayrı dosya:** Yeni bir duyuru geldiğinde tek dosya değişir, kodun geri kalanına dokunulmaz.

### 3.2 `data_loader.py`
Ham 9 excel dosyasını okuyup normalize eder: tarih/saat tipleri, TM isim tutarlılığı, `config/rules.py`'deki filtreleri uygular. Çıktısı: pandas DataFrame'ler, hepsi doğrulanmış (`assert` ile: negatif desi yok, tanımsız TM yok, vb.)

**Bitti tanımı:** Tüm 9 dosya tek komutla yüklenir, şema doğrulama testleri geçer.

### 3.3 `forecast.py`
- Granülarite: (çıkış TM, varış TM, hedef tarih, saat∈{09:00,17:00})
- Yöntem: MVP'deki P(sevkiyat)×E[desi] modelinin saat dilimine genişletilmiş hali — aynı haftagünü+saat diliminin son N gözlemi (tatil günleri hariç tutularak)
- Backtest: geçmiş veriden bir dönem saklanır (leakage yok), WAPE ölçülür
- Çıktı: `Talep-tahmini.xlsx` (şemaya birebir uygun, D00001... ID'li)

**Bitti tanımı:** Backtest WAPE raporlanır, format testi geçer, Kocaeli/tatil filtreleri doğrulanır.

### 3.4 `optimize.py`
- Girdi: `Talep-tahmini.xlsx` + kısıtlar
- Adım 1: Zorunlu kiralık filo her gün sabit atanır (dönüşsüz, uğramasız)
- Adım 2: Kalan talep, spot araçlarla minimum maliyetli şekilde kapatılır — greedy inşa (en ucuz uygun araç tipi + kapasite dolulaştırma) + lokal arama iyileştirme (SLA cezası riski taşıyan atamaları yeniden dener)
- Kısıtlar her adımda kontrol edilir: tır kapasitesi, elleçleme kapasitesi (+gece yarısı oransal bölünme), dakika bazlı yuvarlama
- Çıktı: `Tasima-plani.xlsx` (V0001... ID'li, D00001-1 bölünme formatı)

**Bitti tanımı:** Kısıt ihlali sıfır, toplam maliyet+SLA cezası raporlanır, format testi geçer.

### 3.5 `checker.py` — Bağımsız Doğrulayıcı
optimize.py'den tamamen ayrı yazılır (aynı hatayı iki kere yapmamak için). Girdi olarak sadece üretilen xlsx dosyalarını okur, kuralları sıfırdan uygular:
- Her TM/gün için elleçleme ve tır kapasitesi yeniden hesaplanır, aşım varsa flag
- Her talep için SLA cezası yeniden hesaplanır, optimize.py'nin raporladığıyla karşılaştırılır (fark varsa flag)
- Toplam maliyet yeniden hesaplanır
- ID format kontrolü (regex)

**Bitti tanımı:** checker.py, kasıtlı olarak bozulmuş bir test planını doğru şekilde reddeder (negatif test).

## 4. Test Piramidi

1. Birim testler (`time_utils` — tamam, 7/7 geçti)
2. `data_loader` şema testleri
3. `checker.py` negatif testleri (bozuk plan reddedilmeli)
4. `forecast.py` backtest (WAPE metriği)
5. Uçtan uca: gerçek verilerle tam pipeline çalıştırma + `checker.py` ile PASS almak

## 5. Uygulama Planı — Şimdiden İtibaren Adımlar

| # | Adım | Çıktı | Bitti Tanımı |
|---|---|---|---|
| 1 | `config/rules.py` + `data_loader.py` | Temiz, doğrulanmış veri katmanı | 9 dosya yüklenir, testler geçer |
| 2 | `checker.py` iskeleti (kural motoru, henüz veri yok) | Bağımsız doğrulama fonksiyonları | Birim testleri geçer (elle kurgulanmış örneklerle) |
| 3 | `forecast.py` + backtest | `Talep-tahmini.xlsx` + WAPE raporu | Format testi geçer, WAPE raporlanır |
| 4 | `optimize.py` (önce küçük alt-küme: 2-3 TM ile prototip) | Küçük ölçekli `Tasima-plani.xlsx` | checker.py PASS verir |
| 5 | `optimize.py` tam ölçek (18 TM, 289 güzergah) | Tam `Tasima-plani.xlsx` | checker.py PASS, kısıt ihlali 0 |
| 6 | Uçtan uca pipeline + son rapor | Tüm teslim dosyaları + kaynak kod | Tek komutla baştan sona çalışır |

**Neden Adım 4'te önce küçük alt-küme:** 289 güzergahlık tam problemde hata ayıklamak zor. Önce 2-3 TM'lik basitleştirilmiş bir senaryoda algoritmanın doğru çalıştığını kanıtlayıp sonra ölçeklendirmek, senior mühendislik pratiğidir (erken, ucuz hata yakalama).

## 6. Bilinen Riskler

| Risk | Mitigasyon |
|---|---|
| Tır kapasitesi dosyası resmi olarak güncellenirse | `config/rules.py` tek nokta değişikliği, pipeline yeniden çalıştırılır |
| Optimizasyon 289 güzergahta çok yavaş kalırsa | Güzergahlar birbirinden bağımsız çözülebilir (paralel/parça parça), gerekirse heuristic basitleştirilir |
| Forecast WAPE yüksek çıkarsa | Basit modelden ML'e geçiş denenir ama sadece backtest'te gerçekten iyileşme kanıtlanırsa |
| Format hatası (en büyük risk — otomatik eleme) | `checker.py` her teslimattan önce zorunlu çalıştırılır |

## 7. Şimdi Ne Yapıyoruz

Onay verirseniz sırayla Adım 1'den başlıyoruz: `config/rules.py` ve `data_loader.py`. Her adım bitince kısa bir doğrulama çıktısı (test sonucu) göstereceğim, siz onaylayınca bir sonrakine geçeceğim.

# LoadIQ — 3 Kişilik Takım Görev Dağılımı (Gelişmiş Çözüm Aşaması)

Bu doküman, şu ana kadar tamamlanan işleri ve geriye kalan işi 3 kişiye
bölmek için hazırlandı. Herkes kendi bölümünü bağımsız çalışabilir;
aralarındaki bağlantı noktaları "Bağımlılık" satırlarında belirtilmiştir.

## Şu Ana Kadar Tamamlanan (ortak zemin, herkes bunun üstüne inşa eder)

- `config/rules.py` — tüm sabit iş kuralları
- `src/time_utils.py` — dakika bazlı yuvarlama (test edildi)
- `src/data_loader.py` — 8 ham excel dosyasını okur, doğrular (test edildi)
- `src/checker.py` — bağımsız doğrulayıcı: format, kapasite, SLA, maliyet kontrolü (test edildi)
- `src/forecast.py` — talep tahmin modeli, `Talep-tahmini.xlsx` üretiyor (WAPE ~%21-30, backtest ile doğrulandı)

Bu 5 dosya + testleri zip içinde mevcut. Herkes çalışmaya başlamadan önce:
```bash
cd loadiq
pip install -r requirements.txt
python3 -m pytest tests/ -v   # hepsi geçmeli
```

## Kalan İş — 3 Kişiye Bölünmüş

### Kişi 1 — Optimizasyon Motoru (en kritik, en zor parça)
**Dosya:** `src/optimize.py` (yeni yazılacak)

**Görev:** `Talep-tahmini.xlsx`'i girdi alıp, tüm kısıtlara uyan, minimum
maliyetli bir `Tasima-plani.xlsx` üreten motoru yazmak.

**Alt adımlar:**
1. Zorunlu kiralık filoyu her gün sabit ata (dönüşsüz, uğramasız, `config/rules.py`'deki `Kiralik_Araclar.xlsx`'ten).
2. Kalan talebi spot araçlarla kapat — greedy: en ucuz uygun araç tipini seç, kapasiteyi doldur.
3. Kısıtları her adımda kontrol et: tır kapasitesi (`TIR_TAMAMEN_YASAK_TM`, `TIR_SPOT_YASAK_TM`), elleçleme kapasitesi.
4. Önce KÜÇÜK bir alt-küme (2-3 transfer merkezi) ile prototip yap, `checker.py` ile doğrula, sonra 18 merkeze ölçekle.
5. `Tasima_Plani_Sablon.xlsx` formatına birebir uy (Araç ID, Talep ID bölünme formatı dahil).

**Bağımlılık:** `Talep-tahmini.xlsx` çıktısını (zip'te `outputs/` klasöründe hazır) girdi olarak kullanır — bekletmeye gerek yok, hemen başlayabilir.

**Bitti tanımı:** `checker.py` üretilen planı PASS ile onaylıyor, kısıt ihlali sıfır.

---

### Kişi 2 — Doğrulama, Test Genişletme ve Entegrasyon
**Dosyalar:** `tests/`, `src/checker.py` (genişletme), yeni `src/pipeline.py`

**Görev:** Kişi 1'in ürettiği optimizasyon motorunu sıkı şekilde test etmek
ve tüm pipeline'ı tek komutla çalışır hale getirmek.

**Alt adımlar:**
1. `checker.py`'yi gerçek/büyük ölçekli planla test et, eksik kalan kural varsa ekle (örn. konsolidasyon senaryoları, milk-run/uğrama doğrulaması).
2. Kenar durum testleri yaz: gece yarısını aşan elleçleme, SLA sınırında tam gecikme, talep bölünmesi (`D00001-1`, `D00001-2`).
3. `src/pipeline.py` yaz: `data_loader` → `forecast` → `optimize` → `checker`'ı tek komutla baştan sona çalıştıran orkestratör script.
4. Performans: 289 güzergah tam ölçekte makul sürede bitiyor mu, ölç ve raporla.

**Bağımlılık:** Kişi 1'in `optimize.py`'sinin en azından prototip (küçük ölçek) versiyonu hazır olmalı — o hazırken paralel ilerleyebilir (küçük ölçekli çıktıyla test yazımına başlanabilir).

**Bitti tanımı:** `python3 src/pipeline.py` tek komutla iki teslim dosyasını da üretiyor, tüm testler yeşil.

---

### Kişi 3 — Tahmin Modeli İyileştirme + Teslim Paketi + Sunum Hazırlığı
**Dosyalar:** `src/forecast.py` (iyileştirme), `is_kurallari_spec.md`, sunum materyali

**Görev:** Mevcut tahmin modelini iyileştirmek ve takımın teslim/sunum
tarafını hazırlamak.

**Alt adımlar:**
1. `forecast.py`'deki `n` (geçmiş gözlem penceresi) parametresini daha geniş bir tarih aralığında test et, gerekirse haftanın-günü + saat dışında ek özellik (örn. ay, mevsimsellik) dene — ama HER değişikliği backtest WAPE'siyle kanıtla, kanıtlanmayanı ekleme.
2. Kocaeli / tatil günleri / veri kalitesi ile ilgili yeni bulgu çıkarsa `veri_denetim_raporu.md`'yi güncelle.
3. Takım için Word/PDF sunum ve GitHub README'sini son haline getir (teknik mimari, backtest sonuçları, örnek çıktılar dahil).
4. Jüri sorularına hazırlık: "neden greedy, neden exact MILP değil", "WAPE neden bu seviyede", "format hatası riskini nasıl önlediniz" gibi soruların cevaplarını yaz.

**Bağımlılık:** Yok — hemen başlayabilir, mevcut `forecast.py` ve raporlarla çalışır.

**Bitti tanımı:** Backtest iyileştirmesi kanıtlanmış (ya da mevcut ayarın en iyisi olduğu gösterilmiş), sunum ve README teslime hazır.

## Koordinasyon Önerisi

- Ortak zemin (5 tamamlanmış dosya) tek bir `main` dalına commitlenir.
- Her kişi kendi işini ayrı bir git dalında (`optimize`, `test-entegrasyon`, `forecast-sunum`) yapar, bitince `main`'e birleştirir.
- Kişi 1'in çıktısı olmadan Kişi 2 ölçeklenemez ama küçük prototiple paralel başlayabilir — birbirlerini günlük kısa bir mesajla güncellemeleri yeterli.
- Haftalık kısa bir "checker.py PASS mi" kontrolü tüm takımın ortak referans noktası olsun.

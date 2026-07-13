# LoadIQ — Takım Çalışma Kılavuzu (3 Kişi, Antigravity + Git ile)

Bu doküman, her takım üyesinin BAŞTAN SONA ne yapacağını, hangi araçla,
hangi dosyayla çalışacağını, ne zaman başlayıp ne zaman duracağını ve
işini nereye teslim edeceğini adım adım anlatır. Kaptan bu dosyayı
olduğu gibi ilgili kişiye gönderebilir.

## 0. Herkesin Anlaması Gereken Ortak Çerçeve

**Kullanılan araçlar:** Her kişi kendi bilgisayarına (1) Antigravity IDE,
(2) Python 3.11+, (3) Git kurmalı. Herkes AYNI GitHub deposunu
(`https://github.com/dildasoftware/LoadIQ-LojistikOptimizasyonTeknofest26`)
kendi bilgisayarına indirecek (klonlayacak) ve KENDİ DALINDA (branch)
çalışacak. Böylece 3 kişi aynı anda çalışsa bile birbirinin dosyasının
üzerine yazmaz.

**Neden dal (branch) kullanıyoruz:** Herkes `main` dalında (ana sürüm)
aynı anda çalışırsa, biri diğerinin değişikliğini silebilir/bozabilir.
Her kişi kendi dalında çalışıp bitirince `main`'e "birleştirme isteği"
(pull request) açar, kaptan kontrol edip onaylar. Bu, profesyonel
yazılım ekiplerinin standart çalışma şekli — jüri kod geçmişinizi
incelerse (GitHub commit geçmişi) düzenli bir ekip izlenimi verir.

**Herkesin ilk yapacağı ortak adım (bir kere, herkes kendi bilgisayarında):**

```bash
git clone https://github.com/dildasoftware/LoadIQ-LojistikOptimizasyonTeknofest26.git
cd LoadIQ-LojistikOptimizasyonTeknofest26/stage2_gelismis_cozum
pip install -r requirements.txt
python -m pytest tests/ -v
```

Bu son komut sonunda TÜM testler (şu an 21 tane: 7 zaman testi, 11 veri
testi, 14 checker testi... toplamda birbirine yakın sayılar, tam sayı
`pytest` çıktısında görünür) yeşil (PASS) çıkmalı. Çıkmıyorsa kimse
kendi işine başlamasın, önce bunu bana ya da kaptana bildirsin.

**Genel kural — HERKES İÇİN GEÇERLİ:** Bir işi "bitti" demeden önce
mutlaka `python -m pytest tests/ -v` çalıştırılıp kırmızı (FAIL) test
olmadığından emin olunacak. Kırmızı test varken kimse `git push` yapmayacak.

## 1. Zaman Çizelgesi — Kim Ne Zaman Başlar

```
GÜN 0  (Kaptan)     : Repo temizliği (Antigravity Prompt 1) -> main'e push
                       |
GÜN 0-1 (Kişi 1)     : Optimizasyon - KÜÇÜK PROTOTİP (Prompt 2) başlar
GÜN 0-1 (Kişi 3)     : Tahmin iyileştirme + GitHub/sunum hazırlığı başlar (BEKLEMEZ)
                       |
        Kişi 1 küçük prototipi bitirip checker'dan PASS alınca -->
                       |
GÜN 1-2 (Kişi 2)     : Test/entegrasyon çalışması BAŞLAR (Kişi 1'in küçük
                        prototipini görmeden anlamlı test yazamaz, bu yüzden bekler)
GÜN 1-3 (Kişi 1)     : Optimizasyon - TAM ÖLÇEK (Prompt 3) devam eder
                       |
        Kişi 1 tam ölçek çıktıyı bitirip checker'dan PASS alınca -->
                       |
GÜN 3-4 (Kişi 2)     : Tam pipeline'ı birleştirir, uçtan uca test eder
GÜN 3-4 (Kişi 3)     : Sunum + README'yi gerçek sonuçlarla (maliyet, WAPE) günceller
                       |
GÜN 4-5 (Herkes)     : main'e birleştirme (pull request), son kontrol, teslim
```

**Net bağımlılık kuralı:** Kişi 2, Kişi 1'in KÜÇÜK prototipi bitmeden
anlamlı işe başlayamaz (test edecek bir şey yok). Kişi 3 kimseyi
beklemez, ilk günden başlar. Kişi 1 en uzun süren ve en kritik iştir,
diğer ikisi ona göre ayarlanır.

---

## 2. KİŞİ 1 — Optimizasyon Motoru (En Kritik Görev)

### Ne yapacak (özet)
Talep tahminini (`Talep-tahmini.xlsx`) girdi alıp, tüm kurallara uyan,
en az maliyetli bir taşıma planı (`Tasima-plani.xlsx`) üreten programı
(`optimize.py`) yazacak.

### Hangi araçla
Kendi bilgisayarında Antigravity IDE (içindeki yapay zeka ajanına
promptları yapıştırarak kod yazdıracak). Python/pytest terminalde
doğrulama için.

### Hangi dosyayla çalışacak
- Okuyacağı (değiştirmeyecek): `stage2_gelismis_cozum/config/rules.py`,
  `stage2_gelismis_cozum/src/time_utils.py`,
  `stage2_gelismis_cozum/src/checker.py`,
  `stage2_gelismis_cozum/docs/is_kurallari_spec.md`,
  `stage2_gelismis_cozum/outputs/Talep-tahmini.xlsx`
- Yeni yazacağı: `stage2_gelismis_cozum/src/optimize.py`

### Adım adım TAM SÜREÇ

1. `git checkout -b optimizasyon-motoru` — kendi dalını oluştur.
2. Antigravity'yi aç, `stage2_gelismis_cozum` klasörünü proje olarak seç.
3. `docs/is_kurallari_spec.md` dosyasını oku (10 dakika ayır, atlamadan
   oku — özellikle maliyet formülü, SLA cezası, elleçleme ve tır
   kapasitesi bölümleri).
4. `antigravity_promptlari.md` dosyasındaki **PROMPT 2**'yi Antigravity'ye
   yapıştır. Bu, sadece İstanbul-Yalova arasında küçük bir deneme yaptırır.
5. Antigravity kod yazıp bitirince, terminalde şunu çalıştır:
   ```bash
   python -c "
   import sys; sys.path.insert(0,'src'); sys.path.insert(0,'config')
   from checker import run_all_checks
   # (Antigravity'nin ürettiği küçük planı ve ilgili verileri yükleyip
   #  run_all_checks çağıracak kod - Antigravity bunu senin için de yazabilir,
   #  'checker ile test eden bir script de yaz' diye ekle isteğe)
   "
   ```
   Ya da daha basiti: Antigravity'ye "bu küçük planı checker.py ile test
   et ve sonucu ekrana yazdır" diye ek talimat ver.
6. Sonuç **PASS** değilse, hata mesajlarını (HATA satırlarını) Antigravity'ye
   geri yapıştır, "bunları düzelt" de. PASS alana kadar 5-6 adımlarını tekrarla.
7. PASS aldıktan sonra: `git add -A && git commit -m "optimize.py kucuk prototip - checker PASS"`
   sonra `git push origin optimizasyon-motoru`. **Bu noktada bana veya
   kaptana haber ver** — Kişi 2 senin bu küçük prototipini bekliyor, artık başlayabilir.
8. Şimdi **PROMPT 3**'ü Antigravity'ye yapıştır — bu, aynı mantığı 18
   merkezin, 289 rotanın, 7 günün TAMAMINA büyütür.
9. Antigravity süreyi ölçüp sana raporlayacak — çok yavaşsa (birkaç
   dakikadan uzun sürüyorsa) bana bildir, birlikte bakarız.
10. Tam ölçek çıktı üretilince yine checker.py ile test et, HATA sayısı
    sıfıra inene kadar Antigravity'ye "düzelt" demeye devam et.
11. Sıfır hataya ulaşınca: `outputs/Tasima-plani.xlsx` dosyasının var
    olduğunu, açılıp gözle kontrol edildiğini doğrula (Excel'de aç, birkaç
    satıra bak, mantıklı görünüyor mu).
12. Toplam maliyet ve toplam SLA cezası rakamlarını not al (Antigravity'den
    yazdırmasını iste) — bu bizim final skorumuz olacak, Kişi 3 sunumda kullanacak.
13. `git add -A && git commit -m "optimize.py tam olcek - checker PASS, maliyet X TL"`
    sonra `git push origin optimizasyon-motoru`.
14. GitHub'da bu daldan `main`'e bir **Pull Request** aç, kaptana haber ver.

### Bitti sayılma kriteri
`checker.py` tam ölçek plan için **PASS** veriyor, sıfır kısıt ihlali,
`Tasima-plani.xlsx` şablonla birebir aynı formatta, toplam maliyet
rakamı elde edilmiş.

---

## 3. KİŞİ 2 — Test, Entegrasyon ve Sağlamlaştırma

### Ne yapacak (özet)
Kişi 1'in ürettiği optimizasyon motorunu daha da sıkı test edecek,
eksik kalan kuralları `checker.py`'ye ekleyecek, ve tüm sistemi (veri
okuma + tahmin + optimizasyon + kontrol) TEK KOMUTLA çalışan bir
"orkestra" programı yazacak.

### Hangi araçla
Aynı şekilde kendi bilgisayarında Antigravity + Python/pytest.

### Hangi dosyayla çalışacak
- Değiştirmeyecek (sadece okuyup anlayacak): `src/time_utils.py`,
  `src/data_loader.py`, `src/forecast.py`
- Genişleteceği: `src/checker.py`, `tests/` klasöründeki tüm dosyalar
- Yeni yazacağı: `src/pipeline.py`

### Adım adım TAM SÜREÇ

1. **BEKLE** — Kişi 1 küçük prototipini (Bölüm 2, adım 7) bitirip sana
   haber verene kadar bu görevi başlatma. Bu süre zarfında `docs/is_kurallari_spec.md`
   ve mevcut `src/checker.py` dosyasını baştan sona oku, nasıl çalıştığını anla.
2. Kişi 1 haber verince: `git fetch origin` ve
   `git checkout optimizasyon-motoru` ile onun dalındaki küçük prototipi
   kendi bilgisayarına çek, incele.
3. `git checkout -b test-entegrasyon` — kendi dalını oluştur (ana `main`
   üzerinden, Kişi 1'in dalı üzerinden değil).
4. Antigravity'ye şunu yaptır: "src/checker.py dosyasındaki her fonksiyonu
   (check_id_formats, check_talep_traceability, check_tir_capacity,
   check_ellecleme_capacity, check_sla_penalty, check_cost) tek tek incele.
   Her biri için EK bir kenar durum testi (edge case) yaz: örneğin gece
   yarısını TAM 00:00'da aşan bir elleçleme, SLA süresinin TAM sınırında
   biten bir teslimat, bir talebin 3 farklı araca bölündüğü durum
   (D00001-1, D00001-2, D00001-3). tests/test_checker.py dosyasına ekle."
5. Bu yeni testleri çalıştır: `python -m pytest tests/test_checker.py -v`
   hepsi PASS olmalı.
6. Kişi 1 tam ölçek çıktıyı bitirip (Bölüm 2, adım 14) haber verince:
   `git fetch origin` ile onun güncel dalını çek.
7. Antigravity'ye şunu yaptır: "src/pipeline.py adında yeni bir dosya
   yaz. Bu dosya sırasıyla: data_loader.load_all() -> forecast modülünü
   çağırıp Talep-tahmini.xlsx üretir -> optimize modülünü çağırıp
   Tasima-plani.xlsx üretir -> checker.run_all_checks() ile ikisini de
   doğrular -> PASS/FAIL sonucunu ve toplam maliyeti ekrana yazdırır.
   Tek komutla (`python src/pipeline.py`) baştan sona çalışmalı."
8. Bunu çalıştır, süresini ölç, sonucu kaydet.
9. `git add -A && git commit -m "checker genisletildi + pipeline.py eklendi"`
   `git push origin test-entegrasyon`, Pull Request aç.

### Bitti sayılma kriteri
`python src/pipeline.py` tek komutla baştan sona çalışıp iki dosyayı da
üretiyor ve **PASS** raporluyor. En az 5 yeni kenar durum testi eklenmiş
ve hepsi geçiyor.

---

## 4. KİŞİ 3 — Tahmin İyileştirme + Teslim Paketi + Sunum

### Ne yapacak (özet)
Mevcut tahmin modelinin doğruluğunu artırmaya çalışacak (kanıtlanmadan
hiçbir değişiklik kabul edilmeyecek), ve takımın GitHub/sunum/jüri
hazırlığını toparlayacak.

### Hangi araçla
Antigravity (kod tarafı için) + Word/PowerPoint (sunum için) + GitHub
web arayüzü (README düzenlemek için).

### Hangi dosyayla çalışacak
- Genişleteceği: `src/forecast.py`
- Güncelleyeceği: `README.md` (kök ve stage2 içindeki), `docs/veri_denetim_raporu.md` (gerekirse)
- Yeni yazacağı: sunum dosyası (ayrı, repo dışında tutulabilir)

### Adım adım TAM SÜREÇ

1. **HEMEN BAŞLA**, kimseyi bekleme.
2. `git checkout -b tahmin-sunum` — kendi dalını oluştur.
3. Antigravity'ye şunu yaptır: "src/forecast.py içindeki backtest_wape
   fonksiyonunu kullanarak, n parametresini (geçmiş gözlem penceresi)
   6'dan 24'e kadar 2'şer artırarak dene, HER değeri en az 3 farklı
   test haftasında (örnek: 1-7 Haziran, 8-14 Haziran, 15-21 Haziran)
   çalıştır, sonuçları bir tabloda göster. En istikrarlı (üç haftada da
   iyi performans gösteren) n değerini öner."
4. Eğer daha iyi bir n bulunursa, `forecast.py`'deki varsayılan n
   değerini güncelle VE bunu neden yaptığını bir yorum satırıyla açıkla.
   Daha iyi bulunamazsa mevcut n=8 değeri kalsın, bunu da not et
   ("denedik, n=8 en iyisi çıktı" diye).
5. `python -m pytest tests/ -v` çalıştırıp hiçbir testin bozulmadığından emin ol.
6. Kök dizindeki `README.md`'yi güncelle: proje özeti, iki aşamalı yapı,
   GitHub repo linki, takım bilgisi net şekilde yazılı olsun.
7. Kişi 1 ve Kişi 2'nin işleri bitince (toplam maliyet, SLA cezası, WAPE
   rakamları elinde olunca) bu rakamları `stage2_gelismis_cozum/README.md`'ye işle.
8. Sunum için ayrı bir belgede şunları hazırla: problem tanımı, çözüm
   mimarisi (5 modül: time_utils, data_loader, forecast, optimize, checker),
   neden bu yöntemleri seçtiniz (greedy+lokal arama, P×E tahmin modeli),
   backtest sonuçları, jüri sorularına hazır cevaplar (örn. "neden exact
   optimizasyon değil de greedy?" -> "hesaplama süresi kısıtı ve 289
   güzergahlık ölçek nedeniyle, ama checker.py ile her zaman kural
   uyumluluğunu garanti ediyoruz").
9. `git add -A && git commit -m "forecast iyilestirme + README + sunum"`
   `git push origin tahmin-sunum`, Pull Request aç.

### Bitti sayılma kriteri
Backtest karşılaştırması yapılmış ve sonuç belgelenmiş (iyileşme olsun
olmasın), README güncel ve gerçek rakamları içeriyor, sunum taslağı hazır.

---

## 5. Kaptan (Siz) İçin Kontrol Listesi

- [ ] Prompt 1'i (repo temizliği) çalıştırıp `main`'e push ettiniz mi?
- [ ] Üç kişiye de bu dosyayı ve `antigravity_promptlari.md`'yi gönderdiniz mi?
- [ ] Kişi 1'in küçük prototipi bitince Kişi 2'ye haber verdiniz mi?
- [ ] Üç dal da (`optimizasyon-motoru`, `test-entegrasyon`, `tahmin-sunum`)
      açılan Pull Request'leri sırayla `main`'e birleştirdiniz mi?
- [ ] Birleştirmeden sonra `main` dalında yeniden `pytest tests/ -v`
      çalıştırıp her şeyin hâlâ yeşil olduğunu doğruladınız mı?
- [ ] Son teslim dosyalarını (`Talep-tahmini.xlsx`, `Tasima-plani.xlsx`,
      kaynak kod) yarışma formatına göre paketlediniz mi?

# Antigravity İçin Promptlar — LoadIQ Gelişmiş Çözüm Aşaması

Bu dosyadaki promptları **sırayla, birini bitirip sonucu gördükten sonra
diğerini** Antigravity'ye yapıştırın. Her promptun sonunda "Doğrulama"
notu var — Antigravity'nin çıktısını o kritere göre kontrol edin.

Proje yolu: `C:\Users\hp\LoadlQ\LoadIQ-LojistikOptimizasyonTeknofest26`

---

## PROMPT 1 — Repo Yeniden Yapılanması (Arşivleme + Temiz Zemin)

```
Bağlam: Bu proje TEKNOFEST 2026 Hepsiburada Lojistik Yarışması için. Takım
NASİP. Şu anda repo'da İKİ farklı aşamanın dosyaları karışık halde duruyor:

1) BİRİNCİ AŞAMA (Temel İşlevli Çözüm) - bizi yarı finale çıkaran eski
   çözüm. Dosyalar: Desi_talep (1).xlsx, Kiralık_Araçlar.xlsx,
   Koordinatlar v2 (1).xlsx, Araç_Kapasite_Maliyet.xlsx, analyze_deep.py,
   faq_text.txt, mevcut src/forecast.py, src/optimize.py, src/utils.py,
   src/validate_format.py, tests/test_coverage.py, tests/test_optimality.py,
   outputs/Arac_Planlama.xlsx, outputs/Tahminlenen_Talep.xlsx, data/processed/panel.csv.

2) İKİNCİ AŞAMA (Gelişmiş Çözüm) - yeni, aktif geliştirdiğimiz aşama.
   Bunun kaynak kodu "LoadIQ_kaynak_kodlar.zip" (veya "_zip_extracted"
   klasörü) içinde geldi - bu klasörde config/, data/raw/, src/, tests/,
   outputs/, README.md, requirements.txt, .gitignore var.

GÖREV: Repoyu şu şekilde yeniden düzenle (dosyaları TAŞI, silme, hiçbir
içeriği değiştirme):

a) Kök dizinde "stage1_temel_cozum/" klasörü oluştur. Yukarıda listelenen
   TÜM birinci aşama dosyalarını (data/raw'daki eski 4 excel, analyze_deep.py,
   faq_text.txt, eski src/*.py, eski tests/*.py, eski outputs/*.xlsx,
   data/processed/panel.csv, eski README.md varsa) bu klasöre taşı.
   Mevcut kök README.md'yi de "stage1_temel_cozum/README.md" olarak taşı
   (bu birinci aşamanın orijinal dokümantasyonu, kaybolmasın).

b) Kök dizinde "stage2_gelismis_cozum/" klasörü oluştur. "_zip_extracted"
   (veya zip'in açıldığı) klasördeki TÜM içeriği (config/, data/, src/,
   tests/, outputs/, README.md, requirements.txt, .gitignore, ve varsa
   is_kurallari_spec.md, veri_denetim_raporu.md, sistem_tasarimi_ve_uygulama_plani.md)
   bu klasöre taşı.

c) Kök dizine YENİ bir üst-düzey README.md yaz: Projenin TEKNOFEST 2026
   yarışması olduğunu, iki aşamalı ilerlediğini, stage1'in tamamlandığını
   (yarı final), stage2'nin aktif geliştirildiğini, hangi klasörde neyin
   olduğunu 3-4 cümleyle özetle. Detaylar için stage2_gelismis_cozum/README.md'ye
   yönlendir.

d) Kök dizinde tek bir .gitignore olsun (stage2 içindeki .gitignore'un
   içeriğini kullan, __pycache__, .venv, data/processed, .pytest_cache
   içersin).

e) İşlem bitince: hem stage1_temel_cozum/ hem stage2_gelismis_cozum/
   klasörlerinin içeriğini `ls -R` (veya Windows'ta `tree /F`) ile listele,
   bana göster. Hiçbir dosya kaybolmamış olmalı - taşımadan önceki ve
   sonraki toplam dosya sayısını karşılaştır.

ÖNEMLİ: Hiçbir python dosyasının İÇERİĞİNİ değiştirme, sadece konumunu
taşı. stage2_gelismis_cozum/src/ içindeki dosyalar (time_utils.py,
data_loader.py, forecast.py, checker.py) zaten test edilmiş ve doğrulanmış
durumda - onlara dokunma, sadece taşı.
```

**Doğrulama:** Antigravity işlemi bitirdikten sonra
`cd stage2_gelismis_cozum && python -m pytest tests/ -v` çalıştırıp 14+7=21
testin de geçtiğini görmelisiniz (taşıma sırasında bir şey bozulmadıysa
hepsi PASS verir). Geçmezse Antigravity'ye hatayı yapıştırıp düzeltmesini isteyin.

---

## PROMPT 2 — optimize.py: Küçük Ölçekli Prototip

```
Bağlam: stage2_gelismis_cozum/ klasöründe çalışıyoruz. Elimizde hazır ve
test edilmiş 4 modül var: config/rules.py (sabit iş kuralları),
src/time_utils.py (dakika bazlı süre yuvarlama - ceil mantığı),
src/data_loader.py (8 excel dosyasını okuyup doğrulayan katman),
src/checker.py (üretilen planı bağımsız doğrulayan "hakem" modülü - BUNU
DEĞİŞTİRME, optimize.py'nin doğruluğunu bununla test edeceğiz).

docs/is_kurallari_spec.md dosyasını oku - TÜM iş kuralları orada. Özellikle:
- Maliyet formülü: (Saatlik Kira x Kullanım Süresi) + (Mesafe x Km Maliyeti)
- Kiralık araçlar: her gün zorunlu çıkar, dönmez, rotasından sapamaz
- Spot araçlar: sınırsız sefer, milk-run yapabilir, boş dönüş ZORUNLU DEĞİL
  (dönmüyorsa o bacağı hiç maliyetlendirme)
- SLA cezası: Geciken Desi x Gecikme Saati(yukarı yuvarlı) x 0,4 TL
- Elleçleme: desi x 0.01 dk, gece yarısını aşarsa oransal bölünür
  (time_utils.split_handling_across_midnight kullan)
- Tır kapasitesi: sadece "Tır" tipini kapsar, TM bazlı günlük

GÖREV: src/optimize.py dosyasını yaz. Ama TAM ÖLÇEKTE DEĞİL - önce küçük
bir kanıt (proof of concept) istiyorum:

1. Sadece 2 transfer merkezi (İstanbul, Yalova) ve tek yön (İstanbul->Yalova)
   için, data/raw/Kiralik_Araclar.xlsx'teki zorunlu kiralık araçları ata.
2. Bu iki merkez arası, outputs/Talep-tahmini.xlsx'teki gerçek tahmin
   değerlerini oku, kiralık kapasiteyi aşan kısmı EN UCUZ spot araç
   kombinasyonuyla kapat (basit greedy: kapasitesi en verimli/ucuz olanı
   önce doldur).
3. config/rules.py'deki TIR_SPOT_YASAK_TM ve TIR_TAMAMEN_YASAK_TM
   listelerine uy.
4. Çıktıyı data/raw/Tasima_Plani_Sablon.xlsx ile BİREBİR AYNI kolon
   isimleriyle üret (küçük bir DataFrame, sadece bu 2 merkez için).
5. Ürettiğin küçük planı src/checker.py'deki run_all_checks() fonksiyonuna
   ver, sonucu bana göster. HATA çıkarsa (PASS almadan) bitirme, önce
   hataları düzelt.

Bu ilk versiyon sadece kanıt amaçlı - kod temiz ve fonksiyon bazlı olsun
ki sonraki adımda tüm 289 güzergaha ölçekleyeceğiz. Ölçeklendirmeyi
şimdi yapma, sadece mimariyi doğru kur.
```

**Doğrulama:** Antigravity'nin ürettiği küçük plan `checker.py`'den **PASS**
almalı. PASS almadan bir sonraki adıma geçmeyin - bu, tüm sistemin
temelini kanıtlıyor.

---

## PROMPT 3 — optimize.py: Tam Ölçek + Uçtan Uca Doğrulama

```
Önceki adımda 2 transfer merkezi için prototip optimize.py'yi yazdık ve
checker.py'den PASS aldı. Şimdi bunu TÜM 18 transfer merkezi, 289 aktif
güzergah ve 29 Haziran 09:00 - 5 Temmuz 17:00 penceresine ölçekle.

GÖREV:
1. optimize.py'yi tüm outputs/Talep-tahmini.xlsx'i (4046 satır) işleyecek
   şekilde genişlet. Aynı mantık (kiralık önce, sonra en ucuz spot),
   sadece artık tüm güzergahlar için döngü.
2. Performansı ölç - ne kadar sürüyor? Çok yavaşsa (birkaç dakikayı
   aşıyorsa) bana söyle, birlikte optimize ederiz.
3. Çıktıyı outputs/Tasima-plani.xlsx olarak kaydet (Tasima_Plani_Sablon.xlsx
   ile birebir aynı format).
4. checker.py'nin run_all_checks() fonksiyonunu tam çıktı üzerinde çalıştır.
   Sonucu (PASS/FAIL, kaç hata, kaç uyarı) bana tam olarak göster.
5. Eğer HATA varsa, hangi kategoriden (ID_FORMAT / IZLENEBILIRLIK /
   TIR_KAPASITESI / ELLECLEME_KAPASITESI / SLA_CEZASI / MALIYET) kaç
   tane olduğunu say ve düzelt. Sıfır hataya inene kadar bu döngüyü tekrarla.
6. Son olarak toplam maliyeti (kiralık + spot) ve toplam SLA cezasını
   yazdır - bu bizim "skorumuz" olacak.

ÖNEMLİ: Format ve kısıt ihlali sıfır olmadan bu görevi bitmiş sayma.
Maliyeti düşürmeye çalışırken kuralları bozma - önce PASS, sonra optimizasyon.
```

**Doğrulama:** `checker.py` **PASS** vermeli, toplam maliyet + SLA cezası
raporlanmalı. Bu noktada elinizde teslime hazır iki dosya olacak:
`Talep-tahmini.xlsx` ve `Tasima-plani.xlsx`.

---

## Genel Kurallar (her promptla birlikte hatırlatın gerekirse)

- Antigravity'nin ürettiği HER kod değişikliğinden sonra `pytest tests/ -v`
  çalıştırılmalı, kırmızı test varken ilerlenmemeli.
- `time_utils.py`, `data_loader.py`, `checker.py` dosyaları zaten test
  edilmiş — Antigravity bunları "iyileştirmek" için değiştirmeye
  kalkışırsa (bazı ajanlar bunu yapar), izin vermeyin, sadece `optimize.py`
  ve entegrasyon kodu yeni yazılsın.
- Herhangi bir belirsizlik olursa (örn. bir kural nasıl yorumlanmalı),
  Antigravity'nin varsayım yapıp devam etmesindense, size sorup
  `docs/is_kurallari_spec.md`'ye bakmasını isteyin.

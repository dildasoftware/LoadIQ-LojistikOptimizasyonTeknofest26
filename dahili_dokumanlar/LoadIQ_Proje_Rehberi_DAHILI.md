# LoadIQ — Proje Rehberi (DAHİLİ)

### Sıfırdan Her Şeyi Anlatan Kapsamlı İç Referans Dokümanı

> **Bu belge takıma özeldir; jüri teslim paketine dâhil değildir.**
> Amacı üç kişiye aynı anda hitap etmektir:
> 1. **Hiç bilmeyen biri** — projeyi baştan sona, kavramlarıyla birlikte anlayabilsin.
> 2. **Takım üyesi** — ne yaptığımızı, neyi neden seçtiğimizi, hangi sorunu nasıl çözdüğümüzü çalışabilsin.
> 3. **Bilen biri** — projeyi jüriye/dışarıya güçlü şekilde pazarlayabilsin.
>
> Bağlamı olmayan bir yapay zekâ bile yalnızca bu belgeyi okuyarak projenin tamamını kavrayabilecek şekilde yazılmıştır.

**Takım:** NASİP · **Yarışma:** TEKNOFEST 2026 — Hepsiburada Yapay Zekâ Destekli Lojistik Anahat Optimizasyonu · **Aşama:** Gelişmiş Çözüm
**Nihai sonuç:** Feasible taşıma planı, toplam maliyet **22.106.411 TL**, checker **PASS**, **32/32** test, **0** uygunluk ihlali.

---

## İçindekiler

1. [Yönetici Özeti (30 saniyede proje)](#1-yönetici-özeti)
2. [Yarışma Bağlamı](#2-yarışma-bağlamı)
3. [Problem Tanımı — Derinlemesine](#3-problem-tanımı--derinlemesine)
4. [Temel Kavramlar Sözlüğü (hiç bilmeyen için)](#4-temel-kavramlar-sözlüğü)
5. [Girdi Verileri — 8 Veri Setinin Tam Anatomisi](#5-girdi-verileri)
6. [Çözümün Büyük Resmi — Mimari](#6-çözümün-büyük-resmi--mimari)
7. [Bölüm A — Talep Tahmini (teori + teknik)](#7-bölüm-a--talep-tahmini)
8. [Bölüm B — Optimizasyon Motoru (teori + teknik)](#8-bölüm-b--optimizasyon-motoru)
9. [Bölüm C — Bağımsız Doğrulayıcı (checker felsefesi)](#9-bölüm-c--bağımsız-doğrulayıcı)
10. [Karşılaştığımız Sorunlar ve Çözümleri — Bug Günlüğü](#10-bug-günlüğü)
11. [Maliyet Yolculuğu — 29,84M'den 22,11M'ye](#11-maliyet-yolculuğu)
12. [Nihai Sonuçlar ve Metrikler](#12-nihai-sonuçlar)
13. [İş Kuralları — 20 Kuralın Tamamı](#13-iş-kuralları)
14. [Test ve Doğrulama Stratejisi](#14-test-ve-doğrulama-stratejisi)
15. [Teslim Paketi ve Dosya Yapısı](#15-teslim-paketi)
16. [Kararlar Günlüğü — Neyi Neden Seçtik](#16-kararlar-günlüğü)
17. [Pazarlama Anlatısı — Projeyi Nasıl Sunarım](#17-pazarlama-anlatısı)
18. [Sıkça Sorulacak Sorular (jüri provası)](#18-sıkça-sorulacak-sorular)

---

## 1. Yönetici Özeti

**Tek cümle:** LoadIQ, Türkiye genelindeki 18 dağıtım merkezi arasındaki günlük kargo talebini tahmin eden ve bu talebi tüm operasyonel kurallara uyarak mümkün olan en düşük maliyetle taşıyan araç planını üreten, ürettiği planı kendi kendine bağımsız doğrulayan bir karar-destek sistemidir.

**Ne yapar?** İki çıktı üretir: (1) gelecek bir haftalık **talep tahmini**, (2) bu talebi karşılayan detaylı **taşıma planı** (hangi araç, hangi merkezden, saat kaçta, nereye, ne kadar yük).

**Neyi çözer?** Elle yapıldığında imkânsıza yakın bir kombinasyon problemini — binlerce sevkiyatı, düzinelerce kısıt altında, maliyeti en aza indirerek — otomatik ve tekrarlanabilir biçimde çözer.

**Sonuç ne?** Başlangıç planı 29,84M TL'den, konsolidasyon ve feasibility düzeltmeleriyle **22,11M TL**'ye indirildi (**−%25,9**), ve plan **tam uygulanabilir** (hiçbir araç taşıyamayacağı yükü ya da zamanı ihlal etmiyor). Sonuç, planı üretenden bağımsız yazılmış bir doğrulayıcı tarafından **PASS** aldı.

**Neden güçlü?** Üç ayağı var: (a) kanıta dayalı model seçimi (istatistiksel model, makine öğrenmesini yendi), (b) "sadece-iyileştiren, doğrulayıcı-korumalı" konsolidasyon mimarisi (çözüm asla bozulmaz), (c) üreticiden bağımsız denetleyici (kör nokta bırakmaz). Ayrıca gerçek bir feasibility hatası tespit edilip düzeltildi — bu, planın diskalifiye olmasını önledi.

---

## 2. Yarışma Bağlamı

**TEKNOFEST**, Türkiye'nin en büyük havacılık, uzay ve teknoloji festivalidir; çok sayıda teknoloji yarışması içerir. **Hepsiburada**, bu kapsamda bir **Lojistik Anahat Optimizasyonu** yarışması düzenlemektedir. "Anahat" (line-haul), kargonun dağıtım merkezleri arasındaki uzun mesafeli taşımasını ifade eder — son kilometre (kapıya teslim) değil, merkezler arası ana taşıma hattıdır.

Yarışma iki aşamalıdır:

| Aşama | Ne ister | Bizim durumumuz |
|---|---|---|
| **Temel Çözüm** | Gün bazlı, basitleştirilmiş bir çözüm | ✅ Tamamlandı (yarı finale taşındı) |
| **Gelişmiş Çözüm** | Dakika çözünürlüğünde, gerçek operasyona yakın, tüm kısıtlarla | ✅ Bu belgenin konusu |

Gelişmiş aşama, temel aşamadan şu yönlerle ayrılır: **dakika bazlı** zaman (gün değil), **elleçleme süreleri** (yükleme/boşaltma zamanı), **gece yarısı kapasite sıfırlanması**, **konsolidasyon** senaryoları ve **SLA ceza** mekanizması. Yani gerçek dünyaya çok daha yakın.

---

## 3. Problem Tanımı — Derinlemesine

### 3.1 Fiziksel kurulum

Türkiye'de **18 transfer merkezi** (TM) vardır — bunlar kargonun toplandığı/dağıtıldığı depolardır (İstanbul, Yalova, Kocaeli, Eskişehir, Manisa, Tekirdağ, Balıkesir, Mersin, Şanlıurfa, Bilecik, Sivas, Isparta, Kütahya, Mardin, Erzincan, Karaman, Zonguldak, Denizli). Bu merkezler arasında **289 aktif güzergah** (rota) üzerinde kargo akışı olur. Bir güzergah "A merkezinden B merkezine" yönlü bir hattır (A→B ile B→A farklı rotalardır).

### 3.2 Talep

Kargo miktarı **desi** birimiyle ölçülür. Desi, hacimsel ağırlık birimidir: bir kolinin kapladığı hacmi ağırlığa çeviren lojistik standardıdır (kabaca 1 desi ≈ 1 kg hacimsel eşdeğer). Talep günde **iki kez** oluşur ve iki **saat dilimine** ayrılır:
- **09:00 dilimi:** sabah hazır olan yük.
- **17:00 dilimi:** öğleden sonra hazır olan yük.

Bir aracın bir yükü taşıyabilmesi için, o yükün **hazır olma zamanından önce yola çıkmaması** gerekir (09:00 yükü 09:00'dan önce, 17:00 yükü 17:00'dan önce taşınamaz). Bu, feasibility'nin kalbindeki kısıttır (bkz. Bölüm 10).

### 3.3 İki çıktı

**Çıktı 1 — Talep Tahmini:** Gelecek bir hafta için, her (rota × gün × saat dilimi) kombinasyonunda beklenen desi miktarı. Bu, planlamanın girdisidir: ne kadar yük geleceğini bilmeden araç planlayamazsınız.

**Çıktı 2 — Taşıma Planı:** Tahmin edilen (veya verilen) talebi karşılayan araç atamaları. Her satır bir aracın bir bacağını (leg) tanımlar: Araç ID, çıkış TM, varış TM, çıkış tarih/saati, taşınan desi, maliyet, SLA cezası.

### 3.4 Araç türleri: Kiralık vs Spot

İki tür araç vardır:
- **Kiralık (sözleşmeli) araçlar:** Önceden anlaşılmış sabit filodur. Kullanılsın kullanılmasın maliyeti (büyük ölçüde) baştan taahhüt edilmiştir; dolayısıyla bunları **boş bırakmak israftır** — mümkün olduğunca doldurmak gerekir. Sabit hatlara atanırlar.
- **Spot araçlar:** İhtiyaç oldukça çağrılan esnek araçlardır. Her spot araç bir maliyet doğurur; yalnızca **fayda sağladığında** (getirdiği tasarruf maliyetini aştığında) çağrılmalıdır.

### 3.5 Kısıtlar (kuralların özeti)

1. **Tır/araç kapasitesi:** Her araç türünün taşıyabileceği maksimum desi vardır; aşılamaz.
2. **Elleçleme kapasitesi:** Her TM'nin birim zamanda yükleyip boşaltabileceği desi sınırlıdır (yükleme/boşaltma bir zaman ve kapasite tüketir). Gece yarısı bu kapasite sıfırlanır (yeni güne yeniden başlar).
3. **Çıkış-hazırlık kısıtı:** Araç, yükün hazır olma zamanından önce çıkamaz.
4. **SLA (teslim süresi taahhüdü):** Yük belirli bir sürede varmalıdır; geç kalırsa **ceza** doğar. Ceza formülü: `geciken desi × ⌈gecikme (saat)⌉ × 0,4 TL` (⌈⌉ = yukarı yuvarlama).
5. **Maliyet:** Toplam maliyet = tüm araçların taşıma maliyeti + tüm SLA cezaları. **Hedef: bunu minimize etmek.**

### 3.6 Neden zor bir problem?

Bu bir **kombinatoryal optimizasyon** problemidir. Binlerce sevkiyatı, düzinelerce merkezi, iki araç tipini, zaman pencerelerini ve kapasiteleri aynı anda dengelemek gerekir. Olası plan sayısı astronomiktir; en iyiyi garantili bulmak (kesin çözüm) pratikte imkânsıza yakındır (problem sınıfı NP-zordur). Bu yüzden **akıllı sezgisel (heuristic)** yöntemler kullanırız — makul sürede çok iyi (optimuma yakın) bir çözüm üretirler.

---

## 4. Temel Kavramlar Sözlüğü

Projede geçen her terimi hiç bilmeyen biri için tanımlıyoruz:

| Terim | Anlamı |
|---|---|
| **Desi** | Hacimsel ağırlık birimi; kargonun büyüklüğünü ölçer. |
| **Transfer Merkezi (TM)** | Kargonun toplandığı/dağıtıldığı depo. Toplam 18 adet. |
| **Rota / Güzergah** | İki TM arasındaki yönlü hat (A→B). Toplam 289 aktif. |
| **Anahat (line-haul)** | Merkezler arası uzun mesafe taşıma (son kilometre değil). |
| **Saat dilimi** | Talebin oluştuğu zaman: 09:00 veya 17:00. |
| **Kiralık araç** | Sabit sözleşmeli filo; boş kalması israf. |
| **Spot araç** | İhtiyaca göre çağrılan esnek araç; her çağrı maliyetli. |
| **Elleçleme** | Yükleme/boşaltma işlemi; zaman ve kapasite tüketir. |
| **SLA** | Service Level Agreement — teslim süresi taahhüdü; ihlali ceza. |
| **Feasibility (uygunluk)** | Planın gerçekte uygulanabilir olması (hiçbir kural ihlali yok). |
| **Konsolidasyon** | Az dolu araçları/seferleri birleştirerek maliyet düşürme. |
| **Milk-run** | Bir aracın tek çıkışta birden fazla varışa uğraması (A→B→C). |
| **WAPE** | Weighted Absolute Percentage Error — tahmin hata metriği. |
| **Backtest** | Modeli geçmiş veriyle sınama (geleceği bildiğimizi varsaymadan). |
| **Leakage (sızıntı)** | Modelin, bilmemesi gereken gelecek bilgisini kullanması hatası. |
| **Greedy (açgözlü)** | Her adımda o an en iyi görünen seçimi yapan sezgisel yöntem. |
| **Heuristic (sezgisel)** | Optimumu garanti etmeyen ama hızlı ve çok iyi çözen yöntem. |
| **Checker** | Planı bağımsız denetleyen doğrulayıcı modül (auto-grader). |
| **P×E** | Talep = Sevkiyat olasılığı × koşullu beklenen desi modeli. |
| **Leg (bacak)** | Bir aracın tek bir çıkış-varış hareketi (plandaki bir satır). |

---

## 5. Girdi Verileri

Sistem, yarışmanın verdiği **8 resmi Excel dosyasını** (`data/raw/`) girdi alır. Bunlar asla değiştirilmez (ham veri dokunulmazdır):

| Dosya | İçerik | Rolü |
|---|---|---|
| `Talep_Verisi.xlsx` | Geçmiş talep kayıtları (rota × tarih × saat × desi) | Tahmin modelinin eğitim/geçmiş verisi |
| `Mesafe_Sure_Matrisi.xlsx` | TM'ler arası mesafe ve süre | Rota süresi, SLA ve maliyet hesabı |
| `Tir_Kapasitesi.xlsx` | Her TM/araç için kapasite limitleri | Kapasite kısıtı |
| `Ellecleme_Kapasitesi.xlsx` | Her TM'nin yükleme/boşaltma kapasitesi | Elleçleme kısıtı |
| `Kiralik_Araclar.xlsx` | Sözleşmeli filo listesi ve özellikleri | Faz 1 ön-ataması |
| `Arac_Maliyet_Tablosu.xlsx` | Araç türü başına maliyet parametreleri | Maliyet hesabı |
| `Talep_Tahmini_Sablon.xlsx` | Talep tahmini çıktı formatı | Çıktı şablonu |
| `Tasima_Plani_Sablon.xlsx` | Taşıma planı çıktı formatı | Çıktı şablonu |

**Veri denetimi:** Başlarken bu dosyaları bir "veri denetim" sürecinden geçirdik (`docs/veri_denetim_raporu.md`). Tutarsızlıklar (ör. bir TM listesinin dosyalar arası farklılığı, "Kocaeli" gibi özel durumlar) tespit edilip `data_loader.py` içinde açıkça ele alındı. **İlke:** Veriye körü körüne güvenme; her varsayımı doğrula.

---

## 6. Çözümün Büyük Resmi — Mimari

Sistem, her biri tek bir işten sorumlu, birbirine net arayüzlerle bağlı modüllerden oluşur (tek sorumluluk ilkesi):

```
        data/raw/*.xlsx  (8 resmi veri seti — dokunulmaz)
                │
                ▼
         data_loader.py         → okur, normalize eder, DOĞRULAR
                │
      ┌──────────┴───────────┐
      ▼                      ▼
  forecast.py            optimize.py
 (P×E tahmini)      (2 fazlı greedy + konsolidasyon)
      │                      │
      ▼                      ▼
 Talep-tahmini.xlsx    Tasima-plani.xlsx
                             │
                             ▼
                        checker.py           → BAĞIMSIZ doğrular (12 kontrol)
                             │
                             ▼
                    PASS/FAIL + Maliyet
       (tümünü pipeline.py uçtan uca çalıştırır)
```

Yardımcı modüller: `time_utils.py` (dakika bazlı zaman çekirdeği), `forecast_ml.py` (ML karşılaştırma), `run_backtest.py` (tahmin doğruluğu ölçümü), `analyze_solution.py` (çözüm analizi), `config/rules.py` (tüm sabit kurallar tek yerde).

**Neden bu ayrım?** Her modül bağımsız test edilebilir, değiştirilebilir ve anlaşılabilir. En kritik tasarım kararı: **planı üreten (`optimize.py`) ile doğrulayan (`checker.py`) ayrıdır** — böylece üreticinin hataları denetleyiciye sızmaz.

---

## 7. Bölüm A — Talep Tahmini

### 7.1 Sezgi: neden tahmin gerekir?

Araç planlamak için gelecekte ne kadar yük geleceğini bilmek gerekir. Elimizde geçmiş talep var; bundan geleceği kestirmeliyiz. Ama talep düzensizdir: bazı rota-gün-saat kombinasyonlarında hiç yük yoktur (sıfır), bazılarında yüksektir. Bu "**sıfır-şişkin**" (zero-inflated) yapı, naif ortalamaların yanıltıcı olmasına yol açabilir.

### 7.2 Modelimiz: P×E

Talebi iki bileşenin çarpımı olarak modelledik:

```
Beklenen desi  =  P(sevkiyat olur)  ×  E[desi | sevkiyat olduysa]
                  ─────────────────    ────────────────────────────
                  "Ne sıklıkla yük        "Yük geldiğinde
                   geliyor?"               ortalama ne kadar?"
```

- **P (olasılık):** O rota-gün-saat kombinasyonunda geçmişte kaç kez sevkiyat oldu / toplam gözlem. Örn. bir rotada 8 haftanın 6'sında yük geldiyse P = 6/8 = 0,75.
- **E (koşullu beklenti):** Yük geldiği durumlarda ortalama desi.

**Matematiksel içgörü:** P×E çarpımı, cebirsel olarak o kombinasyonun **basit ortalamasına eşittir** (sıfırlar dâhil). Yani `P×E = (yük gelen haftaların desi toplamı / toplam hafta)`. Bu neden değerli? Çünkü model, hem yorumlanabilir (iki anlamlı bileşene ayrışıyor: "sıklık" ve "büyüklük") hem de matematiksel olarak sağlam (naif ortalamanın kendisi, ama gerekçelendirilmiş biçimi). Jüriye "neden bu?" sorulduğunda, ampirik ortalamanın optimal nokta-tahmin olduğunu (kare hata altında) savunabiliriz.

### 7.3 Hiperparametre: n (kaç geçmiş hafta?)

Tahmin, son **n** haftanın aynı gün-saat dilimine bakarak yapılır. n küçükse (ör. 4) modele daha az veri girer, gürültüye duyarlıdır; n büyükse (ör. 16) eski, alakasız trendleri de içerir. **n'i süpürdük** (1'den 16'ya kadar denedik) ve 3 bağımsız test haftasında doğruluğu ölçtük. **n = 8** en iyi maliyet–doğruluk dengesini verdi; bu yüzden seçildi. Bu, keyfi değil, **deneyle gerekçelendirilmiş** bir karardır.

### 7.4 Doğruluk nasıl ölçüldü? WAPE + leakage-free backtest

- **WAPE (Weighted Absolute Percentage Error):** `Σ|gerçek − tahmin| / Σ|gerçek|`. Toplam hatanın toplam talebe oranı. Yüzde olarak yorumlanır; düşük iyidir. Klasik MAPE'nin sıfır-bölme sorununu yaşamaz, o yüzden bu metrik seçildi.
- **Leakage-free backtest:** Modeli geçmiş bir haftada test ederken, **yalnızca o haftadan önceki veriyi** kullanmasına izin verdik. Yani "geleceği bildiğini varsaymadan" sınadık. Bu, gerçekçi doğruluk verir; aksi hâlde model yapay olarak iyi görünür (sızıntı hatası).
- **Sonuç:** P×E modeli WAPE ≈ **%24,4**.

### 7.5 Neden makine öğrenmesi (LightGBM) değil?

Modern refleks "gradient boosting kullan" olurdu. Biz bunu **körü körüne yapmadık; test ettik.** Bir **LightGBM** modeli (`forecast_ml.py`) eğittik ve aynı leakage-free backtest ile karşılaştırdık:

| Model | WAPE |
|---|---|
| **P×E (istatistiksel)** | **%24,4** ✅ |
| LightGBM (ML) | %32,5 |

ML modeli **kaybetti**. Neden? Veri sıfır-şişkin ve rota-gün-saat başına gözlem az; bu rejimde basit, sağlam bir istatistiksel model, karmaşık bir öğreniciyi geçer (aşırı-öğrenme/az veri). **Karar kanıta dayalıdır.** LightGBM modelini repoda **bilerek tuttuk** — çünkü "ML denedik mi?" sorusuna "evet, denedik ve neden kazanmadığını gösterebiliyoruz" demek, metodolojik olgunluğun kanıtıdır.

### 7.6 Çıktı

`outputs/Talep-tahmini.xlsx` — 4.046 satır; her satır bir (rota × gün × saat dilimi) tahmini. Format, `Talep_Tahmini_Sablon.xlsx` ile birebir uyumludur.

---

## 8. Bölüm B — Optimizasyon Motoru

Bu, projenin kalbidir: tahmin edilen talebi minimum maliyetle araçlara dağıtmak. `optimize.py` (~1.400 satır) bunu üç katmanda yapar.

### 8.1 Neden greedy (kesin çözüm değil)?

Problem NP-zordur; binlerce sevkiyat için tüm kombinasyonları denemek imkânsızdır. Bu yüzden **iki fazlı greedy (açgözlü) sezgisel** kullanırız: her adımda o an en mantıklı kararı verir, makul sürede optimuma çok yakın bir çözüm üretir. Ardından **konsolidasyon** katmanıyla bu çözümü daha da iyileştiririz.

### 8.2 Faz 1 — Zorunlu kiralık ön-ataması

Kiralık araçlar zaten ödendiği için önce onları kullanırız. **Kritik incelik:** Kiralık filoya yalnızca **09:00 tamamlanmalı** talebi yükleriz. Neden? Çünkü kiralık araçlar sabah erken yola çıkar; 17:00 yükünü taşımaya kalkarlarsa, yük hazır olmadan çıkmış olurlar (feasibility ihlali). 17:00 yükü esnek spot araçlara bırakılır. (Bu incelik, Bölüm 10'daki feasibility bug'ının çözümüdür.)

### 8.3 Faz 2 — Fayda esaslı spot seçimi

Kalan talep için spot araçları çağırırız — ama yalnızca **fayda sağlıyorsa**. Her potansiyel spot sefer için: "Bu aracı çağırmanın maliyeti, kazandırdığı SLA cezası tasarrufundan az mı?" Evetse çağrılır. Bu sırada **elleçleme kapasitesi** ve **tır kapasitesi** kısıtları her adımda korunur — hiçbir merkez veya araç limiti aşılmaz.

Özellikle üç kritik rotada (Yalova→Tekirdağ, Yalova→Eskişehir, İstanbul→Manisa) SLA cezası neredeyse sıfırlandı — çünkü bu rotalarda gecikme cezası çok yüksekti ve hedefli spot atama en çok orada fayda sağladı.

### 8.4 Katman 3 — Konsolidasyon (sadece-iyileştiren, checker-korumalı)

Bu, projenin en zarif mimari fikridir. Greedy çözümü elde ettikten sonra iki son-işlem uygularız:

**(a) `konsolide_saat` — Saat birleştirme:** Aynı rotada, bitişik saat dilimlerinde giden az dolu iki seferi tek araçta birleştirir. **371 birleştirme** yapıldı; ~5,37M TL tasarruf.

**(b) `konsolide_milkrun` — Milk-run:** Aynı çıkıştan farklı varışlara giden düşük-dolu araçları tek bir A→B→C rotasında birleştirir (süt toplayan aracın birden çok çiftliğe uğraması gibi). Motor önce aday çiftleri tarar (630 aday bulundu), tasarrufa göre sıralar, uygulanabilir olanları uygular. **215 birleştirme** yapıldı.

**Kritik ilke — "improve-only, checker-gated":** Her konsolidasyon adımı yalnızca (1) toplam maliyeti **düşürüyorsa** ve (2) bağımsız checker'dan **geçiyorsa** kabul edilir. Aksi hâlde geri alınır. **Bu, çözümün asla bozulamayacağını matematiksel olarak garanti eder** — en kötü ihtimalle iyileşme olmaz, ama asla kötüleşmez. Bu yüzden konsolidasyonu eklemek "kaybedecek bir şey olmadan" güvenlidir.

### 8.5 Zaman modeli — `time_utils.py`

Tüm zaman hesapları **dakika bazlıdır** ve yuvarlama **yukarı** (ceil) yapılır (gerçekçi, iyimser olmayan tahmin). Gece yarısını aşan elleçleme, orantılı olarak iki güne bölünür. Bu çekirdek, 7 birim testle korunur.

### 8.6 Çıktı

`outputs/Tasima-plani.xlsx` — 3.725 satır; her satır bir aracın bir bacağı. Format `Tasima_Plani_Sablon.xlsx` ile birebir uyumlu. Maliyet, çift sayımı önlemek için her aracın ilk satırına yazılır (çoklu-bacak seferlerde tekrar edilmez).

---

## 9. Bölüm C — Bağımsız Doğrulayıcı

### 9.1 Felsefe

`checker.py`, `optimize.py`'den **bilinçli olarak bağımsız** yazılmış bir modüldür. Neden? Eğer aynı kod hem planı üretir hem de doğrularsa, üreticinin bir varsayımı yanlışsa doğrulayıcı da aynı yanlışı yapar — hatayı hiç göremezsiniz (kör nokta). Ayrı bir denetleyici, planı **sıfırdan yeniden hesaplayarak** bu kör noktayı ortadan kaldırır. Bu, bir yarışma **auto-grader**'ının (otomatik puanlayıcı) mantığını taklit eder: jüri planı nasıl değerlendirecekse, biz de kendimizi öyle değerlendiririz.

### 9.2 12 kontrol

`checker.py` şu 12 bağımsız kontrolü yapar:

1. **Format uyumu** — çıktı şablona birebir uyuyor mu?
2. **Talep karşılama** — tüm talep taşındı mı, eksik/fazla var mı?
3. **Tır kapasitesi** — hiçbir araç limitini aşmıyor mu?
4. **Araç kapasitesi** — araç türü başına kapasite doğru mu?
5. **Elleçleme kapasitesi** — hiçbir TM elleçleme limitini aşmıyor mu?
6. **Boş spot araç** — 0 desi taşıyan (ama maliyet doğuran) spot araç var mı?
7. **Kiralık filo** — kiralık atamaları sözleşmeye uygun mu?
8. **Milk-run tutarlılığı** — çok-duraklı rotaların zinciri ve maliyeti tutarlı mı?
9. **Çıkış-hazırlık uygunluğu (feasibility)** — her araç, yükün hazır olma zamanından sonra mı çıkıyor?
10. **SLA cezası doğruluğu** — ceza formülü doğru uygulanmış mı?
11. **Maliyet doğruluğu** — toplam maliyet sıfırdan yeniden hesapla eşleşiyor mu?
12. **Bütünlük/izlenebilirlik** — her sevkiyat kaynağına kadar izlenebiliyor mu?

Herhangi biri başarısız olursa checker **FAIL** verir. Nihai planımız **PASS** aldı; 0 ihlal.

### 9.3 Bağımsız çapraz doğrulama

Biz (geliştirici olarak) checker'a da körü körüne güvenmedik. SLA cezasını checker'dan tamamen ayrı bir betikle yeniden hesapladık ve iki sonucun **0,1 TL'den az** farkla eşleştiğini doğruladık. Kapasite, izlenebilirlik ve feasibility taramalarını bağımsız tekrarladık. **İlke: her katmanı bir üst katman denetler.**

---

## 10. Bug Günlüğü

Bu bölüm projenin dürüst hikâyesidir: hangi hataları yaptık, nasıl yakaladık, nasıl çözdük. **Bu bir zayıflık değil, güç göstergesidir** — çünkü her biri bağımsız doğrulama sayesinde yakalandı ve çözüldü. Jüriye "sisteminiz sağlam mı?" denildiğinde, bu hikâye en güçlü cevaptır.

### Bug 1 — Maliyet kolonu şişmesi

- **Belirti:** Toplam maliyet kolonu 49,9M TL topluyordu; gerçek ise ~29,1M idi.
- **Kök neden:** Çok-bacaklı bir sefer birden çok satıra yazılıyordu ve maliyet **her satırda tekrar** ediliyordu; toplarken çift/çok sayım oluyordu.
- **Çözüm:** Maliyet yalnızca aracın **ilk satırına** yazıldı, diğer satırlara 0. `checker.check_cost`, maliyeti sefer (leg) başına toplayacak şekilde güncellendi.
- **Ders:** Toplama mantığı, veri düzeniyle uyumlu olmalı. Bunu checker yakaladı.

### Bug 2 — Boş spot araç

- **Belirti:** 27 spot araç **0 desi** taşıyordu ama her biri ~449.666 TL maliyet doğuruyordu.
- **Kök neden:** Optimizasyon, fayda sağlamayan boş spot seferleri çözümde bırakıyordu.
- **Çözüm:** 0 desi taşıyan spot araçlar plandan düşürüldü (kiralıkların boş seferleri korundu — onlar zaten ödenmiş). Yeni `check_bos_spot_arac` kontrolü eklendi.
- **Etki:** Maliyet 29,84M'ye indi. **Ders:** Maliyet doğuran ama iş yapmayan hiçbir birim çözümde kalmamalı.

### Bug 3 — Feasibility ihlali (KRİTİK) ⚠️

- **Belirti:** 81 kiralık satırı, **17:00 yükünü** ~12:44 gibi bir saatte, yani **yük hazır olmadan** sevk ediyordu. Bu, talebin **~%11,6'sını (767 bin desi)** etkiliyordu.
- **Neden kritik?** Bu plan **gerçekte uygulanamaz** (infeasible). Bir araç var olmayan yükü taşıyamaz. Böyle bir plan jüri tarafından **diskalifiye** edilebilirdi. Düşük maliyet, uygulanamıyorsa hiçbir işe yaramaz.
- **Nasıl yakalandı?** Bağımsız checker'a yeni bir kural eklenerek: `CIKIS_HAZIRLIK` — "araç, yükün hazır olma zamanından önce çıkamaz". Bu kural devreye girer girmez ihlaller ortaya çıktı.
- **Çözüm yolculuğu:** İki seçenek vardı: (a) ihlalli sefer­leri 17:00'a ertelemek → maliyet 25,42M; (b) kiralığı **yalnızca 09:00 yüküne** atayıp 17:00 yükünü spot'a bırakmak → maliyet **22,11M**. (b) hem feasible hem daha ucuzdu; onu benimsedik.
- **İncelik:** Feasible 22,11M çözüm, infeasible 21,74M çözümden yalnızca **~360 bin TL** daha pahalı. Yani uygulanabilirliği neredeyse bedavaya elde ettik — mükemmel bir takas.
- **Ders:** Doğru kısıtı modellemezsen, optimizatör onu "kullanır" (yükü hazır olmadan taşıyarak sahte tasarruf yaratır). Feasibility, maliyetten önce gelir.

### Bug 4 — Yanıltıcı çalıştırma betiği

- **Belirti:** Eski README, jüriye `run_checker_local.py` çalıştırmasını söylüyordu; ama o betik yalnızca `generate_plan` çağırıyor, konsolidasyon ve feasibility katmanlarını **atlıyordu** → yanlış (~30M) bir plan gösteriyordu.
- **Çözüm:** README, gerçek uçtan uca akışı çalıştıran `pipeline.py`'ye yönlendirildi; yanıltıcı betik silindi.
- **Ders:** Dokümantasyon, kodun gerçek davranışıyla birebir tutarlı olmalı. Yanlış talimat, doğru koddan daha zararlı olabilir.

### Ayrıca: dokümantasyon tutarlılık denetimi

Teslim öncesi bir denetimde README'lerin **eski rakamları** taşıdığı görüldü (30,28M / 20 test / %11) — teknik rapor ve SRS ise doğru rakamları (22,11M / 32 test / %25,9) söylüyordu. Bu çelişki giderildi; tüm dokümanlar tek doğruda birleştirildi. **Ders:** Sayısal tutarlılık, güvenilirliğin ta kendisidir; bir çelişki tüm raporu şüpheli kılar.

---

## 11. Maliyet Yolculuğu

Nihai sonuca nasıl ulaştığımızın sayısal öyküsü:

```
  29,84M TL   Başlangıç planı (greedy + boş araç temizliği)
     │
     │  konsolide_saat: 371 birleştirme  (−5,76M)
     ▼
  24,08M TL   Saat konsolidasyonu sonrası
     │
     │  konsolide_milkrun: 215 birleştirme + feasibility düzeltmesi
     ▼
  22,11M TL   NİHAİ — feasible, checker PASS, 0 ihlal
```

**Toplam iyileşme: −7,73M TL (−%25,9), üstelik tam uygulanabilir.**

Her ok, checker'dan geçmiş, geri alınamaz bir iyileşmedir. Hiçbir adımda çözüm kötüleşmedi.

---

## 12. Nihai Sonuçlar

| Metrik | Değer |
|---|---|
| Toplam plan maliyeti (feasible) | **22.106.411 TL** |
| Araç maliyeti | 20.939.526 TL |
| SLA cezası | 1.166.885 TL (toplamın %5,3'ü) |
| Uygunluk (feasibility) ihlali | 0 |
| Doğrulama | checker PASS · 32/32 test |
| Toplam araç seferi | 1.697 |
| — Kiralık | 98 |
| — Spot | 1.599 |
| Taşınan toplam desi | 6.613.772 |
| Talep tahmini (satır) | 4.046 |
| Taşıma planı (satır) | 3.725 |
| Talep tahmini doğruluğu | WAPE ≈ %24,4 (P×E) |
| Başlangıca göre iyileşme | −7,73M TL (−%25,9) |

**Tekrar-üretilebilirlik:** Kaynak kod paketi temiz bir klasöre çıkarılıp sıfırdan çalıştırıldığında (bağımsız ortamda) 32/32 test geçer ve pipeline aynı 22.106.411 TL sonucu üretir — checker PASS. Yani sonuç, bizim makinemize bağlı değildir.

---

## 13. İş Kuralları

Yarışma şartnamesi, resmi Q&A ve duyurulardan **20 iş kuralı** derledik ve tek kaynakta (`config/rules.py`) topladık; tümü `docs/is_kurallari_spec.md`'de belgelidir. **20/20 uyum** sağlandı. Öne çıkanlar:

- Zaman dakika bazlı; süre yuvarlaması yukarı (ceil).
- Elleçleme kapasitesi TM başına sınırlı; gece yarısı sıfırlanır; gece yarısını aşan işlem orantılı bölünür.
- Tır/araç kapasitesi türüne göre sabit; aşılamaz.
- Çıkış-hazırlık kısıtı: araç, yük hazır olmadan çıkamaz (09:00/17:00).
- SLA cezası = geciken desi × ⌈gecikme (saat)⌉ × 0,4 TL.
- Toplam maliyet = araç maliyeti + SLA cezası; hedef minimizasyon.
- Kiralık filo sözleşmeye bağlı; spot araç ihtiyaca göre.

---

## 14. Test ve Doğrulama Stratejisi

Üç katmanlı güvence:

1. **Birim testler (32 adet):** `time_utils` (7), `data_loader` (6), `checker` (19). Her biri tek bir davranışı izole eder. `python -m pytest tests/ -v` ile çalışır.
2. **Bağımsız checker (12 kontrol):** Üretilen planı sıfırdan denetler.
3. **Manuel çapraz doğrulama:** SLA/kapasite/feasibility bağımsız betiklerle yeniden hesaplandı, checker ile <0,1 TL uyum.

**Felsefe:** "Rapora değil, çalıştırmaya güven." Her iddia kod çalıştırılarak doğrulandı.

---

## 15. Teslim Paketi

Yarışma portalına **3 zip** yüklenir:

| Slot | Dosya | İçerik |
|---|---|---|
| Talep Tahmini | `1_TALEP_TAHMINI.zip` | `TALEP TAHMİNİ.xlsx` (4.046 satır) |
| Taşıma Planı | `2_TASIMA_PLANI.zip` | `TAŞIMA PLANI.xlsx` (3.725 satır, 22,11M) |
| Kaynak Kodları | `3_KAYNAK_KOD.zip` | Tüm kod + veri + testler + dokümanlar + çalıştırma kılavuzu |

Kaynak kod paketi **kendi kendine yeterlidir**: girdi verileri, çıktılar ve testler içindedir; harici dosya/internet gerekmez. İçinde jüri için `NASIL_CALISTIRILIR.txt` hızlı kılavuzu, profesyonel `README.md`, teknik rapor, SRS ve sunum bulunur.

**Bu dahili belge (`LoadIQ_Proje_Rehberi_DAHILI.md`) teslim paketine dâhil DEĞİLDİR** — yalnızca takımındır.

---

## 16. Kararlar Günlüğü

Neyi neden seçtik (savunulabilir karar kaydı):

| Karar | Neden |
|---|---|
| P×E tahmini (ML değil) | Leakage-free backtest'te ML'i yendi (%24,4 vs %32,5). Kanıta dayalı. |
| n = 8 | 1–16 süpürmesinde en iyi maliyet–doğruluk dengesi. |
| İki fazlı greedy | NP-zor problemde makul sürede optimuma yakın çözüm. |
| Improve-only, checker-gated konsolidasyon | Çözümün asla kötüleşmemesini garanti eder. |
| Ayrı checker | Üreticinin kör noktalarını denetler; auto-grader mantığı. |
| Kiralığa yalnızca 09:00 yükü | Feasibility'yi garanti eder; 17:00 spot'a. |
| Feasible 22,11M > infeasible 21,74M | Uygulanabilirlik ~360K'ya alındı; diskalifiye riski elendi. |
| LightGBM'i repoda tutmak | "ML denedik mi?" sorusuna kanıtlı cevap; metodolojik şeffaflık. |

---

## 17. Pazarlama Anlatısı

Projeyi jüriye/dışarıya anlatırken kullanılacak çerçeve.

**Asansör konuşması (30 sn):**
> "LoadIQ, 18 dağıtım merkezi arasındaki kargo talebini tahmin edip bu talebi tüm operasyonel kurallara uyarak en düşük maliyetle taşıyan planı üreten bir karar-destek sistemidir. Başlangıç planını %26 iyileştirerek 22,1 milyon TL'ye indirdik — üstelik plan tam uygulanabilir. En güçlü yanımız: planı üreten koddan bağımsız bir doğrulayıcı yazdık; sistem kendi kendini denetliyor ve sonuç sıfır kural ihlaliyle PASS alıyor."

**Üç güçlü mesaj:**
1. **Kanıta dayalı mühendislik.** Hiçbir kararı varsayımla vermedik — ML'i test edip elediğimiz gibi, her hiperparametreyi ölçtük.
2. **Kendi kendini doğrulayan sistem.** Bağımsız checker + improve-only konsolidasyon = çözüm asla bozulmaz, kör nokta kalmaz.
3. **Dürüst ve sağlam.** Gerçek bir feasibility hatasını yakalayıp düzelttik; sonucumuz bizim makinemizde değil, herhangi bir makinede tekrar-üretilebilir.

**Zayıflık sorulursa (dürüst cevap):** "Optimizasyon greedy sezgiseldir, global optimumu garanti etmez; ama improve-only konsolidasyonla optimuma çok yaklaşıyoruz ve çözümün kalitesini bağımsız doğruluyoruz. Gelecekte OR-Tools tabanlı kesin/melez bir çözücü eklenebilir." (Ayrıca: optimize/forecast için ayrı birim test yerine bağımsız checker + entegrasyon doğrulaması kullanıldı — bilinçli bir kapsam kararıdır.)

---

## 18. Sıkça Sorulacak Sorular

**S: Talebi neden ML ile tahmin etmediniz?**
C: Ettik — LightGBM'i test ettik ve WAPE %32,5 ile P×E'nin %24,4'üne kaybetti. Veri sıfır-şişkin ve gözlem az; bu rejimde sağlam istatistiksel model kazanır. Kanıtı repoda (`forecast_ml.py`).

**S: Greedy optimumu bulmaz, nasıl güveniyorsunuz?**
C: Greedy'yi improve-only konsolidasyonla iyileştiriyoruz ve her adım bağımsız checker'dan geçiyor. Çözüm asla kötüleşmiyor; optimuma çok yakın, doğrulanmış bir sonuç elde ediyoruz.

**S: Planınız gerçekten uygulanabilir mi?**
C: Evet, kanıtlı. `CIKIS_HAZIRLIK` kuralı her aracın yük hazır olduktan sonra çıktığını denetliyor; 0 ihlal. Bir feasibility hatasını erkenden yakalayıp düzelttik.

**S: Sonuçları biz de doğrulayabilir miyiz?**
C: Evet. `3_KAYNAK_KOD.zip`'i açın, `pip install -r requirements.txt`, sonra `python -m pytest tests/` (32/32 PASS) ve `python src/pipeline.py` (checker PASS, 22.106.411 TL). Paket kendi kendine yeterli.

**S: Maliyeti daha da düşürebilir miydiniz?**
C: Infeasible bir planla 21,74M mümkündü ama uygulanamaz. Biz uygulanabilirliği ~360K'ya alıp 22,11M feasible'ı seçtik — çünkü uygulanamayan bir plan geçersizdir.

**S: Sistem başka verilerle çalışır mı?**
C: Evet; tüm kurallar `config/rules.py`'de tek kaynakta, yollar görelidir, hiçbir şey sabit-kodlanmamıştır. Yeni veri setiyle pipeline yeniden çalışır.

---

<div align="center">

**LoadIQ — Takım NASİP · TEKNOFEST 2026**
Bu belge takımın iç referansıdır. Sorular: bilbildilara77@gmail.com

</div>


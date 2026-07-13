# LoadIQ — Kanonik İş Kuralları Spesifikasyonu (Tek Doğru Kaynak)

Son güncelleme: 2026-07-13 (13.07.2026 tarihli ek duyuru dahil edildi)

> Bu doküman, şartname PDF'i + soru-cevap oturumu + 13.07.2026 tarihli ek duyurudan derlenen **tek referans** kaynaktır. Kod, bu dokümandaki kurallara göre yazılacak. Yeni bir duyuru geldiğinde önce burası güncellenecek, sonra kod değişecek — tersi değil.

## 0. Neden bu doküman var

Kurallar 3 farklı kaynaktan (ilk bilgilendirme PDF'i, Q&A PDF'i, sonradan gelen düzeltme duyuruları) parça parça geliyor ve bazı noktalarda birbirini güncelliyor (örn. tır kapasitesi, dönüş kuralları). Dağınık kaynaklardan kod yazmak hataya açık; tek kanonik doküman riski azaltır.

## 1. Kapsam ve Tarih Penceresi

- Talep tahmini: **29 Haziran 09:00 – 5 Temmuz 17:00** aralığı için üretilecek (her gün 09:00 ve 17:00 iki ayrı satır).
- Sadece kendi tahminlenen talepler optimize edilecek; jürinin gizli gerçek talebiyle karşılaştırma sadece tahmin başarısı için yapılacak.
- **Optimizasyon için zaman sınırı yok.** 5 Temmuz'da tahminlenen bir talep 7 Temmuz'da teslim edilebilir (SLA cezası oluşursa ödenir, ama "pencere dışına taşamaz" gibi bir kısıt yok).
- Geçmiş veride hiç görülmemiş TM çifti için tahmin üretilmeyecek (bkz. Veri Denetim Raporu — Kocaeli'ye varışlı 17 çift bu kapsamda hariç).

## 2. Zaman Modeli ve Yuvarlama (13.07.2026 duyurusu — KRİTİK)

- Tüm çıkış/varış saatleri **dakika cinsinden (HH:MM)** verilecek.
- **Yol süresi:** `ceil(mesafe_matrisindeki_saat × 60)` — en yakın büyük tam dakikaya yuvarlanır.
  - Örnek (duyuruda verilen): İstanbul→Yalova Tır süresi 0.92 saat = 55.2 dk → **56 dk**.
- **Elleçleme süresi:** `ceil(desi × 0.01)` dakika — en yakın büyük tam dakikaya yuvarlanır.
- Bu iki yuvarlama **ayrı ayrı** yapılır, sonra toplanır (yani önce toplayıp sonra tek seferde yuvarlamak YANLIŞ).
- Gece yarısı (00:00) sınırını aşan elleçleme işlemlerinde desi, geçen süreye **oransal** dağıtılır ve iki günün kapasitesinden buna göre düşülür (örnek: 23:30'da başlayan 10.000 desilik elleçleme → aynı gün 3.000 desi, ertesi gün 7.000 desi).
- Zaman çözünürlüğü dakikadır; araçlar günün herhangi bir dakikasında çıkabilir/elleçlenebilir (mesai kavramı yok, TM'ler 7/24 çalışır).

## 3. Araç Kuralları

### 3.1 Kiralık Araçlar (Zorunlu Filo)
- `Kiralık_Araçlar` listesindeki atamalar **her gün** sabit çalışır, talep olmasa bile çıkarılmak zorunda.
- Rotalarından **sapamazlar** (uğrama/milk-run yok), ama varış TM'sinde **konsolidasyona dahil olabilirler** (yükü bırakıp başka araçla aktarım yapılabilir).
- **Dönüş yapmazlar** (13.07.2026 duyurusuyla kesinleşti — "Kiralık araçlarda dönüş yoktur").
- Tır kapasitesi kısıtına tabidirler (tır tipindeki kiralık araçlar, TM'nin günlük tır kotasını tüketir).

### 3.2 Spot Araçlar
- Gün içinde sınırsız sefer yapabilir, çoklu durak (milk-run/uğrama) yapabilir.
- **Dönüş yapabilir, ancak zorunlu değildir.** 13.07.2026 duyurusu: *"boş spot araçları dönüş hesabına katmak zorunda değilsiniz. Boş araçları döndürmeyiniz."* → Boş dönüş leg'i modellenmeyecek/maliyetlendirilmeyecek; bir spot araç işini bitirdiği TM'de bırakılabilir.
- Minimum doluluk kısıtı **yoktur** (MVP aşamasındaki %10 kuralı bu aşamada kaldırıldı; düşük doluluk cezası yok, sadece SLA riski var).
- Aynı spot aracın aynı gün içinde farklı bir güzergaha çıkması "dönüş" sayılmaz.

### 3.3 Tır Kapasitesi Kısıtı
- Sadece "Tır" araç tipini kapsar (Kamyon/Hafif Kamyon/Kamyonet'e kapasite kısıtı yok).
- Günlük, TM bazlı, gelen+giden ayrımı yapılmaksızın toplam.
- Kiralık tırlar da bu kotayı tüketir.
- Aynı aracın aynı TM'de hareket etmeden (indirmeden) tekrar kullanılması 1 kapasite sayılır; ama **indirilip tekrar yüklenirse** (konsolidasyon/dönüş bacağı) ayrı ayrı sayılır.
- Denetim raporunda tespit edildi: Balıkesir ve Tekirdağ'da zorunlu filo kotanın tamamını tüketiyor → bu iki TM'de **spot Tır kullanılamaz**. 7 TM'de (Bilecik, Denizli, Isparta, Karaman, Kütahya, Sivas, Zonguldak) kapasite tamamen 0 → hiç Tır giremez/çıkamaz.

## 4. Maliyet Formülü

```
Toplam Araç Maliyeti = (Saatlik Kiralama Maliyeti × Kullanım Süresi) + (Kat Edilen Mesafe × Km Başı Maliyet)
```

- **Kullanım Süresi** = çıkış elleçleme + yol süresi + (varsa) bekleme süresi + varış elleçleme süresi + (spot için, dönüş yapılıyorsa) dönüş bacağının kendi süresi. Boş dönüş yapılmıyorsa bu bacak hiç hesaba girmez.
- Kiralık ve spot için saatlik/km maliyetleri farklıdır (bkz. araç maliyet tablosu, 4 araç tipi).
- Süreler dakika cinsinden hesaplanır (bkz. Bölüm 2), maliyet formülündeki "saat" cinsine çevrilirken dakika/60 kullanılır (yuvarlama sadece süre hesaplarken yapılır, maliyet formülünde tekrar yuvarlama yapılmaz).

## 5. Elleçleme Kuralları

- Süre: `ceil(desi × 0.01)` dakika.
- Kapasite: TM başına günlük, gelen+giden+konsolidasyon toplamı, 00:00'da sıfırlanır.
- Konsolidasyonda elleçleme 2 kez sayılır (indirme + tekrar yükleme); toplam kapasiteden ilgili desi kadar (x indirilen + y yüklenen) düşülür.
- Çıkış elleçlemesi, talebin tamamlanma anından sonra herhangi bir zamanda yapılabilir; yapıldığı günün kapasitesinden düşülür.
- Gece yarısını aşan işlemler oransal bölünür (Bölüm 2).

## 6. SLA Cezası

```
SLA Cezası = Geciken Desi × Gecikme Süresi (saat, yukarı yuvarlanmış) × 0,4 TL
```

- SLA başlangıcı: talebin orijinal çıkış TM'sindeki **talep tamamlanma anı** (09:00 veya 17:00).
- SLA bitişi: orijinal varış TM'sinde **elleçlemenin tamamlanma anı** (konsolidasyon dahil tüm ara adımlar bu süreye dahildir).
- SLA süresi güzergaha göre 1 veya 2 gün (24 veya 48 saat) — mesafe matrisindeki `hedef_teslim_gun` alanından.
- Gecikme saate yuvarlanır (yukarı); 2 saat 20 dk gecikme → 3 saat sayılır.
- Gönderiler bekletilebilir; "elleçleme biter bitmez yeni araca yüklenmeli" kuralı yoktur (maliyet açısından avantajlıysa bekletilebilir).

## 7. Konsolidasyon

- Serbesttir, zorunlu değildir.
- Bir araca farklı varış noktalarına gidecek yükler aynı anda yüklenebilir.
- Spot araçlar için uğrama (milk-run) mümkündür; **kiralık araçlar için mümkün değildir.**

## 8. Çıktı Formatları

### 8.1 Talep-tahmini.xlsx
- Sütunlar: Talep ID, Tarih, Talep Tamamlanma Saati (09:00/17:00), Çıkış TM, Varış TM, Tahmin Edilen Desi.
- Her (gün, güzergah, saat) kombinasyonu ayrı satır.
- Talep ID biz üretiyoruz: `D00001`, `D00002`, ...
- Çok düşük tahminler (<0.5 desi gibi) de satırdan çıkarılmaz, sunulmalı.
- Geçmişte hiç görülmemiş TM çifti için satır üretilmez.

### 8.2 Tasima-plani.xlsx
- Sütunlar (gözlemlenen şablona göre): Araç ID, Araç Tipi (Kiralık/Spot), Araç türü (Tır/Kamyon/Hafif Kamyon/Kamyonet), Çıkış TM, Varış TM, Çıkış Tarihi, Çıkış Saati (HH:MM), Varış Tarihi, Varış Saati (HH:MM), Talep ID, Taşınan Desi, Yolculuk süresi, Varış elleçleme süresi, Çıkış elleçleme süresi, SLA cezası, Toplam maliyet.
- Araç ID biz üretiyoruz: `V0001`, `V0002`, ...
- Talep bölünürse: `D00001-1`, `D00001-2` (konsolidasyonda iç içe bölünürse `D00001-1-1` şeklinde uzatılır).
- Format dışı teslimler **değerlendirmeye alınmaz** — şema burada sabitlenmiş, kod bu şemaya birebir uymalı.

## 9. Bilinen Veri Kısıtları (Denetim Raporundan)

- Kocaeli'ye varışlı 17 TM çifti: tahmin/plan üretilmez.
- Balıkesir, Tekirdağ: spot Tır kullanılamaz (zorunlu filo kotayı dolduruyor).
- Bilecik, Denizli, Isparta, Karaman, Kütahya, Sivas, Zonguldak: hiç Tır kullanılamaz.
- Tatil/anomali günleri (tahmin modelinde training havuzundan çıkarılacak): 1 Ocak, 20-21 Mart, 30 Nisan, 1 Mayıs, **27-31 Mayıs (en büyük anomali kümesi)**.

## 10. Değişiklik Günlüğü

- **2026-07-13 duyurusu ile eklenen/değişen kurallar:** dakika bazlı zaman formatı + yukarı yuvarlama (Bölüm 2), spot boş dönüşün zorunlu olmaması (Bölüm 3.2), kiralık araçlarda dönüşün kesin olarak yok sayılması (Bölüm 3.1), tahmin penceresi ve optimizasyon süre sınırı olmadığının teyidi (Bölüm 1).

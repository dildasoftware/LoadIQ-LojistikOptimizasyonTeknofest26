# LoadIQ — Sistem Brifingi ve Görev Sözleşmesi

> **Bu dosya kendi başına yeterlidir.** Herhangi bir yapay zeka sistemine
> (Antigravity, ChatGPT, Claude, Gemini, Cursor, fark etmez) bu dosyanın
> TAMAMINI yapıştırıp, sonuna "Sen [Kişi 1 / Kişi 2 / Kişi 3]'sin, SADECE
> ilgili bölümdeki görevini yap, diğer bölümlere dokunma" diye eklerseniz,
> o yapay zeka önceki konuşmaları bilmeden de tam bağlamla çalışabilir.

---

## BÖLÜM A — PROJE BAĞLAMI (herkes okumalı)

### A.1 Yarışma
Teknofest 2026, Hepsiburada'nın düzenlediği "Yapay Zeka Destekli Lojistik
Anahat Optimizasyonu" yarışması. Takım adı: NASİP. Takım birinci aşamayı
("Temel İşlevli Çözüm") geçip yarı finale kalmış durumda. Şu an ikinci ve
son aşamadayız: **"Gelişmiş Çözüm Aşaması"**.

### A.2 Çözülecek Problem
18 transfer merkezi (depo) arasında, 289 aktif güzergahta gerçekleşen
kargo taleplerini (birim: "desi") tahmin edip, bu talebi kurallara uygun
şekilde minimum maliyetle taşıyan bir plan üretmek. İki teslim çıktısı var:

1. **Talep-tahmini.xlsx** — 29 Haziran 09:00 – 5 Temmuz 17:00 arası, her
   güzergah × gün × saat dilimi (09:00/17:00) için tahmin edilen desi.
   **BU DOSYA ZATEN ÜRETİLDİ VE HAZIR** (bkz. Bölüm B.5).
2. **Tasima-plani.xlsx** — Bu talebi hangi araçla, ne zaman, hangi rotayla
   taşıyacağımızı gösteren detaylı plan. **BU DOSYA HENÜZ YOK, YAPILACAK
   İŞİN ÇOĞU BU.**

### A.3 İş Kuralları (özet — tam detay Bölüm C'de)
- Zaman dakika cinsinden, süreler her zaman **yukarı yuvarlanır** (ceil).
- Kiralık araçlar: her gün zorunlu çıkar, dönmez, rotasından sapmaz.
- Spot araçlar: sınırsız sefer, birden fazla durağa uğrayabilir, boş
  dönüş ZORUNLU DEĞİL (dönmüyorsa o bacağı hiç maliyetlendirme).
- Maliyet = (Saatlik Kira × Kullanım Süresi) + (Mesafe × Km Maliyeti).
- SLA cezası = Geciken Desi × Gecikme Saati (yukarı yuvarlı) × 0,4 TL.
- Elleçleme süresi = desi × 0,01 dk (yukarı yuvarlı); TM'nin günlük
  elleçleme kapasitesi var; gece yarısını aşan işlemler orantılı bölünür.
- Tır kapasitesi sadece "Tır" tipini kapsar, TM bazlı günlük kota var.

### A.4 Sistem Mimarisi (5 modül hazır, 1 modül eksik)

```
data/raw/*.xlsx  ->  data_loader.py  ->  forecast.py  ->  Talep-tahmini.xlsx
                          |                                      |
                          v                                      v
                   (mesafe, kapasite,                      optimize.py  ---> Tasima-plani.xlsx
                    kiralık, maliyet                             ^                  |
                    verileri)  ------------------------------->--+                  v
                                                              checker.py  ---> PASS/FAIL raporu
```

| Modül | Durum | Sorumlu (bu sözleşmede) |
|---|---|---|
| `config/rules.py` | ✅ Hazır, dokunulmayacak | — |
| `src/time_utils.py` | ✅ Hazır, test edilmiş (7 test), dokunulmayacak | — |
| `src/data_loader.py` | ✅ Hazır, test edilmiş (11 kontrol), dokunulmayacak | — |
| `src/forecast.py` | ✅ Çalışıyor, ince ayar yapılabilir | **Kişi 3** |
| `src/checker.py` | ✅ Hazır, test edilmiş (14 test), GENİŞLETİLECEK | **Kişi 2** |
| `src/optimize.py` | ❌ YOK, SIFIRDAN YAZILACAK | **Kişi 1** |
| `src/pipeline.py` | ❌ YOK, SIFIRDAN YAZILACAK | **Kişi 2** |

---

## BÖLÜM B — VERİ SÖZLÜĞÜ (herkes referans almalı)

### B.1 `data/raw/Talep_Verisi.xlsx` (girdi, ham geçmiş veri)
Kolonlar: `tarih, cikis, varis, talep_id, desi, saat`. 66.024 satır,
1 Ocak – 28 Haziran 2026. `data_loader.load_talep()` ile okunur.

### B.2 `data/raw/Mesafe_Sure_Matrisi.xlsx`
Kolonlar: `cikis, varis, mesafe_km, tir_saat, kamyon_saat, hafif_kamyon_saat, kamyonet_saat, sla_gun`.
306 satır (18×17 tüm yönlü çiftler). `sla_gun` ∈ {1, 2}.

### B.3 `data/raw/Ellecleme_Kapasitesi.xlsx`
Kolonlar: `tm, gunluk_kapasite_desi`. 18 satır.

### B.4 `data/raw/Tir_Kapasitesi.xlsx`
Kolonlar: `tm, tir_kapasitesi`. 18 satır. 7 TM'de kapasite 0 (Tır giremez):
Bilecik, Denizli, Isparta, Karaman, Kütahya, Sivas, Zonguldak.

### B.5 `data/raw/Kiralik_Araclar.xlsx`
Kolonlar: `cikis, varis, arac_sayisi, arac_turu`. 12 satır — zorunlu günlük filo.

### B.6 `data/raw/Arac_Maliyet_Tablosu.xlsx`
Kolonlar: `arac_adi, kapasite_desi, kiralik_saatlik_tl, kiralik_km_tl, spot_saatlik_tl, spot_km_tl`.
4 satır: Tır (22.400 desi), Kamyon (12.000), Hafif Kamyon (7.200), Kamyonet (5.600).

### B.7 `outputs/Talep-tahmini.xlsx` (ÜRETİLDİ, hazır girdi)
Kolonlar (şablonla birebir): `Talep ID, Tarih, Talep Tamamlama Saati,
Çıkış Transfer Merkezi, Varış Transfer Merkezi, Tahmin Edilen Desi`.
4046 satır (289 rota × 7 gün × 2 saat).

### B.8 `data/raw/Tasima_Plani_Sablon.xlsx` (HEDEF format)
Kolonlar: `Araç ID, Araç Tipi, Araç türü, Çıkış Transfer Merkezi,
Varış Transfer Merkezi, Çıkış Tarihi, Çıkış Saati, Varış Tarihi,
Varış Saati, Talep ID, Taşınan Desi, Yolculuk süresi, Varış elleçleme
süresi, Çıkış Elleçleme süresi, SLA cezası, Toplam maliyet`.
`optimize.py` bu formatta bir DataFrame üretmeli.

---

## BÖLÜM C — TAM İŞ KURALLARI

(Bu bölüm `docs/is_kurallari_spec.md` dosyasının özetidir — Kişi 1 tam
metni mutlaka okumalı.)

1. **Zaman/yuvarlama:** Yol süresi (dk) = `ceil(mesafe_matrisi_saat × 60)`.
   Elleçleme süresi (dk) = `ceil(desi × 0.01)`. İkisi AYRI yuvarlanır.
   Bu formüller `time_utils.travel_minutes()` ve `time_utils.handling_minutes()`
   fonksiyonlarında zaten yazılı — YENİDEN YAZMAYIN, import edip kullanın.

2. **Kiralık araçlar:** `Kiralik_Araclar.xlsx`'teki atamalar her gün sabit
   çalışır (talep olmasa bile). Rotalarından sapamaz (uğrama yok), ama
   varış TM'sinde konsolidasyona dahil olabilir. Dönmez. Tır kapasitesini tüketir.

3. **Spot araçlar:** Sınırsız sefer, milk-run (çoklu durak) yapabilir.
   Dönebilir ama ZORUNLU DEĞİL — dönmüyorsa o bacağın maliyeti hesaba
   katılmaz. Minimum doluluk kısıtı YOK.

4. **Tır kapasitesi:** Sadece "Tır" tipini kapsar, TM×gün bazlı, kiralık+spot
   toplamı. `config/rules.py`'deki `TIR_TAMAMEN_YASAK_TM` (7 TM, kapasite 0)
   ve `TIR_SPOT_YASAK_TM` (Balıkesir, Tekirdağ — zorunlu filo kotayı dolduruyor) listelerine uyulmalı.

5. **Maliyet formülü:**
   `Toplam Maliyet = (Saatlik Kira × Kullanım Süresi[saat]) + (Mesafe[km] × Km Maliyeti)`.
   Kullanım süresi = çıkış elleçleme + yol + (varsa bekleme) + varış elleçleme (+ dönüş bacağı varsa).

6. **Elleçleme kapasitesi:** TM başına günlük, gelen+giden+konsolidasyon
   toplamı, 00:00'da sıfırlanır. Gece yarısını aşan işlemler süreye
   oransal bölünür — `time_utils.split_handling_across_midnight()` fonksiyonunu kullanın.

7. **SLA cezası:** `Geciken Desi × Gecikme Saati(yukarı yuvarlı) × 0,4 TL`.
   Başlangıç: talebin tamamlanma anı (09:00/17:00). Bitiş: varış TM'sinde
   elleçlemenin TAMAMLANMA anı. SLA süresi = mesafe matrisindeki `sla_gun × 24` saat.

8. **ID formatları:** Talep ID `D00001` biçiminde, bölünürse `D00001-1`,
   iç içe bölünürse `D00001-1-1`. Araç ID `V0001` biçiminde.

---

## BÖLÜM D — KİŞİ 1: OPTİMİZASYON MOTORU

### D.1 Sorumluluk Alanı
`src/optimize.py` dosyasını SIFIRDAN yazmak. Bu, `Talep-tahmini.xlsx`'i
girdi alıp `Tasima-plani.xlsx` formatında bir plan üreten motor.

### D.2 ARAYÜZ SÖZLEŞMESİ (kesin — değiştirilemez)
`optimize.py` dosyası şu imzaya sahip BİR fonksiyon içermeli:

```python
def generate_plan(talep_df: pd.DataFrame, veri: dict) -> pd.DataFrame:
    """
    talep_df: outputs/Talep-tahmini.xlsx'in okunmuş hali (Bölüm B.7 şeması)
    veri: data_loader.load_all()'ın döndürdüğü sözlük — içinde
          veri["mesafe"], veri["ellecleme_kapasitesi"], veri["tir_kapasitesi"],
          veri["kiralik_araclar"], veri["arac_maliyet"] DataFrame'leri var.

    Döndürür: Bölüm B.8'deki (Tasima_Plani_Sablon.xlsx) şemasıyla
              BİREBİR AYNI kolonlara sahip bir pandas DataFrame.
    """
```

**Bu imza sabittir çünkü Kişi 2'nin `pipeline.py`'si bu fonksiyonu bu
isimle, bu parametrelerle çağıracak.** İsim veya parametre değişirse
Kişi 2'nin kodu çalışmaz.

### D.3 Yapılacaklar (adım adım)
1. `docs/is_kurallari_spec.md`'yi tam oku.
2. Önce KÜÇÜK ölçek: sadece İstanbul-Yalova güzergahı için `generate_plan`
   mantığını kur ve test et (checker.py ile).
3. Algoritma: (a) `veri["kiralik_araclar"]`'daki zorunlu filoyu her gün
   sabit ata — bunlar dönmez, sapmaz. (b) Kalan talebi (tahmin − kiralık
   kapasite) en ucuz spot araç kombinasyonuyla kapat (greedy: kapasiteye
   göre en verimli aracı seç). (c) Her adımda tır ve elleçleme kapasitesini kontrol et.
4. Küçük ölçek `checker.run_all_checks()`'ten PASS alınca, tüm 289 güzergaha,
   7 güne, 2 saat dilimine ölçekle.
5. Performansı ölç, çok yavaşsa raporla.

### D.4 Yasaklar
`config/rules.py`, `src/time_utils.py`, `src/data_loader.py`,
`src/checker.py` dosyalarını DEĞİŞTİRMEYİN — sadece import edip kullanın.

### D.5 Kabul Kriterleri (somut, test edilebilir)
- [ ] `from optimize import generate_plan` çalışıyor, hata vermiyor.
- [ ] `generate_plan(talep_df, veri)` çağrısı bir DataFrame döndürüyor.
- [ ] Döndürülen DataFrame'in kolonları Bölüm B.8 ile birebir aynı.
- [ ] `checker.run_all_checks(...)` bu çıktı için `hata_var_mi == False` veriyor.
- [ ] `python -m pytest tests/ -v` hiçbir testi bozmuyor.

---

## BÖLÜM E — KİŞİ 2: TEST, ENTEGRASYON, PIPELINE

### E.1 Sorumluluk Alanı
`src/checker.py`'yi genişletmek (yeni kenar durum testleri) ve
`src/pipeline.py`'yi sıfırdan yazmak — tüm sistemi tek komutla çalıştıran orkestratör.

### E.2 ARAYÜZ SÖZLEŞMESİ
`pipeline.py` şu fonksiyonu içermeli:

```python
def run_pipeline() -> None:
    """
    Sırasıyla:
    1. data_loader.load_all() ile tüm veriyi yükler
    2. outputs/Talep-tahmini.xlsx'i okur (forecast.py zaten üretti, tekrar
       üretmeye GEREK YOK, sadece dosyayı okuyun: pd.read_excel(...))
    3. optimize.generate_plan(talep_df, veri) çağırıp planı üretir
    4. Planı outputs/Tasima-plani.xlsx olarak kaydeder
    5. checker.run_all_checks(...) ile doğrular
    6. Sonucu (PASS/FAIL, toplam maliyet, toplam SLA cezası) ekrana yazdırır
    """
```

Bu fonksiyon `python src/pipeline.py` ile çalıştırıldığında otomatik
tetiklenmeli (`if __name__ == "__main__": run_pipeline()`).

### E.3 Yapılacaklar (adım adım)
1. Kişi 1'in küçük prototipi (Bölüm D.3, adım 4'ten önceki hali) bitene
   kadar BEKLE. Bu sürede `checker.py`'yi baştan sona oku.
2. `checker.py`'ye EK testler yaz (`tests/test_checker.py`'ye ekle): gece
   yarısı sınır durumu, SLA sınırında tam gecikme, 3'e bölünmüş talep senaryosu.
3. Kişi 1'in tam ölçek `generate_plan`'ı hazır olunca `pipeline.py`'yi yaz (Bölüm E.2).
4. `python src/pipeline.py` çalıştırıp uçtan uca PASS aldığını doğrula.

### E.4 Yasaklar
`optimize.py`'nin İÇİNİ değiştirmeyin (Kişi 1'in işi), sadece `generate_plan`'ı
DIŞARIDAN çağırın. `forecast.py`'yi değiştirmeyin (Kişi 3'ün işi).

### E.5 Kabul Kriterleri
- [ ] `python src/pipeline.py` tek komutla baştan sona hatasız çalışıyor.
- [ ] Çıktıda "PASS" ve toplam maliyet rakamı görünüyor.
- [ ] En az 5 yeni test eklendi, hepsi geçiyor.
- [ ] `python -m pytest tests/ -v` tam yeşil.

---

## BÖLÜM F — KİŞİ 3: TAHMİN İYİLEŞTİRME + TESLİM PAKETİ

### F.1 Sorumluluk Alanı
`src/forecast.py`'deki tahmin kalitesini artırmaya çalışmak (kanıtlanmadan
değişiklik yapılmaz) ve GitHub/README/sunum hazırlığı.

### F.2 ARAYÜZ SÖZLEŞMESİ (DEĞİŞTİRİLEMEZ kısım)
`forecast.py` içindeki şu fonksiyon imzaları AYNEN KALMALI (Kişi 1 ve
Kişi 2'nin kodu bunlara bağımlı değil ama `outputs/Talep-tahmini.xlsx`
formatı bunlardan üretiliyor, format bozulmamalı):

```python
def build_panel(talep_df: pd.DataFrame, aktif_rotalar=None) -> pd.DataFrame: ...
def forecast_range(panel: pd.DataFrame, baslangic: date, bitis: date, n: int = 12, method="pxe") -> pd.DataFrame: ...
def assign_talep_id(df: pd.DataFrame) -> pd.DataFrame: ...
```

Sadece `n` parametresinin varsayılan değerini veya `predict_one`'ın İÇ
mantığını (kanıtlanmış iyileştirmeyle) değiştirebilirsiniz. Çıktı şeması
(Bölüm B.7) DEĞİŞMEMELİ.

### F.3 Yapılacaklar (adım adım)
1. `backtest_wape()` fonksiyonunu kullanarak `n` değerini 6-24 arası
   tarayın, en az 3 farklı test haftasında deneyin.
2. İyileşme kanıtlanırsa uygulayın ve yorum satırıyla gerekçelendirin.
   Kanıtlanmazsa mevcut değeri koruyup "denendi, en iyisi buydu" diye not düşün.
3. Değişiklik sonrası `outputs/Talep-tahmini.xlsx`'i YENİDEN üretip
   kaydedin (format kontrolü yapın: satır sayısı 4046, kolonlar Bölüm B.7 ile aynı).
4. README dosyalarını güncelleyin. Kişi 1/2'nin rakamları gelince onları da ekleyin.
5. Sunum taslağını hazırlayın (mimari, yöntem gerekçeleri, jüri soru-cevap).

### F.4 Yasaklar
`optimize.py`, `checker.py`, `pipeline.py` dosyalarına dokunmayın.

### F.5 Kabul Kriterleri
- [ ] Backtest karşılaştırma tablosu üretildi ve belgelendi.
- [ ] `outputs/Talep-tahmini.xlsx` hâlâ 4046 satır, doğru şema.
- [ ] `python -m pytest tests/ -v` tam yeşil.
- [ ] README güncel, sunum taslağı hazır.

---

## BÖLÜM G — BAĞIMLILIK SIRASI (herkes bilmeli)

```
Kişi 3  ──────────────────────────────────────► (bağımsız, hemen başlar)

Kişi 1  ──[küçük prototip]──►[PASS]──[tam ölçek]──►[PASS]──► bitti
                                │
Kişi 2  ─────(bekler)──────────┴──[test yazar]──[pipeline.py]──► bitti
```

Kişi 2, Kişi 1'in küçük prototipi PASS almadan işe başlayamaz (test
edecek somut bir çıktı yok). Kişi 3 kimseyi beklemez. Kişi 1 en uzun sürer.

---

## BÖLÜM H — BU DOSYAYI NASIL KULLANACAKSINIZ

1. Her takım üyesi bu dosyanın TAMAMINI kendi kullandığı yapay zeka
   sistemine (Antigravity, ChatGPT, Claude — fark etmez) yapıştırır.
2. Sonuna şunu ekler: *"Sen Kişi 1'sin [veya 2, veya 3]. Bölüm D'deki
   [veya E, veya F] görevini yap. Diğer bölümlere dokunma. Arayüz
   sözleşmesindeki fonksiyon imzasını birebir koru."*
3. Böylece hangi AI aracını kullanırlarsa kullansınlar, ürettikleri kod
   birbirine tam olarak bağlanır — çünkü fonksiyon isimleri ve
   girdi/çıktı şekilleri baştan sabitlendi.

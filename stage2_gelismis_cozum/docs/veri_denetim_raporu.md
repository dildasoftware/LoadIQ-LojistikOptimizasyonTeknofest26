# LoadIQ — Gelişmiş Çözüm Aşaması: Veri Denetim Raporu

Tarih: 2026-07-13

## 1. Kapsam

- `teknofest26_gelismis` talep verisi: 66.024 satır, 1 Ocak – 28 Haziran 2026 (179 gün)
- Mesafe/süre matrisi: 306 satır (18 TM × 17 yön = tam kapsama)
- Tır kapasitesi: 18 TM
- Elleçleme kapasitesi: 18 TM
- Kiralık araç listesi: 12 satır (zorunlu günlük filo)
- Araç maliyet tablosu: 4 araç tipi (Tır, Kamyon, Hafif Kamyon, Kamyonet)

## 2. Transfer Merkezi / Güzergah Tutarlılığı

- 18 transfer merkezi, tüm 306 olası yönlü çiftin mesafe/süre bilgisi mevcut.
- Talep verisinde sadece **289 çiftte** en az bir talep gözlenmiş. Eksik olan **17 çiftin tamamı Kocaeli'ye varışlı** (`X → Kocaeli`). Kocaeli sadece çıkış transfer merkezi olarak görünüyor, hiçbir zaman varış olarak görünmüyor.
- **Sonuç / kural:** Şartname Q&A'sında da teyit edildiği gibi ("Veri seti görüldüğü gibidir") Kocaeli'ye varışlı hiçbir güzergah için talep tahmini üretilmemeli. Bu 17 çift, tahmin ve optimizasyon kapsamı dışında tutulmalı.

## 3. Tır Kapasitesi × Zorunlu Kiralık Filo Çelişkisi — ÇÖZÜLMÜŞ GÖRÜNÜYOR

Yarışma Q&A'sında takımlar Balıkesir (kapasite=0) ve Tekirdağ (kapasite=1) için zorunlu kiralık tır sayısının kapasiteyi aştığını raporlamış, organizatör "güncelleme yapılacak" demiş.

Elimizdeki `tir_kapasiteleri.xlsx` dosyasında **Balıkesir=1, Tekirdağ=2** olarak görünüyor — Q&A'daki eski değerlerden farklı. Zorunlu kiralık filo ile çapraz kontrol edildiğinde:

| TM | Kapasite | Zorunlu Kiralık Tır Kullanımı | Kalan Spot Tır Hakkı |
|---|---|---|---|
| Balıkesir | 1 | 1 | **0** |
| Tekirdağ | 2 | 2 | **0** |
| İstanbul | 10 | 8 | 2 |
| Yalova | 4 | 3 | 1 |
| Kocaeli | 12 | 3 | 9 |
| Manisa | 4 | 1 | 3 |
| Eskişehir | 10 | 2 | 8 |
| Diğer 11 TM | 0 veya 5-11 | 0 | değişken |

**Bulgu:** Elimizdeki dosya muhtemelen organizatörün söz verdiği güncellenmiş versiyon — artık zorunlu filo ile hiçbir kapasite ihlali yok. Ancak **kritik operasyonel kısıt**: Balıkesir ve Tekirdağ'da zorunlu filo kapasitenin tamamını tüketiyor, yani **bu iki merkezde spot Tır kullanılamaz** (Kamyon/Hafif Kamyon/Kamyonet ile karşılanmalı). Ayrıca 7 TM'de (Bilecik, Denizli, Isparta, Karaman, Kütahya, Sivas, Zonguldak) tır kapasitesi tamamen 0 — bu merkezlere hiçbir zaman Tır giremez/çıkamaz, sadece küçük araçlar kullanılabilir.

**Aksiyon:** Optimizasyon motoruna bu TM bazlı "tır kullanılamaz" listesi sabit kısıt olarak girilmeli. Yine de resmi güncel dosya yayınlanırsa çapraz doğrulama yapılmalı.

## 4. Anomali Günleri (Tatil/Bayram Etkisi)

Günlük toplam desi haftanın gününe göre çok güçlü mevsimsellik gösteriyor (Pazartesi ort. 1.575.188 → Pazar ort. 83.432). Bu normal haftalık döngü, model özelliği olarak (gün-of-week) ele alınmalı, anomali değil.

Bunun ötesinde, haftalık desende beklenenin çok altına düşen **gerçek anomali kümeleri** tespit edildi:

| Tarih | Gün | Toplam Desi | Yorum |
|---|---|---|---|
| 01 Ocak | Perşembe | 184.113 | Yılbaşı |
| 20-21 Mart | Cuma-Cumartesi | 17.766 / 22.803 | Ramazan Bayramı (tahmini) |
| 30 Nisan | Perşembe | 8.622 | Bayram öncesi köprü günü |
| 01 Mayıs | Cuma | 86.753 | İşçi Bayramı |
| **27-31 Mayıs** | **Çar-Paz** | **104 / 105 / 3.077 / 42.971 / 2.010** | **Kurban Bayramı — 5 gün neredeyse tam durma** |

**Kritik bulgu:** 27-31 Mayıs aralığı önceki MVP raporunda hiç bahsedilmemiş, çok daha büyük ve uzun bir anomali (5 gün, hacim normalin %1-5'ine düşüyor). Bu, muhtemelen Kurban Bayramı'nın (arefe + 4 gün) tam örtüşmesi.

**Aksiyon:** Talep tahmin modelinde "son N aynı-haftagünü gözlem" penceresi oluşturulurken bu 5 tatil kümesi (özellikle 27-31 Mayıs) training havuzundan **çıkarılmalı**, aksi halde örneğin haziran sonu Çarşamba tahmini bu sıfıra yakın günden kirlenir. Hedef tahmin penceresi (29 Haziran – 5 Temmuz) resmi tatile denk gelmiyor (19 Mayıs kapsam dışı), bu yönde risk yok.

## 5. Veri Kalitesi — Diğer

- Desi ≤ 0 olan satır yok (temiz).
- SLA hedef teslim günü (`hedef_teslim_gun`) sadece {1, 2} değerlerini alıyor — modelde bu iki senaryoyu ayrı ayrı test etmek gerekiyor.
- Talep verisinde günde sabit 2 saat dilimi (09:00 / 17:00) — şartnameyle birebir uyumlu.

## 6. Sonraki Adım İçin Öneriler

1. Tahmin modelinde gün-of-week + tatil-bayrağı (5 tespit edilen küme) özellik/filtre olarak kullanılmalı.
2. Optimizasyon motoruna TM bazlı "tır kullanılamaz" (9 TM: 7 tam sıfır + Balıkesir + Tekirdağ) sabit kısıtı eklenmeli.
3. Kocaeli'ye varışlı 17 güzergah tahmin ve planlamadan tamamen hariç tutulmalı.
4. Resmi güncellenmiş tır kapasitesi dosyası yayınlanırsa bu rapordaki Bölüm 3 tekrar doğrulanmalı.

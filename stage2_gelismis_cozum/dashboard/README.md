# LoadIQ Lojistik Optimizasyon Dashboard'u SPA Raporu

Bu raporda, `dashboard/index.html` üzerinde yapılan tek sayfa uygulaması (SPA) dönüşümü, veri entegrasyonu, tema ve animasyon ayarları ile harita etkileşimi detayları özetlenmektedir.

---

## 1. Mimari ve SPA Yapısı
Dashboard, harici bir kütüphaneye veya derleme adımına ihtiyaç duymadan doğrudan tarayıcıda çalışabilecek şekilde **Pure JavaScript & CSS** ile tek sayfa uygulaması (SPA) haline getirilmiştir:
*   **Sidebar Seçenekleri:** Sidebar linklerine `onclick="navigateTo(event, 'view-id')"` tanımlanarak sayfa yenilenmeden görünüm değişimi sağlanmıştır.
*   **Akıcı Geçişler:** Görünümler arasında `.view-content` ve `.active` sınıfları aracılığıyla 200ms süren CSS fade & slide (yukarı doğru kayma) geçiş efektleri entegre edilmiştir.
*   **Ortak Header Yönetimi:** Üst bar (topbar) küresel tutulmuş olup, sekmeler arası geçişte başlık, alt başlık ve sağ üst köşedeki `CHECKER: PASS` göstergesi dinamik olarak güncellenmektedir.

---

## 2. Dinamik Veri Entegrasyonu (`data.js`)
Projenin Python veri işleme boru hattı (`generate_dashboard_data.py`) tarafından üretilen `data.js` modülündeki `DASHBOARD_DATA` nesnesi kullanılarak aşağıdaki veriler sekmelere dinamik olarak yüklenmektedir:
*   **Pano Görünümü:** Toplam maliyet, SLA cezası, araç sefer sayıları ve optimizasyon süresi canlı olarak animasyonlu bir şekilde sayılmaktadır.
*   **Talep Tahmini:** Toplam talep satır sayısı (4.046), tarih aralığı, rota adetleri ve ilk 20 tahmin satırı bir veri tablosunda listelenmektedir.
*   **Optimizasyon Motoru:** Eski plan (Baseline) ile yeni optimize planın araç maliyetleri, SLA cezaları ve toplam kazançları kıyaslanmaktadır. Solver ve local checker log çıktıları terminal pencerelerinde sergilenmektedir.
*   **Filo Sekmesi:** Kiralık filo sözleşmeli hat listeleri ve spot araç türlerinin (Tır, Kamyon vb.) sefer adetleri ile doluluk oranları ilerleme çubuklarıyla (progress bar) çizilmektedir.
*   **Transfer Merkezleri:** 18 adet transfer merkezinin kapasiteleri ve TIR limitleri listelenmektedir.
*   **Raporlar:** Taşıma planı (`Tasima_Plani.xlsx`) ve detaylı çözüm analizi (`solution_analysis.xlsx`) için doğrudan indirme butonları yer almaktadır.

---

## 3. Sistem Tercihleri ve Ayarlar
*   **Tema Desteği:** `loadiq-theme` anahtarı altında `localStorage`'da saklanan Açık (Light) ve Koyu (Dark) tema desteği entegre edilmiştir. Tema değiştiğinde arayüz renk şeması anlık olarak güncellenir.
*   **Azaltılmış Hareket (Reduced Motion):** Animasyon hız ayarı değiştirilerek `reduced-motion` modu seçildiğinde, body elementine `.reduced-motion` sınıfı eklenerek SVG üzerindeki araç hareketleri, nabız halkaları ve grafik geçişleri anında durdurulmaktadır. Bu tercih tarayıcı hafızasında saklanmaktadır.

---

## 4. Harita Etkileşimi ve Vurgulama
Transfer Merkezleri sekmesindeki herhangi bir transfer merkezinin yanındaki "Haritada Vurgula →" butonuna tıklandığında:
1.  Sistem otomatik olarak **Pano** sekmesine geçiş yapar.
2.  İlgili Transfer Merkezi düğümü harita üzerinde pürüzsüzce odaklanarak 2.5 kat büyütülür ve 3 saniye boyunca yanıp sönerek kendini belli eder.

---

## 5. Görsel Kanıtlar ve Doğrulama
Yapılan doğrulama testlerinin ekran görüntüsü ve video kayıtları aşağıda paylaşılmıştır:

### Açık Tema Arayüz Görünümü
![Açık Tema ve Ayarlar Görünümü](/C:/Users/MSI/.gemini/antigravity/brain/355c41f3-10c7-42fd-9b4d-b1284baab49b/light_mode_settings.png)

### Dashboard SPA Test Videosu
![Dashboard Doğrulama Akışı](/C:/Users/MSI/.gemini/antigravity/brain/355c41f3-10c7-42fd-9b4d-b1284baab49b/dashboard_verification_1784280951721.webp)

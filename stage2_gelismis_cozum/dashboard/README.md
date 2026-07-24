# LoadIQ Dashboard

**`LoadIQ_Dashboard.html`** — Projenin güncel sonuçlarını gösteren tek dosyalık, kendi kendine yeterli (self-contained) bir panodur. Harici sunucu veya derleme adımı gerektirmez; doğrudan çift tıklanarak tarayıcıda açılır.

## İçerik
- **KPI kartları:** Toplam maliyet (22,11M TL), araç maliyeti, SLA cezası, araç seferi (1.697), uygunluk ihlali (0), test durumu (32/32 · checker PASS).
- **Grafikler (Chart.js):** Maliyet düşüşü (konsolidasyon + feasibility), araç tipi dağılımı, spot araç doluluk dağılımı, günlük SLA cezası.
- **Problem & kapsam, kural uygunluğu (20/20), mühendislik hikâyeleri** (boş-araç bug'ı, milk-run, feasibility düzeltmesi).

## Çalıştırma
- Doğrudan: `LoadIQ_Dashboard.html`'e çift tıklayın; ya da
- `start_dashboard.bat` (yerel HTTP sunucu başlatıp tarayıcıda açar).

Tüm değerler mevcut feasible çözümle (**22.106.411 TL**) birebir tutarlıdır.

"""
LoadIQ - Sabit İş Kuralları

Bu dosya, veri denetim raporunda tespit edilen ve şartname/duyurulardan
gelen SABİT kuralları tek yerde toplar. Yeni bir duyuru ya da veri
düzeltmesi geldiğinde SADECE bu dosya değişir; forecast.py, optimize.py,
checker.py hiç dokunulmadan yeni kurallarla çalışır.

Kaynak: outputs/is_kurallari_spec.md ve outputs/veri_denetim_raporu.md
"""

from datetime import date

# ---------------------------------------------------------------------------
# 1. Tahmin / optimizasyon zaman penceresi
# ---------------------------------------------------------------------------
TAHMIN_BASLANGIC = date(2026, 6, 29)   # 09:00
TAHMIN_BITIS = date(2026, 7, 5)        # 17:00
TALEP_SAATLERI = ["09:00", "17:00"]

# ---------------------------------------------------------------------------
# 2. Kocaeli'ye varışlı güzergahlar için tahmin/plan ÜRETİLMEZ
#    (veri denetim raporu: 17 çiftin tamamı Kocaeli varışlı, hiç talep yok)
# ---------------------------------------------------------------------------
def is_route_excluded(cikis: str, varis: str) -> bool:
    return varis == "Kocaeli"

# ---------------------------------------------------------------------------
# 3. Tır kullanım kısıtları (veri denetim raporu Bölüm 3)
# ---------------------------------------------------------------------------
# Bu TM'lere hiçbir şekilde Tır giremez/çıkamaz (kapasite = 0)
TIR_TAMAMEN_YASAK_TM = {
    "Bilecik", "Denizli", "Isparta", "Karaman", "Kütahya", "Sivas", "Zonguldak",
}

# Bu TM'lerde zorunlu kiralık filo kotanın tamamını dolduruyor -> spot Tır kullanılamaz
TIR_SPOT_YASAK_TM = {"Balıkesir", "Tekirdağ"}

# ---------------------------------------------------------------------------
# 4. Tatil / anomali günleri - tahmin modelinde training havuzundan çıkarılır
#    (veri denetim raporu Bölüm 4)
# ---------------------------------------------------------------------------
TATIL_GUNLERI = {
    date(2026, 1, 1),                                   # Yılbaşı
    date(2026, 3, 20), date(2026, 3, 21),                # Ramazan Bayramı (tahmini)
    date(2026, 4, 30),                                   # Bayram öncesi köprü
    date(2026, 5, 1),                                    # İşçi Bayramı
    date(2026, 5, 27), date(2026, 5, 28), date(2026, 5, 29),
    date(2026, 5, 30), date(2026, 5, 31),                # Kurban Bayramı (5 gün)
}

# ---------------------------------------------------------------------------
# 5. Zaman / yuvarlama kuralları (13.07.2026 duyurusu)
# ---------------------------------------------------------------------------
ELLECLEME_DK_PER_DESI = 0.01   # 1 desi = 0.01 dakika elleçleme süresi
SLA_CEZA_TL_PER_DESI_SAAT = 0.4  # Geciken Desi x Gecikme Saati x 0,4 TL

# ---------------------------------------------------------------------------
# 6. Araç davranış kuralları (13.07.2026 duyurusu ile netleşti)
# ---------------------------------------------------------------------------
KIRALIK_DONUS_YAPAR_MI = False   # Kiralık araçlar kesinlikle dönmez
SPOT_BOS_DONUS_ZORUNLU_MU = False  # Spot araç boş dönüşü zorunlu değil, modellenmez

# ---------------------------------------------------------------------------
# 7. Talep/Araç ID biçimleri (regex olarak checker.py tarafından kullanılacak)
# ---------------------------------------------------------------------------
TALEP_ID_ONEK = "D"    # D00001, bölünürse D00001-1, D00001-1-1 ...
ARAC_ID_ONEK = "V"     # V0001, V0002, ...

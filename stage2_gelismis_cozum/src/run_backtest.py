"""
LoadIQ - Backtest & Tahmin Yeniden Üretimi
-------------------------------------------------
1. n=6,8,10,12,14,16,18,20 için 3 hafta WAPE tablosu
2. pxe vs naive karşılaştırması
3. En iyi n ile outputs/Talep-tahmini.xlsx yeniden üretimi
4. Çıktı doğrulama
"""

import os
import sys
from datetime import date

import pandas as pd
import numpy as np

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)
sys.path.insert(0, os.path.join(_THIS_DIR, "..", "config"))

from data_loader import load_talep
from forecast import build_panel, backtest_wape, forecast_range, assign_talep_id

# ---------------------------------------------------------------------------
# 0. Veri ve panel
# ---------------------------------------------------------------------------
print("Veri yükleniyor...")
talep = load_talep()
panel = build_panel(talep)
print(f"Panel: {len(panel)} satır, {panel.groupby(['cikis','varis']).ngroups} aktif rota\n")

# ---------------------------------------------------------------------------
# 1. n taraması — 3 test haftası
# ---------------------------------------------------------------------------
TEST_HAFTALARI = [
    (date(2026, 6,  1), date(2026, 6,  7), "01-07 Haz"),
    (date(2026, 6,  8), date(2026, 6, 14), "08-14 Haz"),
    (date(2026, 6, 15), date(2026, 6, 21), "15-21 Haz"),
]
N_DEGERLER = [6, 8, 10, 12, 14, 16, 18, 20]

print("=" * 65)
print("ADIM 1 — n parametresi backtest (method=pxe)")
print("=" * 65)

tablo_rows = []
for n in N_DEGERLER:
    row = {"n": n}
    wapes = []
    for bas, bit, etiket in TEST_HAFTALARI:
        sonuc = backtest_wape(panel, bas, bit, n=n, method="pxe")
        w = sonuc["wape"] * 100
        row[etiket] = round(w, 2)
        wapes.append(w)
    row["Ortalama"] = round(float(np.mean(wapes)), 2)
    row["Std"]      = round(float(np.std(wapes, ddof=0)), 2)
    tablo_rows.append(row)

tablo = pd.DataFrame(tablo_rows).set_index("n")
print(tablo.to_string())

# En iyi n: en düşük ortalama; eşitlik varsa en düşük std
en_iyi_row = tablo.sort_values(["Ortalama", "Std"]).iloc[0]
en_iyi_n = int(tablo.sort_values(["Ortalama", "Std"]).index[0])
print(f"\n>>> Önerilen n = {en_iyi_n}  "
      f"(Ort. WAPE={en_iyi_row['Ortalama']:.2f}%, Std={en_iyi_row['Std']:.2f}%)\n")

# ---------------------------------------------------------------------------
# 2. pxe vs naive (en iyi n ile)
# ---------------------------------------------------------------------------
print("=" * 65)
print("ADIM 2 — pxe vs naive karşılaştırması (n=en iyi n)")
print("=" * 65)

karsilastirma = []
for bas, bit, etiket in TEST_HAFTALARI:
    pxe_w   = backtest_wape(panel, bas, bit, n=en_iyi_n, method="pxe")["wape"]   * 100
    naive_w = backtest_wape(panel, bas, bit, n=en_iyi_n, method="naive")["wape"] * 100
    karsilastirma.append({
        "Hafta": etiket,
        "pxe WAPE%": round(pxe_w, 2),
        "naive WAPE%": round(naive_w, 2),
        "Fark (pxe-naive)": round(pxe_w - naive_w, 2),
    })

karsilastirma_df = pd.DataFrame(karsilastirma)
print(karsilastirma_df.to_string(index=False))
# pxe <= naive her haftada (esilik: ayni p_ship~1 durumunda identik)
pxe_daha_iyi = all(r["Fark (pxe-naive)"] <= 0 for r in karsilastirma)
print(f"\n>>> pxe, naive'den {'DAHA IYI [PASS]' if pxe_daha_iyi else 'DAHA KOTU [FAIL]'} "
      f"(fark<=0 her haftada)\n")

# ---------------------------------------------------------------------------
# 3. Tahmin yeniden üretimi
# ---------------------------------------------------------------------------
print("=" * 65)
print(f"ADIM 3 — Tahmin yeniden üretimi (n={en_iyi_n}, method=pxe)")
print("=" * 65)

sablon_path = os.path.join(_THIS_DIR, "..", "data", "raw", "Talep_Tahmini_Sablon.xlsx")
sablon_df   = pd.read_excel(sablon_path)
sablon_kolonlar = list(sablon_df.columns)
print(f"Şablon kolonları: {sablon_kolonlar}")

tahmin_df = forecast_range(panel, date(2026, 6, 29), date(2026, 7, 5), n=en_iyi_n)
tahmin_df = assign_talep_id(tahmin_df)

# Kolonları şablonla aynı sıraya getir (eksik kolon varsa hata ver)
eksik = [k for k in sablon_kolonlar if k not in tahmin_df.columns]
if eksik:
    raise ValueError(f"Tahmin DataFrame'inde şablon kolonu eksik: {eksik}")
tahmin_df = tahmin_df[sablon_kolonlar]

output_path = os.path.join(_THIS_DIR, "..", "outputs", "Talep-tahmini.xlsx")
os.makedirs(os.path.dirname(output_path), exist_ok=True)
tahmin_df.to_excel(output_path, index=False)
print(f"Kaydedildi: {output_path}\n")

# ---------------------------------------------------------------------------
# 4. Çıktı doğrulama
# ---------------------------------------------------------------------------
print("=" * 65)
print("ADIM 4 — Çıktı doğrulama")
print("=" * 65)

kontroller = {}

# (a) Satır sayısı
kontroller["(a) Satır sayısı 4046 mı"] = (
    "PASS ✓" if len(tahmin_df) == 4046
    else f"FAIL ✗ — {len(tahmin_df)} satır"
)

# (b) Kolonlar şablonla birebir
kontroller["(b) Kolonlar şablonla aynı mı"] = (
    "PASS ✓" if list(tahmin_df.columns) == sablon_kolonlar
    else f"FAIL ✗ — {list(tahmin_df.columns)}"
)

# (c) Kocaeli varışlı satır yok mu
kocaeli_var = (tahmin_df["Varış Transfer Merkezi"] == "Kocaeli").sum()
kontroller["(c) Kocaeli varışlı satır yok mu"] = (
    "PASS ✓" if kocaeli_var == 0 else f"FAIL ✗ — {kocaeli_var} satır"
)

# (d) Negatif desi yok mu
negatif = (tahmin_df["Tahmin Edilen Desi"] < 0).sum()
kontroller["(d) Negatif desi yok mu"] = (
    "PASS ✓" if negatif == 0 else f"FAIL ✗ — {negatif} satır"
)

# (e) Talep ID'ler benzersiz mi
benzersiz = tahmin_df["Talep ID"].nunique()
kontroller["(e) Talep ID benzersiz mi"] = (
    "PASS ✓" if benzersiz == len(tahmin_df)
    else f"FAIL ✗ — {benzersiz} benzersiz / {len(tahmin_df)} satır"
)

for k, v in kontroller.items():
    print(f"  {k}: {v}")

print(f"\n  Toplam satır       : {len(tahmin_df)}")
print(f"  Toplam tahmin desi : {tahmin_df['Tahmin Edilen Desi'].sum():,.0f}")
print(f"  Min desi           : {tahmin_df['Tahmin Edilen Desi'].min():.2f}")

print(f"\n  Kullanılan n       : {en_iyi_n}")
print(f"  Ortalama WAPE      : {en_iyi_row['Ortalama']:.2f}%")

# ---------------------------------------------------------------------------
# 5. Seçilen n değerini bildirmek için forecast.py yorumunu güncelle (bilgi)
# ---------------------------------------------------------------------------
print(f"\n>>> forecast.py'ye yorum eklenecek: en iyi n={en_iyi_n} "
      f"(n=6..20 tarandı, WAPE={en_iyi_row['Ortalama']:.2f}%)")

print("\nBitişti. Şimdi pipeline.py çalıştırılabilir.")

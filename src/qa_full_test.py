"""
LoadIQ TEKNOFEST 2026 — Kapsamli QA Test Suiti
20 yillik mühendis gözüyle her metrik tek tek test edilir.

Test edilen metrikler:
  M1.  Format uyumu (sutun adlari, sutun sirasi, satir sayisi)
  M2.  Veri kalitesi (NaN, negatif, dtype)
  M3.  Tarih aralik uyumu (11-17 Mayis 2026, 7 gun, Pzt-Paz)
  M4.  Guzergah tam paneli (89 guzergah x 7 gun = 623 satir)
  M5.  Tahmin degerleri pozitif ve makul aralikta
  M6.  FAQ#1 — Spot arac min %10 doluluk
  M7.  FAQ#3 — Kiralik araclar her gun zorunlu cikis
  M8.  FAQ#6 — Haversine mesafe dogrulugu (spot maliyet = gunluk + km * mesafe)
  M9.  Arac kapasitesi asilmamis (Atanan Desi <= Kapasite)
  M10. Atanan toplam desi >= tahmin (kiralik varsa veya talep >= 560)
  M11. Maliyet hesabi dogrulugu (spot birim maliyet kontrolu)
  M12. Kiralik arac maliyet dogrulugu
  M13. Duplikat satir kontrolu (tam duplikat)
  M14. 17 Mayis (Pazar) dusuk talep: talep<560 ise arac yok — dogru mu?
  M15. Toplam maliyet tutarliligi (satir toplami = Ozet sayfasi)
"""

import pandas as pd
import numpy as np
import os
import math

# ============================================================
# Yardimci fonksiyonlar
# ============================================================

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.asin(math.sqrt(a))

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"
results = []

def check(name, condition, detail="", warn=False):
    symbol = PASS if condition else (WARN if warn else FAIL)
    results.append((name, symbol, detail))
    print(f"  {symbol} {name}: {detail}")
    return condition

# ============================================================
# Dosyalari oku
# ============================================================

print("=" * 70)
print("TEKNOFEST 2026 — KAPSAMLI QA TEST SUITI")
print("=" * 70)

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fc_path = os.path.join(base_dir, "outputs", "Tahminlenen_Talep.xlsx")
pl_path = os.path.join(base_dir, "outputs", "Arac_Planlama.xlsx")
raw_dir = os.path.join(base_dir, "data", "raw")

fc = pd.read_excel(fc_path)
pl = pd.read_excel(pl_path, sheet_name="Arac Planlama")
oz = pd.read_excel(pl_path, sheet_name="Ozet")

# Ham veriler
vehicles_path = coords_path = rentals_path = None
for f in os.listdir(raw_dir):
    fl = f.lower()
    if ('kapasite' in fl or 'maliyet' in fl) and f.endswith('.xlsx'):
        vehicles_path = os.path.join(raw_dir, f)
    elif 'kiral' in fl and f.endswith('.xlsx'):
        rentals_path = os.path.join(raw_dir, f)
    elif 'koordinat' in fl and f.endswith('.xlsx'):
        coords_path = os.path.join(raw_dir, f)

veh_df = pd.read_excel(vehicles_path)
veh_df.columns = ['AracAdi', 'Kapasite', 'KiralikGunluk', 'KiralikKm', 'SpotGunluk', 'SpotKm']
cap_map = dict(zip(veh_df['AracAdi'], veh_df['Kapasite']))
spot_gunluk_map = dict(zip(veh_df['AracAdi'], veh_df['SpotGunluk']))
spot_km_map = dict(zip(veh_df['AracAdi'], veh_df['SpotKm']))
kiralik_gunluk_map = dict(zip(veh_df['AracAdi'], veh_df['KiralikGunluk']))
kiralik_km_map = dict(zip(veh_df['AracAdi'], veh_df['KiralikKm']))

rent_df = pd.read_excel(rentals_path)
rent_df.columns = ['Cikis', 'Varis', 'AracSayisi', 'AracTuru']

coord_df = pd.read_excel(coords_path)
coords = {}
for _, row in coord_df.iterrows():
    coords[row.iloc[0]] = (row.iloc[1], row.iloc[2])

print(f"\nDosyalar okundu:")
print(f"  Tahminlenen_Talep.xlsx: {len(fc)} satir")
print(f"  Arac_Planlama.xlsx:     {len(pl)} satir")
print(f"  Arac tipleri: {veh_df['AracAdi'].tolist()}")
print(f"  Koordinat merkez sayisi: {len(coords)}")

# ============================================================
print("\n" + "=" * 70)
print("M1. FORMAT UYUMU")
print("=" * 70)
# ============================================================

beklenen_fc = ['Tarih', 'Cikis TM', 'Varis TM', 'Tahmin Edilen Desi']
beklenen_pl = ['Arac No', 'Tarih', 'Arac Tipi', 'Cikis TM', 'Varis TM', 'Atanan Desi', 'Maliyet']

check("FC sutun adlari", fc.columns.tolist() == beklenen_fc,
      f"Beklenen: {beklenen_fc} | Mevcut: {fc.columns.tolist()}")
check("PL sutun adlari", pl.columns.tolist() == beklenen_pl,
      f"Beklenen: {beklenen_pl} | Mevcut: {pl.columns.tolist()}")
check("FC satir sayisi = 623", len(fc) == 623, f"Mevcut: {len(fc)}")
check("PL satir sayisi <= 1000", len(pl) <= 1000, f"Mevcut: {len(pl)} (makul aralik)")

# ============================================================
print("\n" + "=" * 70)
print("M2. VERİ KALİTESİ (NaN, negatif, dtype)")
print("=" * 70)
# ============================================================

check("FC - NaN yok", not fc.isnull().any().any(),
      f"NaN sayisi: {fc.isnull().sum().sum()}")
check("PL - NaN yok", not pl.isnull().any().any(),
      f"NaN sayisi: {pl.isnull().sum().sum()}")
check("FC - Tarih datetime", str(fc['Tarih'].dtype).startswith('datetime'),
      f"dtype: {fc['Tarih'].dtype}")
check("PL - Tarih datetime", str(pl['Tarih'].dtype).startswith('datetime'),
      f"dtype: {pl['Tarih'].dtype}")
check("FC - Tahmin Edilen Desi float/int", fc['Tahmin Edilen Desi'].dtype in [float, 'float64'],
      f"dtype: {fc['Tahmin Edilen Desi'].dtype}")
check("PL - Atanan Desi >= 0", (pl['Atanan Desi'] >= 0).all(),
      f"Negatif sayisi: {(pl['Atanan Desi'] < 0).sum()}")
check("PL - Maliyet > 0", (pl['Maliyet'] > 0).all(),
      f"Sifir/negatif: {(pl['Maliyet'] <= 0).sum()}")
check("PL - Arac No benzersiz", pl['Arac No'].nunique() == len(pl),
      f"Benzersiz: {pl['Arac No'].nunique()} / Toplam: {len(pl)}")
check("PL - Tam duplikat yok", not pl.duplicated().any(),
      f"Duplikat: {pl.duplicated().sum()}")

# ============================================================
print("\n" + "=" * 70)
print("M3. TARİH ARALIK UYUMU")
print("=" * 70)
# ============================================================

fc_min = fc['Tarih'].min()
fc_max = fc['Tarih'].max()
pl_min = pl['Tarih'].min()
pl_max = pl['Tarih'].max()

check("FC - Tarih min = 11 Mayis", fc_min == pd.Timestamp('2026-05-11'), f"{fc_min.date()}")
check("FC - Tarih max = 17 Mayis", fc_max == pd.Timestamp('2026-05-17'), f"{fc_max.date()}")
check("FC - 7 benzersiz gun", fc['Tarih'].nunique() == 7, f"{fc['Tarih'].nunique()} gun")
check("PL - Tarih min = 11 Mayis", pl_min == pd.Timestamp('2026-05-11'), f"{pl_min.date()}")
check("PL - Tarih max = 17 Mayis", pl_max == pd.Timestamp('2026-05-17'), f"{pl_max.date()}")

# Hafta ici/sonu dagılım
gun_adlari = fc['Tarih'].dt.day_name().value_counts()
check("FC - Pzt-Paz tam hafta var", len(fc['Tarih'].dt.day_name().unique()) == 7,
      str(fc['Tarih'].dt.day_name().unique().tolist()))

# ============================================================
print("\n" + "=" * 70)
print("M4. GÜZERGAH TAM PANELİ (89 x 7 = 623)")
print("=" * 70)
# ============================================================

routes = fc[['Cikis TM', 'Varis TM']].drop_duplicates()
check("FC - 89 benzersiz guzergah", len(routes) == 89, f"Mevcut: {len(routes)}")
obs_per_route = fc.groupby(['Cikis TM', 'Varis TM']).size()
check("FC - Her guzergah 7 gun", (obs_per_route == 7).all(),
      f"Min: {obs_per_route.min()}, Max: {obs_per_route.max()}")
check("FC - Toplam 623 satir", len(fc) == 623, f"{len(fc)}")

# ============================================================
print("\n" + "=" * 70)
print("M5. TAHMİN DEĞERLERİ MAKUL ARALIKTA")
print("=" * 70)
# ============================================================

tahmin_min = fc['Tahmin Edilen Desi'].min()
tahmin_max = fc['Tahmin Edilen Desi'].max()
tahmin_mean = fc['Tahmin Edilen Desi'].mean()

check("FC - Tum tahminler > 0", (fc['Tahmin Edilen Desi'] > 0).all(),
      f"Sifir/negatif: {(fc['Tahmin Edilen Desi'] <= 0).sum()}")
check("FC - Max tahmin <= 100000", tahmin_max <= 100000,
      f"Max: {tahmin_max:.0f}")
check("FC - Ortalama makul (>500)", tahmin_mean > 500,
      f"Ort: {tahmin_mean:.0f}, Min: {tahmin_min:.0f}, Max: {tahmin_max:.0f}")

# Extreme outlier kontrolu
p99 = fc['Tahmin Edilen Desi'].quantile(0.99)
p1 = fc['Tahmin Edilen Desi'].quantile(0.01)
check("FC - P1/P99 makul oran (P99/P1 < 500)", p99/p1 < 500,
      f"P1={p1:.0f}, P99={p99:.0f}, oran={p99/p1:.0f}x", warn=True)

# ============================================================
print("\n" + "=" * 70)
print("M6. FAQ#1 — SPOT ARAÇ MİN %10 DOLULUK")
print("=" * 70)
# ============================================================

spot_rows = pl[pl['Arac Tipi'].str.startswith('Spot')].copy()
violations_10pct = []

for _, row in spot_rows.iterrows():
    arac_tipi_clean = row['Arac Tipi'].replace('Spot ', '')
    cap = cap_map.get(arac_tipi_clean, 0)
    if cap == 0:
        continue
    min_fill = cap * 0.10
    atanan = row['Atanan Desi']
    if atanan > 0 and atanan < min_fill:
        violations_10pct.append({
            'AracNo': row['Arac No'],
            'Tarih': row['Tarih'],
            'Cikis': row['Cikis TM'],
            'Varis': row['Varis TM'],
            'AracTipi': row['Arac Tipi'],
            'Atanan': atanan,
            'MinFill': min_fill,
            'Kapasite': cap
        })

check("FAQ#1 - Spot arac %10 doluluk", len(violations_10pct) == 0,
      f"Ihlal: {len(violations_10pct)} / {len(spot_rows)} spot arac")
if violations_10pct:
    print("  !!! İLK 5 İHLAL:")
    for v in violations_10pct[:5]:
        pct = v['Atanan']/v['Kapasite']*100
        print(f"    AracNo={v['AracNo']}, {v['Tarih'].date()} {v['Cikis']}->{v['Varis']}: "
              f"{v['AracTipi']}, Atanan={v['Atanan']:.0f}, Min={v['MinFill']:.0f} (%{pct:.1f})")

# Spot araclarin kapasite asimamis mi?
spot_cap_violations = []
for _, row in spot_rows.iterrows():
    arac_tipi_clean = row['Arac Tipi'].replace('Spot ', '')
    cap = cap_map.get(arac_tipi_clean, 0)
    if row['Atanan Desi'] > cap + 0.01:  # 0.01 yuvarlatma toleransi
        spot_cap_violations.append(row)
check("Spot - Kapasite asilmamis", len(spot_cap_violations) == 0,
      f"Kapasite asimi: {len(spot_cap_violations)}")

# ============================================================
print("\n" + "=" * 70)
print("M7. FAQ#3 — KİRALIK ARAÇLAR HER GÜN ZORUNLU")
print("=" * 70)
# ============================================================

kiralik_rows = pl[pl['Arac Tipi'].str.startswith('Kiralik')]
hedef_gunler = 7

rent_violations = []
for _, rent in rent_df.iterrows():
    cikis, varis = rent['Cikis'], rent['Varis']
    arac_sayisi = int(rent['AracSayisi'])
    arac_turu = rent['AracTuru']

    # Bu guzergahta atanan kiralik satirlar
    mask = (
        (kiralik_rows['Cikis TM'] == cikis) &
        (kiralik_rows['Varis TM'] == varis) &
        (kiralik_rows['Arac Tipi'] == f'Kiralik {arac_turu}')
    )
    route_kr = kiralik_rows[mask]
    beklenen_satir = hedef_gunler * arac_sayisi

    if len(route_kr) != beklenen_satir:
        rent_violations.append({
            'Cikis': cikis,
            'Varis': varis,
            'AracTuru': arac_turu,
            'Beklenen': beklened_satir,
            'Mevcut': len(route_kr)
        })

check("FAQ#3 - Kiralik araclar 7 gun zorunlu", len(rent_violations) == 0,
      f"Ihlal: {len(rent_violations)} guzergah")
if rent_violations:
    for v in rent_violations:
        print(f"    {v['Cikis']}->{v['Varis']} {v['AracTuru']}: "
              f"Beklenen {v['Beklenen']}, Mevcut {v['Mevcut']}")

# ============================================================
print("\n" + "=" * 70)
print("M8. FAQ#6 — HAVERSİNE MESAFE VE MALİYET DOĞRULUĞU")
print("=" * 70)
# ============================================================

# Spot arac ornekleri uzerinde maliyet dogrula
sample_errors = []
spot_sample = spot_rows.sample(min(50, len(spot_rows)), random_state=42)

for _, row in spot_sample.iterrows():
    cikis, varis = row['Cikis TM'], row['Varis TM']
    arac_tipi_clean = row['Arac Tipi'].replace('Spot ', '')

    if cikis not in coords or varis not in coords:
        continue

    lat1, lon1 = coords[cikis]
    lat2, lon2 = coords[varis]
    mesafe_km = haversine(lat1, lon1, lat2, lon2)

    gunluk = spot_gunluk_map.get(arac_tipi_clean, 0)
    km_rate = spot_km_map.get(arac_tipi_clean, 0)
    beklenen_maliyet = gunluk + km_rate * mesafe_km

    hata = abs(row['Maliyet'] - beklenen_maliyet)
    hata_pct = hata / beklenen_maliyet * 100 if beklenen_maliyet > 0 else 0

    if hata_pct > 1.0:  # %1 tolerans
        sample_errors.append({
            'Cikis': cikis, 'Varis': varis,
            'Mevcut': row['Maliyet'],
            'Beklenen': round(beklenen_maliyet, 2),
            'Hata%': round(hata_pct, 2)
        })

check("FAQ#6 - Haversine maliyet dogrulugu (%1 tolerans)",
      len(sample_errors) == 0,
      f"{len(sample_errors)} hata {len(spot_sample)} ornekten")
if sample_errors:
    for e in sample_errors[:5]:
        print(f"    {e['Cikis']}->{e['Varis']}: Mevcut={e['Mevcut']:.2f}, "
              f"Beklenen={e['Beklenen']:.2f}, Hata=%{e['Hata%']}")

# ============================================================
print("\n" + "=" * 70)
print("M9. ARAÇ KAPASİTESİ AŞILMAMIŞ (Atanan <= Kapasite)")
print("=" * 70)
# ============================================================

cap_violations = []
for _, row in pl.iterrows():
    arac_tipi_raw = row['Arac Tipi']
    arac_tipi_clean = arac_tipi_raw.replace('Kiralik ', '').replace('Spot ', '')
    cap = cap_map.get(arac_tipi_clean, None)
    if cap is None:
        cap_violations.append({'AracTipi': arac_tipi_raw, 'Sorun': 'Kapasite bulunamadi'})
        continue
    if row['Atanan Desi'] > cap + 0.1:
        cap_violations.append({
            'AracNo': row['Arac No'],
            'Tarih': row['Tarih'],
            'AracTipi': arac_tipi_raw,
            'Atanan': row['Atanan Desi'],
            'Kapasite': cap
        })

check("M9 - Kapasite asilmamis", len(cap_violations) == 0,
      f"Ihlal: {len(cap_violations)}")
if cap_violations:
    for v in cap_violations[:5]:
        print(f"    {v}")

# ============================================================
print("\n" + "=" * 70)
print("M10. ATANAN TOPLAM DESİ >= TAHMİN (kapsam)")
print("=" * 70)
# ============================================================

MIN_SPOT_FILL = min(cap_map.values()) * 0.10  # En kucuk araç min dolulugu
print(f"  Min spot fill esigi: {MIN_SPOT_FILL:.0f} desi")

coverage_fail = []
faq1_exempt = []

for _, frow in fc.iterrows():
    tarih, cikis, varis, tahmin = frow['Tarih'], frow['Cikis TM'], frow['Varis TM'], frow['Tahmin Edilen Desi']
    if tahmin <= 0:
        continue

    mask = (pl['Tarih'] == tarih) & (pl['Cikis TM'] == cikis) & (pl['Varis TM'] == varis)
    assigned = pl[mask]

    # Toplam kapasiteyi hesapla
    total_cap = 0
    for _, arow in assigned.iterrows():
        clean = arow['Arac Tipi'].replace('Kiralik ', '').replace('Spot ', '')
        total_cap += cap_map.get(clean, 0)

    # Kiralik var mi?
    has_rental = (assigned['Arac Tipi'].str.startswith('Kiralik')).any()
    kiralik_cap = 0
    for _, arow in assigned[assigned['Arac Tipi'].str.startswith('Kiralik')].iterrows():
        clean = arow['Arac Tipi'].replace('Kiralik ', '')
        kiralik_cap += cap_map.get(clean, 0)
    remaining_after_rental = max(0, tahmin - kiralik_cap)

    if total_cap < tahmin:
        eksik = tahmin - total_cap
        if eksik < MIN_SPOT_FILL:
            faq1_exempt.append({'Tarih': tarih, 'Cikis': cikis, 'Varis': varis,
                                 'Tahmin': tahmin, 'Eksik': eksik})
        else:
            coverage_fail.append({'Tarih': tarih, 'Cikis': cikis, 'Varis': varis,
                                    'Tahmin': tahmin, 'TotalCap': total_cap, 'Eksik': eksik})

check("M10 - Kapsam yeterli (eksik<560 FAQ1 istisna)", len(coverage_fail) == 0,
      f"Gercek ihlal: {len(coverage_fail)}, FAQ1 istisna: {len(faq1_exempt)}")
if coverage_fail:
    for v in coverage_fail[:5]:
        print(f"    {v['Tarih'].date()} {v['Cikis']}->{v['Varis']}: "
              f"Tahmin={v['Tahmin']:.0f}, Kapsanan={v['TotalCap']:.0f}, Eksik={v['Eksik']:.0f}")

print(f"  [BILGI] {len(faq1_exempt)} guzergahta eksik<560 (FAQ#1 istisna, kabul edilebilir)")

# ============================================================
print("\n" + "=" * 70)
print("M11. SPOT MALİYET HESABI DOĞRULUĞU (TAM KONTROL)")
print("=" * 70)
# ============================================================

spot_maliyet_errors = []
for _, row in spot_rows.iterrows():
    cikis, varis = row['Cikis TM'], row['Varis TM']
    arac_tipi_clean = row['Arac Tipi'].replace('Spot ', '')

    if cikis not in coords or varis not in coords:
        continue

    lat1, lon1 = coords[cikis]
    lat2, lon2 = coords[varis]
    mesafe_km = haversine(lat1, lon1, lat2, lon2)

    gunluk = spot_gunluk_map.get(arac_tipi_clean, 0)
    km_rate = spot_km_map.get(arac_tipi_clean, 0)
    beklenen = gunluk + km_rate * mesafe_km

    hata = abs(row['Maliyet'] - beklenen)
    if hata > 1.0:  # 1 TL tolerans (yuvarlatma)
        spot_maliyet_errors.append({
            'AracNo': row['Arac No'],
            'Cikis': cikis, 'Varis': varis,
            'AracTipi': row['Arac Tipi'],
            'Mevcut': round(row['Maliyet'], 2),
            'Beklenen': round(beklenen, 2),
            'Fark': round(hata, 2)
        })

check("M11 - Spot maliyet (tum satirlar, 1TL tolerans)",
      len(spot_maliyet_errors) == 0,
      f"Hata: {len(spot_maliyet_errors)} / {len(spot_rows)} spot satir")
if spot_maliyet_errors:
    print(f"  Arac tipleri:"); print(veh_df[['AracAdi','SpotGunluk','SpotKm']].to_string())
    for e in spot_maliyet_errors[:8]:
        print(f"    AracNo={e['AracNo']} {e['Cikis']}->{e['Varis']} {e['AracTipi']}: "
              f"Mevcut={e['Mevcut']}, Beklenen={e['Beklenen']}, Fark={e['Fark']}")

# ============================================================
print("\n" + "=" * 70)
print("M12. KİRALIK ARAÇ MALİYET DOĞRULUĞU")
print("=" * 70)
# ============================================================

kiralik_maliyet_errors = []
for _, row in kiralik_rows.iterrows():
    cikis, varis = row['Cikis TM'], row['Varis TM']
    arac_tipi_clean = row['Arac Tipi'].replace('Kiralik ', '')

    if cikis not in coords or varis not in coords:
        continue

    lat1, lon1 = coords[cikis]
    lat2, lon2 = coords[varis]
    mesafe_km = haversine(lat1, lon1, lat2, lon2)

    gunluk = kiralik_gunluk_map.get(arac_tipi_clean, 0)
    km_rate = kiralik_km_map.get(arac_tipi_clean, 0)
    beklenen = gunluk + km_rate * mesafe_km

    hata = abs(row['Maliyet'] - beklenen)
    if hata > 1.0:
        kiralik_maliyet_errors.append({
            'AracNo': row['Arac No'],
            'Cikis': cikis, 'Varis': varis,
            'Mevcut': round(row['Maliyet'], 2),
            'Beklenen': round(beklenen, 2),
            'Fark': round(hata, 2)
        })

check("M12 - Kiralik maliyet (tum satirlar, 1TL tolerans)",
      len(kiralik_maliyet_errors) == 0,
      f"Hata: {len(kiralik_maliyet_errors)} / {len(kiralik_rows)} kiralik satir")
if kiralik_maliyet_errors:
    for e in kiralik_maliyet_errors[:5]:
        print(f"    {e['Cikis']}->{e['Varis']}: Mevcut={e['Mevcut']}, Beklenen={e['Beklenen']}, Fark={e['Fark']}")

# ============================================================
print("\n" + "=" * 70)
print("M13. DUPLIKAT SATIR KONTROLÜ")
print("=" * 70)
# ============================================================

tam_dup = pl.duplicated().sum()
check("M13 - Tam duplikat yok (7 sutun)", tam_dup == 0, f"Duplikat: {tam_dup}")

# ============================================================
print("\n" + "=" * 70)
print("M14. PAZAR (17 MAYIS) DÜŞÜK TALEPLERİN DOĞRULUĞU")
print("=" * 70)
# ============================================================

fc_sun = fc[fc['Tarih'] == '2026-05-17']
unserved_sun = []
for _, row in fc_sun.iterrows():
    cikis, varis, tahmin = row['Cikis TM'], row['Varis TM'], row['Tahmin Edilen Desi']
    mask = (pl['Tarih'] == row['Tarih']) & (pl['Cikis TM'] == cikis) & (pl['Varis TM'] == varis)
    has_vehicle = mask.any()
    if not has_vehicle and tahmin >= MIN_SPOT_FILL:
        unserved_sun.append({'Cikis': cikis, 'Varis': varis, 'Tahmin': tahmin})

check("M14 - Pazar: 560+ desi olan guzergahlarda arac var",
      len(unserved_sun) == 0,
      f"Karsilanmamis (>=560 desi): {len(unserved_sun)}")
if unserved_sun:
    for u in unserved_sun:
        print(f"    {u['Cikis']}->{u['Varis']}: {u['Tahmin']:.0f} desi karsilanmamis!")

sun_no_vehicle = fc_sun[~fc_sun.apply(
    lambda r: ((pl['Tarih'] == r['Tarih']) & (pl['Cikis TM'] == r['Cikis TM']) & (pl['Varis TM'] == r['Varis TM'])).any(),
    axis=1
)]
print(f"  [BILGI] Pazar aracsiz {len(sun_no_vehicle)} guzergah -- en yuksek karsilanmayan: "
      f"{sun_no_vehicle['Tahmin Edilen Desi'].max():.0f} desi (< 560, FAQ#1 dogru)")

# ============================================================
print("\n" + "=" * 70)
print("M15. TOPLAM MALİYET TUTARLILIĞI")
print("=" * 70)
# ============================================================

satir_toplam = pl['Maliyet'].sum()
ozet_toplam_str = oz[oz['Metrik'] == 'GENEL TOPLAM MALIYET (TL)']['Deger'].values
ozet_toplam = float(ozet_toplam_str[0].replace(',', '')) if len(ozet_toplam_str) > 0 else 0

kiralik_satir = pl[pl['Arac Tipi'].str.startswith('Kiralik')]['Maliyet'].sum()
spot_satir = pl[pl['Arac Tipi'].str.startswith('Spot')]['Maliyet'].sum()

ozet_kiralik_str = oz[oz['Metrik'] == 'Toplam Kiralik Maliyet (TL)']['Deger'].values
ozet_spot_str = oz[oz['Metrik'] == 'Toplam Spot Maliyet (TL)']['Deger'].values
ozet_kiralik = float(ozet_kiralik_str[0].replace(',', '')) if len(ozet_kiralik_str) > 0 else 0
ozet_spot = float(ozet_spot_str[0].replace(',', '')) if len(ozet_spot_str) > 0 else 0

print(f"  Satir toplam Maliyet: {satir_toplam:,.2f} TL")
print(f"  Ozet sayfasi toplam: {ozet_toplam:,.2f} TL")
print(f"  Fark: {abs(satir_toplam - ozet_toplam):,.2f} TL")
print(f"  Kiralik (satir): {kiralik_satir:,.2f} | Ozet: {ozet_kiralik:,.2f}")
print(f"  Spot (satir):    {spot_satir:,.2f} | Ozet: {ozet_spot:,.2f}")

check("M15 - Toplam maliyet tutarli (100 TL tolerans)",
      abs(satir_toplam - ozet_toplam) < 100,
      f"Fark: {abs(satir_toplam - ozet_toplam):.2f} TL")

# ============================================================
print("\n" + "=" * 70)
print("ÖZET RAPOR")
print("=" * 70)
# ============================================================

passed = sum(1 for _, s, _ in results if s == PASS)
failed = sum(1 for _, s, _ in results if s == FAIL)
warned = sum(1 for _, s, _ in results if s == WARN)
total = len(results)

print(f"\n  Toplam test: {total}")
print(f"  PASS:  {passed}")
print(f"  WARN:  {warned}")
print(f"  FAIL:  {failed}")
print()

if failed == 0:
    print("  *** TÜM KRİTİK TESTLERİ GEÇTİ — DOSYALAR JÜRIYE HAZIR ***")
else:
    print("  !!! KRİTİK HATALAR VAR — DÜZELTİLMESİ GEREKİYOR !!!")
    print()
    for name, symbol, detail in results:
        if symbol == FAIL:
            print(f"    {FAIL} {name}: {detail}")

print()
print(f"  TOPLAM MALİYET: {satir_toplam:,.2f} TL")
print(f"  Kiralik: {kiralik_satir:,.2f} TL | Spot: {spot_satir:,.2f} TL")

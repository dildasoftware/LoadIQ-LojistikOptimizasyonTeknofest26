"""
test_coverage.py — Kapasite kapsama testi
Her satir icin: (Kiralik + Spot kapasite) >= Tahmini Desi kontrolu yapar.
"""

import pandas as pd
import numpy as np
import os
import sys


def test_capacity_coverage():
    """
    Arac_Planlama.xlsx dosyasindaki her guzergah-gun icin
    atanan toplam kapasitenin tahmini desiyi karsiladigini kontrol eder.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    plan_path = os.path.join(base_dir, "outputs", "Arac_Planlama.xlsx")
    forecast_path = os.path.join(base_dir, "outputs", "Tahminlenen_Talep.xlsx")
    vehicles_path = None
    
    # Arac kapasite bilgisi
    raw_dir = os.path.join(base_dir, "data", "raw")
    for f in os.listdir(raw_dir):
        if 'kapasite' in f.lower() or 'maliyet' in f.lower():
            vehicles_path = os.path.join(raw_dir, f)
    
    assert vehicles_path is not None, "Arac kapasite dosyasi bulunamadi!"
    
    vehicles_df = pd.read_excel(vehicles_path)
    vehicles_df.columns = ['AracAdi', 'Kapasite', 'KiralikGunluk', 'KiralikKm', 'SpotGunluk', 'SpotKm']
    
    # Kapasite haritasi (Kiralik/Spot prefix'i cikar)
    cap_map = dict(zip(vehicles_df['AracAdi'], vehicles_df['Kapasite']))
    
    plan_df = pd.read_excel(plan_path, sheet_name='Arac Planlama')
    forecast_df = pd.read_excel(forecast_path)
    
    print(f"[test_coverage] Plan satiri: {len(plan_df)}, Tahmin satiri: {len(forecast_df)}")
    
    violations = []
    faq1_uncovered = []
    
    for _, frow in forecast_df.iterrows():
        tarih = frow['Tarih']
        cikis = frow['Cikis TM']
        varis = frow['Varis TM']
        tahmin = frow['Tahmin Edilen Desi']
        
        if tahmin <= 0:
            continue
        
        # Bu guzergah-gun icin atanan araclari bul
        mask = (
            (plan_df['Tarih'] == tarih) &
            (plan_df['Cikis TM'] == cikis) &
            (plan_df['Varis TM'] == varis)
        )
        assignments = plan_df[mask]
        
        # Toplam kapasiteyi hesapla
        total_capacity = 0
        for _, arow in assignments.iterrows():
            arac_tipi = arow['Arac Tipi']
            # "Kiralik Tir" veya "Spot Kamyon" gibi prefix'i cikar
            clean_type = arac_tipi.replace('Kiralik ', '').replace('Spot ', '')
            cap = cap_map.get(clean_type, 0)
            total_capacity += cap
        
        if total_capacity < tahmin:
            min_spot_fill = 560  # Kamyonet %10 = 560 desi
            eksik = tahmin - total_capacity
            
            if eksik < min_spot_fill:
                # Kalan desi hicbir spot aracin %10'unu karsilamiyor
                # FAQ #1 geregi spot arac atanamaz
                faq1_uncovered.append({
                    'Tarih': tarih,
                    'Cikis': cikis,
                    'Varis': varis,
                    'Tahmin': tahmin,
                    'Eksik': eksik
                })
            else:
                violations.append({
                    'Tarih': tarih,
                    'Cikis': cikis,
                    'Varis': varis,
                    'Tahmin': tahmin,
                    'Kapasite': total_capacity,
                    'Eksik': tahmin - total_capacity
                })
    
    if faq1_uncovered:
        print(f"  [BILGI] {len(faq1_uncovered)} guzergahta talep <560 desi (FAQ#1 geregi spot arac atanamaz)")
    
    if violations:
        print(f"\n[FAIL] {len(violations)} kapasite ihlali bulundu:")
        for v in violations[:10]:
            print(f"  {v['Tarih']} {v['Cikis']}->{v['Varis']}: "
                  f"Tahmin={v['Tahmin']:.0f}, Kapasite={v['Kapasite']:.0f}, "
                  f"Eksik={v['Eksik']:.0f}")
        assert False, f"{len(violations)} kapasite ihlali!"
    else:
        print(f"[PASS] Tum {len(forecast_df)} guzergah-gun kombinasyonunda kapasite yeterli (veya FAQ#1 istisnasi).")


def test_spot_min_fill():
    """
    FAQ #1: Spot araclarin min %10 doluluk kisitini kontrol eder.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    plan_path = os.path.join(base_dir, "outputs", "Arac_Planlama.xlsx")
    vehicles_path = None
    
    raw_dir = os.path.join(base_dir, "data", "raw")
    for f in os.listdir(raw_dir):
        if 'kapasite' in f.lower() or 'maliyet' in f.lower():
            vehicles_path = os.path.join(raw_dir, f)
    
    vehicles_df = pd.read_excel(vehicles_path)
    vehicles_df.columns = ['AracAdi', 'Kapasite', 'KiralikGunluk', 'KiralikKm', 'SpotGunluk', 'SpotKm']
    cap_map = dict(zip(vehicles_df['AracAdi'], vehicles_df['Kapasite']))
    
    plan_df = pd.read_excel(plan_path, sheet_name='Arac Planlama')
    
    spot_rows = plan_df[plan_df['Arac Tipi'].str.startswith('Spot')]
    violations = []
    
    for _, row in spot_rows.iterrows():
        arac_tipi = row['Arac Tipi'].replace('Spot ', '')
        cap = cap_map.get(arac_tipi, 0)
        atanan = row['Atanan Desi']
        min_fill = cap * 0.10
        
        if atanan < min_fill and atanan > 0:
            violations.append({
                'Tarih': row['Tarih'],
                'Cikis': row['Cikis TM'],
                'Varis': row['Varis TM'],
                'AracTipi': row['Arac Tipi'],
                'Atanan': atanan,
                'MinFill': min_fill,
                'Kapasite': cap
            })
    
    if violations:
        print(f"\n[FAIL] {len(violations)} spot arac %10 doluluk ihlali:")
        for v in violations[:10]:
            print(f"  {v['Tarih']} {v['Cikis']}->{v['Varis']}: "
                  f"{v['AracTipi']} Atanan={v['Atanan']:.0f}, Min={v['MinFill']:.0f}")
        assert False, f"{len(violations)} doluluk ihlali!"
    else:
        print(f"[PASS] Tum {len(spot_rows)} spot aracta %10 doluluk saglaniyor.")


if __name__ == "__main__":
    test_capacity_coverage()
    test_spot_min_fill()
    print("\n[OK] Tum testler GECTI.")

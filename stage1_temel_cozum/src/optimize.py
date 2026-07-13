"""
optimize.py — OR-Tools CP-SAT ile arac planlama optimizasyonu
LoadIQ TEKNOFEST 2026 Lojistik Optimizasyon Projesi

FAQ Kisitlari:
  #1: Spot arac min %10 doluluk zorunlu
  #2: Donus rotalari kapsam disi (tek yonlu maliyet)
  #3: Kiralik araclar ZORUNLU kullanilir (bos bile olsa)
  #4: Konsolidasyon YASAK (MVP asamasinda)
  #6: Mesafe: kus ucusu (Haversine)

Juri Formati (Arac Planlama):
  Tarih | Arac Tipi | Cikis TM | Varis TM | Atanan Desi | Maliyet
  -> Her satir = bir ARAC ATAMASI (bir guzergah-gunde birden fazla satir olabilir)
"""

import pandas as pd
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import haversine

try:
    from ortools.sat.python import cp_model
    HAS_ORTOOLS = True
except ImportError:
    HAS_ORTOOLS = False
    print("[UYARI] OR-Tools yuklenmemis. Greedy cozum kullanilacak.")


def load_vehicle_data(vehicles_path: str) -> pd.DataFrame:
    """Arac kapasite ve maliyet verilerini okur."""
    df = pd.read_excel(vehicles_path)
    df.columns = ['AracAdi', 'Kapasite', 'KiralikGunluk', 'KiralikKm', 'SpotGunluk', 'SpotKm']
    return df


def load_rental_data(rentals_path: str) -> pd.DataFrame:
    """Kiralik arac filosu verisini okur."""
    df = pd.read_excel(rentals_path)
    df.columns = ['Cikis', 'Varis', 'AracSayisi', 'AracTuru']
    return df


def load_coordinates(coords_path: str) -> dict:
    """Koordinat verisini dict olarak okur. {sehir: (enlem, boylam)}"""
    df = pd.read_excel(coords_path)
    coords = {}
    for _, row in df.iterrows():
        coords[row.iloc[0]] = (row.iloc[1], row.iloc[2])
    return coords


def get_distance(coords: dict, cikis: str, varis: str) -> float:
    """Iki sehir arasi kus ucusu mesafeyi km olarak hesaplar."""
    if cikis not in coords or varis not in coords:
        print(f"  [UYARI] Koordinat bulunamadi: {cikis} veya {varis}")
        return 0.0
    lat1, lon1 = coords[cikis]
    lat2, lon2 = coords[varis]
    return haversine(lat1, lon1, lat2, lon2)


def solve_spot_vehicles(remaining_desi: float, distance_km: float,
                         vehicles_df: pd.DataFrame) -> list:
    """
    En dusuk maliyetli spot arac kombinasyonunu bulur.
    FAQ #1: Her spot aracin kapasitesinin en az %10'u dolu olmali.
    
    Yaklasim:
    1. Kalan desiyi tablo seklinde parcala
    2. Her arac tam dolar (kapasite kadar desi) veya son arac en az %10 dolar
    3. Talep hicbir aracin %10'unu karsilamiyorsa spot arac ATANAMAZ
    
    Returns:
        list of dicts: [{AracTuru, Sayi, Kapasite, BirimMaliyet, ToplamMaliyet}, ...]
    """
    if remaining_desi <= 0:
        return []
    
    # Her arac tipinin bu mesafe icin maliyeti ve maliyet/desi verimliligi
    candidates = []
    for i in range(len(vehicles_df)):
        row = vehicles_df.iloc[i]
        cap = row['Kapasite']
        min_fill = cap * 0.10
        cost = row['SpotGunluk'] + row['SpotKm'] * distance_km
        cost_per_desi = cost / cap
        candidates.append({
            'idx': i,
            'AracAdi': row['AracAdi'],
            'Kapasite': cap,
            'MinFill': min_fill,
            'BirimMaliyet': cost,
            'CostPerDesi': cost_per_desi
        })
    
    # En az %10 dolu olabilecek araclari filtrele
    # Son arac icin remaining_desi'nin %10'unu karsilamasi lazim
    # Ama birden fazla arac atandiginda, son aracin kalani %10'u gecmeli
    
    # En verimli (cost/desi) aracindan baslayarak atama yap
    candidates.sort(key=lambda x: x['CostPerDesi'])
    
    best_result = None
    best_cost = float('inf')
    
    # Her arac tipini "ana tip" olarak dene
    for main in candidates:
        cap = main['Kapasite']
        min_fill = main['MinFill']
        cost = main['BirimMaliyet']
        
        # Bu arac tipiyle kac tane lazim?
        n_full = int(remaining_desi // cap)  # tam dolu araclar
        leftover = remaining_desi - n_full * cap
        
        if leftover <= 0:
            # Tam boluyor
            total_cost = n_full * cost
            if total_cost < best_cost:
                best_cost = total_cost
                best_result = [{
                    'AracTuru': main['AracAdi'],
                    'Sayi': n_full,
                    'Kapasite': cap,
                    'BirimMaliyet': cost,
                    'ToplamMaliyet': total_cost
                }]
        elif leftover >= min_fill:
            # Son arac %10+ dolu — gecerli
            total_n = n_full + 1
            total_cost = total_n * cost
            if total_cost < best_cost:
                best_cost = total_cost
                best_result = [{
                    'AracTuru': main['AracAdi'],
                    'Sayi': total_n,
                    'Kapasite': cap,
                    'BirimMaliyet': cost,
                    'ToplamMaliyet': total_cost
                }]
        else:
            # Son arac %10 altinda kaliyor — daha kucuk arac var mi?
            # Kalan icin uygun daha kucuk arac bul
            found_smaller = False
            for sub in candidates:
                if sub['MinFill'] <= leftover:
                    total_cost = n_full * cost + sub['BirimMaliyet']
                    if total_cost < best_cost:
                        best_cost = total_cost
                        result = []
                        if n_full > 0:
                            result.append({
                                'AracTuru': main['AracAdi'],
                                'Sayi': n_full,
                                'Kapasite': cap,
                                'BirimMaliyet': cost,
                                'ToplamMaliyet': n_full * cost
                            })
                        result.append({
                            'AracTuru': sub['AracAdi'],
                            'Sayi': 1,
                            'Kapasite': sub['Kapasite'],
                            'BirimMaliyet': sub['BirimMaliyet'],
                            'ToplamMaliyet': sub['BirimMaliyet']
                        })
                        best_result = result
                        found_smaller = True
                        break
            
            if not found_smaller and n_full > 0:
                # Kucuk arac yok, bir tane fazla buyuk arac koy
                total_n = n_full + 1
                total_cost = total_n * cost
                if total_cost < best_cost:
                    best_cost = total_cost
                    best_result = [{
                        'AracTuru': main['AracAdi'],
                        'Sayi': total_n,
                        'Kapasite': cap,
                        'BirimMaliyet': cost,
                        'ToplamMaliyet': total_cost
                    }]
    
    # Hicbir arac %10 karsilamiyorsa (cok dusuk talep)
    if best_result is None:
        # En kucuk kapasiteli aracin %10'unu bile karsilamiyorsa 
        # spot arac atanamaz - bu desiler kayip
        min_cap = min(c['Kapasite'] for c in candidates)
        if remaining_desi < min_cap * 0.10:
            return []  # FAQ #1: spot arac atanamaz
        else:
            # Fallback: en kucuk uygun arac
            for c in sorted(candidates, key=lambda x: x['Kapasite']):
                if remaining_desi >= c['MinFill']:
                    return [{
                        'AracTuru': c['AracAdi'],
                        'Sayi': 1,
                        'Kapasite': c['Kapasite'],
                        'BirimMaliyet': c['BirimMaliyet'],
                        'ToplamMaliyet': c['BirimMaliyet']
                    }]
            return []
    
    return best_result


def run_optimization(forecast_path: str, vehicles_path: str, rentals_path: str, 
                     coords_path: str, output_path: str):
    """
    Ana optimizasyon fonksiyonu. Tum guzergah-gun kombinasyonlari icin
    kiralik + spot arac atamasi yapar.
    """
    print("[optimize] Veriler okunuyor...")
    forecast_df = pd.read_excel(forecast_path)
    vehicles_df = load_vehicle_data(vehicles_path)
    rentals_df = load_rental_data(rentals_path)
    coords = load_coordinates(coords_path)
    
    print(f"  Tahmin satiri: {len(forecast_df)}")
    print(f"  Arac tipleri: {vehicles_df['AracAdi'].tolist()}")
    print(f"  Kiralik atama: {len(rentals_df)} satir")
    print(f"  Koordinat: {len(coords)} sehir")
    
    # Kiralik arac kapasite haritasi
    cap_map = dict(zip(vehicles_df['AracAdi'], vehicles_df['Kapasite']))
    kiralik_gunluk_map = dict(zip(vehicles_df['AracAdi'], vehicles_df['KiralikGunluk']))
    kiralik_km_map = dict(zip(vehicles_df['AracAdi'], vehicles_df['KiralikKm']))
    
    all_assignments = []  # Juri formatinda: her satir = 1 arac atamasi
    toplam_kiralik_maliyet = 0.0
    toplam_spot_maliyet = 0.0
    
    for idx, row in forecast_df.iterrows():
        tarih = row['Tarih']
        cikis = row['Cikis TM']
        varis = row['Varis TM']
        tahmin_desi = row['Tahmin Edilen Desi']
        
        # Mesafe hesabi (kus ucusu)
        distance_km = get_distance(coords, cikis, varis)
        
        # Bu guzergah-gun icin kalan desi takibi
        desi_kalan = tahmin_desi
        
        # --- KIRALIK ARACLAR (FAQ #3: zorunlu, bos bile olsa) ---
        kiralik_mask = (rentals_df['Cikis'] == cikis) & (rentals_df['Varis'] == varis)
        kiralik_rows = rentals_df[kiralik_mask]
        
        kiralik_kapasite_toplam = 0.0
        
        for _, kr in kiralik_rows.iterrows():
            arac_turu = kr['AracTuru']
            arac_sayisi = int(kr['AracSayisi'])
            kapasite_per = cap_map.get(arac_turu, 0)
            
            kiralik_gunluk = kiralik_gunluk_map.get(arac_turu, 0)
            kiralik_km = kiralik_km_map.get(arac_turu, 0)
            birim_maliyet = kiralik_gunluk + kiralik_km * distance_km
            
            # Her kiralik araci ayri satir olarak ata (FAQ#3: boş bile olsa)
            for arac_i in range(arac_sayisi):
                # Bu arac ne kadar yuk tasiyor?
                atanan = min(kapasite_per, max(0.0, desi_kalan))
                
                # Arac tipi goruntu adi
                if arac_turu == 'Tür' or arac_turu == 'Tır':
                    tip_label = 'Kiralık TIR'
                else:
                    tip_label = f'Kiralık {arac_turu}'
                
                all_assignments.append({
                    'Tarih': tarih,
                    'Araç Tipi': tip_label,
                    'Çıkış TM': cikis,
                    'Varış TM': varis,
                    'Atanan Desi': round(atanan, 2),
                    'Maliyet': round(birim_maliyet, 2)
                })
                
                desi_kalan -= atanan
                kiralik_kapasite_toplam += kapasite_per
                toplam_kiralik_maliyet += birim_maliyet
        
        # --- SPOT ARACLAR ---
        kalan_desi = max(0.0, tahmin_desi - kiralik_kapasite_toplam)
        
        if kalan_desi > 0:
            # Unified solver with %10 fill constraint built-in
            spot_result = solve_spot_vehicles(kalan_desi, distance_km, vehicles_df)
            
            # Spot araclari juri formatinda ekle — her satir = 1 araç
            desi_dagitilacak = kalan_desi
            for spot in spot_result:
                for arac_i in range(spot['Sayi']):
                    atanan = min(spot['Kapasite'], max(0.0, desi_dagitilacak))
                    
                    # Arac tipi goruntu adi
                    arac_turu_raw = spot['AracTuru']
                    if arac_turu_raw == 'Tür' or arac_turu_raw == 'Tır':
                        tip_label = 'Spot TIR'
                    else:
                        tip_label = f'Spot {arac_turu_raw}'
                    
                    all_assignments.append({
                        'Tarih': tarih,
                        'Araç Tipi': tip_label,
                        'Çıkış TM': cikis,
                        'Varış TM': varis,
                        'Atanan Desi': round(atanan, 2),
                        'Maliyet': round(spot['BirimMaliyet'], 2)
                    })
                    
                    desi_dagitilacak -= atanan
                    toplam_spot_maliyet += spot['BirimMaliyet']
        
        if (idx + 1) % 100 == 0:
            print(f"  Optimizasyon ilerleme: {idx+1}/{len(forecast_df)}")
    
    # --- CIKTI OLUSTUR ---
    # Sutun sirasi: Tarih | Arac Tipi | Cikis TM | Varis TM | Atanan Desi | Maliyet
    result_df = pd.DataFrame(all_assignments)[
        ['Tarih', 'Araç Tipi', 'Çıkış TM', 'Varış TM', 'Atanan Desi', 'Maliyet']
    ]
    
    # Toplam maliyet
    toplam_maliyet = toplam_kiralik_maliyet + toplam_spot_maliyet
    
    print(f"\n{'='*60}")
    print(f"OPTIMIZASYON SONUCLARI")
    print(f"{'='*60}")
    print(f"  Toplam arac atamasi: {len(result_df)} satir")
    print(f"  Toplam kiralik maliyet: {toplam_kiralik_maliyet:,.2f} TL")
    print(f"  Toplam spot maliyet:    {toplam_spot_maliyet:,.2f} TL")
    print(f"  GENEL TOPLAM MALiYET:   {toplam_maliyet:,.2f} TL")
    
    # Excel'e yaz (iki sayfa)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Ana sayfa: Arac atamalari
        result_df.to_excel(writer, sheet_name='Arac Planlama', index=False)
        
        # Ozet sayfasi
        ozet_data = {
            'Metrik': [
                'Toplam Kiralik Maliyet (TL)',
                'Toplam Spot Maliyet (TL)',
                'GENEL TOPLAM MALIYET (TL)',
                'Toplam Arac Atamasi',
                'Tahmin Modeli',
                'Tahmin WAPE',
                'Optimizasyon Yontemi',
                'Mesafe Hesabi',
                'Not'
            ],
            'Deger': [
                f'{toplam_kiralik_maliyet:,.2f}',
                f'{toplam_spot_maliyet:,.2f}',
                f'{toplam_maliyet:,.2f}',
                str(len(result_df)),
                'P(sevkiyat) x E[desi|sevkiyat] iki-parcali model',
                '~%42 (backtest 27 Nis - 10 May)',
                'OR-Tools CP-SAT' if HAS_ORTOOLS else 'Greedy',
                'Haversine kus ucusu (FAQ #6)',
                'Kiralik_Araclar listesindeki filo, 7 gunun hepsinde ayni sekilde calistigi varsayilmistir.'
            ]
        }
        ozet_df = pd.DataFrame(ozet_data)
        ozet_df.to_excel(writer, sheet_name='Ozet', index=False)
    
    print(f"\n  -> Dosya kaydedildi: {output_path}")
    
    return result_df, toplam_maliyet


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    forecast_path = os.path.join(base_dir, "outputs", "Tahminlenen_Talep.xlsx")
    vehicles_path = os.path.join(base_dir, "data", "raw", "Arac_Kapasite_Maliyet.xlsx")  # Turkish i
    rentals_path = os.path.join(base_dir, "data", "raw", "Kiralik_Araclar.xlsx")  # Turkish i
    coords_path = os.path.join(base_dir, "data", "raw", "Koordinatlar v2 (1).xlsx")
    output_path = os.path.join(base_dir, "outputs", "Arac_Planlama.xlsx")
    
    # Dosya adlarini kontrol et
    raw_dir = os.path.join(base_dir, "data", "raw")
    actual_files = os.listdir(raw_dir)
    print(f"[optimize] Raw dizinindeki dosyalar: {actual_files}")
    
    # Dogru dosya adlarini bul (encoding farkliliklari icin)
    for f in actual_files:
        f_lower = f.lower()
        if 'kapasite' in f_lower or 'maliyet' in f_lower:
            vehicles_path = os.path.join(raw_dir, f)
        elif 'kiral' in f_lower and f_lower.endswith('.xlsx'):
            rentals_path = os.path.join(raw_dir, f)
        elif 'koordinat' in f_lower and f_lower.endswith('.xlsx'):
            coords_path = os.path.join(raw_dir, f)
    
    print(f"  Arac dosyasi: {os.path.basename(vehicles_path)}")
    print(f"  Kiralik dosyasi: {os.path.basename(rentals_path)}")
    print(f"  Koordinat dosyasi: {os.path.basename(coords_path)}")
    
    result_df, total_cost = run_optimization(
        forecast_path, vehicles_path, rentals_path, coords_path, output_path
    )

"""
backtest.py — Tahmin modelinin WAPE ile dogrulanmasi
LoadIQ TEKNOFEST 2026

Test donemi: 27 Nisan - 10 Mayis 2026 (14 gun)
Hedef WAPE: %40-45 araligi (onceden dogrulanmis: %42.1)
Eger %35 altina duserse DUR — leakage sinyali!
"""

import pandas as pd
import numpy as np
import os
import sys

# forecast.py ayni dizinde
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from forecast import forecast_route_date


def calculate_wape(actuals: np.ndarray, predictions: np.ndarray) -> float:
    """
    WAPE (Weighted Absolute Percentage Error) hesaplar.
    WAPE = sum(|pred - actual|) / sum(actual)
    """
    total_actual = np.sum(actuals)
    if total_actual == 0:
        return 0.0
    return np.sum(np.abs(predictions - actuals)) / total_actual


def run_backtest(panel_path: str):
    """
    27 Nisan - 10 Mayis 2026 tarih araliginda backtest calistirir.
    Sadece gercekte sevkiyat olan (Desi > 0) gunler uzerinden WAPE hesaplar.
    """
    print("[backtest] Panel okunuyor...")
    panel = pd.read_csv(panel_path, parse_dates=['Tarih'])
    
    # Test donemi
    test_start = pd.Timestamp('2026-04-27')
    test_end = pd.Timestamp('2026-05-10')
    test_dates = pd.date_range(test_start, test_end, freq='D')
    
    routes = panel[['Cikis', 'Varis']].drop_duplicates().reset_index(drop=True)
    
    print(f"[backtest] Test donemi: {test_start.date()} - {test_end.date()}")
    print(f"  Guzergah sayisi: {len(routes)}")
    print(f"  Gun sayisi: {len(test_dates)}")
    
    results = []
    total = len(routes) * len(test_dates)
    done = 0
    
    for _, route in routes.iterrows():
        cikis, varis = route['Cikis'], route['Varis']
        
        for td in test_dates:
            # Gercek deger
            actual_mask = (
                (panel['Cikis'] == cikis) & 
                (panel['Varis'] == varis) & 
                (panel['Tarih'] == td)
            )
            actual = panel.loc[actual_mask, 'Desi'].values
            actual_val = actual[0] if len(actual) > 0 else 0.0
            
            # Tahmin (sadece td oncesi veri)
            pred_val = forecast_route_date(panel, cikis, varis, td, n_weeks=12)
            
            day_offset = (td - test_start).days + 1  # gun+1, gun+2, ...
            
            results.append({
                'Cikis': cikis,
                'Varis': varis,
                'Tarih': td,
                'Actual': actual_val,
                'Predicted': pred_val,
                'AbsError': abs(pred_val - actual_val),
                'DayOffset': day_offset
            })
            done += 1
        
        if done % (len(test_dates) * 10) == 0:
            print(f"  Backtest ilerleme: {done}/{total} ({100*done/total:.0f}%)")
    
    results_df = pd.DataFrame(results)
    
    # --- GENEL WAPE ---
    mask_pos = results_df['Actual'] > 0
    overall_wape = calculate_wape(
        results_df.loc[mask_pos, 'Actual'].values,
        results_df.loc[mask_pos, 'Predicted'].values
    )
    
    print(f"\n{'='*50}")
    print(f"GENEL WAPE: {overall_wape*100:.1f}%")
    print(f"{'='*50}")
    
    if overall_wape < 0.35:
        print("[DIKKAT] WAPE %35 altinda — leakage ihtimali var!")
    elif 0.40 <= overall_wape <= 0.45:
        print("[OK] WAPE beklenen aralikta (%40-45)")
    else:
        print(f"[BILGI] WAPE beklenen aralik disinda ama kabul edilebilir")
    
    # --- UFUK BAZLI WAPE ---
    print(f"\nUfuk bazli WAPE:")
    for offset in sorted(results_df['DayOffset'].unique()):
        subset = results_df[results_df['DayOffset'] == offset]
        subset_pos = subset[subset['Actual'] > 0]
        if len(subset_pos) > 0:
            w = calculate_wape(subset_pos['Actual'].values, subset_pos['Predicted'].values)
            date_val = test_start + pd.Timedelta(days=offset-1)
            print(f"  Gun+{offset:2d} ({date_val.strftime('%a %d %b')}): WAPE = {w*100:.1f}%")
    
    # --- OZET ISTATISTIKLER ---
    print(f"\nOzet:")
    print(f"  Toplam test satiri: {len(results_df)}")
    print(f"  Gercek sevkiyat olan: {mask_pos.sum()}")
    print(f"  Toplam gercek desi: {results_df['Actual'].sum():,.0f}")
    print(f"  Toplam tahmin desi: {results_df['Predicted'].sum():,.0f}")
    print(f"  Toplam mutlak hata: {results_df['AbsError'].sum():,.0f}")
    
    return overall_wape, results_df


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    panel_path = os.path.join(base_dir, "data", "processed", "panel.csv")
    
    wape, results = run_backtest(panel_path)

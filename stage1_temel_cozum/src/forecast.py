"""
forecast.py — P(sevkiyat) x E[desi|sevkiyat] iki parcali tahmin modeli
LoadIQ TEKNOFEST 2026 Lojistik Optimizasyon Projesi

Model:
  1. Hedef tarihin haftanin gunu bulunur
  2. Guzergah icin, hedef tarihten ONCEKI son n_weeks ayni-gune 
     denk gelen gozlemler alinir
  3. p_ship = gozlemlerin kacinda Desi>0
  4. e_desi = Desi>0 olanlarin ortalamasi
  5. Tahmin = p_ship * e_desi

ONEMLI: Leakage yok — SADECE target_date oncesi veri kullanilir.
"""

import pandas as pd
import numpy as np
import os


def forecast_route_date(panel_df: pd.DataFrame, cikis: str, varis: str, 
                        target_date: pd.Timestamp, n_weeks: int = 12) -> float:
    """
    Belirli bir guzergah ve hedef tarih icin desi tahmini yapar.
    
    Args:
        panel_df: Tam panel verisi (Cikis, Varis, Tarih, Desi)
        cikis: Cikis Transfer Merkezi
        varis: Varis Transfer Merkezi
        target_date: Tahmin yapilacak hedef tarih
        n_weeks: Gecmise donuk kac haftaya bakilacagi
        
    Returns:
        Tahmini desi miktari (float)
    """
    target_weekday = target_date.weekday()  # 0=Mon, 6=Sun
    
    # Bu guzergahin gecmis verisini al (sadece target_date ONCESI)
    mask = (
        (panel_df['Cikis'] == cikis) & 
        (panel_df['Varis'] == varis) & 
        (panel_df['Tarih'] < target_date)
    )
    route_hist = panel_df.loc[mask].copy()
    
    # Ayni haftanin gunune denk gelen gozlemleri filtrele
    route_hist = route_hist[route_hist['Tarih'].dt.weekday == target_weekday]
    
    # Son n_weeks gozlemi al (en yakin tarihlerden)
    route_hist = route_hist.sort_values('Tarih', ascending=False).head(n_weeks)
    
    if len(route_hist) == 0:
        return 0.0
    
    # p_ship: sevkiyat yapilma olasiligi
    shipments = route_hist['Desi'] > 0
    p_ship = shipments.mean()
    
    # e_desi: sevkiyat yapildiginda ortalama desi
    positive_desi = route_hist.loc[shipments, 'Desi']
    e_desi = positive_desi.mean() if len(positive_desi) > 0 else 0.0
    
    return p_ship * e_desi


def forecast_week(panel_df: pd.DataFrame, target_dates: list, 
                  n_weeks: int = 12) -> pd.DataFrame:
    """
    Tum guzergahlar ve verilen hedef tarihler icin tahminleri olusturur.
    
    Args:
        panel_df: Tam panel verisi
        target_dates: Tahmin yapilacak tarihlerin listesi
        n_weeks: Gecmise donuk hafta sayisi
        
    Returns:
        Tahmin sonuclarini iceren DataFrame
    """
    # Benzersiz guzergahlari bul
    routes = panel_df[['Cikis', 'Varis']].drop_duplicates().reset_index(drop=True)
    
    results = []
    total = len(routes) * len(target_dates)
    done = 0
    
    for _, route in routes.iterrows():
        cikis = route['Cikis']
        varis = route['Varis']
        
        for target_date in target_dates:
            td = pd.Timestamp(target_date)
            pred = forecast_route_date(panel_df, cikis, varis, td, n_weeks)
            results.append({
                'Tarih': td,
                'Cikis TM': cikis,
                'Varis TM': varis,
                'Tahmin Edilen Desi': round(pred, 2)
            })
            done += 1
            
        if done % (len(target_dates) * 10) == 0:
            print(f"  Tahmin ilerleme: {done}/{total} ({100*done/total:.0f}%)")
    
    forecast_df = pd.DataFrame(results)
    print(f"  Tahmin tamamlandi: {len(forecast_df)} satir")
    
    return forecast_df


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    panel_path = os.path.join(base_dir, "data", "processed", "panel.csv")
    output_path = os.path.join(base_dir, "outputs", "Tahminlenen_Talep.xlsx")
    
    print("[forecast] Panel okunuyor...")
    panel = pd.read_csv(panel_path, parse_dates=['Tarih'])
    
    # 11-17 Mayis 2026
    target_dates = pd.date_range('2026-05-11', '2026-05-17', freq='D')
    
    print("[forecast] Tahminler hesaplaniyor...")
    forecast_df = forecast_week(panel, target_dates)
    
    # Juri formatinda kaydet: Tarih | Cikis TM | Varis TM | Tahmin Edilen Desi
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    forecast_df.to_excel(output_path, index=False, sheet_name='Tahminlenen Talep')
    
    print(f"[forecast] Dosya kaydedildi: {output_path}")
    print(f"  Toplam tahmin satiri: {len(forecast_df)}")
    print(f"  Sifir tahmin: {(forecast_df['Tahmin Edilen Desi'] == 0).sum()}")
    print(f"  Ortalama tahmin: {forecast_df['Tahmin Edilen Desi'].mean():.2f}")
    print(f"  Max tahmin: {forecast_df['Tahmin Edilen Desi'].max():.2f}")

"""
build_panel.py — Ham veriyi tam (güzergah x tarih) panele çevirir
LoadIQ TEKNOFEST 2026 Lojistik Optimizasyon Projesi

Mantık:
  - Desi_talep Excel dosyasını okur
  - Tüm benzersiz (Çıkış, Varış) güzergah çiftlerini bulur
  - Min-max tarih aralığındaki tüm günleri oluşturur
  - Her (güzergah, tarih) kombinasyonu için tam panel oluşturur
  - Veri setinde olmayan kombinasyonlara Desi=0 atar (eksik = sevkiyat yok)
"""

import pandas as pd
import numpy as np
import os
import sys

def build_panel(input_path: str, output_path: str) -> pd.DataFrame:
    """
    Ham talep verisinden tam tarihli panel verisini oluşturur.
    
    Args:
        input_path: Ham Desi_talep xlsx dosyasının yolu
        output_path: İşlenmiş panel.csv dosyasının kaydedileceği yol
    
    Returns:
        Panel DataFrame
    """
    # 1. Ham veriyi oku
    df = pd.read_excel(input_path)
    col_cikis = df.columns[0]   # Çıkış Transfer Merkezi
    col_varis = df.columns[1]   # Varış Transfer Merkezi
    col_tarih = df.columns[2]   # Tarih
    col_desi  = df.columns[3]   # Toplam Desi
    
    df[col_tarih] = pd.to_datetime(df[col_tarih])
    
    print(f"[build_panel] Ham veri okundu: {len(df)} satır")
    print(f"  Sütunlar: {df.columns.tolist()}")
    
    # 2. Benzersiz güzergahları bul
    routes = df[[col_cikis, col_varis]].drop_duplicates().reset_index(drop=True)
    n_routes = len(routes)
    print(f"  Benzersiz güzergah sayısı: {n_routes}")
    
    # 3. Tam tarih aralığını oluştur
    date_min = df[col_tarih].min()
    date_max = df[col_tarih].max()
    all_dates = pd.date_range(date_min, date_max, freq='D')
    n_dates = len(all_dates)
    print(f"  Tarih aralığı: {date_min.date()} - {date_max.date()} ({n_dates} gün)")
    
    # 4. Tam paneli oluştur (cross join)
    routes_repeated = pd.concat([routes] * n_dates, ignore_index=True)
    dates_repeated = np.repeat(all_dates, n_routes)
    
    panel = pd.DataFrame({
        'Cikis': routes_repeated[col_cikis].values,
        'Varis': routes_repeated[col_varis].values,
        'Tarih': dates_repeated,
    })
    
    # 5. Orijinal verideki desi değerlerini eşleştir
    df_renamed = df.rename(columns={
        col_cikis: 'Cikis',
        col_varis: 'Varis',
        col_tarih: 'Tarih',
        col_desi:  'Desi'
    })
    
    panel = panel.merge(
        df_renamed[['Cikis', 'Varis', 'Tarih', 'Desi']],
        on=['Cikis', 'Varis', 'Tarih'],
        how='left'
    )
    
    # 6. Eksik değerleri 0 yap (sevkiyat yok)
    panel['Desi'] = panel['Desi'].fillna(0.0)
    
    # 7. Doğrulamalar
    expected_rows = n_routes * n_dates
    actual_rows = len(panel)
    
    dup_check = panel.duplicated(subset=['Cikis', 'Varis', 'Tarih'])
    n_dups = dup_check.sum()
    
    zero_count = (panel['Desi'] == 0).sum()
    zero_pct = 100 * zero_count / actual_rows
    
    print(f"\n[DOĞRULAMA]")
    print(f"  Beklenen satır sayısı: {expected_rows}")
    print(f"  Gerçek satır sayısı:   {actual_rows}")
    print(f"  Duplicate satır:       {n_dups}")
    print(f"  Sıfır (sevkiyatsız):   {zero_count} ({zero_pct:.1f}%)")
    
    if actual_rows != expected_rows:
        print(f"  [UYARI] Satir sayisi beklentiden farkli!")
    if n_dups > 0:
        print(f"  [HATA] Duplicate satirlar var!")
        # Eger orijinal veride ayni guzergah-tarih icin birden fazla kayit varsa topla
        panel = panel.groupby(['Cikis', 'Varis', 'Tarih'], as_index=False)['Desi'].sum()
        print(f"  -> Duplicateler toplanarak cozuldu: {len(panel)} satir")
    
    print(f"  [OK] Panel basariyla olusturuldu")
    
    # 8. Tarih sırasına göre sırala ve kaydet
    panel = panel.sort_values(['Cikis', 'Varis', 'Tarih']).reset_index(drop=True)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    panel.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"  -> Dosya kaydedildi: {output_path}")
    
    return panel


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_path = os.path.join(base_dir, "data", "raw", "Desi_talep (1).xlsx")
    output_path = os.path.join(base_dir, "data", "processed", "panel.csv")
    
    panel = build_panel(input_path, output_path)

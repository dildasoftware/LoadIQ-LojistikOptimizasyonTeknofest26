"""n=8 ile Talep-tahmini.xlsx yeniden üretimi."""
import os, sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "config"))

import pandas as pd
from data_loader import load_talep
from forecast import build_panel, forecast_range, assign_talep_id

print("Veri yukleniyor...")
talep = load_talep()
panel = build_panel(talep)

sablon_path = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "Talep_Tahmini_Sablon.xlsx")
sablon_kolonlar = list(pd.read_excel(sablon_path).columns)

print("Tahmin uretiliyor (n=8)...")
tahmin_df = forecast_range(panel, date(2026, 6, 29), date(2026, 7, 5), n=8)
tahmin_df = assign_talep_id(tahmin_df)
tahmin_df = tahmin_df[sablon_kolonlar]

out_path = os.path.join(os.path.dirname(__file__), "..", "outputs", "Talep-tahmini.xlsx")
os.makedirs(os.path.dirname(out_path), exist_ok=True)
tahmin_df.to_excel(out_path, index=False)

print(f"Kaydedildi: {out_path}")
print(f"Satir sayisi    : {len(tahmin_df)}")
print(f"4046 mi         : {len(tahmin_df) == 4046}")
print(f"Toplam desi     : {tahmin_df['Tahmin Edilen Desi'].sum():,.0f}")
print(f"Negatif desi    : {(tahmin_df['Tahmin Edilen Desi'] < 0).sum()}")
kocaeli_col = "Varış Transfer Merkezi"
print(f"Kocaeli varish  : {(tahmin_df[kocaeli_col] == 'Kocaeli').sum()}")
print(f"Benzersiz TalepID: {tahmin_df['Talep ID'].nunique()} / {len(tahmin_df)}")

import os
import sys
import time
import pandas as pd

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_THIS_DIR, "src"))
sys.path.insert(0, os.path.join(_THIS_DIR, "config"))

from data_loader import load_all
from optimize import generate_plan
from checker import run_all_checks

def run_test():
    print("=== Loading data ===")
    veri = load_all()
    
    # Read the forecasted demands
    forecast_path = os.path.join(_THIS_DIR, "outputs", "Talep-tahmini.xlsx")
    if not os.path.exists(forecast_path):
        print(f"Error: {forecast_path} not found. Please run forecast.py first if needed.")
        return
        
    talep_df = pd.read_excel(forecast_path)
    print(f"Forecasted demands loaded. Total rows: {len(talep_df)}")

    # ---------------------------------------------------------------------------
    # Phase 1: Istanbul <-> Yalova Prototype (1-2 days)
    # ---------------------------------------------------------------------------
    print("\n--- PHASE 1: Istanbul <-> Yalova Prototype (First 2 Days) ---")
    first_two_dates = sorted(talep_df["Tarih"].unique())[:2]
    proto_mask = (
        ((talep_df["Çıkış Transfer Merkezi"] == "İstanbul") & (talep_df["Varış Transfer Merkezi"] == "Yalova")) |
        ((talep_df["Çıkış Transfer Merkezi"] == "Yalova") & (talep_df["Varış Transfer Merkezi"] == "İstanbul"))
    ) & (talep_df["Tarih"].isin(first_two_dates))
    
    talep_df_proto = talep_df[proto_mask].copy()
    print(f"Prototype demands count: {len(talep_df_proto)}")
    
    print("Generating prototype plan...")
    start_time = time.time()
    plan_df_proto = generate_plan(talep_df_proto, veri)
    end_time = time.time()
    print(f"Prototype plan generated in {end_time - start_time:.4f} seconds. Rows: {len(plan_df_proto)}")
    
    print("Running checker on prototype plan...")
    rapor_proto = run_all_checks(
        talep_df_proto, plan_df_proto,
        veri["mesafe"], veri["tir_kapasitesi"],
        veri["ellecleme_kapasitesi"], veri["arac_maliyet"]
    )
    print("--- PROTOTYPE CHECKER REPORT ---")
    print(rapor_proto.ozet())
    
    # ---------------------------------------------------------------------------
    # Phase 2: Full Scale (18 TM / 289 Routes / 7 Days)
    # ---------------------------------------------------------------------------
    print("\n--- PHASE 2: Full Scale Optimization ---")
    print("Generating full plan...")
    start_time = time.time()
    plan_df_full = generate_plan(talep_df, veri)
    end_time = time.time()
    print(f"Full plan generated in {end_time - start_time:.4f} seconds. Rows: {len(plan_df_full)}")
    
    print("Running checker on full plan...")
    rapor_full = run_all_checks(
        talep_df, plan_df_full,
        veri["mesafe"], veri["tir_kapasitesi"],
        veri["ellecleme_kapasitesi"], veri["arac_maliyet"]
    )
    print("--- FULL SCALE CHECKER REPORT ---")
    print(rapor_full.ozet())
    
    # Save the full plan
    output_plan_path = os.path.join(_THIS_DIR, "outputs", "Tasima_Plani.xlsx")
    plan_df_full.to_excel(output_plan_path, index=False)
    print(f"\nSaved full plan to {output_plan_path}")
    
    # Print summary of costs and SLA
    leg_cols = ["Araç ID", "Çıkış Transfer Merkezi", "Varış Transfer Merkezi", "Çıkış Tarihi", "Çıkış Saati"]
    actual_vehicle_cost = plan_df_full.groupby(leg_cols)["Toplam maliyet"].first().sum()
    total_sla = plan_df_full["SLA cezası"].sum()
    
    print("\n=== SUMMARY STATISTICS ===")
    print(f"Total Rows in Plan: {len(plan_df_full)}")
    print(f"Actual Unique Vehicle Cost: {actual_vehicle_cost:,.2f} TL")
    print(f"Total SLA Penalty: {total_sla:,.2f} TL")
    print(f"Combined Real Cost (Vehicle + SLA): {actual_vehicle_cost + total_sla:,.2f} TL")

if __name__ == "__main__":
    run_test()

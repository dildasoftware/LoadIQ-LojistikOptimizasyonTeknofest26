"""
LoadIQ - LightGBM Tabanlı Talep Tahmin Modeli ve Karşılaştırma (forecast_ml.py)

Bu modül:
1. Zaman serisi panel verisi üzerinden leakagesiz özellik mühendisliği yapar.
2. LightGBM regresyon modeli eğitir.
3. 3 test haftasında (1-7 Haz, 8-14 Haz, 15-21 Haz 2026) adil backtest
   ile LightGBM ve mevcut PxE (n=8) WAPE performansını karşılaştırır.
"""

import os
import sys
from datetime import date, datetime, timedelta
import pandas as pd
import numpy as np
import lightgbm as lgb

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)
sys.path.insert(0, os.path.join(_THIS_DIR, "..", "config"))

from data_loader import load_talep
import forecast
import rules


def prepare_features(panel: pd.DataFrame) -> pd.DataFrame:
    """
    Panel verisinden zaman serisi ve lag özelliklerini türetir.
    Leakage olmaması için lag'ler kesinlikle hedef tarihten ÖNCEKİ verilerden hesaplanır.
    """
    df = panel.copy()
    df["tarih_dt"] = pd.to_datetime(df["tarih"])
    df["ay"] = df["tarih_dt"].dt.month
    df["ayin_gunu"] = df["tarih_dt"].dt.day
    df["saat_num"] = df["saat"].apply(lambda s: 0 if str(s) == "09:00" else 1)
    df["tatil_int"] = df["tatil_mi"].astype(int)

    # Rota kategorik değişkeni
    df["rota_str"] = df["cikis"] + "_" + df["varis"]
    rotalar = sorted(df["rota_str"].unique())
    rota_map = {r: i for i, r in enumerate(rotalar)}
    df["rota_code"] = df["rota_str"].map(rota_map).astype("category")

    # Lag hesaplamaları (No-leakage: hedef günden strictly önceki tatil olmayan aynı haftagünü verileri)
    df = df.sort_values(["cikis", "varis", "saat", "haftanin_gunu", "tarih"]).reset_index(drop=True)

    # Tatil günlerinin değerleri eğitim havuzunda kirlilik yaratmaması için NaN yapılarak kaydırılır
    df["desi_clean"] = np.where(df["tatil_mi"], np.nan, df["desi"])

    grup = df.groupby(["cikis", "varis", "saat", "haftanin_gunu"])["desi_clean"]

    # shift(1): Mevcut günü hariç tutar, sadece önceki tatil-olmayan gözlemleri alır
    df["lag_1_haftagunu"] = grup.transform(lambda s: s.ffill().shift(1)).fillna(0.0)
    df["mean_4_haftagunu"] = grup.transform(lambda s: s.ffill().shift(1).rolling(4, min_periods=1).mean()).fillna(0.0)
    df["mean_8_haftagunu"] = grup.transform(lambda s: s.ffill().shift(1).rolling(8, min_periods=1).mean()).fillna(0.0)

    # Sıralamayı tekrar tarihe göre düzenle
    df = df.sort_values(["tarih", "cikis", "varis", "saat"]).reset_index(drop=True)

    return df



def train_and_predict_ml(train_df: pd.DataFrame, test_df: pd.DataFrame) -> np.ndarray:
    """
    Train verisiyle LightGBM regresyon modelini eğitir ve test verisini tahmin eder.
    """
    features = [
        "haftanin_gunu", "saat_num", "ay", "ayin_gunu",
        "rota_code", "tatil_int",
        "lag_1_haftagunu", "mean_4_haftagunu", "mean_8_haftagunu"
    ]
    categorical_features = ["rota_code", "haftanin_gunu", "saat_num", "tatil_int"]

    X_train = train_df[features]
    y_train = train_df["desi"]

    X_test = test_df[features]

    model = lgb.LGBMRegressor(
        n_estimators=100,
        learning_rate=0.05,
        num_leaves=31,
        random_state=42,
        verbosity=-1
    )

    model.fit(
        X_train, y_train,
        categorical_feature=categorical_features
    )

    preds = model.predict(X_test)
    return np.maximum(preds, 0.0)  # Negatif tahminleri 0'a çek


def evaluate_backtest():
    """
    3 Farklı test haftası için PxE (n=8) vs LightGBM (ML) WAPE karşılaştırmasını yapar.
    """
    talep_df = load_talep()
    panel = forecast.build_panel(talep_df)
    feat_df = prepare_features(panel)

    test_haftalari = [
        (date(2026, 6, 1), date(2026, 6, 7), "1-7 Haziran 2026"),
        (date(2026, 6, 8), date(2026, 6, 14), "8-14 Haziran 2026"),
        (date(2026, 6, 15), date(2026, 6, 21), "15-21 Haziran 2026"),
    ]

    sonuc_tablosu = []

    for bas, bit, etiket in test_haftalari:
        # 1. Mevcut PxE (n=8) WAPE
        pxe_res = forecast.backtest_wape(panel, bas, bit, n=8, method="pxe")
        pxe_wape = pxe_res["wape"] * 100.0

        # 2. LightGBM (ML) WAPE (Strictly Train: tarih < bas)
        train_mask = feat_df["tarih"] < bas
        test_mask = (feat_df["tarih"] >= bas) & (feat_df["tarih"] <= bit)

        train_data = feat_df[train_mask].copy()
        test_data = feat_df[test_mask].copy()

        ml_preds = train_and_predict_ml(train_data, test_data)
        test_data["ml_pred"] = ml_preds

        toplam_hata = (test_data["ml_pred"] - test_data["desi"]).abs().sum()
        toplam_gercek = test_data["desi"].sum()
        ml_wape = (toplam_hata / toplam_gercek * 100.0) if toplam_gercek > 0 else 0.0

        sonuc_tablosu.append({
            "Hafta": etiket,
            "PxE (n=8) WAPE (%)": round(pxe_wape, 2),
            "LightGBM (ML) WAPE (%)": round(ml_wape, 2)
        })

    res_df = pd.DataFrame(sonuc_tablosu)

    # Ortalamalar
    ort_pxe = round(res_df["PxE (n=8) WAPE (%)"].mean(), 2)
    ort_ml = round(res_df["LightGBM (ML) WAPE (%)"].mean(), 2)

    print("\n" + "=" * 65)
    print("      TALEP TAHMİN MODELİ KARŞILAŞTIRMA TABLOSU (WAPE %)")
    print("=" * 65)
    print(f"{'Hafta':<25} | {'PxE (n=8) WAPE (%)':<20} | {'LightGBM (ML) WAPE (%)':<20}")
    print("-" * 65)
    for _, r in res_df.iterrows():
        print(f"{r['Hafta']:<25} | %{r['PxE (n=8) WAPE (%)']:<19.2f} | %{r['LightGBM (ML) WAPE (%)']:<19.2f}")
    print("-" * 65)
    print(f"{'3-Hafta Ortalaması':<25} | %{ort_pxe:<19.2f} | %{ort_ml:<19.2f}")
    print("=" * 65)

    if ort_pxe < ort_ml:
        print(f"\nSONUÇ: PxE (n=8) yöntemi (Ort. WAPE %{ort_pxe:.2f}), LightGBM modelinden (Ort. WAPE %{ort_ml:.2f}) "
              f"{ort_ml - ort_pxe:.2f} puan DAHA DÜŞÜK (DAHA İYİ) başarım gösterdi.")
    else:
        print(f"\nSONUÇ: LightGBM yöntemi (Ort. WAPE %{ort_ml:.2f}), PxE (n=8) yönteminden (Ort. WAPE %{ort_pxe:.2f}) "
              f"{ort_pxe - ort_ml:.2f} puan DAHA DÜŞÜK (DAHA İYİ) başarım gösterdi.")
    print("=" * 65 + "\n")

    return res_df


if __name__ == "__main__":
    evaluate_backtest()

"""
LoadIQ - Uçtan Uca Çalıştırma Pipeline'ı

Bu modül:
1. Tüm kaynak verileri yükler.
2. Hazır talep tahmini dosyasını okur.
3. Taşıma planını üretir.
4. Planı Excel dosyasına kaydeder.
5. Checker ile doğrular.
6. PASS/FAIL ve maliyet özetini ekrana yazdırır.
"""

import os
import sys

import pandas as pd


# ---------------------------------------------------------------------------
# Proje yolları
# ---------------------------------------------------------------------------

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))

# src ve config modüllerinin bulunabilmesi için:
sys.path.insert(0, _THIS_DIR)
sys.path.insert(0, os.path.join(_ROOT, "config"))


from data_loader import load_all
from optimize import generate_plan
from checker import run_all_checks


FORECAST_PATH = os.path.join(_ROOT, "outputs", "Talep-tahmini.xlsx")
PLAN_PATH = os.path.join(_ROOT, "outputs", "Tasima-plani.xlsx")


# Aynı araç bacağı birden fazla talebi taşıyabilir.
# Toplam maliyet her satırda tekrarlandığından çift sayımı önlemek gerekir.
LEG_COLUMNS = [
    "Araç ID",
    "Çıkış Transfer Merkezi",
    "Varış Transfer Merkezi",
    "Çıkış Tarihi",
    "Çıkış Saati",
]


def _hesapla_maliyet_ozeti(plan_df: pd.DataFrame) -> tuple[float, float, float]:
    """
    Planın araç maliyeti, SLA cezası ve genel toplamını hesaplar.

    Araç maliyeti aynı araç bacağında birden fazla satırda tekrar
    edebileceği için bacak bazında yalnızca bir kez sayılır.
    """
    if plan_df.empty:
        return 0.0, 0.0, 0.0

    arac_maliyeti = (
        plan_df.groupby(LEG_COLUMNS, dropna=False)["Toplam maliyet"]
        .first()
        .sum()
    )

    sla_cezasi = plan_df["SLA cezası"].sum()
    genel_toplam = arac_maliyeti + sla_cezasi

    return (
        float(arac_maliyeti),
        float(sla_cezasi),
        float(genel_toplam),
    )


def run_pipeline() -> None:
    """
    LoadIQ sistemini uçtan uca çalıştırır.

    Sırasıyla:
    1. Tüm kaynak verilerini yükler.
    2. Talep-tahmini.xlsx dosyasını okur.
    3. optimize.generate_plan() ile taşıma planını üretir.
    4. Tasima-plani.xlsx dosyasını kaydeder.
    5. checker.run_all_checks() ile planı doğrular.
    6. PASS/FAIL ve maliyet özetini yazdırır.
    """
    print("=" * 70)
    print("LOADIQ - UÇTAN UCA PIPELINE")
    print("=" * 70)

    # -----------------------------------------------------------------------
    # 1. Kaynak verileri yükle
    # -----------------------------------------------------------------------
    print("\n[1/6] Kaynak veriler yükleniyor...")
    veri = load_all()
    print("Kaynak veriler yüklendi.")

    # -----------------------------------------------------------------------
    # 2. Tahmin dosyasını oku
    # -----------------------------------------------------------------------
    print("\n[2/6] Talep tahmini okunuyor...")

    if not os.path.exists(FORECAST_PATH):
        raise FileNotFoundError(
            "Talep tahmini dosyası bulunamadı:\n"
            f"{FORECAST_PATH}\n"
            "Önce forecast.py çıktısının üretildiğinden emin olun."
        )

    talep_df = pd.read_excel(FORECAST_PATH)

    if talep_df.empty:
        raise ValueError("Talep-tahmini.xlsx dosyası boş.")

    print(f"Talep tahmini okundu: {len(talep_df)} satır.")

    # -----------------------------------------------------------------------
    # 3. Planı üret
    # -----------------------------------------------------------------------
    print("\n[3/6] Taşıma planı üretiliyor...")
    plan_df = generate_plan(talep_df, veri)

    if not isinstance(plan_df, pd.DataFrame):
        raise TypeError(
            "generate_plan() bir pandas DataFrame döndürmelidir. "
            f"Dönen tip: {type(plan_df).__name__}"
        )

    if plan_df.empty:
        raise ValueError("generate_plan() boş bir taşıma planı döndürdü.")

    print(f"Taşıma planı üretildi: {len(plan_df)} satır.")

    # -----------------------------------------------------------------------
    # 4. Planı kaydet
    # -----------------------------------------------------------------------
    print("\n[4/6] Taşıma planı kaydediliyor...")
    os.makedirs(os.path.dirname(PLAN_PATH), exist_ok=True)
    plan_df.to_excel(PLAN_PATH, index=False)
    print(f"Taşıma planı kaydedildi:\n{PLAN_PATH}")

    # -----------------------------------------------------------------------
    # 5. Checker doğrulaması
    # -----------------------------------------------------------------------
    print("\n[5/6] Plan doğrulanıyor...")

    rapor = run_all_checks(
        talep_df=talep_df,
        plan_df=plan_df,
        mesafe_df=veri["mesafe"],
        tir_kapasitesi_df=veri["tir_kapasitesi"],
        ellecleme_df=veri["ellecleme_kapasitesi"],
        arac_maliyet_df=veri["arac_maliyet"],
    )

    print("\n" + rapor.ozet())

    # -----------------------------------------------------------------------
    # 6. Maliyet özeti
    # -----------------------------------------------------------------------
    print("\n[6/6] Maliyet özeti hesaplanıyor...")

    arac_maliyeti, sla_cezasi, genel_toplam = _hesapla_maliyet_ozeti(
        plan_df
    )

    print("\n" + "-" * 70)
    print("PIPELINE SONUCU")
    print("-" * 70)
    print(f"Durum              : {'FAIL' if rapor.hata_var_mi else 'PASS'}")
    print(f"Plan satırı         : {len(plan_df):,}")
    print(f"Benzersiz araç      : {plan_df['Araç ID'].nunique():,}")
    print(f"Araç maliyeti       : {arac_maliyeti:,.2f} TL")
    print(f"Toplam SLA cezası   : {sla_cezasi:,.2f} TL")
    print(f"Genel toplam maliyet: {genel_toplam:,.2f} TL")
    print("-" * 70)

    if rapor.hata_var_mi:
        print("\nPipeline tamamlandı ancak doğrulama sonucu FAIL.")
    else:
        print("\nPipeline başarıyla tamamlandı: PASS.")


if __name__ == "__main__":
    run_pipeline()
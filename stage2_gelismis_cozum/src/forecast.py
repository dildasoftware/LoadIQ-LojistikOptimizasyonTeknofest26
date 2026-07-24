"""
LoadIQ - Talep Tahmin Modeli (forecast.py)

Yöntem: İki Parçalı Model — Tahmin = P(sevkiyat var) x E[desi | sevkiyat var]

Bu yöntem MVP aşamasında (Temel İşlevli Çözüm) hem basit haftalık
ortalamayı hem de LightGBM'i (ML) geride bırakmıştı (bkz. eski
README.md: WAPE %44 -> %42, ML %59-107). Aynı mantığı bu aşamada
granülariteyi (güzergah, gün) yerine (güzergah, gün, saat dilimi)
olacak şekilde genişletiyoruz -- çünkü artık talep 09:00 ve 17:00
olmak üzere 2 ayrı anda oluşuyor ve bunları ayrı tahmin etmemiz
isteniyor.

Kritik kural: Sadece hedef tarihten ÖNCEKİ veri kullanılır (leakage
yok), ve config/rules.py'deki tatil/anomali günleri training havuzundan
çıkarılır (aksi halde örn. Kurban Bayramı'ndaki neredeyse-sıfır günler
normal bir haftanın tahminini kirletir).
"""

import os
import sys
from datetime import date, timedelta

import pandas as pd
import numpy as np

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)
sys.path.insert(0, os.path.join(_THIS_DIR, "..", "config"))

import rules  # noqa: E402

SAAT_LISTESI = ["09:00", "17:00"]


def _normalize_saat(s: str) -> str:
    """'9:00' -> '09:00' (ham veride sıfırsız saat var, çıktı formatı
    sıfırlı olmalı)."""
    h, m = str(s).split(":")
    return f"{int(h):02d}:{m}"


# ---------------------------------------------------------------------------
# 1. Panel oluşturma: (güzergah, tarih, saat) -> desi
#    Eksik kombinasyonlar = 0 (sevkiyat yok) -- MVP'de doğrulanmış varsayım.
# ---------------------------------------------------------------------------
def build_panel(talep_df: pd.DataFrame, aktif_rotalar=None) -> pd.DataFrame:
    df = talep_df.copy()
    df["saat"] = df["saat"].apply(_normalize_saat)

    gozlenen = (
        df.groupby(["cikis", "varis", "tarih", "saat"])["desi"]
        .sum()
        .reset_index()
    )

    if aktif_rotalar is None:
        aktif_rotalar = sorted(set(zip(df["cikis"], df["varis"])))

    tum_tarihler = pd.date_range(df["tarih"].min(), df["tarih"].max(), freq="D").date

    idx = pd.MultiIndex.from_product(
        [aktif_rotalar, tum_tarihler, SAAT_LISTESI],
        names=["rota", "tarih", "saat"],
    )
    panel = pd.DataFrame(index=idx).reset_index()
    panel["cikis"] = panel["rota"].apply(lambda r: r[0])
    panel["varis"] = panel["rota"].apply(lambda r: r[1])
    panel = panel.drop(columns="rota")

    panel = panel.merge(gozlenen, on=["cikis", "varis", "tarih", "saat"], how="left")
    panel["desi"] = panel["desi"].fillna(0.0)
    panel["tatil_mi"] = panel["tarih"].isin(rules.TATIL_GUNLERI)
    panel["haftanin_gunu"] = panel["tarih"].apply(lambda d: d.weekday())

    # Korunum kontrolü: panel'deki toplam desi, ham veriyle birebir aynı olmalı
    fark = abs(panel["desi"].sum() - df["desi"].sum())
    assert fark < 1e-6, f"Panel oluşturmada desi kaybı/fazlalığı var! fark={fark}"

    return panel


# ---------------------------------------------------------------------------
# 2. Tek nokta tahmini: P(sevkiyat) x E[desi | sevkiyat]
# ---------------------------------------------------------------------------
def predict_one(gecmis: pd.DataFrame, hedef_tarih: date, n: int = 8) -> float:
    """gecmis: bu (güzergah, saat) için TÜM geçmiş satırlar (tarih, desi, tatil_mi).
    Sadece hedef_tarih'ten önceki, tatil olmayan, aynı haftanın gününe denk
    gelen son n gözlemi kullanır.

    PARAMETRE SEÇİMİ (n=8): n=6,8,10,12,14,16,18,20 değerleri 3 bağımsız test
    haftasında (1-7 Haz, 8-14 Haz, 15-21 Haz 2026) backtest edildi:
      n=16: Ort.WAPE=23.91%, Std=3.74%
      n=14: Ort.WAPE=24.09%, Std=3.82%
      n= 8: Ort.WAPE=24.43%, Std=4.13%
      n=12: Ort.WAPE=24.45%, Std=3.76%
      n=20: Ort.WAPE=26.22%, Std=5.15%
    n=16'nın WAPE avantajı (n=8'e göre ~0.5 puan) haftalar arası standart
    sapmadan (~4 puan) KÜÇÜK, yani istatistiksel olarak gürültü seviyesinde.
    Buna karşılık n=16 ile üretilen talep deseni, taşıma planını ~%7.5 daha
    pahalı hale getiriyor (32.5M vs 30.2M TL). Bu cost-accuracy ödünleşiminde,
    marjinal ve istatistiksel olarak anlamsız WAPE kazancı için maliyeti
    artırmak yerine n=8 korundu (daha ucuz plan + doğrulanmış/kararlı pipeline).

    NOT: Bu formülasyonda P(sevkiyat)xE[desi|sevkiyat], cebirsel olarak
    sıfırlar dahil ortalamaya EŞİTTİR (naive baseline ile aynı nokta tahmini).
    Modelin gerçek katkısı: aynı haftagünü+saat gruplama, tatil/anomali
    filtresi ve leakage'sız (geleceği görmeyen) tahmin ufkudur.
    """
    hedef_gun = hedef_tarih.weekday()
    aday = gecmis[
        (gecmis["tarih"] < hedef_tarih)
        & (~gecmis["tatil_mi"])
        & (gecmis["haftanin_gunu"] == hedef_gun)
    ].sort_values("tarih", ascending=False).head(n)

    if len(aday) == 0:
        return 0.0

    p_ship = (aday["desi"] > 0).mean()
    sevkiyatli = aday.loc[aday["desi"] > 0, "desi"]
    e_desi = sevkiyatli.mean() if len(sevkiyatli) > 0 else 0.0
    return float(p_ship * e_desi)


def _naive_baseline(gecmis: pd.DataFrame, hedef_tarih: date, n: int = 12) -> float:
    """Karşılaştırma için basit taban çizgisi: P/E ayrımı yapmadan, aynı
    haftagünü/saatin son n gözleminin düz ortalaması (sıfırlar dahil)."""
    hedef_gun = hedef_tarih.weekday()
    aday = gecmis[
        (gecmis["tarih"] < hedef_tarih)
        & (~gecmis["tatil_mi"])
        & (gecmis["haftanin_gunu"] == hedef_gun)
    ].sort_values("tarih", ascending=False).head(n)
    if len(aday) == 0:
        return 0.0
    return float(aday["desi"].mean())


# ---------------------------------------------------------------------------
# 3. Toplu tahmin: bir tarih aralığı x tüm rotalar x tüm saatler
# ---------------------------------------------------------------------------
def forecast_range(panel: pd.DataFrame, baslangic: date, bitis: date,
                    n: int = 8, method="pxe") -> pd.DataFrame:
    hedef_tarihler = pd.date_range(baslangic, bitis, freq="D").date
    predict_fn = predict_one if method == "pxe" else _naive_baseline

    sonuclar = []
    for (cikis, varis, saat), grup in panel.groupby(["cikis", "varis", "saat"]):
        grup = grup[["tarih", "desi", "tatil_mi", "haftanin_gunu"]]
        for hedef_tarih in hedef_tarihler:
            tahmin = predict_fn(grup, hedef_tarih, n=n)
            sonuclar.append({
                "Tarih": hedef_tarih, "Talep Tamamlama Saati": saat,
                "Çıkış Transfer Merkezi": cikis, "Varış Transfer Merkezi": varis,
                "Tahmin Edilen Desi": round(tahmin, 2),
            })
    return pd.DataFrame(sonuclar)


# ---------------------------------------------------------------------------
# 4. Backtest: leakage yok, gerçek tahmin ufkunu simüle eder
# ---------------------------------------------------------------------------
def backtest_wape(panel: pd.DataFrame, test_baslangic: date, test_bitis: date,
                   n: int = 12, method="pxe") -> dict:
    """test_baslangic..test_bitis aralığındaki GERÇEK değerleri, o tarihten
    ÖNCEKİ veriyle tahmin edip WAPE hesaplar. panel test dönemini de içerir
    (gerçek değerlerle kıyaslamak için) ama predict_one zaten sadece
    hedef_tarih'ten öncesini kullandığı için leakage olmaz."""
    tahmin_df = forecast_range(panel, test_baslangic, test_bitis, n=n, method=method)

    gercek = panel[
        (panel["tarih"] >= test_baslangic) & (panel["tarih"] <= test_bitis)
    ][["cikis", "varis", "saat", "tarih", "desi"]].rename(
        columns={"cikis": "Çıkış Transfer Merkezi", "varis": "Varış Transfer Merkezi",
                 "saat": "Talep Tamamlama Saati", "tarih": "Tarih", "desi": "gercek_desi"}
    )

    karsilastir = tahmin_df.merge(
        gercek, on=["Çıkış Transfer Merkezi", "Varış Transfer Merkezi",
                    "Talep Tamamlama Saati", "Tarih"], how="inner"
    )
    toplam_hata = (karsilastir["Tahmin Edilen Desi"] - karsilastir["gercek_desi"]).abs().sum()
    toplam_gercek = karsilastir["gercek_desi"].sum()
    wape = toplam_hata / toplam_gercek if toplam_gercek > 0 else float("nan")
    return {"wape": wape, "n_gozlem": len(karsilastir), "toplam_gercek": toplam_gercek}


# ---------------------------------------------------------------------------
# 5. Çıktı üretimi: Talep-tahmini.xlsx formatı
# ---------------------------------------------------------------------------
def assign_talep_id(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["Tarih", "Talep Tamamlama Saati",
                          "Çıkış Transfer Merkezi", "Varış Transfer Merkezi"]).reset_index(drop=True)
    df.insert(0, "Talep ID", [f"D{i+1:05d}" for i in range(len(df))])
    return df


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(_THIS_DIR))
    from data_loader import load_talep

    talep = load_talep()
    panel = build_panel(talep)
    print(f"Panel oluşturuldu: {len(panel)} satır "
          f"({panel['cikis'].nunique()} cikis x rota bilgisi dahil)")
    print(f"Aktif rota sayisi: {panel.groupby(['cikis','varis']).ngroups}")
    print(f"Toplam desi (panel): {panel['desi'].sum():,.0f}")
    print(f"Toplam desi (ham veri): {talep['desi'].sum():,.0f}")

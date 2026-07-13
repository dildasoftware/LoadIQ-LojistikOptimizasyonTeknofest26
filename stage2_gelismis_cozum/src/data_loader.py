"""
LoadIQ - Veri Yükleme ve Doğrulama Katmanı

Görevi: data/raw/ altındaki 8 ham excel dosyasını okur, temizler,
tip dönüşümlerini yapar ve config/rules.py'deki kısıtları uygular.
Her fonksiyon sonunda kendi verisini doğrular (assert) -- yanlış/bozuk
veri sessizce ilerlemez, hemen hata verir.

Kullanım:
    from data_loader import load_all
    veri = load_all()
    veri["talep"]            # DataFrame
    veri["mesafe"]           # DataFrame
    ...
"""

import os
import sys
import pandas as pd

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
_RAW_DIR = os.path.join(_PROJECT_ROOT, "data", "raw")
_PROCESSED_DIR = os.path.join(_PROJECT_ROOT, "data", "processed")

sys.path.insert(0, os.path.join(_PROJECT_ROOT, "config"))
import rules  # noqa: E402


def _path(filename: str) -> str:
    p = os.path.join(_RAW_DIR, filename)
    if not os.path.exists(p):
        raise FileNotFoundError(f"Beklenen veri dosyası bulunamadı: {p}")
    return p


def load_talep() -> pd.DataFrame:
    """Geçmiş talep verisi: tarih, çıkış/varış TM, talep_id, desi, saat.

    66.024 satırlık dosyayı excel'den her seferinde okumak ~7 saniye
    sürüyor (openpyxl yavaş). İlk okumadan sonra data/processed/ altına
    CSV önbelleği yazılır; sonraki çağrılar oradan ~0.1 saniyede okur.
    Ham excel dosyası değişirse önbellek otomatik yenilenir (mtime kontrolü).
    """
    os.makedirs(_PROCESSED_DIR, exist_ok=True)
    raw_path = _path("Talep_Verisi.xlsx")
    cache_path = os.path.join(_PROCESSED_DIR, "talep_cache.csv")

    use_cache = (
        os.path.exists(cache_path)
        and os.path.getmtime(cache_path) > os.path.getmtime(raw_path)
    )
    if use_cache:
        df = pd.read_csv(cache_path)
        df["tarih"] = pd.to_datetime(df["tarih"]).dt.date
    else:
        df = pd.read_excel(raw_path)
        df.columns = ["tarih", "cikis", "varis", "talep_id", "desi", "saat"]
        df["tarih"] = pd.to_datetime(df["tarih"]).dt.date
        df.to_csv(cache_path, index=False)

    assert (df["desi"] >= 0).all(), "Negatif desi bulundu!"
    assert df["cikis"].notna().all() and df["varis"].notna().all(), "Boş TM adı var!"
    assert set(df["saat"].unique()) <= {"9:00", "17:00", "09:00"}, \
        f"Beklenmeyen saat değeri: {df['saat'].unique()}"

    # Kocaeli'ye varışlı satırları bilerek işaretle (kullanılmayacak ama
    # veri kaybını gizlememek için filtrelemiyoruz, flag ekliyoruz)
    df["haric_tutulan_rota"] = df.apply(
        lambda r: rules.is_route_excluded(r["cikis"], r["varis"]), axis=1
    )
    df["tatil_mi"] = df["tarih"].isin(rules.TATIL_GUNLERI)
    return df


def load_mesafe() -> pd.DataFrame:
    """TM çiftleri arası mesafe, araç tipine göre süre (saat), SLA gün sayısı."""
    df = pd.read_excel(_path("Mesafe_Sure_Matrisi.xlsx"))
    df.columns = [
        "cikis", "varis", "mesafe_km", "tir_saat", "kamyon_saat",
        "hafif_kamyon_saat", "kamyonet_saat", "sla_gun",
    ]
    assert (df["mesafe_km"] > 0).all(), "Sıfır/negatif mesafe bulundu!"
    assert set(df["sla_gun"].unique()) <= {1, 2}, \
        f"Beklenmeyen SLA gün değeri: {df['sla_gun'].unique()}"
    return df


def load_ellecleme_kapasitesi() -> pd.DataFrame:
    df = pd.read_excel(_path("Ellecleme_Kapasitesi.xlsx"))
    df.columns = ["tm", "gunluk_kapasite_desi"]
    assert (df["gunluk_kapasite_desi"] > 0).all(), "Sıfır elleçleme kapasitesi bulundu!"
    return df


def load_tir_kapasitesi() -> pd.DataFrame:
    df = pd.read_excel(_path("Tir_Kapasitesi.xlsx"))
    df.columns = ["tm", "tir_kapasitesi"]
    assert (df["tir_kapasitesi"] >= 0).all(), "Negatif tır kapasitesi bulundu!"

    # config/rules.py'deki tamamen yasak listesiyle çapraz kontrol
    sifir_olanlar = set(df[df["tir_kapasitesi"] == 0]["tm"])
    beklenen = rules.TIR_TAMAMEN_YASAK_TM
    if sifir_olanlar != beklenen:
        print(
            "UYARI: tir kapasitesi=0 olan TM listesi config/rules.py ile "
            f"uyuşmuyor. Veride: {sifir_olanlar} | Kuralda: {beklenen}. "
            "Muhtemelen veri güncellenmiş, rules.py'yi kontrol edin."
        )
    return df


def load_kiralik_araclar() -> pd.DataFrame:
    df = pd.read_excel(_path("Kiralik_Araclar.xlsx"))
    df.columns = ["cikis", "varis", "arac_sayisi", "arac_turu"]
    assert (df["arac_sayisi"] > 0).all(), "Sıfır/negatif kiralık araç sayısı!"
    return df


def load_arac_maliyet() -> pd.DataFrame:
    df = pd.read_excel(_path("Arac_Maliyet_Tablosu.xlsx"))
    df.columns = [
        "arac_adi", "kapasite_desi", "kiralik_saatlik_tl",
        "kiralik_km_tl", "spot_saatlik_tl", "spot_km_tl",
    ]
    beklenen_araclar = {"Tır", "Kamyon", "Hafif Kamyon", "Kamyonet"}
    assert set(df["arac_adi"]) == beklenen_araclar, \
        f"Araç tablosu beklenmedik tipler içeriyor: {set(df['arac_adi'])}"
    return df


def load_all() -> dict:
    """Tüm veri setlerini yükler ve TM listesinin tüm dosyalarda tutarlı
    olduğunu doğrular."""
    veri = {
        "talep": load_talep(),
        "mesafe": load_mesafe(),
        "ellecleme_kapasitesi": load_ellecleme_kapasitesi(),
        "tir_kapasitesi": load_tir_kapasitesi(),
        "kiralik_araclar": load_kiralik_araclar(),
        "arac_maliyet": load_arac_maliyet(),
    }

    tm_talep = set(veri["talep"]["cikis"]) | set(veri["talep"]["varis"])
    tm_ellecleme = set(veri["ellecleme_kapasitesi"]["tm"])
    tm_tir = set(veri["tir_kapasitesi"]["tm"])

    assert tm_ellecleme == tm_tir, (
        f"TM listesi elleçleme ve tır kapasitesi dosyalarında farklı! "
        f"Sadece elleçlemede: {tm_ellecleme - tm_tir}, "
        f"Sadece tırda: {tm_tir - tm_ellecleme}"
    )
    assert tm_talep <= (tm_ellecleme | {"Kocaeli"}), (
        f"Talep verisinde tanımsız TM var: {tm_talep - tm_ellecleme}"
    )

    return veri


if __name__ == "__main__":
    veri = load_all()
    print("=== Veri yükleme başarılı ===")
    for ad, df in veri.items():
        print(f"  {ad:24s}: {len(df):>7} satır")

    talep = veri["talep"]
    print()
    print("Toplam satır (Kocaeli-haric dahil):", len(talep))
    print("Haric tutulan (Kocaeli varisli) satir sayisi:", talep["haric_tutulan_rota"].sum())
    print("Tatil gunu isaretli satir sayisi:", talep["tatil_mi"].sum())
    print("Benzersiz TM sayisi:", len(set(talep["cikis"]) | set(talep["varis"])))
    print("Benzersiz aktif rota sayisi:", talep.groupby(["cikis", "varis"]).ngroups)

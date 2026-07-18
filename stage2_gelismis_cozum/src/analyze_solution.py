"""
LoadIQ - Çözüm Analiz Modülü (analyze_solution.py)
Teknofest 2026 Lojistik Optimizasyon - Gelişmiş Çözüm Aşaması

Bu modül optimize.generate_plan() çıktısını alıp profesyonel bir analiz üretir.
Mevcut hiçbir dosyayı değiştirmez; tamamen bağımsız çalışır.
"""

import os
import sys
import datetime
from typing import Dict, Tuple
from collections import defaultdict

import pandas as pd
import numpy as np

# --- Proje yolları ---
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
sys.path.insert(0, _THIS_DIR)
sys.path.insert(0, os.path.join(_ROOT, "config"))

from data_loader import load_all
from optimize import generate_plan
from time_utils import handling_minutes, split_handling_across_midnight
import rules

# ---------------------------------------------------------------------------
# YARDIMCI: yazdırma
# ---------------------------------------------------------------------------
SEP = "=" * 70
SEP2 = "-" * 70

def _header(title: str) -> None:
    """Bölüm başlığı yazdır."""
    print(f"\n{SEP}\n  {title}\n{SEP}")

def _fmt(val: float, suffix: str = " TL") -> str:
    """Sayıyı okunabilir formatta döndür."""
    return f"{val:,.2f}{suffix}"

# ---------------------------------------------------------------------------
# 1. TOPLAM MALİYET RAPORU
# ---------------------------------------------------------------------------
def analiz_toplam_maliyet(plan: pd.DataFrame) -> Dict:
    """Araç maliyeti, SLA maliyeti ve toplam maliyeti hesaplar.

    ÖNEMLİ: 'Toplam maliyet' sütunu her leg (araç seferi) için tek değer
    içerir, ancak bir araç birden fazla talep taşıyorsa aynı satır tekrar
    eder. Çift sayımı önlemek için groupby(leg_cols).first() kullanılır.
    Bu yaklaşım run_checker_local.py ile birebir aynıdır.
    """
    # Leg bazında araç maliyeti (çift sayım önlenir)
    _LEG_COLS = ["Araç ID", "Çıkış Transfer Merkezi", "Varış Transfer Merkezi",
                 "Çıkış Tarihi", "Çıkış Saati"]
    arac_maliyet_toplam = plan.groupby(_LEG_COLS)["Toplam maliyet"].first().sum()

    # SLA cezası talep/satır bazındadır — direkt toplam doğrudur
    sla_toplam = plan["SLA cezası"].sum()

    toplam = arac_maliyet_toplam + sla_toplam
    sla_oran = (sla_toplam / toplam * 100) if toplam > 0 else 0

    _header("1. TOPLAM MALİYET RAPORU")
    print(f"  Araç Maliyeti   : {_fmt(arac_maliyet_toplam)}")
    print(f"  SLA Cezası      : {_fmt(sla_toplam)}")
    print(f"  Toplam Maliyet  : {_fmt(toplam)}")
    print(f"  SLA Oranı       : %{sla_oran:.1f}")
    print(f"  [Benzersiz sefer: {plan.groupby(_LEG_COLS).ngroups}, Toplam satır: {len(plan)}]")

    return {
        "arac_maliyet": arac_maliyet_toplam,
        "sla_maliyet": sla_toplam,
        "toplam": toplam,
        "sla_oran": sla_oran,
    }

# ---------------------------------------------------------------------------
# 2. ARAÇ DAĞILIMI
# ---------------------------------------------------------------------------
def analiz_arac_dagilimi(plan: pd.DataFrame) -> pd.DataFrame:
    """Araç türü ve tipine göre kullanım dağılımını gösterir."""
    # Her sefer benzersiz Araç ID ile
    araclar = plan.drop_duplicates(subset=["Araç ID"])[["Araç ID", "Araç Tipi", "Araç türü"]]
    pivot = (
        araclar.groupby(["Araç türü", "Araç Tipi"])
        .size()
        .reset_index(name="Adet")
    )
    _header("2. ARAÇ DAĞILIMI")
    for _, row in pivot.iterrows():
        print(f"  {row['Araç türü']:15s} | {row['Araç Tipi']:8s} | {row['Adet']:5d} adet")
    return pivot

# ---------------------------------------------------------------------------
# 3. EN PAHALI 20 TALEP
# ---------------------------------------------------------------------------
def analiz_en_pahali_talepler(plan: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    """Her talep satırı için araç + SLA toplamını hesaplar ve sıralar."""
    df = plan.copy()
    df["Toplam Talep Maliyeti"] = df["Toplam maliyet"] + df["SLA cezası"]
    top = df.nlargest(n, "Toplam Talep Maliyeti")[[
        "Talep ID", "Araç türü", "Toplam maliyet", "SLA cezası",
        "Toplam Talep Maliyeti", "Taşınan Desi",
        "Çıkış Transfer Merkezi", "Varış Transfer Merkezi"
    ]]
    _header(f"3. EN PAHALI {n} TALEP")
    print(top.to_string(index=False))
    return top

# ---------------------------------------------------------------------------
# 4. EN FAZLA SLA CEZASI OLUŞTURAN 20 ROTA
# ---------------------------------------------------------------------------
def analiz_sla_rota(plan: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    """Rota bazında toplam SLA, toplam desi ve ortalama gecikme analizi."""
    df = plan.copy()
    # gecikme saatini SLA cezasından geri hesapla: ceza = desi * saat * 0.4
    df["gecikme_saat"] = df.apply(
        lambda r: r["SLA cezası"] / (r["Taşınan Desi"] * rules.SLA_CEZA_TL_PER_DESI_SAAT)
        if r["Taşınan Desi"] > 0 and r["SLA cezası"] > 0 else 0,
        axis=1,
    )
    grp = (
        df.groupby(["Çıkış Transfer Merkezi", "Varış Transfer Merkezi", "Araç türü"])
        .agg(
            Toplam_SLA=("SLA cezası", "sum"),
            Toplam_Desi=("Taşınan Desi", "sum"),
            Ort_Gecikme=("gecikme_saat", "mean"),
        )
        .reset_index()
        .nlargest(n, "Toplam_SLA")
    )
    _header(f"4. EN FAZLA SLA CEZASI OLUŞTURAN {n} ROTA")
    print(grp.to_string(index=False))
    return grp

# ---------------------------------------------------------------------------
# 5. EN FAZLA GECİKME ÜRETEN 20 TM
# ---------------------------------------------------------------------------
def analiz_gec_tm(plan: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    """Çıkış TM bazında toplam SLA cezası."""
    df = plan[plan["SLA cezası"] > 0]
    grp = (
        df.groupby("Çıkış Transfer Merkezi")["SLA cezası"]
        .sum()
        .reset_index()
        .rename(columns={"SLA cezası": "Toplam_SLA"})
        .nlargest(n, "Toplam_SLA")
    )
    _header(f"5. EN FAZLA GECİKME ÜRETEN {n} TM")
    print(grp.to_string(index=False))
    return grp

# ---------------------------------------------------------------------------
# 6. GÜNLERE GÖRE SLA DAĞILIMI
# ---------------------------------------------------------------------------
def analiz_gunluk_sla(plan: pd.DataFrame) -> pd.DataFrame:
    """Çıkış tarihine göre SLA cezası dağılımı."""
    grp = (
        plan.groupby("Çıkış Tarihi")["SLA cezası"]
        .sum()
        .reset_index()
        .sort_values("Çıkış Tarihi")
    )
    _header("6. GÜNLERE GÖRE SLA DAĞILIMI")
    print(grp.to_string(index=False))
    return grp

# ---------------------------------------------------------------------------
# 7. SAATLERE GÖRE SLA DAĞILIMI
# ---------------------------------------------------------------------------
def analiz_saatlik_sla(plan: pd.DataFrame) -> pd.DataFrame:
    """Çıkış saatine (09:00 / 17:00) göre SLA cezası dağılımı."""
    grp = (
        plan.groupby("Çıkış Saati")["SLA cezası"]
        .sum()
        .reset_index()
        .sort_values("SLA cezası", ascending=False)
    )
    _header("7. SAATLERE GÖRE SLA DAĞILIMI")
    print(grp.to_string(index=False))
    return grp

# ---------------------------------------------------------------------------
# 8. KİRALIK ARAÇ ANALİZİ
# ---------------------------------------------------------------------------
def analiz_kiralik(plan: pd.DataFrame, veri: dict) -> pd.DataFrame:
    """Her kiralık araç güzergahı için doluluk ve boş sefer analizi."""
    kiralik = plan[plan["Araç Tipi"] == "Kiralık"]
    kiralik_araclar_df = veri["kiralik_araclar"]
    arac_maliyet_df = veri["arac_maliyet"]

    cap_map = {
        row["arac_adi"]: row["kapasite_desi"]
        for _, row in arac_maliyet_df.iterrows()
    }

    grp = (
        kiralik.groupby(["Çıkış Transfer Merkezi", "Varış Transfer Merkezi", "Araç türü"])
        .agg(
            Toplam_Sefer=("Araç ID", "nunique"),
            Toplam_Desi=("Taşınan Desi", "sum"),
        )
        .reset_index()
    )
    grp["Kapasite_Per_Sefer"] = grp["Araç türü"].map(cap_map)
    grp["Toplam_Kapasite"] = grp["Toplam_Sefer"] * grp["Kapasite_Per_Sefer"]
    grp["Doluluk_%"] = (grp["Toplam_Desi"] / grp["Toplam_Kapasite"] * 100).round(1)
    grp["Bos_Sefer"] = (kiralik[kiralik["Taşınan Desi"] == 0]
                        .groupby(["Çıkış Transfer Merkezi", "Varış Transfer Merkezi", "Araç türü"])
                        ["Araç ID"].nunique()
                        .reindex(grp.set_index(["Çıkış Transfer Merkezi", "Varış Transfer Merkezi", "Araç türü"]).index, fill_value=0)
                        .values)
    grp["Bos_Kapasite"] = grp["Toplam_Kapasite"] - grp["Toplam_Desi"]

    _header("8. KİRALIK ARAÇ ANALİZİ")
    print(grp.to_string(index=False))
    return grp

# ---------------------------------------------------------------------------
# 9. SPOT ARAÇ ANALİZİ
# ---------------------------------------------------------------------------
def analiz_spot(plan: pd.DataFrame, veri: dict) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Spot araç tipi ve rota bazında kullanım yoğunluğu ve ortalama doluluk."""
    spot = plan[plan["Araç Tipi"] == "Spot"]
    cap_map = {
        row["arac_adi"]: row["kapasite_desi"]
        for _, row in veri["arac_maliyet"].iterrows()
    }

    # Her benzersiz araç seferi (Araç ID) için toplam desi ve araç türü
    seferler = spot.groupby(["Araç ID", "Araç türü"])["Taşınan Desi"].sum().reset_index()
    seferler["Kapasite"] = seferler["Araç türü"].map(cap_map)
    seferler["Doluluk_%"] = (seferler["Taşınan Desi"] / seferler["Kapasite"] * 100)

    # Araç türü bazında grupla ve ortalama doluluğu al
    tip_grp = (
        seferler.groupby("Araç türü")
        .agg(
            Adet=("Araç ID", "count"),
            Toplam_Desi=("Taşınan Desi", "sum"),
            Ort_Doluluk_Yuzde=("Doluluk_%", "mean")
        )
        .reset_index()
        .sort_values("Adet", ascending=False)
    )
    # Oranları yuvarla
    tip_grp["Ort_Doluluk_Yuzde"] = tip_grp["Ort_Doluluk_Yuzde"].round(1)

    rota_grp = (
        spot.groupby(["Çıkış Transfer Merkezi", "Varış Transfer Merkezi"])
        .agg(Adet=("Araç ID", "nunique"), Toplam_Desi=("Taşınan Desi", "sum"))
        .reset_index()
        .nlargest(20, "Adet")
    )

    _header("9. SPOT ARAÇ ANALİZİ")
    print("  -- Araç Tipi Bazında --")
    print(tip_grp.to_string(index=False))
    print("\n  -- Yoğun Rotalar (İlk 20) --")
    print(rota_grp.to_string(index=False))
    return tip_grp, rota_grp

# ---------------------------------------------------------------------------
# 10. ELLEÇLEMEKAPASİTE ANALİZİ
# ---------------------------------------------------------------------------
def _to_dt(tarih, saat_str) -> datetime.datetime:
    """tarih (date/Timestamp) + 'HH:MM' -> datetime"""
    if isinstance(tarih, pd.Timestamp):
        tarih = tarih.date()
    elif isinstance(tarih, datetime.date):
        pass
    elif isinstance(tarih, str):
        tarih = datetime.datetime.strptime(tarih, "%Y-%m-%d").date()
    h, m = map(int, str(saat_str).split(":"))
    return datetime.datetime(tarih.year, tarih.month, tarih.day, h, m)


def analiz_ellecleme(plan: pd.DataFrame, veri: dict) -> pd.DataFrame:
    """TM ve güne göre taşınan toplam desiyi kapasite ile karşılaştırır.
    
    TUTARLILIK DOĞRULAMASI (Bölüm 10 vs checker.py):
    Buradaki hesaplama, checker.py'deki split_handling_across_midnight mantığını
    birebir kullanarak gece yarısı oransal bölmesini eksiksiz simüle eder.
    """
    cap_df = veri["ellecleme_kapasitesi"].set_index("tm")["gunluk_kapasite_desi"]
    kullanim = defaultdict(float)

    for _, row in plan.iterrows():
        desi = row["Taşınan Desi"]

        # Çıkış elleçlemesi
        if pd.notna(row.get("Çıkış Tarihi")) and pd.notna(row.get("Çıkış Saati")):
            cikis_bitis = _to_dt(row["Çıkış Tarihi"], row["Çıkış Saati"])
            sure = row.get("Çıkış Elleçleme süresi")
            if pd.isna(sure):
                sure = row.get("Çıkış elleçleme süresi")
            if pd.isna(sure):
                sure = handling_minutes(desi)
            baslangic = cikis_bitis - datetime.timedelta(minutes=int(sure))
            for tarih, dk, desi_payi in split_handling_across_midnight(baslangic, int(sure), desi):
                kullanim[(row["Çıkış Transfer Merkezi"], tarih)] += desi_payi

        # Varış elleçlemesi
        if pd.notna(row.get("Varış Tarihi")) and pd.notna(row.get("Varış Saati")):
            varis_baslangic = _to_dt(row["Varış Tarihi"], row["Varış Saati"])
            sure = row.get("Varış elleçleme süresi")
            if pd.isna(sure):
                sure = row.get("Varış Elleçleme süresi")
            if pd.isna(sure):
                sure = handling_minutes(desi)
            for tarih, dk, desi_payi in split_handling_across_midnight(varis_baslangic, int(sure), desi):
                kullanim[(row["Varış Transfer Merkezi"], tarih)] += desi_payi

    # combined dataframe oluştur
    records = []
    for (tm, tarih), toplam_desi in kullanim.items():
        records.append({
            "TM": tm,
            "Tarih": tarih,
            "Desi": toplam_desi
        })
    
    if not records:
        combined = pd.DataFrame(columns=["TM", "Tarih", "Desi", "Kapasite", "Doluluk_%", "Asim_mi"])
    else:
        combined = pd.DataFrame(records)
        combined["Kapasite"] = combined["TM"].map(cap_df)
        combined["Doluluk_%"] = (combined["Desi"] / combined["Kapasite"] * 100).round(1)
        combined["Asim_mi"] = combined["Doluluk_%"] > 100

    asim = combined[combined["Asim_mi"]]
    _header("10. ELLEÇLEME KAPASİTE ANALİZİ")
    print(f"  Kapasite aşım sayısı: {len(asim)}")
    if not asim.empty:
        print(asim.to_string(index=False))
    dolu = combined.nlargest(10, "Doluluk_%")
    print("\n  -- En Dolu 10 TM/Gün --")
    print(dolu.to_string(index=False))
    return combined

# ---------------------------------------------------------------------------
# 11. TIR KAPASİTE ANALİZİ
# ---------------------------------------------------------------------------
def analiz_tir_kapasite(plan: pd.DataFrame, veri: dict) -> pd.DataFrame:
    """TM ve gün bazında TIR kullanım ve boş kapasite analizi.
    
    TUTARLILIK DOĞRULAMASI (Bölüm 11 vs checker.py):
    Buradaki hesaplama, checker.py'deki check_tir_capacity mantığını
    birebir kullanarak (Araç ID, TM, Tarih, Yön) bazında benzersiz
    TIR hareketlerini sayar.
    """
    tir_cap_df = veri["tir_kapasitesi"].set_index("tm")["tir_kapasitesi"]
    tirlar = plan[plan["Araç türü"] == "Tır"]

    # (tm, tarih) -> {(arac_id, yon)} kümesi
    kullanim = defaultdict(set)
    for _, row in tirlar.iterrows():
        arac_id = row["Araç ID"]
        for tm, tarih, yon in [
            (row["Çıkış Transfer Merkezi"], row["Çıkış Tarihi"], "cikis"),
            (row["Varış Transfer Merkezi"], row["Varış Tarihi"], "varis"),
        ]:
            if pd.isna(tarih):
                continue
            # Tarihi date nesnesine çevir
            if isinstance(tarih, pd.Timestamp):
                t_date = tarih.date()
            elif isinstance(tarih, datetime.date):
                t_date = tarih
            elif isinstance(tarih, str):
                t_date = datetime.datetime.strptime(tarih, "%Y-%m-%d").date()
            else:
                t_date = tarih
            kullanim[(tm, t_date)].add((arac_id, yon))

    # combined dataframe oluştur
    records = []
    for (tm, tarih), kullananlar in kullanim.items():
        records.append({
            "TM": tm,
            "Tarih": tarih,
            "Kullanilan": len(kullananlar)
        })

    if not records:
        combined = pd.DataFrame(columns=["TM", "Tarih", "Kullanilan", "Kapasite", "Bos"])
    else:
        combined = pd.DataFrame(records)
        combined["Kapasite"] = combined["TM"].map(tir_cap_df).fillna(0).astype(int)
        combined["Bos"] = combined["Kapasite"] - combined["Kullanilan"]

    _header("11. TIR KAPASİTE ANALİZİ")
    # Kullanılan en yüksek günleri listele
    print(combined.sort_values("Kullanilan", ascending=False).head(20).to_string(index=False))
    return combined

# ---------------------------------------------------------------------------
# 12. PARETO ANALİZİ
# ---------------------------------------------------------------------------
def analiz_pareto(plan: pd.DataFrame) -> pd.DataFrame:
    """SLA'nın %80'ini oluşturan rotaları bulur (Pareto prensibi)."""
    grp = (
        plan.groupby(["Çıkış Transfer Merkezi", "Varış Transfer Merkezi"])["SLA cezası"]
        .sum()
        .reset_index()
        .sort_values("SLA cezası", ascending=False)
        .reset_index(drop=True)
    )
    toplam = grp["SLA cezası"].sum()
    grp["Kumulatif_%"] = (grp["SLA cezası"].cumsum() / toplam * 100).round(1)
    pareto80 = grp[grp["Kumulatif_%"] <= 80]

    _header("12. PARETO ANALİZİ — SLA'nın %80'ini Oluşturan Rotalar")
    print(f"  Toplam SLA: {_fmt(toplam)}")
    print(f"  %80'i oluşturan rota sayısı: {len(pareto80)}")
    print(pareto80.to_string(index=False))
    return grp

# ---------------------------------------------------------------------------
# 13. OTOMATİK YORUM
# ---------------------------------------------------------------------------
def otomatik_yorum(
    maliyet: Dict,
    arac_dag: pd.DataFrame,
    sla_rota: pd.DataFrame,
    gec_tm: pd.DataFrame,
    kiralik: pd.DataFrame,
    spot_tip: pd.DataFrame,
    pareto: pd.DataFrame,
    plan: pd.DataFrame,
) -> None:
    """Gerçek verilere dayalı otomatik yorum üretir."""
    _header("13. OTOMATİK YORUM")

    # SLA oranı
    print(f"  • Toplam maliyetin %{maliyet['sla_oran']:.1f}'i SLA cezasından oluşuyor.")

    # Pareto
    toplam_sla = pareto["SLA cezası"].sum()
    p80 = pareto[pareto["Kumulatif_%"] <= 80]
    print(f"  • SLA'nın %80'i yalnızca {len(p80)} rotadan geliyor.")

    # En büyük darboğaz TM
    if not gec_tm.empty:
        bos_tm = gec_tm.iloc[0]["Çıkış Transfer Merkezi"]
        print(f"  • En büyük darboğaz: {bos_tm} TM.")

    # Kiralık doluluk
    if not kiralik.empty:
        ort_dol = kiralik["Doluluk_%"].mean()
        print(f"  • Kiralık araçların ortalama doluluk oranı %{ort_dol:.1f}.")
        bos_sefer_toplam = kiralik["Bos_Sefer"].sum()
        print(f"  • Kiralık araçlarda toplam {int(bos_sefer_toplam)} boş sefer yapıldı.")

    # Spot araç tipi baskınlığı
    if not spot_tip.empty:
        total_spot = spot_tip["Adet"].sum()
        en_cok = spot_tip.iloc[0]
        oran = en_cok["Adet"] / total_spot * 100 if total_spot > 0 else 0
        print(f"  • Spot araçların %{oran:.0f}'i {en_cok['Araç türü']} tipi.")

    # Kamyonet doluluk (varsa)
    if not spot_tip.empty:
        kam_row = spot_tip[spot_tip["Araç türü"] == "Kamyonet"]
        if not kam_row.empty:
            dol = kam_row.iloc[0]["Ort_Doluluk_Yuzde"]
            print(f"  • Kamyonetlerin ortalama doluluğu %{dol:.1f}.")

    # Toplam plan özeti
    print(f"  • Toplam {len(plan)} satır, {plan['Araç ID'].nunique()} benzersiz araç seferi planlandı.")

# ---------------------------------------------------------------------------
# EXCEL ÇIKTISI
# ---------------------------------------------------------------------------
def excel_ciktisi(
    plan: pd.DataFrame,
    maliyet: Dict,
    arac_dag: pd.DataFrame,
    sla_rota: pd.DataFrame,
    gec_tm: pd.DataFrame,
    gunluk: pd.DataFrame,
    kiralik: pd.DataFrame,
    spot_tip: pd.DataFrame,
    spot_rota: pd.DataFrame,
    ellecleme: pd.DataFrame,
    tir_kap: pd.DataFrame,
    pareto: pd.DataFrame,
    output_dir: str,
) -> None:
    """Tüm analiz sonuçlarını outputs/solution_analysis.xlsx dosyasına yazar."""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "solution_analysis.xlsx")

    # Summary sayfası
    summary_data = {
        "Metrik": [
            "Araç Maliyeti (TL)", "SLA Cezası (TL)", "Toplam Maliyet (TL)",
            "SLA Oranı (%)", "Toplam Plan Satırı", "Toplam Araç Seferi",
        ],
        "Değer": [
            round(maliyet["arac_maliyet"], 2),
            round(maliyet["sla_maliyet"], 2),
            round(maliyet["toplam"], 2),
            round(maliyet["sla_oran"], 2),
            len(plan),
            plan["Araç ID"].nunique(),
        ],
    }
    summary_df = pd.DataFrame(summary_data)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        arac_dag.to_excel(writer, sheet_name="Vehicle Analysis", index=False)
        sla_rota.to_excel(writer, sheet_name="SLA Analysis", index=False)
        gec_tm.to_excel(writer, sheet_name="TM Analysis", index=False)
        pareto.to_excel(writer, sheet_name="Pareto", index=False)

        # Route Analysis: spot rota + sla rota birleşimi
        route_df = pd.concat([
            sla_rota.assign(Kaynak="SLA"),
            spot_rota.rename(columns={"Adet": "Spot_Sefer", "Toplam_Desi": "Spot_Desi"}).assign(Kaynak="Spot"),
        ], ignore_index=True)
        route_df.to_excel(writer, sheet_name="Route Analysis", index=False)

    print(f"\n  Excel kaydedildi: {path}")

# ---------------------------------------------------------------------------
# ANA FONKSİYON
# ---------------------------------------------------------------------------
def run_analysis() -> None:
    """Tam analizi çalıştırır: veri yükleme → plan üretme → analiz → raporlama."""
    print(SEP)
    print("  LoadIQ — ÇÖZÜM ANALİZ RAPORU")
    print(f"  {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print(SEP)

    # Veri yükle
    print("\nVeri yükleniyor...")
    veri = load_all()

    # Talep tahmin dosyasını yükle (forecast çıktısı)
    forecast_path = os.path.join(_ROOT, "outputs", "Talep-tahmini.xlsx")
    if not os.path.exists(forecast_path):
        raise FileNotFoundError(f"Tahmin dosyası bulunamadı: {forecast_path}")
    talep_df = pd.read_excel(forecast_path)

    # Plan üret
    print("Plan üretiliyor...")
    plan = generate_plan(talep_df, veri)
    print(f"Plan üretildi: {len(plan)} satır\n")

    output_dir = os.path.join(_ROOT, "outputs")

    # Analizleri çalıştır
    maliyet    = analiz_toplam_maliyet(plan)
    arac_dag   = analiz_arac_dagilimi(plan)
    en_pahali  = analiz_en_pahali_talepler(plan)
    sla_rota   = analiz_sla_rota(plan)
    gec_tm     = analiz_gec_tm(plan)
    gunluk     = analiz_gunluk_sla(plan)
    saatlik    = analiz_saatlik_sla(plan)
    kiralik    = analiz_kiralik(plan, veri)
    spot_tip, spot_rota = analiz_spot(plan, veri)
    ellecleme  = analiz_ellecleme(plan, veri)
    tir_kap    = analiz_tir_kapasite(plan, veri)
    pareto     = analiz_pareto(plan)

    otomatik_yorum(maliyet, arac_dag, sla_rota, gec_tm, kiralik, spot_tip, pareto, plan)

    # Excel çıktısı
    excel_ciktisi(
        plan, maliyet, arac_dag, sla_rota, gec_tm, gunluk,
        kiralik, spot_tip, spot_rota, ellecleme, tir_kap, pareto, output_dir,
    )

    print(f"\n{SEP}")
    print("  ANALYSIS COMPLETED")
    print(SEP)


if __name__ == "__main__":
    run_analysis()

"""
LoadIQ - Bağımsız Doğrulayıcı (checker.py)

BİLEREK optimize.py'den ayrı yazılmıştır. Amaç: optimizasyon motorunun
ürettiği sonucu, motorun kendi hesapladığı değerlere GÜVENMEDEN, sıfırdan
yeniden hesaplayıp karşılaştırmak. Aynı formülü iki kere aynı yerde
yazarsak bir hata ikisinde de tekrarlanır ve kendimizi kandırırız; bu
yüzden burada formüller time_utils.py ve config/rules.py'den okunur,
optimize.py'nin iç mantığından değil.

Kontrol ettiği şeyler:
  1. ID format uyumu (D00001, D00001-1, V0001)
  2. Talep izlenebilirliği (bölünen desi'ler toplamı orijinal tahmine eşit mi)
  3. Tır kapasitesi ihlali (TM x gün)
  4. Elleçleme kapasitesi ihlali (TM x gün, gece yarısı oransal bölünme dahil)
  5. SLA cezası doğruluğu (yeniden hesaplanıp raporlanan değerle kıyaslanır)
  6. Maliyet doğruluğu (yeniden hesaplanıp raporlanan değerle kıyaslanır)

Kullanım:
    from checker import run_all_checks
    rapor = run_all_checks(talep_df, plan_df, mesafe_df, tir_kapasitesi_df,
                            ellecleme_df, arac_maliyet_df)
    print(rapor.ozet())
"""

import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pandas as pd

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)
sys.path.insert(0, os.path.join(_THIS_DIR, "..", "config"))

from time_utils import travel_minutes, handling_minutes, split_handling_across_midnight  # noqa: E402
import rules  # noqa: E402

TALEP_ID_RE = re.compile(r"^D\d{5}(-\d+)*$")
ARAC_ID_RE = re.compile(r"^V\d{4,}$")


@dataclass
class Sorun:
    kategori: str
    seviye: str  # "HATA" (hard fail) | "UYARI"
    aciklama: str


@dataclass
class DogrulamaRaporu:
    sorunlar: list = field(default_factory=list)

    def ekle(self, kategori, seviye, aciklama):
        self.sorunlar.append(Sorun(kategori, seviye, aciklama))

    @property
    def hata_var_mi(self):
        return any(s.seviye == "HATA" for s in self.sorunlar)

    def ozet(self):
        n_hata = sum(1 for s in self.sorunlar if s.seviye == "HATA")
        n_uyari = sum(1 for s in self.sorunlar if s.seviye == "UYARI")
        satirlar = [f"SONUÇ: {'FAIL' if self.hata_var_mi else 'PASS'}  "
                    f"({n_hata} hata, {n_uyari} uyarı)"]
        for s in self.sorunlar:
            satirlar.append(f"  [{s.seviye}] ({s.kategori}) {s.aciklama}")
        return "\n".join(satirlar)


def _base_talep_id(talep_id: str) -> str:
    """D00001-1-2 -> D00001 (bölünmüş talebin kök ID'sini bulur)."""
    return talep_id.split("-")[0]


def _to_dt(tarih, saat_str) -> datetime:
    """tarih (date/Timestamp) + 'HH:MM' -> datetime"""
    if isinstance(tarih, pd.Timestamp):
        tarih = tarih.date()
    h, m = map(int, str(saat_str).split(":"))
    return datetime(tarih.year, tarih.month, tarih.day, h, m)


# ---------------------------------------------------------------------------
# 1. ID Format Kontrolü
# ---------------------------------------------------------------------------
def check_id_formats(plan_df: pd.DataFrame, rapor: DogrulamaRaporu):
    kotu_talep = [t for t in plan_df["Talep ID"].unique() if not TALEP_ID_RE.match(str(t))]
    for t in kotu_talep:
        rapor.ekle("ID_FORMAT", "HATA", f"Geçersiz Talep ID formatı: '{t}'")

    kotu_arac = [a for a in plan_df["Araç ID"].unique() if not ARAC_ID_RE.match(str(a))]
    for a in kotu_arac:
        rapor.ekle("ID_FORMAT", "HATA", f"Geçersiz Araç ID formatı: '{a}'")


# ---------------------------------------------------------------------------
# 2. Talep İzlenebilirliği: bölünen desi toplamları orijinal tahminle eşleşiyor mu
# ---------------------------------------------------------------------------
def check_talep_traceability(talep_df: pd.DataFrame, plan_df: pd.DataFrame,
                              rapor: DogrulamaRaporu, tolerans=0.01):
    talep_desi = talep_df.set_index("Talep ID")["Tahmin Edilen Desi"].to_dict()

    plan_df = plan_df.copy()
    plan_df["_kok_id"] = plan_df["Talep ID"].apply(_base_talep_id)
    tasinan_toplam = plan_df.groupby("_kok_id")["Taşınan Desi"].sum()

    for kok_id, beklenen_desi in talep_desi.items():
        tasinan = tasinan_toplam.get(kok_id, 0.0)
        if abs(tasinan - beklenen_desi) > tolerans:
            rapor.ekle(
                "IZLENEBILIRLIK", "HATA",
                f"{kok_id}: tahmin edilen {beklenen_desi} desi, planda taşınan "
                f"{tasinan} desi (fark: {tasinan - beklenen_desi:+.2f})"
            )

    plan_kok_ids = set(tasinan_toplam.index)
    tanimsiz = plan_kok_ids - set(talep_desi.keys())
    for kok_id in tanimsiz:
        rapor.ekle("IZLENEBILIRLIK", "HATA",
                   f"Planda var ama tahmin dosyasında olmayan Talep ID kökü: {kok_id}")


# ---------------------------------------------------------------------------
# 3. Tır Kapasitesi Kontrolü
# ---------------------------------------------------------------------------
def check_tir_capacity(plan_df: pd.DataFrame, tir_kapasitesi_df: pd.DataFrame,
                        rapor: DogrulamaRaporu):
    kapasite = tir_kapasitesi_df.set_index("tm")["tir_kapasitesi"].to_dict()

    tir_hareketleri = plan_df[plan_df["Araç türü"] == "Tır"].copy()
    if tir_hareketleri.empty:
        return

    # Aynı (Araç ID, TM, Tarih) hareketsiz tekrar kullanım = 1 kapasite;
    # burada basitleştirilmiş kural: (Araç ID, TM, Tarih) bazında benzersiz
    # sayıyoruz (indirilip tekrar yüklenen ayrı satır olarak zaten görünür).
    kullanim = defaultdict(set)  # (tm, tarih) -> {(arac_id, yon)}
    for _, row in tir_hareketleri.iterrows():
        arac_id = row["Araç ID"]
        for tm, tarih, yon in [
            (row["Çıkış Transfer Merkezi"], row["Çıkış Tarihi"], "cikis"),
            (row["Varış Transfer Merkezi"], row["Varış Tarihi"], "varis"),
        ]:
            if pd.isna(tarih):
                continue
            kullanim[(tm, pd.Timestamp(tarih).date())].add((arac_id, yon))

    for (tm, tarih), kullananlar in kullanim.items():
        adet = len(kullananlar)
        kota = kapasite.get(tm, 0)
        if adet > kota:
            rapor.ekle(
                "TIR_KAPASITESI", "HATA",
                f"{tm} - {tarih}: {adet} tır hareketi, kapasite {kota} "
                f"(aşım: {adet - kota})"
            )
        if tm in rules.TIR_TAMAMEN_YASAK_TM:
            rapor.ekle(
                "TIR_KAPASITESI", "HATA",
                f"{tm}: bu merkeze tır kapasitesi tamamen yasak (config/rules.py), "
                f"ama planda {adet} tır hareketi var"
            )


# ---------------------------------------------------------------------------
# 4. Elleçleme Kapasitesi Kontrolü (gece yarısı oransal bölünme dahil)
# ---------------------------------------------------------------------------
def check_ellecleme_capacity(plan_df: pd.DataFrame, ellecleme_df: pd.DataFrame,
                              rapor: DogrulamaRaporu):
    kapasite = ellecleme_df.set_index("tm")["gunluk_kapasite_desi"].to_dict()
    kullanim = defaultdict(float)  # (tm, tarih) -> toplam elleçlenen desi

    for _, row in plan_df.iterrows():
        desi = row["Taşınan Desi"]

        # Çıkış elleçlemesi: Çıkış TM'de, çıkış saatinden GERİYE doğru
        # (çıkış elleçleme süresi kadar önce başlamış, çıkış anında biter)
        if pd.notna(row.get("Çıkış Tarihi")) and pd.notna(row.get("Çıkış Saati")):
            cikis_bitis = _to_dt(row["Çıkış Tarihi"], row["Çıkış Saati"])
            sure = row.get("Çıkış Elleçleme süresi", handling_minutes(desi))
            baslangic = cikis_bitis - timedelta(minutes=int(sure))
            for tarih, dk, desi_payi in split_handling_across_midnight(baslangic, int(sure), desi):
                kullanim[(row["Çıkış Transfer Merkezi"], tarih)] += desi_payi

        # Varış elleçlemesi: Varış TM'de, varış saatinden İTİBAREN başlar
        if pd.notna(row.get("Varış Tarihi")) and pd.notna(row.get("Varış Saati")):
            varis_baslangic = _to_dt(row["Varış Tarihi"], row["Varış Saati"])
            sure = row.get("Varış elleçleme süresi", handling_minutes(desi))
            for tarih, dk, desi_payi in split_handling_across_midnight(varis_baslangic, int(sure), desi):
                kullanim[(row["Varış Transfer Merkezi"], tarih)] += desi_payi

    for (tm, tarih), toplam_desi in kullanim.items():
        kota = kapasite.get(tm)
        if kota is None:
            rapor.ekle("ELLECLEME_KAPASITESI", "UYARI", f"Bilinmeyen TM: {tm}")
            continue
        if toplam_desi > kota + 1e-6:
            rapor.ekle(
                "ELLECLEME_KAPASITESI", "HATA",
                f"{tm} - {tarih}: {toplam_desi:.1f} desi elleçlenmiş, "
                f"kapasite {kota:.1f} (aşım: {toplam_desi - kota:.1f})"
            )


# ---------------------------------------------------------------------------
# 5. SLA Cezası Yeniden Hesabı
# ---------------------------------------------------------------------------
def _sla_saat(cikis_tm, varis_tm, mesafe_df) -> int:
    row = mesafe_df[(mesafe_df["cikis"] == cikis_tm) & (mesafe_df["varis"] == varis_tm)]
    if row.empty:
        raise ValueError(f"Mesafe matrisinde bulunamadı: {cikis_tm} -> {varis_tm}")
    return int(row.iloc[0]["sla_gun"]) * 24


def check_sla_penalty(plan_df: pd.DataFrame, talep_df: pd.DataFrame,
                       mesafe_df: pd.DataFrame, rapor: DogrulamaRaporu,
                       tolerans_tl=0.5):
    talep_bilgi = talep_df.set_index("Talep ID").to_dict("index")

    plan_df = plan_df.copy()
    plan_df["_kok_id"] = plan_df["Talep ID"].apply(_base_talep_id)

    # Her kök talep için PLANDAKİ EN GEÇ varış elleçleme tamamlanma anı
    # (bölünmüş talep birden fazla araçla gidiyorsa, her parçanın kendi
    # SLA cezası ayrı hesaplanmalı; burada satır bazında hesaplıyoruz)
    for _, row in plan_df.iterrows():
        kok_id = row["_kok_id"]
        if kok_id not in talep_bilgi:
            continue  # zaten IZLENEBILIRLIK kontrolünde flag'lendi
        bilgi = talep_bilgi[kok_id]
        talep_tamamlanma = _to_dt(bilgi["Tarih"], bilgi["Talep Tamamlama Saati"])

        if pd.isna(row.get("Varış Tarihi")) or pd.isna(row.get("Varış Saati")):
            continue
        varis_ellecleme_bitis = _to_dt(row["Varış Tarihi"], row["Varış Saati"]) + \
            timedelta(minutes=int(row.get("Varış elleçleme süresi", 0)))

        sla_limit_saat = _sla_saat(bilgi["Çıkış Transfer Merkezi"], bilgi["Varış Transfer Merkezi"], mesafe_df)
        sla_bitis = talep_tamamlanma + timedelta(hours=sla_limit_saat)

        gecikme_saniye = (varis_ellecleme_bitis - sla_bitis).total_seconds()
        if gecikme_saniye <= 0:
            beklenen_ceza = 0.0
        else:
            gecikme_saat = -(-int(gecikme_saniye) // 3600)  # yukarı yuvarlama
            beklenen_ceza = row["Taşınan Desi"] * gecikme_saat * rules.SLA_CEZA_TL_PER_DESI_SAAT

        raporlanan_ceza = row.get("SLA cezası", 0.0)
        if abs(raporlanan_ceza - beklenen_ceza) > tolerans_tl:
            rapor.ekle(
                "SLA_CEZASI", "HATA",
                f"{row['Talep ID']} (Araç {row['Araç ID']}): beklenen ceza "
                f"{beklenen_ceza:.2f} TL, raporlanan {raporlanan_ceza:.2f} TL"
            )


# ---------------------------------------------------------------------------
# 6. Maliyet Yeniden Hesabı
# ---------------------------------------------------------------------------
# BİLİNEN VARSAYIM (organizatörle netleşmesi gerekiyor): Bir araç aynı
# bacakta (leg) birden fazla Talep ID taşıyorsa, şablonda "Toplam maliyet"
# sütununun her satırda AYNI (tüm bacağın toplam maliyeti) tekrarlandığını
# varsayıyoruz -- bölünüp dağıtılmadığını varsayıyoruz. Bu netleşene kadar
# leg bazında GRUPLAYIP tekrarlanan değerleri bir kere sayıyoruz.
def check_cost(plan_df: pd.DataFrame, arac_maliyet_df: pd.DataFrame,
                mesafe_df: pd.DataFrame, rapor: DogrulamaRaporu, tolerans_tl=0.5):
    maliyet_tablosu = arac_maliyet_df.set_index("arac_adi").to_dict("index")

    leg_kolonlari = ["Araç ID", "Araç Tipi", "Araç türü", "Çıkış Transfer Merkezi",
                      "Varış Transfer Merkezi", "Çıkış Tarihi", "Çıkış Saati",
                      "Varış Tarihi", "Varış Saati"]
    if plan_df[leg_kolonlari].isna().any(axis=1).any():
        rapor.ekle("MALIYET", "UYARI",
                   "Bazı satırlarda bacak (leg) bilgisi eksik, maliyet kontrolü atlandı.")
        plan_df = plan_df.dropna(subset=leg_kolonlari)

    milkrun_arac_idler = set(
        arac_id for arac_id, g in plan_df.groupby("Araç ID")
        if g[leg_kolonlari].drop_duplicates().shape[0] > 1
    )

    for leg_key, grup in plan_df.groupby(leg_kolonlari, dropna=False):
        (arac_id, arac_tipi, arac_turu, cikis_tm, varis_tm,
         cikis_tarih, cikis_saat, varis_tarih, varis_saat) = leg_key

        if arac_id in milkrun_arac_idler:
            # Çok bacaklı milk-run araçlarının maliyeti check_milkrun_tutarlilik ile kontrol edilir
            continue

        if arac_turu not in maliyet_tablosu:
            rapor.ekle("MALIYET", "HATA", f"Bilinmeyen araç türü: {arac_turu}")
            continue
        fiyat = maliyet_tablosu[arac_turu]
        saatlik = fiyat["kiralik_saatlik_tl"] if arac_tipi == "Kiralık" else fiyat["spot_saatlik_tl"]
        km_tl = fiyat["kiralik_km_tl"] if arac_tipi == "Kiralık" else fiyat["spot_km_tl"]

        mesafe_row = mesafe_df[(mesafe_df["cikis"] == cikis_tm) & (mesafe_df["varis"] == varis_tm)]
        if mesafe_row.empty:
            rapor.ekle("MALIYET", "HATA", f"Mesafe bulunamadı: {cikis_tm}->{varis_tm}")
            continue
        mesafe_km = mesafe_row.iloc[0]["mesafe_km"]

        # kullanım süresi = çıkış elleçleme + yol + varış elleçleme (dakika)
        cikis_ellecleme = grup["Çıkış Elleçleme süresi"].iloc[0]
        varis_ellecleme = grup["Varış elleçleme süresi"].iloc[0]
        yolculuk = grup["Yolculuk süresi"].iloc[0]
        kullanim_dk = cikis_ellecleme + yolculuk + varis_ellecleme
        kullanim_saat = kullanim_dk / 60.0

        beklenen_maliyet = (saatlik * kullanim_saat) + (mesafe_km * km_tl)
        # İlk satır tam maliyeti taşır, diğerleri 0.0; toplam her zaman bacağın gerçek maliyeti.
        # (Eski format: tüm satırlar aynı değeri tekrarlıyordu → .sum() yanlış çarpım yapardı;
        #  yeni format: ilk satır maliyet, diğerleri 0.0 → .sum() doğru.)
        # Hem eski hem yeni formatla uyumlu olmak için:  önce grubun toplam maliyet tutarını
        # al; eğer tüm satırlar aynı değeri taşıyorsa (eski format) grubun ilk satırını kullan.
        toplam_raporlanan = grup["Toplam maliyet"].sum()
        ilk_deger = grup["Toplam maliyet"].iloc[0]
        grup_boyutu = len(grup)
        # Eski formatta: her satır aynı değeri taşır → toplam = ilk_deger * satır sayısı.
        # Yeni formatta: ilk satır maliyet, geri kalanlar 0 → toplam = ilk_deger (= tam maliyet).
        if grup_boyutu > 1 and abs(toplam_raporlanan - ilk_deger * grup_boyutu) < 0.5:
            # Eski format (uyumluluk): tüm satırlar tekrarlıyordu, bir kere say
            raporlanan_maliyet = ilk_deger
        else:
            # Yeni format: toplam zaten tam maliyet
            raporlanan_maliyet = toplam_raporlanan

        if abs(raporlanan_maliyet - beklenen_maliyet) > tolerans_tl:
            rapor.ekle(
                "MALIYET", "HATA",
                f"Araç {arac_id} ({cikis_tm}->{varis_tm}, {cikis_tarih} {cikis_saat}): "
                f"beklenen maliyet {beklenen_maliyet:.2f} TL, raporlanan "
                f"{raporlanan_maliyet:.2f} TL"
            )



# ---------------------------------------------------------------------------
# 7. Araç Kapasitesi Kontrolü
# ---------------------------------------------------------------------------
def check_arac_kapasitesi(plan_df: pd.DataFrame, arac_maliyet_df: pd.DataFrame,
                           rapor: DogrulamaRaporu):
    """
    Her bacakta taşınan toplam desi, o araç türünün kapasitesini aşıyor mu?

    Bacak tanımı: Araç ID + Çıkış Tarihi + Çıkış Saati +
                  Çıkış Transfer Merkezi + Varış Transfer Merkezi
    Kapasite değerleri arac_maliyet_df'in 'kapasite_desi' kolonundan okunur.
    """
    kapasite = arac_maliyet_df.set_index("arac_adi")["kapasite_desi"].to_dict()

    leg_kolonlari = [
        "Araç ID", "Araç türü",
        "Çıkış Transfer Merkezi", "Varış Transfer Merkezi",
        "Çıkış Tarihi", "Çıkış Saati",
    ]

    for leg_key, grup in plan_df.groupby(leg_kolonlari, dropna=False):
        arac_id, arac_turu, cikis_tm, varis_tm, cikis_tarih, cikis_saat = leg_key

        if arac_turu not in kapasite:
            rapor.ekle("ARAC_KAPASITESI", "HATA",
                       f"Bilinmeyen araç türü kapasite tablosunda: '{arac_turu}'")
            continue

        cap = kapasite[arac_turu]
        toplam_desi = grup["Taşınan Desi"].sum()

        if toplam_desi > cap + 1e-6:
            rapor.ekle(
                "ARAC_KAPASITESI", "HATA",
                f"Araç {arac_id} ({arac_turu}, {cikis_tm}->{varis_tm}, "
                f"{cikis_tarih} {cikis_saat}): "
                f"taşınan {toplam_desi:.1f} desi, kapasite {cap} desi "
                f"(aşım: {toplam_desi - cap:.1f} desi)"
            )


# ---------------------------------------------------------------------------
# 8. Kiralık Filo Kontrolü
# ---------------------------------------------------------------------------
def check_kiralik_filo(plan_df: pd.DataFrame, kiralik_araclar_df: pd.DataFrame,
                        rapor: DogrulamaRaporu):
    """
    Planlama penceresindeki her gün (29 Haziran - 5 Temmuz) için planda o gün
    çıkan benzersiz kiralık araç sayısı, kiralik_araclar_df'teki toplam günlük
    zorunlu araç kotasına eşit veya fazla olmalıdır.

    kiralik_araclar_df kolonları: cikis, varis, arac_sayisi, arac_turu
    """
    from datetime import date

    gunluk_kota = int(kiralik_araclar_df["arac_sayisi"].sum())

    kiralik_plan = plan_df[plan_df["Araç Tipi"] == "Kiralık"].copy()

    # Planlama penceresi: 29 Haziran - 5 Temmuz (7 gün)
    planlama_gunleri = [
        date(2026, 6, 29) + __import__("datetime").timedelta(days=i)
        for i in range(7)
    ]

    for gun in planlama_gunleri:
        # O gün çıkan benzersiz kiralık araç sayısı
        gun_mask = kiralik_plan["Çıkış Tarihi"].apply(
            lambda x: (pd.Timestamp(x).date() if pd.notna(x) else None) == gun
        )
        gun_kiralik = kiralik_plan[gun_mask]["Araç ID"].nunique()

        if gun_kiralik < gunluk_kota:
            rapor.ekle(
                "KIRALIK_FILO", "HATA",
                f"{gun}: beklenen kiralık araç sayısı {gunluk_kota}, "
                f"planda bulunan {gun_kiralik} "
                f"(eksik: {gunluk_kota - gun_kiralik})"
            )


# ---------------------------------------------------------------------------
# 10. Boş Spot Araç Kontrolü
# ---------------------------------------------------------------------------
def check_bos_spot_arac(plan_df: pd.DataFrame, rapor: DogrulamaRaporu):
    """
    Araç Tipi=="Spot" olup toplam Taşınan Desi==0 olan araçlar planda
    olmamalıdır — bunlar gereksiz maliyet üretir.
    Araç Tipi=="Kiralık" araçlar muaftır (şartname gereği boş sefer yapabilir).
    """
    spot_df = plan_df[plan_df["Araç Tipi"] == "Spot"]
    if spot_df.empty:
        return
    toplam_desi = spot_df.groupby("Araç ID")["Taşınan Desi"].sum()
    bos_araclar = toplam_desi[toplam_desi <= 0].index.tolist()
    for arac_id in bos_araclar:
        rapor.ekle(
            "BOS_SPOT_ARAC", "HATA",
            f"Spot araç {arac_id}: planda var ama hiç yük taşımıyor "
            f"(toplam Taşınan Desi = 0). Gereksiz maliyet ekleniyor."
        )


# ---------------------------------------------------------------------------
# 11. Milk-Run Tutarlılık Kontrolü
# ---------------------------------------------------------------------------
def check_milkrun_tutarlilik(plan_df: pd.DataFrame, mesafe_df: pd.DataFrame,
                             arac_maliyet_df: pd.DataFrame, rapor: DogrulamaRaporu,
                             tolerans_tl=0.5):
    """
    Çok bacaklı (milk-run) araç seferlerinin tutarlılığını doğrular.

    Bir Araç ID birden fazla farklı bacakta (Leg: Çıkış TM, Varış TM, Çıkış Tarihi, Çıkış Saati)
    görünüyorsa:
    1. Bacaklar çıkış zamanına göre sıralanır.
    2. Zincir Kontrolü: Ardışık bacaklar arasında zincir kopuk olmamalıdır:
       bacak[i].varis_tm == bacak[i+1].cikis_tm VE
       bacak[i].varis_zaman <= bacak[i+1].cikis_zaman.
       Zincir kopuksa "MILKRUN_ZINCIR" kategorisinde HATA eklenir.
    3. Maliyet Kontrolü:
       Tek bir araç olarak tüm bacakların süre (çıkış elleçleme + yol + varış elleçleme) ve mesafeleri toplanır:
       Toplam maliyet = saatlik * (toplam_kullanim_dk / 60.0) + km_tl * toplam_mesafe_km
       Bu değer, planda o araç için raporlanan toplam maliyet ile tutarlı olmalıdır.
       Fark toleransı aşarsa "MILKRUN_MALIYET" kategorisinde HATA eklenir.
    """
    if plan_df.empty:
        return

    maliyet_tablosu = arac_maliyet_df.set_index("arac_adi").to_dict("index")
    LEG_COLS = [
        "Çıkış Transfer Merkezi", "Varış Transfer Merkezi",
        "Çıkış Tarihi", "Çıkış Saati", "Varış Tarihi", "Varış Saati"
    ]

    for arac_id, arac_grup in plan_df.groupby("Araç ID"):
        leg_gruplar = []
        for leg_key, lg in arac_grup.groupby(LEG_COLS, dropna=False):
            (cikis_tm, varis_tm, cikis_tarih, cikis_saat, varis_tarih, varis_saat) = leg_key
            cikis_dt = _to_dt(cikis_tarih, cikis_saat)
            varis_dt = _to_dt(varis_tarih, varis_saat)

            cikis_ellecleme = lg["Çıkış Elleçleme süresi"].iloc[0]
            varis_ellecleme = lg["Varış elleçleme süresi"].iloc[0]
            yolculuk = lg["Yolculuk süresi"].iloc[0]

            mesafe_row = mesafe_df[(mesafe_df["cikis"] == cikis_tm) & (mesafe_df["varis"] == varis_tm)]
            mesafe_km = float(mesafe_row.iloc[0]["mesafe_km"]) if not mesafe_row.empty else 0.0

            leg_maliyet = float(lg["Toplam maliyet"].sum())

            leg_gruplar.append({
                "cikis_tm": cikis_tm,
                "varis_tm": varis_tm,
                "cikis_dt": cikis_dt,
                "varis_dt": varis_dt,
                "cikis_ellecleme": cikis_ellecleme,
                "varis_ellecleme": varis_ellecleme,
                "yolculuk": yolculuk,
                "mesafe_km": mesafe_km,
                "leg_maliyet": leg_maliyet,
                "arac_tipi": lg["Araç Tipi"].iloc[0],
                "arac_turu": lg["Araç türü"].iloc[0],
            })

        if len(leg_gruplar) <= 1:
            continue

        leg_gruplar.sort(key=lambda x: x["cikis_dt"])

        # 1. Zincir Kontrolü
        for i in range(len(leg_gruplar) - 1):
            mevcut_leg = leg_gruplar[i]
            sonraki_leg = leg_gruplar[i + 1]
            if mevcut_leg["varis_tm"] != sonraki_leg["cikis_tm"]:
                rapor.ekle(
                    "MILKRUN_ZINCIR", "HATA",
                    f"Araç {arac_id} milk-run zinciri kopuk: "
                    f"bacak {i+1} varış TM '{mevcut_leg['varis_tm']}' != "
                    f"bacak {i+2} çıkış TM '{sonraki_leg['cikis_tm']}'"
                )
            if sonraki_leg["cikis_dt"] < mevcut_leg["varis_dt"]:
                rapor.ekle(
                    "MILKRUN_ZINCIR", "HATA",
                    f"Araç {arac_id} zaman sırası uyumsuz: "
                    f"bacak {i+2} çıkış zamanı ({sonraki_leg['cikis_dt']}), "
                    f"bacak {i+1} varış zamanından ({mevcut_leg['varis_dt']}) önce!"
                )

        # 2. Maliyet Kontrolü
        arac_turu = leg_gruplar[0]["arac_turu"]
        arac_tipi = leg_gruplar[0]["arac_tipi"]
        if arac_turu in maliyet_tablosu:
            fiyat = maliyet_tablosu[arac_turu]
            saatlik = fiyat["kiralik_saatlik_tl"] if arac_tipi == "Kiralık" else fiyat["spot_saatlik_tl"]
            km_tl = fiyat["kiralik_km_tl"] if arac_tipi == "Kiralık" else fiyat["spot_km_tl"]

            toplam_kullanim_dk = sum(lg["cikis_ellecleme"] + lg["yolculuk"] + lg["varis_ellecleme"] for lg in leg_gruplar)
            toplam_mesafe_km = sum(lg["mesafe_km"] for lg in leg_gruplar)
            beklenen_maliyet = (saatlik * (toplam_kullanim_dk / 60.0)) + (km_tl * toplam_mesafe_km)

            toplam_raporlanan_maliyet = sum(lg["leg_maliyet"] for lg in leg_gruplar)

            if abs(toplam_raporlanan_maliyet - beklenen_maliyet) > tolerans_tl:
                rapor.ekle(
                    "MILKRUN_MALIYET", "HATA",
                    f"Milk-run araç {arac_id}: beklenen toplam maliyet {beklenen_maliyet:.2f} TL, "
                    f"raporlanan {toplam_raporlanan_maliyet:.2f} TL"
                )


# ---------------------------------------------------------------------------
# 12. Çıkış Hazırlık Kontrolü: Araç çıkış anı, yük hazır olma anından önce olamaz
# ---------------------------------------------------------------------------
def check_cikis_hazirlik(plan_df: pd.DataFrame, talep_df: pd.DataFrame,
                         rapor: DogrulamaRaporu):
    """
    Her plan satırı için: O satırdaki Talep ID'nin (kök ID) tahmindeki (talep_df)
    talep tamamlanma anı (Tarih + Talep Tamamlama Saati) ile aracın ÇIKIŞ anını
    (Çıkış Tarihi + Çıkış Saati) karşılaştırır.

    Eğer aracın ÇIKIŞ anı yükün hazır olma (tamamlanma) anından ÖNCE ise
    "CIKIS_HAZIRLIK" kategorisinde HATA eklenir.
    """
    if plan_df.empty or talep_df.empty:
        return

    talep_hazir_map = {}
    if "Talep ID" in talep_df.columns:
        for _, row in talep_df.iterrows():
            tid = str(row["Talep ID"])
            kok = _base_talep_id(tid)
            t_dt = _to_dt(row["Tarih"], row["Talep Tamamlama Saati"])
            talep_hazir_map[tid] = t_dt
            talep_hazir_map[kok] = t_dt
    else:
        # data_loader / panel formatı
        for _, row in talep_df.iterrows():
            if "tarih" in row and "saat" in row:
                t_dt = _to_dt(row["tarih"], row["saat"])
                key = (row.get("cikis"), row.get("varis"), row.get("tarih"), row.get("saat"))
                talep_hazir_map[key] = t_dt

    for _, row in plan_df.iterrows():
        tid = str(row["Talep ID"])
        kok = _base_talep_id(tid)
        hazir_dt = talep_hazir_map.get(tid) or talep_hazir_map.get(kok)
        if hazir_dt is None:
            continue

        cikis_tarih = row.get("Çıkış Tarihi")
        cikis_saat = row.get("Çıkış Saati")
        if pd.isna(cikis_tarih) or pd.isna(cikis_saat):
            continue

        cikis_dt = _to_dt(cikis_tarih, cikis_saat)
        arac_id = row.get("Araç ID")

        if cikis_dt < hazir_dt:
            rapor.ekle(
                "CIKIS_HAZIRLIK", "HATA",
                f"Araç {arac_id}, talep {tid}, çıkış {cikis_dt} ama yük {hazir_dt} anında hazır oluyor"
            )


# ---------------------------------------------------------------------------
# 13. Ana Fonksiyon
# ---------------------------------------------------------------------------
def run_all_checks(talep_df, plan_df, mesafe_df, tir_kapasitesi_df,
                    ellecleme_df, arac_maliyet_df,
                    kiralik_araclar_df=None) -> DogrulamaRaporu:
    rapor = DogrulamaRaporu()
    check_id_formats(plan_df, rapor)
    check_talep_traceability(talep_df, plan_df, rapor)
    check_tir_capacity(plan_df, tir_kapasitesi_df, rapor)
    check_ellecleme_capacity(plan_df, ellecleme_df, rapor)
    check_sla_penalty(plan_df, talep_df, mesafe_df, rapor)
    check_cost(plan_df, arac_maliyet_df, mesafe_df, rapor)
    check_arac_kapasitesi(plan_df, arac_maliyet_df, rapor)
    check_bos_spot_arac(plan_df, rapor)
    check_milkrun_tutarlilik(plan_df, mesafe_df, arac_maliyet_df, rapor)
    check_cikis_hazirlik(plan_df, talep_df, rapor)
    if kiralik_araclar_df is not None:
        check_kiralik_filo(plan_df, kiralik_araclar_df, rapor)
    return rapor


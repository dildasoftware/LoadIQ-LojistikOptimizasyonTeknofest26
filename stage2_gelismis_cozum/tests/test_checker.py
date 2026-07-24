"""
checker.py için negatif testler.

Amaç: checker.py'nin GERÇEKTEN bozuk bir plan verildiğinde bunu doğru
şekilde reddettiğini kanıtlamak. Sadece "doğru planı onaylıyor mu" yeterli
değil -- bir doğrulayıcının asıl işi hatayı yakalamaktır. Bu yüzden her
kural için bilerek bozulmuş bir senaryo kuruyoruz ve checker'ın bunu
HATA olarak işaretlediğini doğruluyoruz.
"""

import sys
import os
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "config"))

from checker import (
    run_all_checks, check_id_formats, check_talep_traceability,
    check_tir_capacity, check_ellecleme_capacity, check_sla_penalty,
    check_cost, check_arac_kapasitesi, check_kiralik_filo,
    check_bos_spot_arac, check_milkrun_tutarlilik, check_cikis_hazirlik, DogrulamaRaporu,
)


# ---------------------------------------------------------------------------
# TEST R: Çıkış Hazırlık Geçerli (Çıkış zamanı >= Yük hazır olma anı) -> PASS
# ---------------------------------------------------------------------------
def test_cikis_hazirlik_gecerli_pass_veriyor():
    """
    Araç çıkış zamanı (09:00), talep hazır olma zamanı (09:00) veya sonrasındaysa
    CIKIS_HAZIRLIK hatası üretilmemeli.
    """
    satir = _gecerli_plan_satiri()
    satir["Talep ID"] = "D00001"
    satir["Çıkış Tarihi"] = pd.Timestamp(2026, 6, 29)
    satir["Çıkış Saati"] = "09:00"
    plan_df = pd.DataFrame([satir])

    talep_df = pd.DataFrame([{
        "Talep ID": "D00001",
        "Tarih": pd.Timestamp(2026, 6, 29),
        "Talep Tamamlama Saati": "09:00",
        "Tahmin Edilen Desi": 100
    }])

    rapor = DogrulamaRaporu()
    check_cikis_hazirlik(plan_df, talep_df, rapor)

    assert not rapor.hata_var_mi, f"Geçerli çıkış hazırlık hata vermemeliydi: {rapor.ozet()}"


# ---------------------------------------------------------------------------
# TEST S: Çıkış Hazırlık Uyumsuz (Çıkış < Yük hazır olma anı) -> HATA
# ---------------------------------------------------------------------------
def test_cikis_hazirlik_erken_cikis_hata_verir():
    """
    Araç çıkış zamanı (09:00), talep hazır olma zamanından (17:00) önce ise
    CIKIS_HAZIRLIK hatası üretilmeli.
    """
    satir = _gecerli_plan_satiri()
    satir["Talep ID"] = "D00002"
    satir["Çıkış Tarihi"] = pd.Timestamp(2026, 6, 29)
    satir["Çıkış Saati"] = "09:00"  # Erken çıkış!
    plan_df = pd.DataFrame([satir])

    talep_df = pd.DataFrame([{
        "Talep ID": "D00002",
        "Tarih": pd.Timestamp(2026, 6, 29),
        "Talep Tamamlama Saati": "17:00",  # 17:00'de hazır oluyor
        "Tahmin Edilen Desi": 100
    }])

    rapor = DogrulamaRaporu()
    check_cikis_hazirlik(plan_df, talep_df, rapor)

    assert rapor.hata_var_mi, "Erken çıkış CIKIS_HAZIRLIK hatası üretmelidir."
    assert any(s.kategori == "CIKIS_HAZIRLIK" for s in rapor.sorunlar)


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))



# ---------------------------------------------------------------------------
# TEST P: Milk-Run Geçerli 2-Bacaklı Sefer -> HATA YOK
# ---------------------------------------------------------------------------
def test_milkrun_gecerli_pass_veriyor():
    """
    Geçerli 2-bacaklı milk-run (İstanbul -> Kocaeli -> Bursa) zinciri düzgün
    ve maliyeti doğru hesaplanmışsa HATA üretmemeli.
    """
    mesafe_df = pd.DataFrame([
        {"cikis": "İstanbul", "varis": "Kocaeli", "mesafe_km": 100.0, "sla_gun": 1, "kamyonet_saat": 1.0},
        {"cikis": "Kocaeli", "varis": "Bursa", "mesafe_km": 150.0, "sla_gun": 1, "kamyonet_saat": 1.0},
    ])
    arac_maliyet_df = pd.DataFrame([{
        "arac_adi": "Kamyonet", "kapasite_desi": 5600,
        "kiralik_saatlik_tl": 50, "kiralik_km_tl": 5,
        "spot_saatlik_tl": 100, "spot_km_tl": 10
    }])

    bacak1 = _gecerli_plan_satiri()
    bacak1["Araç ID"] = "V8001"
    bacak1["Araç türü"] = "Kamyonet"
    bacak1["Araç Tipi"] = "Spot"
    bacak1["Çıkış Transfer Merkezi"] = "İstanbul"
    bacak1["Varış Transfer Merkezi"] = "Kocaeli"
    bacak1["Çıkış Tarihi"] = pd.Timestamp(2026, 6, 29)
    bacak1["Çıkış Saati"] = "09:00"
    bacak1["Varış Tarihi"] = pd.Timestamp(2026, 6, 29)
    bacak1["Varış Saati"] = "11:00"
    bacak1["Çıkış Elleçleme süresi"] = 30
    bacak1["Yolculuk süresi"] = 60
    bacak1["Varış elleçleme süresi"] = 30
    # Toplam kullanım bacak1 = 120 dk

    bacak2 = _gecerli_plan_satiri()
    bacak2["Araç ID"] = "V8001"
    bacak2["Araç türü"] = "Kamyonet"
    bacak2["Araç Tipi"] = "Spot"
    bacak2["Çıkış Transfer Merkezi"] = "Kocaeli"
    bacak2["Varış Transfer Merkezi"] = "Bursa"
    bacak2["Çıkış Tarihi"] = pd.Timestamp(2026, 6, 29)
    bacak2["Çıkış Saati"] = "12:00"
    bacak2["Varış Tarihi"] = pd.Timestamp(2026, 6, 29)
    bacak2["Varış Saati"] = "14:00"
    bacak2["Çıkış Elleçleme süresi"] = 30
    bacak2["Yolculuk süresi"] = 60
    bacak2["Varış elleçleme süresi"] = 30
    # Toplam kullanım bacak2 = 120 dk

    # Toplam kullanım = 240 dk = 4 saat. Toplam mesafe = 250 km.
    # Beklenen maliyet = (100 * 4) + (10 * 250) = 400 + 2500 = 2900 TL
    bacak1["Toplam maliyet"] = 2900.0
    bacak2["Toplam maliyet"] = 0.0

    plan_df = pd.DataFrame([bacak1, bacak2])

    rapor = DogrulamaRaporu()
    check_milkrun_tutarlilik(plan_df, mesafe_df, arac_maliyet_df, rapor)

    assert not rapor.hata_var_mi, f"Geçerli milk-run hata vermemeliydi: {rapor.ozet()}"


# ---------------------------------------------------------------------------
# TEST Q: Milk-Run Zinciri Kopuk (bacak[i].varis != bacak[i+1].cikis) -> HATA
# ---------------------------------------------------------------------------
def test_milkrun_zincir_kopuk_hata_verir():
    """
    Zinciri kopuk milk-run (İstanbul -> Kocaeli, sonra Bursa -> Ankara)
    MILKRUN_ZINCIR hatası üretmelidir.
    """
    mesafe_df = pd.DataFrame([
        {"cikis": "İstanbul", "varis": "Kocaeli", "mesafe_km": 100.0, "sla_gun": 1, "kamyonet_saat": 1.0},
        {"cikis": "Bursa", "varis": "Ankara", "mesafe_km": 350.0, "sla_gun": 1, "kamyonet_saat": 3.0},
    ])
    arac_maliyet_df = pd.DataFrame([{
        "arac_adi": "Kamyonet", "kapasite_desi": 5600,
        "kiralik_saatlik_tl": 50, "kiralik_km_tl": 5,
        "spot_saatlik_tl": 100, "spot_km_tl": 10
    }])

    bacak1 = _gecerli_plan_satiri()
    bacak1["Araç ID"] = "V8002"
    bacak1["Çıkış Transfer Merkezi"] = "İstanbul"
    bacak1["Varış Transfer Merkezi"] = "Kocaeli"
    bacak1["Çıkış Tarihi"] = pd.Timestamp(2026, 6, 29)
    bacak1["Çıkış Saati"] = "09:00"
    bacak1["Varış Tarihi"] = pd.Timestamp(2026, 6, 29)
    bacak1["Varış Saati"] = "11:00"

    bacak2 = _gecerli_plan_satiri()
    bacak2["Araç ID"] = "V8002"
    bacak2["Çıkış Transfer Merkezi"] = "Bursa"  # Kocaeli olmalıydı -> KOPUK!
    bacak2["Varış Transfer Merkezi"] = "Ankara"
    bacak2["Çıkış Tarihi"] = pd.Timestamp(2026, 6, 29)
    bacak2["Çıkış Saati"] = "12:00"
    bacak2["Varış Tarihi"] = pd.Timestamp(2026, 6, 29)
    bacak2["Varış Saati"] = "16:00"

    plan_df = pd.DataFrame([bacak1, bacak2])

    rapor = DogrulamaRaporu()
    check_milkrun_tutarlilik(plan_df, mesafe_df, arac_maliyet_df, rapor)

    assert rapor.hata_var_mi, "Zinciri kopuk milk-run HATA üretmelidir."
    assert any(s.kategori == "MILKRUN_ZINCIR" for s in rapor.sorunlar)


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
from time_utils import travel_minutes, handling_minutes


# ---------------------------------------------------------------------------
# Ortak, gerçekçi (İstanbul->Yalova gerçek verisiyle) sabit fixture'lar
# ---------------------------------------------------------------------------
def _mesafe_df():
    return pd.DataFrame([{
        "cikis": "İstanbul", "varis": "Yalova", "mesafe_km": 60,
        "tir_saat": 0.92, "kamyon_saat": 0.86, "hafif_kamyon_saat": 0.8,
        "kamyonet_saat": 0.75, "sla_gun": 1,
    }])


def _arac_maliyet_df():
    return pd.DataFrame([
        {"arac_adi": "Tır", "kapasite_desi": 22400, "kiralik_saatlik_tl": 291.6667,
         "kiralik_km_tl": 13, "spot_saatlik_tl": 487.5, "spot_km_tl": 25},
        {"arac_adi": "Kamyon", "kapasite_desi": 12000, "kiralik_saatlik_tl": 208.3333,
         "kiralik_km_tl": 10, "spot_saatlik_tl": 318.25, "spot_km_tl": 21},
        {"arac_adi": "Hafif Kamyon", "kapasite_desi": 7200, "kiralik_saatlik_tl": 208.3333,
         "kiralik_km_tl": 10, "spot_saatlik_tl": 364.5833, "spot_km_tl": 20},
        {"arac_adi": "Kamyonet", "kapasite_desi": 5600, "kiralik_saatlik_tl": 156.25,
         "kiralik_km_tl": 6, "spot_saatlik_tl": 197.9167, "spot_km_tl": 18},
    ])


def _talep_df():
    return pd.DataFrame([{
        "Talep ID": "D00001", "Tarih": pd.Timestamp(2026, 6, 29),
        "Talep Tamamlama Saati": "09:00", "Çıkış Transfer Merkezi": "İstanbul",
        "Varış Transfer Merkezi": "Yalova", "Tahmin Edilen Desi": 1000,
    }])


def _gecerli_plan_satiri(desi=1000):
    """1000 desi, Kamyonet, gecikmesiz, doğru maliyetli TEK bir geçerli satır."""
    cikis_ellecleme = handling_minutes(desi)   # 10 dk
    yolculuk = travel_minutes(0.75)             # 45 dk (Kamyonet)
    varis_ellecleme = handling_minutes(desi)    # 10 dk
    kullanim_saat = (cikis_ellecleme + yolculuk + varis_ellecleme) / 60.0
    saatlik = 197.9167
    km_tl = 18
    dogru_maliyet = saatlik * kullanim_saat + 60 * km_tl

    return {
        "Araç ID": "V0001", "Araç Tipi": "Spot", "Araç türü": "Kamyonet",
        "Çıkış Transfer Merkezi": "İstanbul", "Varış Transfer Merkezi": "Yalova",
        "Çıkış Tarihi": pd.Timestamp(2026, 6, 29), "Çıkış Saati": "09:10",
        "Varış Tarihi": pd.Timestamp(2026, 6, 29), "Varış Saati": "09:55",
        "Talep ID": "D00001", "Taşınan Desi": desi,
        "Yolculuk süresi": yolculuk, "Varış elleçleme süresi": varis_ellecleme,
        "Çıkış Elleçleme süresi": cikis_ellecleme,
        "SLA cezası": 0.0, "Toplam maliyet": dogru_maliyet,
    }


# ---------------------------------------------------------------------------
# TEST A: Geçerli plan -> hiçbir HATA olmamalı
# ---------------------------------------------------------------------------
def test_gecerli_plan_pass_veriyor():
    talep_df = _talep_df()
    plan_df = pd.DataFrame([_gecerli_plan_satiri()])
    tir_kap = pd.DataFrame([{"tm": "İstanbul", "tir_kapasitesi": 10},
                             {"tm": "Yalova", "tir_kapasitesi": 4}])
    ellecleme = pd.DataFrame([{"tm": "İstanbul", "gunluk_kapasite_desi": 394785.9},
                               {"tm": "Yalova", "gunluk_kapasite_desi": 513170.7}])

    rapor = run_all_checks(talep_df, plan_df, _mesafe_df(), tir_kap, ellecleme, _arac_maliyet_df())
    assert not rapor.hata_var_mi, f"Geçerli plan HATA vermemeliydi:\n{rapor.ozet()}"


# ---------------------------------------------------------------------------
# TEST B: Bozuk ID formatı -> yakalanmalı
# ---------------------------------------------------------------------------
def test_bozuk_id_formati_yakalaniyor():
    plan_df = pd.DataFrame([{**_gecerli_plan_satiri(), "Talep ID": "TALEP-1", "Araç ID": "ARAC1"}])
    rapor = DogrulamaRaporu()
    check_id_formats(plan_df, rapor)
    assert rapor.hata_var_mi
    kategoriler = {s.kategori for s in rapor.sorunlar}
    assert "ID_FORMAT" in kategoriler


# ---------------------------------------------------------------------------
# TEST C: Taşınan desi toplamı tahminle uyuşmuyor -> yakalanmalı
# ---------------------------------------------------------------------------
def test_desi_uyusmazligi_yakalaniyor():
    talep_df = _talep_df()  # 1000 desi tahmin edilmiş
    satir = _gecerli_plan_satiri(desi=400)  # ama sadece 400 desi taşınmış!
    plan_df = pd.DataFrame([satir])
    rapor = DogrulamaRaporu()
    check_talep_traceability(talep_df, plan_df, rapor)
    assert rapor.hata_var_mi
    assert any(s.kategori == "IZLENEBILIRLIK" for s in rapor.sorunlar)


# ---------------------------------------------------------------------------
# TEST D: Tır kapasitesi aşımı -> yakalanmalı
# ---------------------------------------------------------------------------
def test_tir_kapasitesi_asimi_yakalaniyor():
    satir1 = {**_gecerli_plan_satiri(), "Araç türü": "Tır", "Araç ID": "V0001"}
    satir2 = {**_gecerli_plan_satiri(), "Araç türü": "Tır", "Araç ID": "V0002"}
    plan_df = pd.DataFrame([satir1, satir2])
    # Kapasite 1 ama 2 farklı tır İstanbul'dan çıkıyor -> ihlal
    tir_kap = pd.DataFrame([{"tm": "İstanbul", "tir_kapasitesi": 1},
                             {"tm": "Yalova", "tir_kapasitesi": 1}])
    rapor = DogrulamaRaporu()
    check_tir_capacity(plan_df, tir_kap, rapor)
    assert rapor.hata_var_mi
    assert any(s.kategori == "TIR_KAPASITESI" for s in rapor.sorunlar)


# ---------------------------------------------------------------------------
# TEST E: Elleçleme kapasitesi aşımı -> yakalanmalı
# ---------------------------------------------------------------------------
def test_ellecleme_kapasitesi_asimi_yakalaniyor():
    plan_df = pd.DataFrame([_gecerli_plan_satiri(desi=5000)])
    # Yapay olarak çok küçük kapasite veriyoruz (100 desi) - kesin aşılır
    ellecleme = pd.DataFrame([{"tm": "İstanbul", "gunluk_kapasite_desi": 100},
                               {"tm": "Yalova", "gunluk_kapasite_desi": 100}])
    rapor = DogrulamaRaporu()
    check_ellecleme_capacity(plan_df, ellecleme, rapor)
    assert rapor.hata_var_mi
    assert any(s.kategori == "ELLECLEME_KAPASITESI" for s in rapor.sorunlar)


# ---------------------------------------------------------------------------
# TEST F: Yanlış raporlanan SLA cezası -> yakalanmalı
# ---------------------------------------------------------------------------
def test_yanlis_sla_cezasi_yakalaniyor():
    talep_df = _talep_df()  # SLA: 24 saat, talep tamamlanma 29.06 09:00 -> limit 30.06 09:00
    satir = _gecerli_plan_satiri()
    # Aracı bilerek 2 gün geciktiriyoruz (varış 02.07'de tamamlanıyor)
    satir["Varış Tarihi"] = pd.Timestamp(2026, 7, 2)
    satir["Varış Saati"] = "09:55"
    satir["SLA cezası"] = 0.0  # ama yanlışlıkla ceza yok denmiş!
    plan_df = pd.DataFrame([satir])
    rapor = DogrulamaRaporu()
    check_sla_penalty(plan_df, talep_df, _mesafe_df(), rapor)
    assert rapor.hata_var_mi
    assert any(s.kategori == "SLA_CEZASI" for s in rapor.sorunlar)


# ---------------------------------------------------------------------------
# TEST G: Yanlış raporlanan maliyet -> yakalanmalı
# ---------------------------------------------------------------------------
def test_yanlis_maliyet_yakalaniyor():
    satir = _gecerli_plan_satiri()
    satir["Toplam maliyet"] = 1.0  # bariz yanlış
    plan_df = pd.DataFrame([satir])
    rapor = DogrulamaRaporu()
    check_cost(plan_df, _arac_maliyet_df(), _mesafe_df(), rapor)
    assert rapor.hata_var_mi
    assert any(s.kategori == "MALIYET" for s in rapor.sorunlar)


# ---------------------------------------------------------------------------
# TEST H: Talep üç parçaya bölünüp toplam doğruysa kabul edilmeli
# ---------------------------------------------------------------------------
def test_talep_uc_parcaya_bolunup_tam_tasiniyor():
    talep_df = _talep_df()  # D00001 için beklenen toplam: 1000 desi

    satir_1 = {
        **_gecerli_plan_satiri(desi=300),
        "Talep ID": "D00001-1",
        "Araç ID": "V0001",
    }

    satir_2 = {
        **_gecerli_plan_satiri(desi=350),
        "Talep ID": "D00001-2",
        "Araç ID": "V0002",
    }

    satir_3 = {
        **_gecerli_plan_satiri(desi=350),
        "Talep ID": "D00001-3",
        "Araç ID": "V0003",
    }

    plan_df = pd.DataFrame([
        satir_1,
        satir_2,
        satir_3,
    ])

    rapor = DogrulamaRaporu()

    check_talep_traceability(
        talep_df,
        plan_df,
        rapor,
    )

    assert not rapor.hata_var_mi, rapor.ozet()

# ---------------------------------------------------------------------------
# TEST I: SLA tam sınırında tamamlanıyorsa ceza olmamalı
# ---------------------------------------------------------------------------
def test_sla_tam_sinirinda_ceza_yok():
    talep_df = _talep_df()

    satir = _gecerli_plan_satiri()

    # Talep 29.06.2026 09:00'da tamamlanıyor.
    # SLA 1 gün olduğu için son teslim bitişi 30.06.2026 09:00.
    # Varış elleçlemesi 10 dakika sürdüğünden varış başlangıcı 08:50 olmalı.
    satir["Varış Tarihi"] = pd.Timestamp(2026, 6, 30)
    satir["Varış Saati"] = "08:50"
    satir["Varış elleçleme süresi"] = 10
    satir["SLA cezası"] = 0.0

    plan_df = pd.DataFrame([satir])
    rapor = DogrulamaRaporu()

    check_sla_penalty(
        plan_df,
        talep_df,
        _mesafe_df(),
        rapor,
    )

    assert not rapor.hata_var_mi, rapor.ozet()

# ---------------------------------------------------------------------------
# TEST J: SLA sınırı 1 dakika aşılırsa 1 saatlik ceza uygulanmalı
# ---------------------------------------------------------------------------
def test_sla_bir_dakika_gecikmede_bir_saat_ceza():
    talep_df = _talep_df()

    satir = _gecerli_plan_satiri()

    # SLA bitişi: 30.06.2026 09:00
    # Varış elleçlemesi 08:51'de başlayıp 09:01'de tamamlanıyor.
    # Böylece SLA tam 1 dakika aşılmış oluyor.
    satir["Varış Tarihi"] = pd.Timestamp(2026, 6, 30)
    satir["Varış Saati"] = "08:51"
    satir["Varış elleçleme süresi"] = 10

    # 1 dakika gecikme yukarı yuvarlanarak 1 saat kabul edilir.
    # Ceza = 1000 desi × 1 saat × 0.4 TL
    satir["SLA cezası"] = 400.0

    plan_df = pd.DataFrame([satir])
    rapor = DogrulamaRaporu()

    check_sla_penalty(
        plan_df,
        talep_df,
        _mesafe_df(),
        rapor,
    )

    assert not rapor.hata_var_mi, rapor.ozet()

# ---------------------------------------------------------------------------
# TEST K: 5 Temmuz talebi SLA içinde 6 Temmuz teslim edilebilir
# ---------------------------------------------------------------------------
def test_bes_temmuz_talebi_alti_temmuz_teslim_edilebilir():
    talep_df = pd.DataFrame([{
        "Talep ID": "D00001",
        "Tarih": pd.Timestamp(2026, 7, 5),
        "Talep Tamamlama Saati": "17:00",
        "Çıkış Transfer Merkezi": "İstanbul",
        "Varış Transfer Merkezi": "Yalova",
        "Tahmin Edilen Desi": 1000,
    }])

    satir = _gecerli_plan_satiri()

    satir["Çıkış Tarihi"] = pd.Timestamp(2026, 7, 6)
    satir["Varış Tarihi"] = pd.Timestamp(2026, 7, 6)
    satir["Çıkış Saati"] = "08:00"
    satir["Varış Saati"] = "08:45"
    satir["SLA cezası"] = 0.0

    plan_df = pd.DataFrame([satir])

    rapor = DogrulamaRaporu()

    check_sla_penalty(
        plan_df,
        talep_df,
        _mesafe_df(),
        rapor,
    )

    assert not rapor.hata_var_mi, rapor.ozet()

# ---------------------------------------------------------------------------
# TEST L: Planda tahminde olmayan talep varsa hata verilmeli
# ---------------------------------------------------------------------------
def test_planda_bilinmeyen_talep_hata_verir():
    talep_df = _talep_df()

    satir = _gecerli_plan_satiri()

    # Tahminde olmayan bir talep
    satir["Talep ID"] = "D99999"

    plan_df = pd.DataFrame([satir])

    rapor = DogrulamaRaporu()

    check_talep_traceability(
        talep_df,
        plan_df,
        rapor,
    )

    assert rapor.hata_var_mi


# ---------------------------------------------------------------------------
# TEST M: Araç kapasitesini aşan yük -> HATA yakalanmalı
# ---------------------------------------------------------------------------
def test_arac_kapasitesi_asimi_yakalaniyor():
    """Kamyonet kapasitesi 5600 desi; 6000 desi yüklenirse HATA çıkmalı."""
    satir = _gecerli_plan_satiri(desi=6000)   # Kamyonet kapasitesi 5600
    plan_df = pd.DataFrame([satir])

    rapor = DogrulamaRaporu()
    check_arac_kapasitesi(plan_df, _arac_maliyet_df(), rapor)

    assert rapor.hata_var_mi
    assert any(s.kategori == "ARAC_KAPASITESI" for s in rapor.sorunlar)


# ---------------------------------------------------------------------------
# TEST N: Bir gün eksik kiralık filo -> HATA yakalanmalı
# ---------------------------------------------------------------------------
def test_eksik_kiralik_filo_yakalaniyor():
    """
    Günlük kota 2 kiralık araç; 29 Haziran'da yalnızca 1 araç planlanırsa
    KIRALIK_FILO hatası üretilmeli.
    """
    # kiralik_araclar_df: 2 satır -> günlük toplam kota = 2
    kiralik_df = pd.DataFrame([
        {"cikis": "İstanbul", "varis": "Yalova", "arac_sayisi": 1, "arac_turu": "Kamyonet"},
        {"cikis": "Yalova", "varis": "İstanbul", "arac_sayisi": 1, "arac_turu": "Kamyonet"},
    ])

    # Sadece 1 kiralık araç var, 29 Haziran'da
    satir = _gecerli_plan_satiri()
    satir["Araç Tipi"] = "Kiralık"
    satir["Çıkış Tarihi"] = pd.Timestamp(2026, 6, 29)

    plan_df = pd.DataFrame([satir])

    rapor = DogrulamaRaporu()
    check_kiralik_filo(plan_df, kiralik_df, rapor)

    assert rapor.hata_var_mi
    assert any(s.kategori == "KIRALIK_FILO" for s in rapor.sorunlar)


# ---------------------------------------------------------------------------
# TEST O: Boş Spot araç (0 desi) -> HATA yakalanmalı
# ---------------------------------------------------------------------------
def test_bos_spot_arac_yakalaniyor():
    """
    Araç Tipi=="Spot" ve toplam Taşınan Desi==0 olan araç planda bulunursa
    BOS_SPOT_ARAC hatası üretilmeli.
    Kiralık boş araç (Araç Tipi=="Kiralık") hata üretmemeli.
    """
    # Spot araç, 0 desi -> HATA beklenir
    satir = _gecerli_plan_satiri(desi=0)
    satir["Araç Tipi"] = "Spot"
    satir["Araç ID"] = "V9901"
    plan_df = pd.DataFrame([satir])

    rapor = DogrulamaRaporu()
    check_bos_spot_arac(plan_df, rapor)

    assert rapor.hata_var_mi, "Bos Spot arac HATA uretmeli"
    assert any(s.kategori == "BOS_SPOT_ARAC" for s in rapor.sorunlar)

    # Kiralık boş araç -> HATA OLMAMALI
    satir_kiralik = _gecerli_plan_satiri(desi=0)
    satir_kiralik["Araç Tipi"] = "Kiralık"
    satir_kiralik["Araç ID"] = "V9902"
    plan_kiralik = pd.DataFrame([satir_kiralik])

    rapor2 = DogrulamaRaporu()
    check_bos_spot_arac(plan_kiralik, rapor2)
    assert not rapor2.hata_var_mi, "Kiralik bos arac BOS_SPOT_ARAC hatasi uretmemeli"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))

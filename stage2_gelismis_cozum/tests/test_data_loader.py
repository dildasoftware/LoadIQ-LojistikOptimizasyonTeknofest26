import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "config"))

from data_loader import load_all
import rules


@pytest.fixture(scope="module")
def veri():
    """66.024 satırlık excel'i her testte değil, modül başına 1 kez okur.
    (İlk versiyonda her test kendi load_all() çağırıyordu, 6 test x ~7sn
    okuma süresi = testler zaman aşımına giriyordu. Bu düzeltildi.)"""
    return load_all()


def test_tum_dosyalar_yukleniyor(veri):
    assert len(veri["talep"]) == 66024
    assert len(veri["mesafe"]) == 306
    assert len(veri["ellecleme_kapasitesi"]) == 18
    assert len(veri["tir_kapasitesi"]) == 18
    assert len(veri["kiralik_araclar"]) == 12
    assert len(veri["arac_maliyet"]) == 4


def test_18_transfer_merkezi_tutarli(veri):
    tm_talep = set(veri["talep"]["cikis"]) | set(veri["talep"]["varis"])
    assert len(tm_talep) == 18


def test_289_aktif_rota(veri):
    rota_sayisi = veri["talep"].groupby(["cikis", "varis"]).ngroups
    assert rota_sayisi == 289


def test_kocaeli_varisli_rota_yok(veri):
    assert (veri["talep"]["varis"] == "Kocaeli").sum() == 0


def test_negatif_desi_yok(veri):
    assert (veri["talep"]["desi"] < 0).sum() == 0


def test_tir_yasak_tm_listesi_config_ile_uyumlu(veri):
    sifir_olanlar = set(veri["tir_kapasitesi"][veri["tir_kapasitesi"]["tir_kapasitesi"] == 0]["tm"])
    assert sifir_olanlar == rules.TIR_TAMAMEN_YASAK_TM


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))

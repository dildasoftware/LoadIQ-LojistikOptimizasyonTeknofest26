import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from time_utils import (
    travel_minutes,
    handling_minutes,
    split_handling_across_midnight,
)


def test_travel_minutes_duyuru_ornegi():
    # Duyuru: Istanbul->Yalova Tir suresi 0.92 saat -> 55.2 dk -> 56 dk
    assert travel_minutes(0.92) == 56


def test_travel_minutes_tam_sayi_float_hatasi_yok():
    # 60 dk tam ise 61'e sicramamali (float hassasiyet testi)
    assert travel_minutes(1.0) == 60
    assert travel_minutes(2.0) == 120


def test_travel_minutes_kucuk_deger():
    assert travel_minutes(0.01) == 1  # 0.6 dk -> 1 dk


def test_handling_minutes_ornekler():
    assert handling_minutes(5000) == 50
    assert handling_minutes(10000) == 100
    assert handling_minutes(1) == 1  # 0.01 dk -> yukari yuvarla -> 1 dk


def test_handling_minutes_sifir():
    assert handling_minutes(0) == 0


def test_split_handling_gece_yarisi_duyuru_ornegi():
    # Duyuru: 29.06 23:30'da baslayan 10.000 desilik (100 dk) ellecleme
    # -> 29.06: 3000 desi (30 dk), 30.06: 7000 desi (70 dk)
    start = datetime(2026, 6, 29, 23, 30)
    segments = split_handling_across_midnight(start, duration_minutes=100, desi=10000)
    assert len(segments) == 2
    day1, min1, desi1 = segments[0]
    day2, min2, desi2 = segments[1]
    assert day1 == start.date()
    assert min1 == 30
    assert desi1 == 3000
    assert day2.day == 30
    assert min2 == 70
    assert desi2 == 7000


def test_split_handling_gece_yarisini_asmiyorsa_tek_segment():
    start = datetime(2026, 6, 29, 10, 0)
    segments = split_handling_across_midnight(start, duration_minutes=50, desi=5000)
    assert len(segments) == 1
    assert segments[0] == (start.date(), 50, 5000)


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))

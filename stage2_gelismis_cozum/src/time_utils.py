"""
LoadIQ - Zaman ve Yuvarlama Yardımcı Fonksiyonları

Bu modül, 13.07.2026 tarihli ek duyuruda netleşen zaman/yuvarlama kurallarını
uygular. Kaynak: outputs/is_kurallari_spec.md Bölüm 2.

KURALLAR:
  - Yol süresi (dakika) = ceil(mesafe_matrisi_saat * 60)
  - Elleçleme süresi (dakika) = ceil(desi * 0.01)
  - İki yuvarlama AYRI yapılır, sonra toplanır (önce toplayıp tek seferde
    yuvarlamak YANLIŞ).
  - Gece yarısını (00:00) aşan elleçleme işlemleri, geçirilen süreye oransal
    olarak günler arasında bölünür.

Doğrulama örneği (duyurudan): İstanbul->Yalova Tır süresi 0.92 saat.
0.92 * 60 = 55.2 dk -> yukarı yuvarla -> 56 dk.
"""

import math
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_CEILING

_EPS = 1e-9


def _ceil_clean(value: float) -> int:
    """Kayan nokta hatalarından (ör. 60.00000000001) etkilenmeyen yukarı yuvarlama.

    Değeri önce 6 ondalık basamağa yuvarlayıp öyle ceil alıyoruz; böylece
    tam sayıya çok yakın ama teknik olarak üstünde kalan float değerler
    yanlışlıkla bir üst tam sayıya sıçramıyor.
    """
    d = Decimal(str(round(value, 6)))
    return int(d.to_integral_value(rounding=ROUND_CEILING))


def travel_minutes(hours: float) -> int:
    """Yol süresini (saat) dakikaya çevirip yukarı yuvarlar.

    >>> travel_minutes(0.92)
    56
    """
    if hours < 0:
        raise ValueError(f"Negatif süre olamaz: {hours}")
    return _ceil_clean(hours * 60)


def handling_minutes(desi: float) -> int:
    """Elleçleme süresini (desi * 0.01 dk/desi) yukarı yuvarlar.

    >>> handling_minutes(5000)
    50
    >>> handling_minutes(10000)
    100
    """
    if desi < 0:
        raise ValueError(f"Negatif desi olamaz: {desi}")
    return _ceil_clean(desi * 0.01)


def split_handling_across_midnight(start: datetime, duration_minutes: int, desi: float):
    """Gece yarısını aşan bir elleçleme işlemini, geçen süreye oransal olarak
    günlere böler.

    Döner: [(tarih: date, dakika_payı: int, desi_payı: float), ...]

    Doğrulama örneği (duyurudan):
    29.06 23:30'da başlayan 10.000 desilik (100 dk) elleçleme ->
      29.06: 30 dk, 3000 desi
      30.06: 70 dk, 7000 desi
    """
    if duration_minutes <= 0:
        return []

    end = start + timedelta(minutes=duration_minutes)
    if start.date() == end.date():
        return [(start.date(), duration_minutes, desi)]

    segments = []
    cursor = start
    remaining_minutes = duration_minutes
    while remaining_minutes > 0:
        midnight = datetime(cursor.year, cursor.month, cursor.day) + timedelta(days=1)
        minutes_today = min(remaining_minutes, int((midnight - cursor).total_seconds() // 60))
        if minutes_today <= 0:
            # cursor tam gece yarısındaysa bir sonraki güne geç
            cursor = midnight
            continue
        desi_share = desi * (minutes_today / duration_minutes)
        segments.append((cursor.date(), minutes_today, desi_share))
        remaining_minutes -= minutes_today
        cursor = midnight
    return segments


def format_hhmm(dt: datetime) -> str:
    """Çıktı dosyaları için HH:MM formatı (13.07.2026 duyurusu: SSDD yeterli,
    saniye istenmiyor)."""
    return dt.strftime("%H:%M")

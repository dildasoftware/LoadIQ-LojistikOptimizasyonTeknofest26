"""
utils.py — Ortak yardımcı fonksiyonlar
LoadIQ TEKNOFEST 2026 Lojistik Optimizasyon Projesi
"""

import math

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    İki nokta arasındaki kuş uçuşu mesafeyi (Haversine formülü) 
    kilometre cinsinden hesaplar.
    
    FAQ #6'ya göre mesafeler kuş uçuşu hesaplanacaktır.
    Karayolu katsayısı KULLANILMAZ.
    
    Args:
        lat1, lon1: Birinci noktanın enlem/boylamı (derece)
        lat2, lon2: İkinci noktanın enlem/boylamı (derece)
    
    Returns:
        Mesafe (km)
    """
    R = 6371.0  # Dünya yarıçapı (km)
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

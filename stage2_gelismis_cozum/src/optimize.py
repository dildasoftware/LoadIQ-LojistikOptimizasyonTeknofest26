"""
LoadIQ - Optimizasyon Motoru (optimize.py)
Teknofest 2026 Lojistik Optimizasyon Yarışması - Gelişmiş Çözüm Aşaması
"""

import os
import sys
import math
import datetime
from datetime import timedelta
from collections import defaultdict
import pandas as pd
# pyrefly: ignore [missing-import]
import numpy as np

# Proje dizinlerini ekle
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _THIS_DIR)
sys.path.insert(0, os.path.abspath(os.path.join(_THIS_DIR, "..", "config")))

from time_utils import travel_minutes, handling_minutes, split_handling_across_midnight, format_hhmm
# pyrefly: ignore [missing-import]
import rules


def to_datetime(date_val, time_str):
    """Tarih (date/Timestamp/str) ve saat (HH:MM) bilgisini datetime nesnesine dönüştürür."""
    if isinstance(date_val, pd.Timestamp):
        date_val = date_val.date()
    elif isinstance(date_val, str):
        # Olası string tarihleri parse et
        date_val = datetime.datetime.strptime(date_val.split(" ")[0], "%Y-%m-%d").date()
    h, m = map(int, str(time_str).split(":"))
    return datetime.datetime(date_val.year, date_val.month, date_val.day, h, m)


def calculate_vehicle_cost(arac_tipi, arac_turu, total_desi, yol_dk, mesafe_km, vehicle_maliyet):
    """checker.py ile birebir uyumlu olacak şekilde araç bacak maliyetini hesaplar."""
    fiyat = vehicle_maliyet[arac_turu]
    if arac_tipi == "Kiralık":
        saatlik = fiyat["kiralik_saatlik"]
        km_tl = fiyat["kiralik_km"]
    else:
        saatlik = fiyat["spot_saatlik"]
        km_tl = fiyat["spot_km"]
    
    cikis_ellecleme = handling_minutes(total_desi)
    varis_ellecleme = handling_minutes(total_desi)
    kullanim_dk = cikis_ellecleme + yol_dk + varis_ellecleme
    kullanim_saat = kullanim_dk / 60.0
    return (saatlik * kullanim_saat) + (mesafe_km * km_tl)


def get_dummy_demand_for_route(cikis, varis, talep_df):
    """Boş kiralık araçları juri formatına uydurmak için rota bazlı bir dummy talep ID döndürür."""
    route_demands = talep_df[(talep_df["Çıkış Transfer Merkezi"] == cikis) & (talep_df["Varış Transfer Merkezi"] == varis)]
    if not route_demands.empty:
        return route_demands.iloc[0]["Talep ID"]
    return talep_df.iloc[0]["Talep ID"]


def generate_plan(talep_df: pd.DataFrame, veri: dict) -> pd.DataFrame:
    """
    Kiralık ve spot araç filolarını planlayarak jüri şablonuna uygun plan DataFrame'ini üretir.
    """
    mesafe_df = veri["mesafe"]
    ellecleme_df = veri["ellecleme_kapasitesi"]
    tir_kapasitesi_df = veri["tir_kapasitesi"]
    kiralik_araclar_df = veri["kiralik_araclar"]
    arac_maliyet_df = veri["arac_maliyet"]

    # Tarihleri normalize et
    talep_df = talep_df.copy()
    talep_df["Tarih"] = talep_df["Tarih"].apply(lambda x: x.date() if isinstance(x, pd.Timestamp) else x)

    # Araç maliyet ve kapasite haritası
    vehicle_maliyet = {}
    for _, row in arac_maliyet_df.iterrows():
        name = row["arac_adi"]
        vehicle_maliyet[name] = {
            "capacity": row["kapasite_desi"],
            "kiralik_saatlik": row["kiralik_saatlik_tl"],
            "kiralik_km": row["kiralik_km_tl"],
            "spot_saatlik": row["spot_saatlik_tl"],
            "spot_km": row["spot_km_tl"]
        }

    # Rota mesafe ve süre (yolculuk dakikaları) haritası
    route_details = {}
    dur_col_map = {
        "Tır": "tir_saat",
        "Kamyon": "kamyon_saat",
        "Hafif Kamyon": "hafif_kamyon_saat",
        "Kamyonet": "kamyonet_saat"
    }
    for _, row in mesafe_df.iterrows():
        c = row["cikis"]
        v = row["varis"]
        route_details[(c, v)] = {
            "mesafe_km": row["mesafe_km"],
            "sla_gun": int(row["sla_gun"]),
            "durations": {
                vt: travel_minutes(row[col]) for vt, col in dur_col_map.items()
            }
        }

    # Planlama tarih penceresi
    start_date = rules.TAHMIN_BASLANGIC
    end_date = rules.TAHMIN_BITIS

    # Günlük Tır ve Elleçleme kapasitelerini ilklendir (hata almamak için geniş bir aralık)
    remaining_tir = {}
    for _, row in tir_kapasitesi_df.iterrows():
        tm = row["tm"]
        cap = row["tir_kapasitesi"]
        remaining_tir[tm] = {}
        for day_offset in range(-5, 35):
            d = start_date + timedelta(days=day_offset)
            remaining_tir[tm][d] = cap

    remaining_ellecleme = {}
    for _, row in ellecleme_df.iterrows():
        tm = row["tm"]
        cap = row["gunluk_kapasite_desi"]
        remaining_ellecleme[tm] = {}
        for day_offset in range(-5, 35):
            d = start_date + timedelta(days=day_offset)
            remaining_ellecleme[tm][d] = cap

    # Bekleyen talepler kuyruğunu oluştur
    pending_demands = defaultdict(list)
    for _, row in talep_df.iterrows():
        c = row["Çıkış Transfer Merkezi"]
        v = row["Varış Transfer Merkezi"]
        
        # Kocaeli varışlı rotalar hariç tutulur
        if rules.is_route_excluded(c, v):
            continue
            
        tid = row["Talep ID"]
        t_date = row["Tarih"]
        t_saat = row["Talep Tamamlama Saati"]
        t_dt = to_datetime(t_date, t_saat)
        desi = row["Tahmin Edilen Desi"]
        if desi > 0:
            pending_demands[(c, v)].append({
                "talep_id": tid,
                "completion_time": t_dt,
                "desi": desi,
                "base_desi": desi
            })

    # Talepleri zaman sırasına göre sırala
    for r in pending_demands:
        pending_demands[r].sort(key=lambda x: x["completion_time"])

    # Oluşturulan araç seferleri listesi
    trips = []

    # Araç ID üreteci
    global_vehicle_counter = 0
    def next_vehicle_id():
        nonlocal global_vehicle_counter
        global_vehicle_counter += 1
        return f"V{global_vehicle_counter:04d}"

    # Elleçleme kapasitesini aşmayacak en büyük yükü hesaplar (oransal gece yarısı dahil)
    def check_and_fit_ellecleme(cikis, varis, start_dt, yol_dk, w):
        def is_feasible(w_test):
            if w_test <= 0:
                return True
            c_dk = handling_minutes(w_test)
            v_dk = handling_minutes(w_test)
            dep_dt = start_dt + timedelta(minutes=c_dk)
            arr_dt = dep_dt + timedelta(minutes=yol_dk)
            
            c_segs = split_handling_across_midnight(start_dt, c_dk, w_test)
            v_segs = split_handling_across_midnight(arr_dt, v_dk, w_test)
            
            for d, _, share in c_segs:
                if remaining_ellecleme[cikis].get(d, 0.0) < share - 1e-5:
                    return False
            for d, _, share in v_segs:
                if remaining_ellecleme[varis].get(d, 0.0) < share - 1e-5:
                    return False
            return True

        if is_feasible(w):
            c_dk = handling_minutes(w)
            dep_dt = start_dt + timedelta(minutes=c_dk)
            arr_dt = dep_dt + timedelta(minutes=yol_dk)
            return w, c_dk, handling_minutes(w), arr_dt

        # Binary search ile kapasiteye sığan en büyük desiyi bul
        low = 0.0
        high = float(w)
        best_w = 0.0
        for _ in range(15):
            mid = (low + high) / 2.0
            if is_feasible(mid):
                best_w = mid
                low = mid
            else:
                high = mid
        best_w = math.floor(best_w)
        if best_w <= 0:
            return 0.0, 0, 0, None

        c_dk = handling_minutes(best_w)
        dep_dt = start_dt + timedelta(minutes=c_dk)
        arr_dt = dep_dt + timedelta(minutes=yol_dk)
        return best_w, c_dk, handling_minutes(best_w), arr_dt

    # Tır kapasitesini kontrol et
    def check_tir_cap(cikis, varis, dep_date, arr_date):
        if remaining_tir[cikis].get(dep_date, 0) < 1:
            return False
        if remaining_tir[varis].get(arr_date, 0) < 1:
            return False
        return True

    # 1. KIRALIK ARAÇLARIN ÖNCEDEN ATANMASI (HER GÜN SABİT)
    for day_offset in range((end_date - start_date).days + 1):
        D = start_date + timedelta(days=day_offset)
        for _, row in kiralik_araclar_df.iterrows():
            c = row["cikis"]
            v = row["varis"]
            if rules.is_route_excluded(c, v):
                continue
            arac_turu = row["arac_turu"]
            arac_turu = "Tır" if arac_turu.lower() in ["tir", "tır"] else arac_turu
            arac_sayisi = int(row["arac_sayisi"])
            
            if (c, v) not in route_details:
                continue
            r_det = route_details[(c, v)]
            yol_dk = r_det["durations"][arac_turu]
            mesafe_km = r_det["mesafe_km"]
            cap = vehicle_maliyet[arac_turu]["capacity"]
            
            for _ in range(arac_sayisi):
                # Gün D saat 17:00'ye kadar tamamlanan tüm bekleyen talepler
                active_demands = [d for d in pending_demands[(c, v)] if d["completion_time"] <= datetime.datetime(D.year, D.month, D.day, 17, 0)]
                
                loaded_demands = []
                loaded_desi = 0.0
                
                for d in list(active_demands):
                    rem_cap = cap - loaded_desi
                    if rem_cap <= 0:
                        break
                    
                    load = min(d["desi"], rem_cap)
                    
                    # Kiralık araca yüklenirse varış ve SLA gecikmesini hesapla:
                    t_start = datetime.datetime(D.year, D.month, D.day, 9, 0)
                    c_ellec_est = handling_minutes(loaded_desi + load)
                    v_ellec_est = handling_minutes(loaded_desi + load)
                    varis_dt_est = t_start + timedelta(minutes=c_ellec_est + yol_dk + v_ellec_est)
                    
                    # SLA son tarihi
                    sla_deadline = d["completion_time"] + timedelta(hours=r_det["sla_gun"] * 24)
                    
                    # Gecikme saati ve SLA cezası
                    gecikme_s = max(0.0, (varis_dt_est - sla_deadline).total_seconds())
                    gecikme_h = -(-int(gecikme_s) // 3600)  # tavan (ceil)
                    kiralik_sla_cost = load * gecikme_h * 0.4
                    
                    # Aynı load'ı HEMEN spot araçla göndermenin en ucuz maliyeti:
                    min_spot_cost = float('inf')
                    for vt in ["Tır", "Kamyon", "Hafif Kamyon", "Kamyonet"]:
                        # Tır spot yasak kontrolü
                        if vt == "Tır":
                            if c in rules.TIR_TAMAMEN_YASAK_TM or v in rules.TIR_TAMAMEN_YASAK_TM:
                                continue
                            if c in rules.TIR_SPOT_YASAK_TM or v in rules.TIR_SPOT_YASAK_TM:
                                continue
                        
                        vt_yol_dk = r_det["durations"][vt]
                        vt_c_dk = handling_minutes(load)
                        vt_v_dk = handling_minutes(load)
                        vt_toplam_dk = vt_c_dk + vt_yol_dk + vt_v_dk
                        
                        mt = vehicle_maliyet[vt]
                        saatlik = mt["spot_saatlik"]
                        km_tl = mt["spot_km"]
                        vt_cost = (saatlik * vt_toplam_dk / 60.0) + (mesafe_km * km_tl)
                        if vt_cost < min_spot_cost:
                            min_spot_cost = vt_cost
                    
                    # Kiralık ile gecikmenin SLA cezası, spot gönderme maliyetinden fazla ise kiralığa yükleme
                    if kiralik_sla_cost > min_spot_cost:
                        continue
                    
                    # Kiralık yükleme mantığı
                    if d["desi"] <= rem_cap:
                        loaded_demands.append({
                            "talep_id": d["talep_id"],
                            "desi": d["desi"]
                        })
                        loaded_desi += d["desi"]
                        pending_demands[(c, v)].remove(d)
                        active_demands.remove(d)
                    else:
                        loaded_demands.append({
                            "talep_id": d["talep_id"],
                            "desi": rem_cap
                        })
                        loaded_desi += rem_cap
                        d["desi"] -= rem_cap
                        break
                
                # Kalkış saati DAİMA 09:00 olarak sabitleniyor.
                # Kiralık araçlar talep saatine bağlı değildir; şartname gereği
                # her gün düzenli çalışırlar. Sabit kalkış → deterministik varış
                # tarihi → TIR kapasitesi gün çakışması önlenir (Balıkesir/Tekirdağ).
                t_start = datetime.datetime(D.year, D.month, D.day, 9, 0)

                # Talep olmayan kiralık araç: 0 desiyle çalıştır (şartname gereği)
                if not loaded_demands:
                    dummy_tid = get_dummy_demand_for_route(c, v, talep_df)
                    loaded_demands.append({
                        "talep_id": dummy_tid,
                        "desi": 0.0
                    })
                    loaded_desi = 0.0
                
                c_ellecleme = handling_minutes(loaded_desi)
                v_ellecleme = handling_minutes(loaded_desi)
                cikis_dt = t_start + timedelta(minutes=c_ellecleme)
                varis_dt = cikis_dt + timedelta(minutes=yol_dk)
                
                cost = calculate_vehicle_cost("Kiralık", arac_turu, loaded_desi, yol_dk, mesafe_km, vehicle_maliyet)
                
                trips.append({
                    "arac_id": next_vehicle_id(),
                    "arac_tipi": "Kiralık",
                    "arac_turu": arac_turu,
                    "cikis": c,
                    "varis": v,
                    "cikis_dt": cikis_dt,
                    "varis_dt": varis_dt,
                    "t_start": t_start,
                    "demands": loaded_demands,
                    "yolculuk_suresi": yol_dk,
                    "cikis_ellecleme": c_ellecleme,
                    "varis_ellecleme": v_ellecleme,
                    "maliyet": cost
                })
                
                # Kapasite tüketimleri
                if arac_turu == "Tır":
                    dep_date = cikis_dt.date()
                    arr_date = varis_dt.date()
                    remaining_tir[c][dep_date] = max(0, remaining_tir[c].get(dep_date, 0) - 1)
                    remaining_tir[v][arr_date] = max(0, remaining_tir[v].get(arr_date, 0) - 1)
                
                for day, _, share in split_handling_across_midnight(t_start, c_ellecleme, loaded_desi):
                    remaining_ellecleme[c][day] = remaining_ellecleme[c].get(day, 0) - share
                for day, _, share in split_handling_across_midnight(varis_dt, v_ellecleme, loaded_desi):
                    remaining_ellecleme[v][day] = remaining_ellecleme[v].get(day, 0) - share

    # 2. SPOT ARAÇLARIN PLANLANMASI (DÖNGÜ)
    D = start_date
    max_days = 25
    loop_count = 0
    route_sla_gun = {r: route_details[r]["sla_gun"] for r in pending_demands if r in route_details}

    while loop_count < max_days:
        total_pending_desi = sum(sum(d["desi"] for d in demands) for demands in pending_demands.values())
        if total_pending_desi <= 0:
            break
            
        is_cleanup = (D > end_date)
        
        # Öncelikli rotaları bul: sla_gun (küçükten büyüğe), toplam bekleyen desi (büyükten küçüğe)
        routes_to_process = []
        for route, demands in pending_demands.items():
            active_demands = [d for d in demands if d["completion_time"] <= datetime.datetime(D.year, D.month, D.day, 17, 0)]
            if active_demands:
                total_w = sum(d["desi"] for d in active_demands)
                sla_gun = route_sla_gun.get(route, 2)
                routes_to_process.append((route, total_w, sla_gun))
        
        routes_to_process.sort(key=lambda x: (x[2], -x[1]))
        
        for route_info in routes_to_process:
            route = route_info[0]
            c, v = route
            
            active_demands = [d for d in pending_demands[route] if d["completion_time"] <= datetime.datetime(D.year, D.month, D.day, 17, 0)]
            if not active_demands:
                continue
                
            unique_times = sorted(list(set(d["completion_time"] for d in active_demands)))
            
            for t_j in unique_times:
                while True:
                    current_active = [d for d in pending_demands[route] if d["completion_time"] <= t_j]
                    W = sum(d["desi"] for d in current_active)
                    if W <= 0:
                        break
                        
                    candidates = []
                    for vt in ["Tır", "Kamyon", "Hafif Kamyon", "Kamyonet"]:
                        if vt == "Tır":
                            if c in rules.TIR_TAMAMEN_YASAK_TM or v in rules.TIR_TAMAMEN_YASAK_TM:
                                continue
                            if c in rules.TIR_SPOT_YASAK_TM or v in rules.TIR_SPOT_YASAK_TM:
                                continue
                                
                        cap = vehicle_maliyet[vt]["capacity"]
                        w_try = min(W, cap)
                        
                        r_det = route_details[(c, v)]
                        yol_dk = r_det["durations"][vt]
                        mesafe_km = r_det["mesafe_km"]
                        
                        w_fit, c_dk, v_dk, arr_dt = check_and_fit_ellecleme(c, v, t_j, yol_dk, w_try)
                        if w_fit <= 0:
                            continue
                            
                        dep_dt = t_j + timedelta(minutes=c_dk)
                        if vt == "Tır":
                            if not check_tir_cap(c, v, dep_dt.date(), arr_dt.date()):
                                continue
                                
                        cost = calculate_vehicle_cost("Spot", vt, w_fit, yol_dk, mesafe_km, vehicle_maliyet)
                        benefit = w_fit * 9.6 - cost  # SLA tasarrufu (24 saat gecikme = 9.6 TL/desi)
                        
                        candidates.append({
                            "arac_turu": vt,
                            "w_fit": w_fit,
                            "cost": cost,
                            "benefit": benefit,
                            "dep_dt": dep_dt,
                            "arr_dt": arr_dt,
                            "cikis_ellecleme": c_dk,
                            "varis_ellecleme": v_dk
                        })
                    
                    if not candidates:
                        break
                        
                    chosen = None
                    if is_cleanup:
                        # Temizlik bacağında bekleyen her şeyi bitir (en yüksek tonaj, en ucuz maliyet)
                        candidates.sort(key=lambda x: (-x["w_fit"], x["cost"]))
                        chosen = candidates[0]
                    else:
                        candidates.sort(key=lambda x: -x["benefit"])
                        best = candidates[0]
                        if best["benefit"] > 0:
                            chosen = best
                            
                    if chosen is None:
                        break

                    w_allocated = chosen["w_fit"]
                    vt_chosen = chosen["arac_turu"]
                    dep_dt = chosen["dep_dt"]
                    arr_dt = chosen["arr_dt"]
                    c_dk = chosen["cikis_ellecleme"]
                    v_dk = chosen["varis_ellecleme"]
                    cost = chosen["cost"]
                    
                    # Talepleri yükle
                    loaded_demands = []
                    rem_w = w_allocated
                    for d in list(pending_demands[route]):
                        if rem_w <= 0:
                            break
                        if d["completion_time"] > t_j:
                            continue
                        if d["desi"] <= rem_w:
                            loaded_demands.append({
                                "talep_id": d["talep_id"],
                                "desi": d["desi"]
                            })
                            rem_w -= d["desi"]
                            pending_demands[route].remove(d)
                        else:
                            loaded_demands.append({
                                "talep_id": d["talep_id"],
                                "desi": rem_w
                            })
                            d["desi"] -= rem_w
                            rem_w = 0.0
                            break
                            
                    trips.append({
                        "arac_id": next_vehicle_id(),
                        "arac_tipi": "Spot",
                        "arac_turu": vt_chosen,
                        "cikis": c,
                        "varis": v,
                        "cikis_dt": dep_dt,
                        "varis_dt": arr_dt,
                        "t_start": t_j,
                        "demands": loaded_demands,
                        "yolculuk_suresi": route_details[(c, v)]["durations"][vt_chosen],
                        "cikis_ellecleme": c_dk,
                        "varis_ellecleme": v_dk,
                        "maliyet": cost
                    })
                    
                    if vt_chosen == "Tır":
                        remaining_tir[c][dep_dt.date()] -= 1
                        remaining_tir[v][arr_dt.date()] -= 1
                        
                    for day, _, share in split_handling_across_midnight(t_j, c_dk, w_allocated):
                        remaining_ellecleme[c][day] -= share
                    for day, _, share in split_handling_across_midnight(arr_dt, v_dk, w_allocated):
                        remaining_ellecleme[v][day] -= share
        
        D += timedelta(days=1)
        loop_count += 1

    # 3. TALEP BÖLÜNME İNDEKSLERİNİN ATANMASI VE SATIRLARIN FLATTEN EDİLMESİ
    base_counts = defaultdict(int)
    for trip in trips:
        for d in trip["demands"]:
            base_counts[d["talep_id"]] += 1

    split_indices = defaultdict(int)
    rows = []
    talep_bilgi = talep_df.set_index("Talep ID").to_dict("index")

    for trip in trips:
        arac_id = trip["arac_id"]
        arac_tipi = trip["arac_tipi"]
        arac_turu = trip["arac_turu"]
        cikis = trip["cikis"]
        varis = trip["varis"]
        cikis_date = trip["cikis_dt"].date()
        cikis_saat = format_hhmm(trip["cikis_dt"])
        varis_date = trip["varis_dt"].date()
        varis_saat = format_hhmm(trip["varis_dt"])
        yol_dk = trip["yolculuk_suresi"]
        c_dk = trip["cikis_ellecleme"]
        v_dk = trip["varis_ellecleme"]
        cost = trip["maliyet"]

        for demand_index, d in enumerate(trip["demands"]):
            base_id = d["talep_id"]
            desi = d["desi"]

            if base_counts[base_id] > 1:
                split_indices[base_id] += 1
                talep_id_str = f"{base_id}-{split_indices[base_id]}"
            else:
                talep_id_str = base_id

            # SLA cezası hesabı (talep/satır bazında doğru — dokunulmadı)
            bilgi = talep_bilgi.get(base_id)
            if bilgi is not None:
                talep_tamamlanma = to_datetime(bilgi["Tarih"], bilgi["Talep Tamamlama Saati"])
                sla_limit_saat = route_details[(cikis, varis)]["sla_gun"] * 24
                sla_bitis = talep_tamamlanma + timedelta(hours=sla_limit_saat)
                varis_ellecleme_bitis = trip["varis_dt"] + timedelta(minutes=v_dk)
                gecikme_saniye = (varis_ellecleme_bitis - sla_bitis).total_seconds()
                if gecikme_saniye <= 0:
                    sla_penalty = 0.0
                else:
                    gecikme_saat = -(-int(gecikme_saniye) // 3600)
                    sla_penalty = desi * gecikme_saat * rules.SLA_CEZA_TL_PER_DESI_SAAT
            else:
                sla_penalty = 0.0

            # "Toplam maliyet": bacak (leg) maliyeti yalnızca İLK satıra yazılır.
            # Aynı bacağın 2., 3., ... talep satırlarına 0.0 yazılır.
            # Böylece sütunun düz toplamı = gerçek araç maliyeti (şişme yok).
            # NOT: SLA cezası sütunu zaten satır bazında doğru; değiştirilmedi.
            satir_maliyeti = round(cost, 2) if demand_index == 0 else 0.0

            rows.append({
                "Araç ID": arac_id,
                "Araç Tipi": arac_tipi,
                "Araç türü": arac_turu,
                "Çıkış Transfer Merkezi": cikis,
                "Varış Transfer Merkezi": varis,
                "Çıkış Tarihi": cikis_date,
                "Çıkış Saati": cikis_saat,
                "Varış Tarihi": varis_date,
                "Varış Saati": varis_saat,
                "Talep ID": talep_id_str,
                "Taşınan Desi": round(desi, 2),
                "Yolculuk süresi": int(yol_dk),
                "Varış elleçleme süresi": int(v_dk),
                "Çıkış Elleçleme süresi": int(c_dk),
                "SLA cezası": round(sla_penalty, 2),
                "Toplam maliyet": satir_maliyeti,
            })

    plan_df = pd.DataFrame(rows)

    # 0-desi Spot satırlarını ve tamamen boş Spot araçlarını temizle.
    # Kiralık araçlar şartname gereği boş sefer yapabilir → dokunma.
    plan_df = _temizle_bos_spot(plan_df)

    cols = [
        "Araç ID", "Araç Tipi", "Araç türü", "Çıkış Transfer Merkezi",
        "Varış Transfer Merkezi", "Çıkış Tarihi", "Çıkış Saati", "Varış Tarihi",
        "Varış Saati", "Talep ID", "Taşınan Desi", "Yolculuk süresi",
        "Varış elleçleme süresi", "Çıkış Elleçleme süresi", "SLA cezası",
        "Toplam maliyet"
    ]
    return plan_df[cols]


# ---------------------------------------------------------------------------
# Yardımcı: 0-desi Spot satır ve araç temizleyici
# ---------------------------------------------------------------------------
def _temizle_bos_spot(plan_df: pd.DataFrame) -> pd.DataFrame:
    """
    Spot araçlarda ortaya çıkan 0-desilik parça satırlarını ve bu nedenle
    tamamen boş kalan Spot araçlarını plandan çıkarır.

    Neden oluşur: Bir talep bölünürken kalan parça bir Spot araca atanır;
    ama o parçanın gerçek yükü (desi) başka bir araçta taşınmış olduğundan
    bu araçtaki satır 0 desi ile kalır.

    Kural:
    - Araç Tipi == "Spot" ve toplam Taşınan Desi == 0 → tüm satırları sil.
    - Spot bacak içinde 0-desi satır var ama bacak toplamı > 0 → sadece 0-desi
      satırları sil; leg maliyeti (Toplam maliyet toplamı) kaybedilmeden
      kalan ilk dolu satıra aktarılır.
    - Araç Tipi == "Kiralık" → HIÇBIR satıra dokunma.
    """
    if plan_df.empty:
        return plan_df

    mask_kiralik = plan_df["Araç Tipi"] == "Kiralık"
    kiralik_df = plan_df[mask_kiralik].copy()
    spot_df = plan_df[~mask_kiralik].copy()

    if spot_df.empty:
        return plan_df

    LEG_COLS = [
        "Araç ID", "Çıkış Transfer Merkezi", "Varış Transfer Merkezi",
        "Çıkış Tarihi", "Çıkış Saati",
    ]

    temiz_parcalar = []
    for arac_id, arac_grup in spot_df.groupby("Araç ID", sort=False):
        if arac_grup["Taşınan Desi"].sum() <= 0:
            # Araç tamamen boş → at, maliyetini de at (gerçeksiz sefer)
            continue

        # Araç dolu, ama bazı satırlar 0-desi olabilir
        leg_parcalar = []
        for _, leg_grup in arac_grup.groupby(LEG_COLS, dropna=False, sort=False):
            toplam_desi = leg_grup["Taşınan Desi"].sum()
            if toplam_desi <= 0:
                # Leg tamamen boş (savunmacı; yukarıda zaten araç kontrolü var)
                continue

            dolu_mask = leg_grup["Taşınan Desi"] > 0
            if dolu_mask.all():
                leg_parcalar.append(leg_grup)
                continue

            # 0-desi satır(lar) var; maliyet toplamını koru, satırları at
            leg_maliyet = round(float(leg_grup["Toplam maliyet"].sum()), 2)
            dolu_grup = leg_grup[dolu_mask].copy().reset_index(drop=True)

            # Eğer cost 0-desi satırdaydı (demand_index==0), kaybolmuş olur
            # → ilk dolu satıra yükle
            maliyet_dolu = round(float(dolu_grup["Toplam maliyet"].sum()), 2)
            if abs(maliyet_dolu - leg_maliyet) > 0.005:
                dolu_grup.at[dolu_grup.index[0], "Toplam maliyet"] = leg_maliyet

            leg_parcalar.append(dolu_grup)

        if leg_parcalar:
            temiz_parcalar.append(pd.concat(leg_parcalar, ignore_index=True))

    spot_temiz = (
        pd.concat(temiz_parcalar, ignore_index=True)
        if temiz_parcalar
        else pd.DataFrame(columns=spot_df.columns)
    )

    return pd.concat([kiralik_df, spot_temiz], ignore_index=True)


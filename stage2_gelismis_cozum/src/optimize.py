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
                # Sadece 09:00 tamamlanma saatli talepler yüklenir;
                # 17:00 talepler pending'de kalarak spot aşamasına bırakılır.
                active_demands = [
                    d for d in pending_demands[(c, v)]
                    if d["completion_time"].hour == 9
                    and d["completion_time"].date() <= D
                ]
                
                loaded_demands = []
                loaded_desi = 0.0
                
                for d in list(active_demands):
                    rem_cap = cap - loaded_desi
                    if rem_cap <= 0:
                        break
                    
                    load = min(d["desi"], rem_cap)
                    
                    # Kiralik araç her zaman D günü 09:00'da yüklemeye başlar.
                    t_start_est = datetime.datetime(D.year, D.month, D.day, 9, 0)
                    
                    c_ellec_est = handling_minutes(loaded_desi + load)
                    v_ellec_est = handling_minutes(loaded_desi + load)
                    varis_dt_est = t_start_est + timedelta(minutes=c_ellec_est + yol_dk + v_ellec_est)
                    
                    sla_deadline = d["completion_time"] + timedelta(hours=r_det["sla_gun"] * 24)
                    gecikme_s = max(0.0, (varis_dt_est - sla_deadline).total_seconds())
                    gecikme_h = -(-int(gecikme_s) // 3600)
                    kiralik_sla_cost = load * gecikme_h * 0.4
                    
                    min_spot_cost = float('inf')
                    for vt in ["Tır", "Kamyon", "Hafif Kamyon", "Kamyonet"]:
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
                    
                    if kiralik_sla_cost > min_spot_cost:
                        continue
                    
                    if d["desi"] <= rem_cap:
                        loaded_demands.append({
                            "talep_id": d["talep_id"],
                            "desi": d["desi"],
                            "completion_time": d["completion_time"]
                        })
                        loaded_desi += d["desi"]
                        pending_demands[(c, v)].remove(d)
                        active_demands.remove(d)
                    else:
                        loaded_demands.append({
                            "talep_id": d["talep_id"],
                            "desi": rem_cap,
                            "completion_time": d["completion_time"]
                        })
                        loaded_desi += rem_cap
                        d["desi"] -= rem_cap
                        break
                
                # YÜKLEME BAŞLANGIÇ ANI: Her zaman D günü 09:00.
                # Sadece 09:00 talep yüklendiğinden 17:00 koşulu/TIR downgrade gerekmez.
                t_start = datetime.datetime(D.year, D.month, D.day, 9, 0)
                if not loaded_demands:
                    dummy_tid = get_dummy_demand_for_route(c, v, talep_df)
                    loaded_demands.append({
                        "talep_id": dummy_tid,
                        "desi": 0.0,
                        "completion_time": t_start
                    })
                    loaded_desi = 0.0

                c_ellecleme = handling_minutes(loaded_desi)
                v_ellecleme = handling_minutes(loaded_desi)
                cikis_dt = t_start + timedelta(minutes=c_ellecleme)
                varis_dt = cikis_dt + timedelta(minutes=yol_dk)

                
                cost = calculate_vehicle_cost("Kiralık", arac_turu, loaded_desi, yol_dk, mesafe_km, vehicle_maliyet)
                
                clean_loaded_demands = [{"talep_id": item["talep_id"], "desi": item["desi"]} for item in loaded_demands]

                trips.append({
                    "arac_id": next_vehicle_id(),
                    "arac_tipi": "Kiralık",
                    "arac_turu": arac_turu,
                    "cikis": c,
                    "varis": v,
                    "cikis_dt": cikis_dt,
                    "varis_dt": varis_dt,
                    "t_start": t_start,
                    "demands": clean_loaded_demands,
                    "yolculuk_suresi": yol_dk,
                    "cikis_ellecleme": c_ellecleme,
                    "varis_ellecleme": v_ellecleme,
                    "maliyet": cost
                })
                
                # Kapasite tüketimleri
                if arac_turu == "Tır":
                    remaining_tir[c][D] = max(0, remaining_tir[c].get(D, 0) - 1)
                    remaining_tir[v][varis_dt.date()] = max(0, remaining_tir[v].get(varis_dt.date(), 0) - 1)
                
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
        cikis_date = trip["t_start"].date() if arac_tipi == "Kiralık" else trip["cikis_dt"].date()
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


# ---------------------------------------------------------------------------
# Son-İşlem Katmanı: 09:00 + 17:00 Spot Seferlerini Birleştir
# ---------------------------------------------------------------------------
def konsolide_saat(plan_df: pd.DataFrame, veri: dict) -> pd.DataFrame:
    """
    Post-processing: Aynı (Çıkış TM, Varış TM, Çıkış Tarihi) üzerinde
    09:00 ve 17:00 bloğunda ayrı Spot araçlar varsa, onları tek bir Spot
    araca birleştirmeyi dener.

    Birleştirme YALNIZCA şu koşulların TÜMÜ sağlanırsa yapılır:
      1. Birleşik desi bir araç tipine sığıyor (en küçük uygun tip seçilir).
      2. Tır yasaklı transfer merkezlerine Tır atanmaz (rules.TIR_TAMAMEN_YASAK_TM).
      3. Tır günlük kotası aşılamaz.
      4. Yeni araç 17:00 bloğu kalkış saatini kullanır (her iki yük hazır).
      5. SLA ihlali ve elleçleme kapasitesi ihlali oluşmaz.
      6. Yeni toplam maliyet eskisinden DÜŞÜK.

    Kiralık araçlara kesinlikle dokunulmaz.
    """
    arac_maliyet_df = veri["arac_maliyet"]
    mesafe_df = veri["mesafe"]
    ellecleme_df = veri["ellecleme_kapasitesi"]
    tir_kapasitesi_df = veri["tir_kapasitesi"]
    talep_df = veri.get("talep_tahmin")
    if talep_df is None:
        return plan_df

    # 1. Sabit Haritalar
    vehicle_maliyet = {}
    for _, row in arac_maliyet_df.iterrows():
        nm = row["arac_adi"]
        vehicle_maliyet[nm] = {
            "capacity": row["kapasite_desi"],
            "spot_saatlik": row["spot_saatlik_tl"],
            "spot_km": row["spot_km_tl"],
        }

    ARAC_SIRA = ["Kamyonet", "Hafif Kamyon", "Kamyon", "Tır"]

    dur_col_map = {
        "Tır": "tir_saat", "Kamyon": "kamyon_saat",
        "Hafif Kamyon": "hafif_kamyon_saat", "Kamyonet": "kamyonet_saat",
    }
    rota_km = {}
    rota_yol_dk = {}
    rota_sla_gun = {}
    for _, r in mesafe_df.iterrows():
        c, v = r["cikis"], r["varis"]
        rota_km[(c, v)] = r["mesafe_km"]
        rota_sla_gun[(c, v)] = int(r["sla_gun"])
        for arac, kol in dur_col_map.items():
            rota_yol_dk[(c, v, arac)] = travel_minutes(r[kol])

    tir_kota = tir_kapasitesi_df.set_index("tm")["tir_kapasitesi"].to_dict()
    ellecleme_kota = ellecleme_df.set_index("tm")["gunluk_kapasite_desi"].to_dict()

    # Talep bilgi haritası
    def _kok_id(tid: str) -> str:
        return str(tid).split("-")[0]

    talep_bilgi = (
        talep_df.set_index("Talep ID")[["Tarih", "Talep Tamamlama Saati"]]
        .to_dict("index")
    )

    guncel_plan = plan_df.copy()

    # Mevcut Tır Hareket Haritası: (tm, tarih) -> set(arac_id)
    tir_hareketleri = guncel_plan[guncel_plan["Araç türü"] == "Tır"]
    tir_kullanim = defaultdict(set)
    for _, row in tir_hareketleri.iterrows():
        aid = row["Araç ID"]
        if pd.notna(row["Çıkış Tarihi"]):
            tir_kullanim[(row["Çıkış Transfer Merkezi"], pd.Timestamp(row["Çıkış Tarihi"]).date())].add(aid)
        if pd.notna(row["Varış Tarihi"]):
            tir_kullanim[(row["Varış Transfer Merkezi"], pd.Timestamp(row["Varış Tarihi"]).date())].add(aid)

    # Mevcut Elleçleme Yük Haritası: (tm, tarih) -> float
    ellecleme_yuku = defaultdict(float)
    for _, row in guncel_plan.iterrows():
        desi = row["Taşınan Desi"]
        if pd.notna(row["Çıkış Tarihi"]) and pd.notna(row["Çıkış Saati"]):
            cikis_bitis = to_datetime(row["Çıkış Tarihi"], row["Çıkış Saati"])
            sure = row.get("Çıkış Elleçleme süresi", handling_minutes(desi))
            baslangic = cikis_bitis - timedelta(minutes=int(sure))
            for tarih, _, desi_payi in split_handling_across_midnight(baslangic, int(sure), desi):
                ellecleme_yuku[(row["Çıkış Transfer Merkezi"], tarih)] += desi_payi
        if pd.notna(row["Varış Tarihi"]) and pd.notna(row["Varış Saati"]):
            varis_baslangic = to_datetime(row["Varış Tarihi"], row["Varış Saati"])
            sure = row.get("Varış elleçleme süresi", handling_minutes(desi))
            for tarih, _, desi_payi in split_handling_across_midnight(varis_baslangic, int(sure), desi):
                ellecleme_yuku[(row["Varış Transfer Merkezi"], tarih)] += desi_payi

    def _saat_blok(s: str) -> str:
        try:
            return "sabah" if int(str(s).split(":")[0]) < 14 else "aksam"
        except Exception:
            return "diger"

    spot_mask = guncel_plan["Araç Tipi"] == "Spot"
    spot_df = guncel_plan[spot_mask].copy()

    if spot_df.empty:
        return guncel_plan

    spot_arac_saat = (
        spot_df.groupby(["Çıkış Transfer Merkezi", "Varış Transfer Merkezi",
                         "Çıkış Tarihi", "Araç ID"])["Çıkış Saati"]
        .first()
        .reset_index()
    )
    spot_arac_saat["blok"] = spot_arac_saat["Çıkış Saati"].apply(_saat_blok)

    GRUP_COLS = ["Çıkış Transfer Merkezi", "Varış Transfer Merkezi", "Çıkış Tarihi"]
    grup_bloklar = (
        spot_arac_saat.groupby(GRUP_COLS)["blok"]
        .apply(set)
        .reset_index(name="bloklar")
    )
    kandidatlar = grup_bloklar[
        grup_bloklar["bloklar"].apply(lambda x: "sabah" in x and "aksam" in x)
    ]

    birlesme_sayisi = 0
    toplam_tasarruf = 0.0
    silinecek_arac_idler = set()
    yeni_eklenecek_satirlar = []

    for _, kand in kandidatlar.iterrows():
        cikis_tm = kand["Çıkış Transfer Merkezi"]
        varis_tm = kand["Varış Transfer Merkezi"]
        cikis_tarihi = kand["Çıkış Tarihi"]
        if isinstance(cikis_tarihi, pd.Timestamp):
            cikis_tarihi = cikis_tarihi.date()

        grup_arac = spot_arac_saat[
            (spot_arac_saat["Çıkış Transfer Merkezi"] == cikis_tm) &
            (spot_arac_saat["Varış Transfer Merkezi"] == varis_tm) &
            (spot_arac_saat["Çıkış Tarihi"] == cikis_tarihi)
        ]

        sabah_ids = [aid for aid in grup_arac[grup_arac["blok"] == "sabah"]["Araç ID"].unique() if aid not in silinecek_arac_idler]
        aksam_ids = [aid for aid in grup_arac[grup_arac["blok"] == "aksam"]["Araç ID"].unique() if aid not in silinecek_arac_idler]

        if len(sabah_ids) != 1 or len(aksam_ids) != 1:
            continue

        sabah_id, aksam_id = sabah_ids[0], aksam_ids[0]

        sabah_sat = spot_df[spot_df["Araç ID"] == sabah_id]
        aksam_sat = spot_df[spot_df["Araç ID"] == aksam_id]

        birlesik_desi = sabah_sat["Taşınan Desi"].sum() + aksam_sat["Taşınan Desi"].sum()
        if birlesik_desi <= 0:
            continue

        eski_m = float(sabah_sat["Toplam maliyet"].sum() + aksam_sat["Toplam maliyet"].sum())

        secilen_turu = None
        secilen_satirlar = None
        secilen_m = 0.0

        for arac_turu in ARAC_SIRA:
            # 1. Kapasite
            if vehicle_maliyet.get(arac_turu, {}).get("capacity", 0) < birlesik_desi:
                continue

            # 2. Tır Yasak TM
            if arac_turu == "Tır":
                if cikis_tm in rules.TIR_TAMAMEN_YASAK_TM or varis_tm in rules.TIR_TAMAMEN_YASAK_TM:
                    continue

            # Saatler ve süreler
            yeni_cikis_saat_str = aksam_sat["Çıkış Saati"].iloc[0]
            mesafe_km = rota_km.get((cikis_tm, varis_tm), 0)
            yol_dk = rota_yol_dk.get((cikis_tm, varis_tm, arac_turu), 0)
            c_dk = handling_minutes(birlesik_desi)
            v_dk = handling_minutes(birlesik_desi)

            cikis_dt = to_datetime(cikis_tarihi, yeni_cikis_saat_str)
            varis_dt = cikis_dt + timedelta(minutes=c_dk + yol_dk)
            varis_dt_ellecleme_bitis = varis_dt + timedelta(minutes=v_dk)
            yeni_varis_tarihi = varis_dt.date()
            yeni_varis_saat_str = format_hhmm(varis_dt)

            # 3. Tır Günlük Kota Kontrolü
            if arac_turu == "Tır":
                cikis_tir_mevcut = len(tir_kullanim[(cikis_tm, cikis_tarihi)] - {sabah_id, aksam_id})
                varis_tir_mevcut = len(tir_kullanim[(varis_tm, yeni_varis_tarihi)] - {sabah_id, aksam_id})
                if cikis_tir_mevcut + 1 > tir_kota.get(cikis_tm, 0):
                    continue
                if varis_tir_mevcut + 1 > tir_kota.get(varis_tm, 0):
                    continue

            # 4. Maliyet Kontrolü
            kullanim_dk = c_dk + yol_dk + v_dk
            kullanim_saat = kullanim_dk / 60.0
            yeni_m = round(
                vehicle_maliyet[arac_turu]["spot_saatlik"] * kullanim_saat
                + vehicle_maliyet[arac_turu]["spot_km"] * mesafe_km,
                2,
            )
            if yeni_m >= eski_m - 0.005:
                continue

            # 5. SLA Kontrolü
            sla_gun = rota_sla_gun.get((cikis_tm, varis_tm), 1)
            sla_ihlal = False
            tum_satirlar = pd.concat([aksam_sat, sabah_sat])
            for _, s_row in tum_satirlar.iterrows():
                tid = s_row["Talep ID"]
                kok_id = _kok_id(tid)
                bilgi = talep_bilgi.get(tid) or talep_bilgi.get(kok_id)
                if bilgi is not None:
                    t_dt = to_datetime(bilgi["Tarih"], bilgi["Talep Tamamlama Saati"])
                    sla_limit = t_dt + timedelta(hours=sla_gun * 24)
                    if varis_dt_ellecleme_bitis > sla_limit:
                        sla_ihlal = True
                        break
            if sla_ihlal:
                continue

            # 6. Elleçleme Kapasitesi Kontrolü
            # Eski iki aracın elleçleme yükünü düş, yenininkini ekle ve kota aşımına bak
            yeni_satirlar = []
            for kaynak in [aksam_sat, sabah_sat]:
                for _, satir in kaynak.iterrows():
                    y = satir.copy()
                    y["Araç ID"] = aksam_id
                    y["Araç türü"] = arac_turu
                    y["Çıkış Saati"] = yeni_cikis_saat_str
                    y["Çıkış Tarihi"] = cikis_tarihi
                    y["Varış Tarihi"] = yeni_varis_tarihi
                    y["Varış Saati"] = yeni_varis_saat_str
                    y["Yolculuk süresi"] = int(yol_dk)
                    y["Çıkış Elleçleme süresi"] = int(c_dk)
                    y["Varış elleçleme süresi"] = int(v_dk)
                    y["SLA cezası"] = 0.0
                    y["Toplam maliyet"] = yeni_m if len(yeni_satirlar) == 0 else 0.0
                    yeni_satirlar.append(y)

            # Geçici elleçleme farklarını hesapla
            temp_ellecleme = defaultdict(float)
            # Eskileri düş
            for _, r in tum_satirlar.iterrows():
                d = r["Taşınan Desi"]
                c_b = to_datetime(r["Çıkış Tarihi"], r["Çıkış Saati"])
                s_c = r.get("Çıkış Elleçleme süresi", handling_minutes(d))
                for t, _, dp in split_handling_across_midnight(c_b - timedelta(minutes=int(s_c)), int(s_c), d):
                    temp_ellecleme[(r["Çıkış Transfer Merkezi"], t)] -= dp
                v_b = to_datetime(r["Varış Tarihi"], r["Varış Saati"])
                s_v = r.get("Varış elleçleme süresi", handling_minutes(d))
                for t, _, dp in split_handling_across_midnight(v_b, int(s_v), d):
                    temp_ellecleme[(r["Varış Transfer Merkezi"], t)] += 0 # Zaten düştük
            # Yenileri ekle
            c_b_new = cikis_dt
            for t, _, dp in split_handling_across_midnight(c_b_new - timedelta(minutes=c_dk), c_dk, birlesik_desi):
                temp_ellecleme[(cikis_tm, t)] += dp
            v_b_new = varis_dt
            for t, _, dp in split_handling_across_midnight(v_b_new, v_dk, birlesik_desi):
                temp_ellecleme[(varis_tm, t)] += dp

            # Kota aşımı var mı?
            ellecleme_ihlal = False
            for (tm, t), fark in temp_ellecleme.items():
                yeni_toplam = ellecleme_yuku[(tm, t)] + fark
                if yeni_toplam > ellecleme_kota.get(tm, float("inf")) + 1e-5:
                    ellecleme_ihlal = True
                    break
            if ellecleme_ihlal:
                continue

            # Başarılı tip bulundu
            secilen_turu = arac_turu
            secilen_satirlar = yeni_satirlar
            secilen_m = yeni_m
            break

        if secilen_turu is not None:
            birlesme_sayisi += 1
            toplam_tasarruf += (eski_m - secilen_m)
            silinecek_arac_idler.add(sabah_id)
            silinecek_arac_idler.add(aksam_id)
            yeni_eklenecek_satirlar.extend(secilen_satirlar)

            # Haritaları güncelle
            if secilen_turu == "Tır":
                tir_kullanim[(cikis_tm, cikis_tarihi)].add(aksam_id)
                tir_kullanim[(varis_tm, yeni_varis_tarihi)].add(aksam_id)

    if birlesme_sayisi == 0:
        print("  konsolide_saat: Uygun birleştirme bulunamadı.")
        return plan_df

    kalan_plan = guncel_plan[~guncel_plan["Araç ID"].isin(silinecek_arac_idler)].copy()
    yeni_df = pd.DataFrame(yeni_eklenecek_satirlar)
    sonuc_df = pd.concat([kalan_plan, yeni_df], ignore_index=True)

    print(f"  konsolide_saat: {birlesme_sayisi} birleştirme yapıldı.")
    print(f"  Toplam Tasarruf: {toplam_tasarruf:,.2f} TL")
    return sonuc_df


# ---------------------------------------------------------------------------
# Aday Bulucu: 2-Duraklı Milk-Run Adaylarını Listele (Planı Değiştirmez)
# ---------------------------------------------------------------------------
def milkrun_adaylari(plan_df: pd.DataFrame, veri: dict) -> list:
    """
    Planı DEĞİŞTİRMEDEN, aynı çıkış merkezinden farklı varış merkezlerine giden
    düşük doluluklu (<%50) Spot araçları tarar ve potansiyel 2-duraklı milk-run
    adaylarını bulur.

    Döndürür: [(arac1_id, arac2_id, tahmini_tasarruf), ...]
    """
    from itertools import combinations

    arac_maliyet_df = veri["arac_maliyet"]
    mesafe_df = veri["mesafe"]

    vehicle_info = {}
    for _, row in arac_maliyet_df.iterrows():
        vehicle_info[row["arac_adi"]] = {
            "capacity": row["kapasite_desi"],
            "spot_saatlik": row["spot_saatlik_tl"],
            "spot_km": row["spot_km_tl"],
        }

    ARAC_SIRA = ["Kamyonet", "Hafif Kamyon", "Kamyon", "Tır"]
    dur_col_map = {
        "Tır": "tir_saat", "Kamyon": "kamyon_saat",
        "Hafif Kamyon": "hafif_kamyon_saat", "Kamyonet": "kamyonet_saat",
    }

    rota_km = {}
    rota_yol_dk = {}
    for _, r in mesafe_df.iterrows():
        c, v = r["cikis"], r["varis"]
        rota_km[(c, v)] = r["mesafe_km"]
        for arac, kol in dur_col_map.items():
            rota_yol_dk[(c, v, arac)] = travel_minutes(r[kol])

    spot_mask = plan_df["Araç Tipi"] == "Spot"
    spot_df = plan_df[spot_mask].copy()

    if spot_df.empty:
        print("  milkrun_adaylari: Hiç Spot araç yok.")
        return []

    arac_ozet = {}
    for arac_id, grup in spot_df.groupby("Araç ID"):
        cikis_tm = grup["Çıkış Transfer Merkezi"].iloc[0]
        varis_tm = grup["Varış Transfer Merkezi"].iloc[0]
        cikis_tarih = grup["Çıkış Tarihi"].iloc[0]
        cikis_saat = grup["Çıkış Saati"].iloc[0]
        arac_turu = grup["Araç türü"].iloc[0]
        toplam_desi = grup["Taşınan Desi"].sum()
        kapasite = vehicle_info.get(arac_turu, {}).get("capacity", 1)
        doluluk = toplam_desi / kapasite

        if doluluk < 0.50 and toplam_desi > 0:
            eski_maliyet = grup["Toplam maliyet"].sum()
            arac_ozet[arac_id] = {
                "arac_id": arac_id,
                "cikis_tm": cikis_tm,
                "varis_tm": varis_tm,
                "cikis_tarih": cikis_tarih,
                "cikis_saat": cikis_saat,
                "arac_turu": arac_turu,
                "toplam_desi": toplam_desi,
                "doluluk": doluluk,
                "eski_maliyet": eski_maliyet
            }

    kalkis_gruplari = defaultdict(list)
    for a_id, info in arac_ozet.items():
        key = (info["cikis_tm"], info["cikis_tarih"], info["cikis_saat"])
        kalkis_gruplari[key].append(info)

    adaylar = []

    for (cikis_tm, cikis_tarih, cikis_saat), araclar in kalkis_gruplari.items():
        if len(araclar) < 2:
            continue

        for a1, a2 in combinations(araclar, 2):
            if a1["varis_tm"] == a2["varis_tm"]:
                continue

            birlesik_desi = a1["toplam_desi"] + a2["toplam_desi"]

            secilen_tip = None
            for tip in ARAC_SIRA:
                if vehicle_info.get(tip, {}).get("capacity", 0) >= birlesik_desi:
                    secilen_tip = tip
                    break

            if secilen_tip is None:
                continue

            eski_toplam_maliyet = a1["eski_maliyet"] + a2["eski_maliyet"]

            b_tm = a1["varis_tm"]
            c_tm = a2["varis_tm"]

            en_iyi_yeni_maliyet = float("inf")

            for (durak1, durak2, desi1, desi2) in [
                (b_tm, c_tm, a1["toplam_desi"], a2["toplam_desi"]),
                (c_tm, b_tm, a2["toplam_desi"], a1["toplam_desi"])
            ]:
                if (durak1, durak2) not in rota_km:
                    continue

                km1 = rota_km.get((cikis_tm, durak1), 0)
                km2 = rota_km.get((durak1, durak2), 0)
                toplam_km = km1 + km2

                yol1 = rota_yol_dk.get((cikis_tm, durak1, secilen_tip), 0)
                yol2 = rota_yol_dk.get((durak1, durak2, secilen_tip), 0)

                c_dk = handling_minutes(birlesik_desi)
                d1_dk = handling_minutes(desi1)
                d2_dk = handling_minutes(desi2)

                toplam_kullanim_dk = c_dk + yol1 + d1_dk + yol2 + d2_dk
                kullanim_saat = toplam_kullanim_dk / 60.0

                saatlik_tl = vehicle_info[secilen_tip]["spot_saatlik"]
                km_tl = vehicle_info[secilen_tip]["spot_km"]

                yeni_m = round(saatlik_tl * kullanim_saat + km_tl * toplam_km, 2)
                if yeni_m < en_iyi_yeni_maliyet:
                    en_iyi_yeni_maliyet = yeni_m

            if en_iyi_yeni_maliyet < eski_toplam_maliyet:
                tasarruf = round(eski_toplam_maliyet - en_iyi_yeni_maliyet, 2)
                adaylar.append((a1["arac_id"], a2["arac_id"], tasarruf))

    adaylar.sort(key=lambda x: x[2], reverse=True)

    print(f"\n==================================================")
    print(f"MILK-RUN ADAY TARAMASI")
    print(f"==================================================")
    print(f"Bulunan Aday Çift Sayısı: {len(adaylar)}")
    if adaylar:
        print("\nİlk 10 Aday Çift (Araç 1, Araç 2, Tahmini Tasarruf):")
        for i, (a1, a2, tas) in enumerate(adaylar[:10], 1):
            print(f"  {i:2d}. {a1} + {a2} -> Tahmini Tasarruf: {tas:,.2f} TL")
    print(f"==================================================\n")

    return adaylar


# ---------------------------------------------------------------------------
# Son-İşlem Katmanı: 2-Duraklı Milk-Run Seferlerini Konsolide Et
# ---------------------------------------------------------------------------
def konsolide_milkrun(plan_df: pd.DataFrame, veri: dict) -> pd.DataFrame:
    """
    Milk-run konsolidasyon katmanı:
    Aynı çıkış transfer merkezinden farklı varış merkezlerine giden 2 düşük doluluklu (<%50) Spot aracı
    tek bir A -> B -> C milk-run seferinde birleştirir.

    Uygulama Koşulları:
      1. Birleşik desi bir araç tipine sığmalı (en küçük uygun araç seçilir).
      2. Tır yasaklı transfer merkezlerine Tır atanmaz (rules.TIR_TAMAMEN_YASAK_TM).
      3. Tır günlük kotası ve elleçleme kapasiteleri aşılamaz.
      4. SLA ihlali oluşmaz.
      5. Yeni Toplam Maliyet (Yeni Araç Maliyeti + Yeni SLA Cezası) < Eski Toplam Maliyet olmalı.

    Kiralık araçlara kesinlikle dokunulmaz.
    """
    from checker import check_tir_capacity, check_ellecleme_capacity, DogrulamaRaporu

    talep_df = veri.get("talep_tahmin")
    if talep_df is None:
        return plan_df

    arac_maliyet_df = veri["arac_maliyet"]
    mesafe_df = veri["mesafe"]
    tir_kapasitesi_df = veri["tir_kapasitesi"]
    ellecleme_df = veri["ellecleme_kapasitesi"]
    kiralik_araclar_df = veri.get("kiralik_araclar")

    adaylar = milkrun_adaylari(plan_df, veri)
    if not adaylar:
        return plan_df

    vehicle_info = {}
    for _, row in arac_maliyet_df.iterrows():
        vehicle_info[row["arac_adi"]] = {
            "capacity": row["kapasite_desi"],
            "spot_saatlik": row["spot_saatlik_tl"],
            "spot_km": row["spot_km_tl"],
        }

    ARAC_SIRA = ["Kamyonet", "Hafif Kamyon", "Kamyon", "Tır"]
    dur_col_map = {
        "Tır": "tir_saat", "Kamyon": "kamyon_saat",
        "Hafif Kamyon": "hafif_kamyon_saat", "Kamyonet": "kamyonet_saat",
    }

    rota_details = {}
    for _, r in mesafe_df.iterrows():
        c, v = r["cikis"], r["varis"]
        rota_details[(c, v)] = {
            "mesafe_km": float(r["mesafe_km"]),
            "sla_gun": int(r["sla_gun"]),
            "durations": {vt: travel_minutes(r[col]) for vt, col in dur_col_map.items()}
        }

    talep_bilgi = talep_df.set_index("Talep ID")[["Tarih", "Talep Tamamlama Saati"]].to_dict("index")

    def _kok_id(tid: str) -> str:
        return str(tid).split("-")[0]

    guncel_plan = plan_df.copy()
    kabul_edilen_birlesme = 0
    eski_toplam_maliyet_genel = 0.0
    yeni_toplam_maliyet_genel = 0.0

    silinecek_arac_idler = set()
    yeni_eklenecek_satirlar = []

    for a1_id, a2_id, _ in adaylar:
        if a1_id in silinecek_arac_idler or a2_id in silinecek_arac_idler:
            continue

        a1_sat = guncel_plan[guncel_plan["Araç ID"] == a1_id]
        a2_sat = guncel_plan[guncel_plan["Araç ID"] == a2_id]

        if a1_sat.empty or a2_sat.empty:
            continue

        cikis_tm1 = a1_sat["Çıkış Transfer Merkezi"].iloc[0]
        cikis_tm2 = a2_sat["Çıkış Transfer Merkezi"].iloc[0]
        if cikis_tm1 != cikis_tm2:
            continue

        cikis_tm = cikis_tm1
        b_tm = a1_sat["Varış Transfer Merkezi"].iloc[0]
        c_tm = a2_sat["Varış Transfer Merkezi"].iloc[0]

        if b_tm == c_tm:
            continue

        cikis_tarih = a1_sat["Çıkış Tarihi"].iloc[0]
        cikis_saat_str = a1_sat["Çıkış Saati"].iloc[0]

        desi1 = a1_sat["Taşınan Desi"].sum()
        desi2 = a2_sat["Taşınan Desi"].sum()
        birlesik_desi = desi1 + desi2

        eski_arac_maliyeti = a1_sat["Toplam maliyet"].sum() + a2_sat["Toplam maliyet"].sum()
        eski_sla_cezasi = a1_sat["SLA cezası"].sum() + a2_sat["SLA cezası"].sum()
        eski_toplam = eski_arac_maliyeti + eski_sla_cezasi

        secilen_tip = None
        for tip in ARAC_SIRA:
            if vehicle_info.get(tip, {}).get("capacity", 0) >= birlesik_desi:
                secilen_tip = tip
                break
        if secilen_tip is None:
            continue

        en_iyi_opsiyon = None
        en_ucuz_yeni_toplam = float("inf")

        for (durak1, durak2, d1_sat, d2_sat, desi_durak1, desi_durak2) in [
            (b_tm, c_tm, a1_sat, a2_sat, desi1, desi2),
            (c_tm, b_tm, a2_sat, a1_sat, desi2, desi1)
        ]:
            if (cikis_tm, durak1) not in rota_details or (durak1, durak2) not in rota_details:
                continue

            if secilen_tip == "Tır":
                if cikis_tm in rules.TIR_TAMAMEN_YASAK_TM or durak1 in rules.TIR_TAMAMEN_YASAK_TM or durak2 in rules.TIR_TAMAMEN_YASAK_TM:
                    continue

            r1 = rota_details[(cikis_tm, durak1)]
            r2 = rota_details[(durak1, durak2)]

            km1 = r1["mesafe_km"]
            km2 = r2["mesafe_km"]
            toplam_km = km1 + km2

            yol1_dk = r1["durations"][secilen_tip]
            yol2_dk = r2["durations"][secilen_tip]

            c_dk = handling_minutes(birlesik_desi)
            v1_dk = handling_minutes(desi_durak1)
            v2_dk = handling_minutes(desi_durak2)

            toplam_kullanim_dk = c_dk + yol1_dk + v1_dk + yol2_dk + v2_dk
            kullanim_saat = toplam_kullanim_dk / 60.0

            saatlik_tl = vehicle_info[secilen_tip]["spot_saatlik"]
            km_tl = vehicle_info[secilen_tip]["spot_km"]

            yeni_arac_maliyeti = round(saatlik_tl * kullanim_saat + km_tl * toplam_km, 2)

            cikis1_dt = to_datetime(cikis_tarih, cikis_saat_str)
            varis1_dt = cikis1_dt + timedelta(minutes=c_dk + yol1_dk)
            varis1_ellecleme_bitis = varis1_dt + timedelta(minutes=v1_dk)

            cikis2_dt = varis1_dt + timedelta(minutes=v1_dk)
            varis2_dt = cikis2_dt + timedelta(minutes=yol2_dk)
            varis2_ellecleme_bitis = varis2_dt + timedelta(minutes=v2_dk)

            yeni_sla_cezasi = 0.0
            yeni_bacak1_satirlar = []
            for _, s_row in d1_sat.iterrows():
                y = s_row.copy()
                y["Araç ID"] = a1_id
                y["Araç türü"] = secilen_tip
                y["Çıkış Transfer Merkezi"] = cikis_tm
                y["Varış Transfer Merkezi"] = durak1
                y["Çıkış Tarihi"] = cikis1_dt.date()
                y["Çıkış Saati"] = format_hhmm(cikis1_dt)
                y["Varış Tarihi"] = varis1_dt.date()
                y["Varış Saati"] = format_hhmm(varis1_dt)
                y["Yolculuk süresi"] = int(yol1_dk)
                y["Çıkış Elleçleme süresi"] = int(c_dk)
                y["Varış elleçleme süresi"] = int(v1_dk)

                tid = y["Talep ID"]
                kok = _kok_id(tid)
                bilgi = talep_bilgi.get(tid) or talep_bilgi.get(kok)
                sla_pen = 0.0
                if bilgi is not None:
                    t_dt = to_datetime(bilgi["Tarih"], bilgi["Talep Tamamlama Saati"])
                    sla_limit = t_dt + timedelta(hours=r1["sla_gun"] * 24)
                    gecikme_sec = (varis1_ellecleme_bitis - sla_limit).total_seconds()
                    if gecikme_sec > 0:
                        gecikme_saat = -(-int(gecikme_sec) // 3600)
                        sla_pen = round(y["Taşınan Desi"] * gecikme_saat * rules.SLA_CEZA_TL_PER_DESI_SAAT, 2)
                y["SLA cezası"] = sla_pen
                yeni_sla_cezasi += sla_pen
                yeni_bacak1_satirlar.append(y)

            yeni_bacak2_satirlar = []
            for _, s_row in d2_sat.iterrows():
                y = s_row.copy()
                y["Araç ID"] = a1_id
                y["Araç türü"] = secilen_tip
                y["Çıkış Transfer Merkezi"] = durak1
                y["Varış Transfer Merkezi"] = durak2
                y["Çıkış Tarihi"] = cikis2_dt.date()
                y["Çıkış Saati"] = format_hhmm(cikis2_dt)
                y["Varış Tarihi"] = varis2_dt.date()
                y["Varış Saati"] = format_hhmm(varis2_dt)
                y["Yolculuk süresi"] = int(yol2_dk)
                y["Çıkış Elleçleme süresi"] = int(0)
                y["Varış elleçleme süresi"] = int(v2_dk)

                tid = y["Talep ID"]
                kok = _kok_id(tid)
                bilgi = talep_bilgi.get(tid) or talep_bilgi.get(kok)
                sla_pen = 0.0
                if bilgi is not None:
                    r_a_durak2 = rota_details.get((cikis_tm, durak2))
                    sla_g = r_a_durak2["sla_gun"] if r_a_durak2 else r2["sla_gun"]
                    t_dt = to_datetime(bilgi["Tarih"], bilgi["Talep Tamamlama Saati"])
                    sla_limit = t_dt + timedelta(hours=sla_g * 24)
                    gecikme_sec = (varis2_ellecleme_bitis - sla_limit).total_seconds()
                    if gecikme_sec > 0:
                        gecikme_saat = -(-int(gecikme_sec) // 3600)
                        sla_pen = round(y["Taşınan Desi"] * gecikme_saat * rules.SLA_CEZA_TL_PER_DESI_SAAT, 2)
                y["SLA cezası"] = sla_pen
                yeni_sla_cezasi += sla_pen
                yeni_bacak2_satirlar.append(y)

            yeni_toplam_maliyet = yeni_arac_maliyeti + yeni_sla_cezasi

            if yeni_toplam_maliyet < eski_toplam and yeni_toplam_maliyet < en_ucuz_yeni_toplam:
                en_ucuz_yeni_toplam = yeni_toplam_maliyet

                for idx, sat in enumerate(yeni_bacak1_satirlar):
                    sat["Toplam maliyet"] = yeni_arac_maliyeti if idx == 0 else 0.0
                for sat in yeni_bacak2_satirlar:
                    sat["Toplam maliyet"] = 0.0

                en_iyi_opsiyon = {
                    "yeni_satirlar": yeni_bacak1_satirlar + yeni_bacak2_satirlar,
                    "yeni_toplam_maliyet": yeni_toplam_maliyet,
                    "eski_toplam_maliyet": eski_toplam
                }

        if en_iyi_opsiyon is None:
            continue

        # Hızlı Kapasite Kontrolleri
        test_plan = pd.concat([
            guncel_plan[~guncel_plan["Araç ID"].isin(list(silinecek_arac_idler) + [a1_id, a2_id])],
            pd.DataFrame(yeni_eklenecek_satirlar + en_iyi_opsiyon["yeni_satirlar"])
        ], ignore_index=True)

        sim_rapor = DogrulamaRaporu()
        check_tir_capacity(test_plan, tir_kapasitesi_df, sim_rapor)
        check_ellecleme_capacity(test_plan, ellecleme_df, sim_rapor)

        if not sim_rapor.hata_var_mi:
            kabul_edilen_birlesme += 1
            silinecek_arac_idler.add(a1_id)
            silinecek_arac_idler.add(a2_id)
            yeni_eklenecek_satirlar.extend(en_iyi_opsiyon["yeni_satirlar"])
            eski_toplam_maliyet_genel += en_iyi_opsiyon["eski_toplam_maliyet"]
            yeni_toplam_maliyet_genel += en_iyi_opsiyon["yeni_toplam_maliyet"]

    if kabul_edilen_birlesme == 0:
        print("  konsolide_milkrun: Kabul edilen milk-run birleştirmesi olmadı.")
        return plan_df

    sonuc_plan = pd.concat([
        guncel_plan[~guncel_plan["Araç ID"].isin(silinecek_arac_idler)],
        pd.DataFrame(yeni_eklenecek_satirlar)
    ], ignore_index=True)

    net_tasarruf = eski_toplam_maliyet_genel - yeni_toplam_maliyet_genel
    print(f"\n==================================================")
    print(f"KONSOLİDE MILK-RUN SONUÇLARI")
    print(f"==================================================")
    print(f"Kabul Edilen Milk-Run Birleşmesi : {kabul_edilen_birlesme}")
    print(f"Azalan Araç Sayısı              : {kabul_edilen_birlesme}")
    print(f"Eski Maliyet (Birleştirilen)   : {eski_toplam_maliyet_genel:,.2f} TL")
    print(f"Yeni Maliyet (Birleştirilen)   : {yeni_toplam_maliyet_genel:,.2f} TL")
    print(f"Net Tasarruf                   : {net_tasarruf:,.2f} TL")
    print(f"==================================================\n")

    return sonuc_plan

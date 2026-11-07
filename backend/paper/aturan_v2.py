import hashlib
import sys
from datetime import datetime

import numpy as np
import pandas as pd
from bson import json_util

from backend.db import data as dt
from backend.db import koneksi as kdb
from backend.paper import pantau

ID_H11A = "h11a_v2"
ID_H29 = "h29_v2"
K_ZONA_V2 = "pantau_zona_v2"
TGL_KUNCI = "2026-11-07"
HORIZON_BUKTI = {"h11a": "±32-51 bulan (vs JII 32, vs bobot sama 48-51, vs pilihan acak 45 bulan di dev; di 2020+ vs pilihan acak tidak tercapai sampai 60 bulan)",
                 "h29": "±43 bulan atau lebih (dev 43 bulan; di 2020+ tidak tercapai sampai 60 bulan)"}
KEPUTUSAN_2027 = [
    "Syarat lama 'tidak pernah WASPADA/GAGAL → uang nyata 10-20%' DIGANTI (keputusan user 2026-11-07, alasan: sifat aturan dari audit, bukan hasil paper). "
    "Di 12 bulan strategi tanpa edge tetap lolos 32-88% (aturan lama maupun baru), jadi lolos 12 bulan bukan bukti edge.",
    "Okt/Nov 2027 = keputusan MANUAL user dengan porsi kecil (peringatan keras H33: porsi awal maks 10% dari dana yang direncanakan untuk H11a), dicatat eksplisit sebagai BUKAN bukti edge.",
    f"Horizon bukti dari audit: H11a {HORIZON_BUKTI['h11a']}; H29 {HORIZON_BUKTI['h29']}.",
    "Rem GAGAL tetap mengikat: kalau GAGAL, strategi tidak dilanjutkan ke uang asli dan aturan tidak boleh diubah lalu diteruskan.",
]
ATURAN_H11A = [
    "GAGAL (h11a_v2, dikunci 2026-11-07): pita simultan q 0,34% dari jalur normal bootstrap 2020+ — return < pita mulai hari ke-63, ATAU drawdown terdalam < pita, ATAU rugi beruntun > pita (per jumlah trade). Alarm palsu 250 hari 5,0% (bootstrap 2020+) / 1,0% (dev).",
    "GAGAL juga kalau drawdown < -45% atau bug eksekusi tak terjelaskan > 5 hari bursa (U1). Tetap.",
    "WASPADA (info saja, bukan syarat uang nyata): pita simultan q 0,70%, return mulai hari ke-21, drawdown, rugi beruntun; insiden terbuka ≤ 5 hari bursa; cadangan Yahoo > 10% (U4).",
    "U2 (selisih paper vs backtest, u2_v1 / u2_h22_v1) = info saja, tidak mengubah status.",
    "Hari > 500 memakai pita hari ke-500. Zona lama h11a_v1 tetap dihitung dan disimpan berdampingan sebagai pembanding (pantau_zona).",
]
ATURAN_H29 = [
    "GAGAL (h29_v2, dikunci 2026-11-07): dinilai di hari bursa ke-250 — return kumulatif < -26,96% (≈ -27,0%) ATAU drawdown terdalam sampai hari itu < -39,06% (≈ -39,1%). Alarm palsu 5,0% (bootstrap 2020+) / 0,0% (dev).",
    "GAGAL juga kalau drawdown < -45% atau bug eksekusi tak terjelaskan > 5 hari bursa (U1). Tetap.",
    "WASPADA (info saja): zona h29_v1 (return < p5 mulai hari ke-21 atau drawdown < p5), insiden terbuka, cadangan Yahoo > 10% (U4). U2 info saja.",
    "Zona h29_v1 tetap dihitung dan disimpan berdampingan (pantau_zona).",
]


def db():
    return kdb.koneksi()


def sidik_paper():
    out = {}
    for c in sorted(x for x in db().list_collection_names() if x.startswith("paper_")):
        h = hashlib.sha256()
        n = 0
        for d in db()[c].find({}).sort("_id", 1):
            h.update(json_util.dumps(d, sort_keys=True).encode())
            n += 1
        out[c] = {"dokumen": n, "sidik": h.hexdigest()[:16]}
    b = db().batas_paper.find_one({"_id": pantau.ID_ZONA})
    out["batas_paper/h11a_v1"] = {"dokumen": 1, "sidik": hashlib.sha256(json_util.dumps(b, sort_keys=True).encode()).hexdigest()[:16]}
    return out


def status_paper():
    z = pantau.keadaan()
    return {s: {"hari": z[s]["hari"], "terakhir": pantau.tgl_str(z[s]["terakhir"]["tgl"]) if z[s]["terakhir"] else None,
                "status": z[s]["terakhir"]["status"] if z[s]["terakhir"] else None,
                "pernah_waspada": z[s]["pernah_waspada"], "pernah_gagal": z[s]["pernah_gagal"]} for s in ("h11a", "h29")}


def kunci():
    if db().batas_paper.find_one({"_id": ID_H11A}) or db()[pantau.K_BATAS].find_one({"_id": ID_H29}):
        print("h11a_v2 / h29_v2 sudah ada, tidak ditimpa (pra-registrasi).")
        return
    a = dt.baca_hasil("audit_aturan_paper")
    if not a:
        raise RuntimeError("hasil_riset/audit_aturan_paper belum ada; jalankan backend.research.audit_aturan_paper dulu")
    bulat = lambda d: {**d, "ret": [round(float(x), 2) for x in d["ret"]], "dd": [round(float(x), 2) for x in d["dd"]], "ber": [int(x) for x in d["ber"]]}
    g, w = bulat(a["kandidat_h11a"]["gagal"]["i"]), bulat(a["kandidat_h11a"]["waspada"]["i"])
    g29 = a["kandidat_h29"]["gagal"]["ii"]
    sumber = {"hasil_riset": "audit_aturan_paper", "dijalankan": a["dijalankan"],
              "sidik_audit": hashlib.sha256(json_util.dumps(a, sort_keys=True).encode()).hexdigest()[:16]}
    saat = {"tanggal": TGL_KUNCI, "dikunci": datetime.now(), "status_paper": status_paper(), "sidik_paper": sidik_paper(),
            "alasan": "sifat aturan (alarm palsu dan daya pembeda dari audit 2026-11-07), bukan hasil paper", "keputusan": "user 2026-11-07"}
    dok11 = {"_id": ID_H11A, "status": "dikunci", **saat, "sumber": sumber, "cara": "pita simultan (kandidat i), kalibrasi bootstrap blok 20 hari 5.000 jalur kurva h11a_2020_konservatif seed 7",
             "horizon": len(g["ret"]),
             "gagal": {"q": g["q"], "mulai_ret": 63, "ret": g["ret"], "dd": g["dd"], "ber": g["ber"], "alarm_palsu_250": g["kena"]["normal_a"], "alarm_palsu_250_dev": g["kena"]["normal_b"]},
             "waspada": {"q": w["q"], "mulai_ret": 21, "ret": w["ret"], "dd": w["dd"], "ber": w["ber"], "info_saja": True,
                         "alarm_palsu_250": w["kena"]["normal_a"], "alarm_palsu_250_dev": w["kena"]["normal_b"]},
             "batas_dd": pantau.BATAS_DD, "aturan": ATURAN_H11A, "keputusan_2027": KEPUTUSAN_2027}
    dok29 = {"_id": ID_H29, "status": "dikunci", **saat, "sumber": sumber, "cara": "posisi akhir (kandidat ii) di hari ke-250, kalibrasi bootstrap kurva h29_v1",
             "gagal_akhir": {"hari": 250, "ret": g29["ret_250"], "dd": g29["dd_250"], "q": g29["q"], "alarm_palsu_250": g29["kena"]["normal_a"],
                             "alarm_palsu_250_dev": g29["kena"]["normal_b"]},
             "batas_dd": pantau.BATAS_DD, "waspada_zona": pantau.ID_ZONA_H29, "aturan": ATURAN_H29, "keputusan_2027": KEPUTUSAN_2027}
    db().batas_paper.insert_one(dok11)
    db()[pantau.K_BATAS].insert_one(dok29)
    print(f"dikunci {ID_H11A} (batas_paper) dan {ID_H29} ({pantau.K_BATAS}) {TGL_KUNCI}")
    print("status paper saat dikunci:", saat["status_paper"])
    for k, v in saat["sidik_paper"].items():
        print(f"  {k}: {v['dokumen']} dok, sidik {v['sidik']}")


def _pita(arr, i):
    return arr[min(i, len(arr) - 1)]


def zona_h11a(b2, modal, nilai, net):
    nilai = np.asarray(nilai, dtype=float)
    puncak = np.maximum.accumulate(np.maximum(nilai, modal))
    ret = (nilai / modal - 1) * 100
    dd = np.minimum.accumulate(nilai / puncak - 1) * 100
    h = len(nilai) - 1
    beruntun = pantau.rugi_beruntun_terpanjang(net)
    out = {"hari": h, "ret": ret, "dd": dd, "beruntun": beruntun, "trade": len(net), "gagal": [], "waspada": [], "batas": None}
    if h < 1:
        return out
    i = h - 1
    k = len(net)
    batas = {}
    for jenis in ("gagal", "waspada"):
        p = b2[jenis]
        batas[jenis] = {"ret": _pita(p["ret"], i), "dd": _pita(p["dd"], i), "ber": _pita(p["ber"], k - 1) if k else None, "mulai_ret": p["mulai_ret"]}
    r, d_ = float(ret[-1]), float(dd[-1])
    for jenis in ("gagal", "waspada"):
        bt = batas[jenis]
        a = []
        if h >= bt["mulai_ret"] and r < bt["ret"]:
            a.append(f"return {r:.1f}% di bawah pita {jenis} ({bt['ret']:.1f}%)")
        if d_ < bt["dd"]:
            a.append(f"drawdown {d_:.1f}% lebih dalam dari pita {jenis} ({bt['dd']:.1f}%)")
        if bt["ber"] is not None and beruntun > bt["ber"]:
            a.append(f"rugi beruntun {beruntun}x melebihi pita {jenis} ({bt['ber']}x)")
        out[jenis] = a
    out["batas"] = batas
    return out


def zona_h29(b2, nilai):
    nilai = np.asarray(nilai, dtype=float)
    modal = nilai[0]
    puncak = np.maximum.accumulate(np.maximum(nilai, modal))
    ret = (nilai / modal - 1) * 100
    dd = np.minimum.accumulate(nilai / puncak - 1) * 100
    h = len(nilai) - 1
    g = b2["gagal_akhir"]
    out = {"hari": h, "ret": ret, "dd": dd, "gagal": [], "batas": {"hari": g["hari"], "ret": g["ret"], "dd": g["dd"]}}
    if h >= g["hari"]:
        r250, d250 = float(ret[g["hari"]]), float(dd[g["hari"]])
        if r250 < g["ret"]:
            out["gagal"].append(f"return hari ke-{g['hari']} {r250:.1f}% di bawah {g['ret']:.1f}%")
        if d250 < g["dd"]:
            out["gagal"].append(f"drawdown terdalam sampai hari ke-{g['hari']} {d250:.1f}% lebih dalam dari {g['dd']:.1f}%")
    return out


def rem(dd_maks, aktif, kal, t, cadangan):
    gagal, waspada = [], []
    if dd_maks is not None and dd_maks < pantau.BATAS_DD:
        gagal.append(f"drawdown {dd_maks:.1f}% lebih dalam dari {pantau.BATAS_DD:.0f}%")
    for x in aktif:
        u = pantau.umur(x["buka"], t, kal)
        jelas = x.get("penjelasan") and pantau.umur(x["buka"], x["penjelasan"]["tgl"], kal) <= pantau.T_BUG and pd.Timestamp(x["penjelasan"]["tgl"]) <= pd.Timestamp(t)
        if jelas:
            continue
        if u > pantau.T_BUG:
            gagal.append(f"bug eksekusi: {x['sumber']} sejak {x['buka']} belum terjelaskan lebih dari {pantau.T_BUG} hari bursa")
        else:
            waspada.append(f"insiden {x['sumber']} sejak {x['buka']} ({u}/{pantau.T_BUG} hari bursa)")
    if cadangan is not None and cadangan > pantau.BATAS_CADANGAN:
        waspada.append(f"{cadangan * 100:.0f}% hari memakai cadangan Yahoo (batas {pantau.BATAS_CADANGAN * 100:.0f}%)")
    return gagal, waspada


def catat():
    from backend.paper import h29

    b2 = db().batas_paper.find_one({"_id": ID_H11A, "status": "dikunci"})
    z2 = db()[pantau.K_BATAS].find_one({"_id": ID_H29, "status": "dikunci"})
    st = db().paper_status.find_one({"_id": "status"})
    if not b2 or not z2 or not st:
        return 0
    c = db()[K_ZONA_V2]
    ada = {x["_id"] for x in c.find({}, {"_id": 1})}
    ek = list(db().paper_ekuitas.find({}, {"_id": 0, "tgl": 1, "ekuitas": 1}).sort("tgl", 1))
    jual = [(pd.Timestamp(t["tgl"]), t["net_pct"]) for t in db().paper_transaksi.find({"aksi": "jual"}, {"tgl": 1, "net_pct": 1}).sort("tgl", 1)]
    kal = [pd.Timestamp(e["tgl"]) for e in ek]
    insiden = list(db()[pantau.K_INSIDEN].find({}))
    u2 = db()[pantau.K_BATAS].find_one({"_id": "u2_v1", "status": "dikunci"})
    u22 = db()[pantau.K_BATAS].find_one({"_id": "u2_h22_v1", "status": "dikunci"})
    d11, d22 = pantau.banding_terakhir("h11a"), pantau.banding_terakhir("h22")
    sekarang = datetime.now()
    baru = 0
    nilai = [e["ekuitas"] for e in ek]
    for j, t in enumerate(kal):
        _id = f"h11a:{t.date()}"
        if _id in ada:
            continue
        z = zona_h11a(b2, st["modal_awal"], nilai[: j + 1], [n for tj, n in jual if tj <= t])
        dd_maks = float(z["dd"][-1])
        g, w = rem(dd_maks, pantau.insiden_pada(insiden, "h11a", t), kal, t, pantau.cadangan_yahoo("h11a", t))
        gagal, waspada = [f"pita {ID_H11A}: {a}" for a in z["gagal"]] + g, [f"pita {ID_H11A} (info): {a}" for a in z["waspada"]] + w
        dat, cat = pantau.data_h11a(t, d11, u2, "INFO DATA")
        c.insert_one({"_id": _id, "strategi": "h11a", "aturan": ID_H11A, "tgl": t.to_pydatetime(), "hari": z["hari"],
                      "status": "gagal" if gagal else "waspada" if waspada else "normal", "gagal": gagal, "waspada": waspada,
                      "info_data": dat + cat, "batas": z["batas"], "return_pct": round(float(z["ret"][-1]), 2), "dd_maks_pct": round(dd_maks, 2),
                      "trade": z["trade"], "beruntun": z["beruntun"], "dicatat": sekarang, "isi_mundur": t != kal[-1]})
        baru += 1
    data = h29.seri() or []
    kal22 = [pd.Timestamp(r["tgl"]) for r in data]
    bz = db()[pantau.K_BATAS].find_one({"_id": pantau.ID_ZONA_H29, "status": "dikunci"})
    for j, t in enumerate(kal22):
        _id = f"h29:{t.date()}"
        if _id in ada:
            continue
        x = np.array([r["h29"] for r in data[: j + 1]], float)
        z = zona_h29(z2, x)
        zl = pantau.zona_h29(bz, x) if bz else {"alasan": []}
        dd_maks = float(z["dd"][-1])
        aktif = pantau.insiden_pada(insiden, "h11a", t) + pantau.insiden_pada(insiden, "h22", t)
        cad = max([v for v in (pantau.cadangan_yahoo("h11a", t), pantau.cadangan_yahoo("h22", t)) if v is not None], default=None)
        g, w = rem(dd_maks, aktif, kal22, t, cad)
        gagal = [f"{ID_H29}: {a}" for a in z["gagal"]] + g
        waspada = [f"zona {pantau.ID_ZONA_H29} (info): {a}" for a in zl["alasan"]] + w
        dat, cat = pantau.data_h29(t, d11, d22, u2, u22)
        c.insert_one({"_id": _id, "strategi": "h29", "aturan": ID_H29, "tgl": t.to_pydatetime(), "hari": z["hari"],
                      "status": "gagal" if gagal else "waspada" if waspada else "normal", "gagal": gagal, "waspada": waspada,
                      "info_data": [a.replace("WASPADA DATA", "INFO DATA") for a in dat] + cat, "batas": z["batas"],
                      "return_pct": round(float(z["ret"][-1]), 2), "dd_maks_pct": round(dd_maks, 2), "dicatat": sekarang, "isi_mundur": t != kal22[-1]})
        baru += 1
    return baru


def ringkas_audit():
    a = dt.baca_hasil("audit_aturan_paper") or {}
    if not a:
        return None
    h11, h29 = a["h11a"], a["h29"]
    k11, k29 = a["kandidat_h11a"], a["kandidat_h29"]
    lk = a["lolos_kandidat_h11a"]["waspada_dan_gagal_i"]
    u2 = a.get("u2", {})
    baris = [
        {"aturan": "H11a GAGAL zona h11a_v1 (lama)", "alarm": [h11["normal_a"]["250"]["gagal"], h11["normal_b"]["250"]["gagal"]], "ambang": "≤ 5%",
         "lulus": h11["normal_a"]["250"]["gagal"] <= 5 and h11["normal_b"]["250"]["gagal"] <= 5, "jadi": "diganti pita simultan q 0,34%"},
        {"aturan": "H11a GAGAL pita simultan h11a_v2 (baru)", "alarm": [k11["gagal"]["i"]["kena"]["normal_a"], k11["gagal"]["i"]["kena"]["normal_b"]], "ambang": "≤ 5%",
         "lulus": True, "jadi": "dipakai",
         "null": [k11["gagal"]["i"]["kena"][x] for x in ("null1_a", "null2_a", "null3_a", "null1_b", "null2_b", "null3_b")]},
        {"aturan": "H11a WASPADA lama (syarat uang nyata)", "alarm": [h11["normal_a"]["250"]["waspada"], h11["normal_b"]["250"]["waspada"]], "ambang": "≤ 10%",
         "lulus": False, "jadi": "jadi info (pita q 0,70%)"},
        {"aturan": "H11a WASPADA pita q 0,70% (info)", "alarm": [k11["waspada"]["i"]["kena"]["normal_a"], k11["waspada"]["i"]["kena"]["normal_b"]], "ambang": "info", "lulus": True, "jadi": "info saja"},
        {"aturan": "DD < -45% (H11a)", "alarm": [h11["normal_a"]["250"]["dd45"], h11["normal_b"]["250"]["dd45"]], "ambang": "≤ 5%", "lulus": True, "jadi": "tetap"},
        {"aturan": "DD < -45% (H29)", "alarm": [h29["normal_a"]["250"]["dd45"], h29["normal_b"]["250"]["dd45"]], "ambang": "≤ 5%", "lulus": True, "jadi": "tetap"},
        {"aturan": "H29 GAGAL hari ke-250 h29_v2 (baru)", "alarm": [k29["gagal"]["ii"]["kena"]["normal_a"], k29["gagal"]["ii"]["kena"]["normal_b"]], "ambang": "≤ 5%",
         "lulus": True, "jadi": "ditambahkan", "null": [k29["gagal"]["ii"]["kena"]["null_a"], k29["gagal"]["ii"]["kena"]["null_b"]]},
        {"aturan": "Zona h29_v1 WASPADA", "alarm": [h29["normal_a"]["250"]["waspada"], h29["normal_b"]["250"]["waspada"]], "ambang": "info", "lulus": True, "jadi": "info, tetap dihitung"},
        {"aturan": "U2 pita replay H11a", "alarm": [u2.get("h11a_pita_replay_250"), None], "ambang": "≤ 10% bila syarat", "lulus": False, "jadi": "info saja"},
        {"aturan": "U2 pita H22 / H29", "alarm": [u2.get("h22_pita_250"), u2.get("h29_pita_250")], "ambang": "info", "lulus": True, "jadi": "info saja"},
        {"aturan": "U1 bug eksekusi / U4 cadangan Yahoo", "alarm": [None, None], "ambang": "—", "lulus": None, "jadi": "tetap (data riwayat belum cukup)"},
    ]
    lolos = [
        {"kriteria": "H11a lama: tidak pernah WASPADA/GAGAL 12 bulan", "normal": [h11["normal_a"]["250"]["lolos"], h11["normal_b"]["250"]["lolos"]],
         "null": [h11[x]["250"]["lolos"] for x in ("null1_a", "null2_a", "null3_a", "null1_b", "null2_b", "null3_b")]},
        {"kriteria": "H11a dengan pita baru (WASPADA + GAGAL)", "normal": [lk["normal_a"], lk["normal_b"]],
         "null": [lk[x] for x in ("null1_a", "null2_a", "null3_a", "null1_b", "null2_b", "null3_b")]},
        {"kriteria": "H29: tidak GAGAL (DD > -45%) 12 bulan", "normal": [h29["normal_a"]["250"]["lolos"], h29["normal_b"]["250"]["lolos"]],
         "null": [h29["null_a"]["250"]["lolos"], h29["null_b"]["250"]["lolos"]]},
    ]
    tmin = {s: {reg: {n: v["bulan_minimum"] for n, v in x.items()} for reg, x in a[f"horizon_minimum_{s}"].items()} for s in ("h11a", "h29")}
    return {"dijalankan": a.get("dijalankan"), "baris": baris, "lolos": lolos, "horizon_minimum": tmin}


def keadaan(strategi):
    xs = list(db()[K_ZONA_V2].find({"strategi": strategi}, {"_id": 0}).sort("tgl", 1))
    lama = list(db()[pantau.K_ZONA].find({"strategi": strategi}, {"_id": 0, "tgl": 1, "status": 1, "alasan": 1}).sort("tgl", 1))
    pertama = lambda daftar, s: next((pantau.tgl_str(x["tgl"]) for x in daftar if x["status"] == s), None)
    dok = db().batas_paper.find_one({"_id": ID_H11A}) if strategi == "h11a" else db()[pantau.K_BATAS].find_one({"_id": ID_H29})
    terakhir = xs[-1] if xs else None
    return {"aturan_id": ID_H11A if strategi == "h11a" else ID_H29, "ada": bool(dok),
            "dikunci": dok["tanggal"] if dok else None, "status_paper_saat_kunci": (dok or {}).get("status_paper", {}).get(strategi),
            "aturan": (dok or {}).get("aturan", []), "keputusan_2027": KEPUTUSAN_2027, "horizon_bukti": HORIZON_BUKTI[strategi],
            "terakhir": {**terakhir, "tgl": pantau.tgl_str(terakhir["tgl"])} if terakhir else None,
            "pernah_gagal": pertama(xs, "gagal"), "pernah_waspada": pertama(xs, "waspada"), "hari": len(xs),
            "lama": {"id": pantau.ID_ZONA if strategi == "h11a" else pantau.ID_ZONA_H29, "terakhir": lama[-1]["status"] if lama else None,
                     "pernah_waspada": pertama(lama, "waspada"), "pernah_gagal": pertama(lama, "gagal")},
            "audit": ringkas_audit()}


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else "catat"
    if p == "kunci":
        kunci()
        print(f"catatan harian v2 baru: {catat()}")
    else:
        print(f"catatan harian v2 baru: {catat()}")
    print("SELESAI")

import pandas as pd

LIBUR = {
    2026: {
        "2026-01-01": "Tahun Baru 2026 Masehi",
        "2026-01-16": "Isra Mikraj Nabi Muhammad SAW",
        "2026-02-16": "Cuti Bersama Tahun Baru Imlek",
        "2026-02-17": "Tahun Baru Imlek 2577 Kongzili",
        "2026-03-18": "Cuti Bersama Hari Suci Nyepi",
        "2026-03-19": "Hari Suci Nyepi Tahun Baru Saka 1948",
        "2026-03-20": "Cuti Bersama Idulfitri 1447 H",
        "2026-03-23": "Cuti Bersama Idulfitri 1447 H",
        "2026-03-24": "Cuti Bersama Idulfitri 1447 H",
        "2026-04-03": "Wafat Yesus Kristus",
        "2026-05-01": "Hari Buruh Internasional",
        "2026-05-14": "Kenaikan Yesus Kristus",
        "2026-05-15": "Cuti Bersama Kenaikan Yesus Kristus",
        "2026-05-27": "Iduladha 1447 H",
        "2026-05-28": "Cuti Bersama Iduladha",
        "2026-06-01": "Hari Lahir Pancasila",
        "2026-06-16": "1 Muharam Tahun Baru Islam 1448 H",
        "2026-08-17": "Proklamasi Kemerdekaan",
        "2026-08-25": "Maulid Nabi Muhammad SAW",
        "2026-12-24": "Cuti Bersama Kelahiran Yesus Kristus",
        "2026-12-25": "Kelahiran Yesus Kristus",
        "2026-12-31": "Libur Bursa",
    },
    2027: {
        "2027-01-01": "Tahun Baru 2027 Masehi",
        "2027-01-05": "Isra Mikraj Nabi Muhammad SAW",
        "2027-02-05": "Cuti Bersama Tahun Baru Imlek",
        "2027-03-08": "Hari Suci Nyepi Tahun Baru Saka 1949",
        "2027-03-09": "Cuti Bersama Idulfitri 1448 H",
        "2027-03-10": "Idulfitri 1448 H",
        "2027-03-11": "Idulfitri 1448 H",
        "2027-03-12": "Cuti Bersama Idulfitri 1448 H",
        "2027-03-15": "Cuti Bersama Idulfitri 1448 H",
        "2027-03-25": "Cuti Bersama Wafat Yesus Kristus",
        "2027-03-26": "Wafat Yesus Kristus",
        "2027-05-06": "Kenaikan Yesus Kristus",
        "2027-05-17": "Iduladha 1448 H",
        "2027-05-18": "Cuti Bersama Iduladha",
        "2027-05-19": "Cuti Bersama Waisak",
        "2027-05-20": "Hari Raya Waisak 2571 BE",
        "2027-06-01": "Hari Lahir Pancasila",
        "2027-08-17": "Proklamasi Kemerdekaan",
        "2027-12-24": "Cuti Bersama Kelahiran Yesus Kristus",
        "2027-12-31": "Libur Bursa",
    },
}

STATUS = {
    2026: {"status": "resmi", "sumber": "Pengumuman BEI Peng-00171/BEI.POP/09-2025, dicocokkan dengan data IHSG Jan-Nov 2026"},
    2027: {"status": "sementara", "sumber": "ringkasan artikel Setneg tentang SKB 3 Menteri 1205/3/2 Tahun 2026 dan laporan media atas Peng-00169/BEI.POP/09-2026, belum dicocokkan ke kalender resmi IDX"},
}


def status_tahun(tahun):
    return (STATUS.get(int(tahun)) or {}).get("status")


def tahun_sementara():
    return sorted(t for t in LIBUR if status_tahun(t) != "resmi")


def tahun_terisi(tahun):
    return int(tahun) in LIBUR


def libur_set():
    return {pd.Timestamp(t) for per in LIBUR.values() for t in per}


def nama_libur(tgl):
    t = pd.Timestamp(tgl).normalize()
    return LIBUR.get(t.year, {}).get(str(t.date()))


def hari_bursa(tgl):
    t = pd.Timestamp(tgl).normalize()
    return t.weekday() < 5 and nama_libur(t) is None


def hari_bursa_antara(awal, akhir):
    return [x for x in pd.bdate_range(pd.Timestamp(awal).normalize(), pd.Timestamp(akhir).normalize()) if nama_libur(x) is None]

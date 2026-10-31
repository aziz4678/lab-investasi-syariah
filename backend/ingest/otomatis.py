import sys

from backend.ingest import chrome_lab


def impor_untuk(sid):
    from backend.ingest import impor_browser as ib
    if sid == "kepemilikan_pdf":
        from backend.ingest import kepemilikan_idx
        return kepemilikan_idx.impor
    if sid in ("keuangan_idx", "idx_statistik"):
        return lambda: ib.jalankan_modul("backend.ingest.keuangan_idx", ["gabung"])
    if sid in ("bibit_rd", "ojk_pto"):
        return lambda: ib.jalankan_modul("backend.ingest.rd_platform")
    if sid == "ojk_nab":
        return lambda: ib.jalankan_modul("backend.ingest.ojk_nab")
    return {"pengumuman": ib.pengumuman, "idx_harian": ib.idx_harian, "lapkeu": ib.lapkeu, "fundamental": ib.fundamental,
            "profil": ib.profil, "dividen_idx": ib.dividen, "idx_logo": ib.logo}.get(sid)


def jalan(sid):
    from backend.app.services import sumber_data as sd
    s = next((x for x in sd.SUMBER if x["id"] == sid), None)
    if not s or s.get("cara") != "browser":
        raise SystemExit(f"Sumber '{sid}' bukan sumber lewat browser")
    impor = impor_untuk(sid)
    if impor is None:
        raise SystemExit(f"Belum ada impor otomatis untuk '{sid}'")
    print(f"Ambil otomatis: {s['nama']}", flush=True)
    st = chrome_lab.status()
    if not st["jalan"]:
        print("Chrome Lab belum terbuka, membuka sekarang...", flush=True)
        chrome_lab.buka(s.get("url") or chrome_lab.URL_IDX)
    teks = sd.skrip(s["skrip"])
    print(f"Menjalankan script {s['skrip']} di Chrome Lab ({s.get('url')})", flush=True)
    chrome_lab.jalankan(teks, s.get("url") or chrome_lab.URL_IDX, batas_menit=240)
    print("\nScript selesai, mengimpor hasil...\n", flush=True)
    impor()


if __name__ == "__main__":
    jalan(sys.argv[1])

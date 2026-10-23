(async () => {
  const MULAI = 2015;
  const MAJU = 3;
  const JEDA = 600;
  const JEDA_TOLAK = [30, 60, 120, 240];
  const tunggu = ms => new Promise(r => setTimeout(r, ms));
  const lapor = (...x) => console.warn("[dividen]", ...x);
  const st = window.__dividen = { tahap: "mulai", selesai: 0, total: 0, acara: 0, catatan: "" };
  const simpan = (data, nama) => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(data)], { type: "application/json" }));
    a.download = nama;
    a.click();
  };
  const ambil = async url => {
    for (let coba = 0; coba <= JEDA_TOLAK.length; coba++) {
      const henti = new AbortController();
      const batas = setTimeout(() => henti.abort(), 25000);
      let r;
      try {
        r = await fetch(url, { credentials: "include", signal: henti.signal });
      } catch (e) {
        clearTimeout(batas);
        if (coba < JEDA_TOLAK.length) {
          st.catatan = "koneksi lambat, coba lagi";
          await tunggu(5000);
          continue;
        }
        throw e;
      }
      clearTimeout(batas);
      if (r.ok) return r.json();
      if ((r.status === 429 || r.status === 403) && coba < JEDA_TOLAK.length) {
        st.catatan = `IDX menolak (${r.status}), tunggu ${JEDA_TOLAK[coba]} detik`;
        lapor(st.catatan);
        await tunggu(JEDA_TOLAK[coba] * 1000);
        continue;
      }
      throw new Error("status " + r.status);
    }
  };
  const kini = new Date();
  const bulan = [];
  for (let d = new Date(MULAI, 0, 1); d <= new Date(kini.getFullYear(), kini.getMonth() + MAJU, 1); d.setMonth(d.getMonth() + 1)) {
    bulan.push(`${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, "0")}01`);
  }
  Object.assign(st, { tahap: "kalender", total: bulan.length });
  lapor(`Mengambil kalender dividen IDX ${bulan.length} bulan... cek progres kapan saja: ketik __dividen lalu Enter`);
  const acara = {};
  const gagal = [];
  for (let i = 0; i < bulan.length; i++) {
    try {
      const j = await ambil(`/primary/Home/GetCalendar?range=m&date=${bulan[i]}&lang=id`);
      for (const x of j.Results || j.data || []) {
        if (/dividen/i.test(x.description || "")) acara[x.id] = { id: x.id, kode: x.title, ket: x.description, tgl: x.start };
      }
    } catch (e) {
      gagal.push(bulan[i]);
    }
    Object.assign(st, { selesai: i + 1, acara: Object.keys(acara).length, catatan: "" });
    lapor(`${i + 1}/${bulan.length} bulan, ${Object.keys(acara).length} acara dividen`);
    await tunggu(JEDA);
  }
  const batas = new Date(kini.getTime() - 150 * 864e5).toISOString().slice(0, 10);
  const kodeBaru = [...new Set(Object.values(acara).filter(x => (x.tgl || "").slice(0, 10) >= batas).map(x => x.kode))].sort();
  Object.assign(st, { tahap: "profil", selesai: 0, total: kodeBaru.length });
  lapor(`Mengambil nilai dividen terakhir dari profil ${kodeBaru.length} emiten...`);
  const profil = {};
  for (let i = 0; i < kodeBaru.length; i++) {
    try {
      const j = await ambil(`/primary/ListedCompany/GetCompanyProfilesDetail?KodeEmiten=${kodeBaru[i]}&language=id-id`);
      profil[kodeBaru[i]] = j.Dividen || [];
    } catch (e) {
      profil[kodeBaru[i]] = null;
    }
    st.selesai = i + 1;
    if ((i + 1) % 5 === 0) lapor(`${i + 1}/${kodeBaru.length} profil`);
    await tunggu(JEDA);
  }
  const hasil = { dibuat: kini.toISOString(), bulan_awal: bulan[0], bulan_akhir: bulan[bulan.length - 1], gagal, acara: Object.values(acara), profil };
  simpan(hasil, gagal.length > 6 ? "idx_dividen_sebagian.json" : "idx_dividen.json");
  st.tahap = "SELESAI";
  lapor("SELESAI,", hasil.acara.length, "acara dividen,", gagal.length, "bulan gagal. File:", gagal.length > 6 ? "idx_dividen_sebagian.json" : "idx_dividen.json");
  return `SELESAI ${hasil.acara.length} acara, ${gagal.length} bulan gagal`;
})();

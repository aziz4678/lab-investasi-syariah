(async () => {
  const TAHUN_MULAI = 2019;
  const TAHUN_SELESAI = new Date().getFullYear();
  const PERIODE = ["tw1", "tw2", "tw3", "audit"];
  const UKURAN = 100;
  const JEDA = 800;
  const BASIS = "https://www.idx.co.id/primary/ListedCompany/GetFinancialReport";
  const tunggu = ms => new Promise(res => setTimeout(res, ms));
  const hasil = [];
  let gagalBeruntun = 0;
  for (let th = TAHUN_MULAI; th <= TAHUN_SELESAI; th++) {
    for (const p of PERIODE) {
      let dari = 0;
      let total = null;
      const unik = new Set();
      let tanpaBaru = 0;
      while (total === null || unik.size < total) {
        const url = `${BASIS}?indexFrom=${dari}&pageSize=${UKURAN}&year=${th}&reportType=rdf&EmitenType=s&periode=${p}&kodeEmiten=&SortColumn=KodeEmiten&SortOrder=asc`;
        try {
          const r = await fetch(url, { credentials: "include" });
          if (!r.ok) throw new Error("status " + r.status);
          const j = await r.json();
          total = j.ResultCount || 0;
          const sebelum = unik.size;
          for (const a of j.Results || []) {
            if (unik.has(a.KodeEmiten)) continue;
            unik.add(a.KodeEmiten);
            const lamp = (a.Attachments || []).map(x => x.File_Modified).filter(Boolean);
            hasil.push([a.KodeEmiten, a.Report_Period, a.Report_Year, a.File_Modified, lamp.length ? lamp.sort()[0] : null, lamp.length]);
          }
          gagalBeruntun = 0;
          dari += 1;
          tanpaBaru = unik.size === sebelum ? tanpaBaru + 1 : 0;
          if (!(j.Results || []).length || tanpaBaru >= 2) break;
        } catch (e) {
          gagalBeruntun += 1;
          console.log(th, p, dari, "gagal:", e.message);
          if (gagalBeruntun >= 5) { console.log("5 gagal beruntun, berhenti"); dari = Infinity; th = TAHUN_SELESAI + 1; break; }
          await tunggu(JEDA * 5);
        }
        await tunggu(JEDA);
      }
      console.log(th, p, "total", total, "| terkumpul", hasil.length);
    }
  }
  const kolom = ["kode", "periode", "tahun", "file_modified", "lampiran_terawal", "jumlah_lampiran"];
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify({ kolom, data: hasil })], { type: "application/json" }));
  a.download = "idx_lapkeu.json";
  a.click();
  console.log("SELESAI,", hasil.length, "laporan tersimpan ke idx_lapkeu.json");
})();

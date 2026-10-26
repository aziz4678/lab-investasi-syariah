(async () => {
  const TAHUN = __TAHUN__;
  const JEDA = 3000;
  const BULAN = { jan: 1, feb: 2, mar: 3, apr: 4, may: 5, mei: 5, jun: 6, jul: 7, aug: 8, agu: 8, agt: 8, sep: 9, oct: 10, okt: 10, nov: 11, dec: 12, des: 12 };
  const tunggu = (ms) => new Promise((r) => setTimeout(r, ms));
  const simpan = (blob, nama) => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = nama;
    a.click();
  };
  const ambil = async (url, jenis) => {
    for (let coba = 1; coba <= 5; coba++) {
      try {
        const r = await fetch(url, { credentials: "include" });
        if (r.ok) return jenis === "json" ? await r.json() : await r.blob();
        console.log(`  status ${r.status}, tunggu ${10 * coba} dtk (coba ${coba}/5)`);
      } catch (e) {
        console.log(`  gagal ${e.message}, tunggu ${10 * coba} dtk (coba ${coba}/5)`);
      }
      await tunggu(10000 * coba);
    }
    throw new Error(`IDX tidak merespons: ${url}`);
  };

  const daftar = [];
  for (const th of TAHUN) {
    const isi = await ambil(`/primary/Statistic/GetStatistic?year=${th}&type=monthly&lang=en`, "json");
    for (const x of isi || []) {
      const m = String(x.number || "").toLowerCase().match(/([a-z]+)\s+(\d{4})/);
      if (m && BULAN[m[1].slice(0, 3)] && x.file) daftar.push({ periode: `${m[2]}-${String(BULAN[m[1].slice(0, 3)]).padStart(2, "0")}`, file: x.file });
    }
    console.log(`${th}: ${(isi || []).length} laporan bulanan`);
  }
  daftar.sort((a, b) => a.periode.localeCompare(b.periode));
  console.log(`Mengunduh ${daftar.length} laporan bulanan IDX Statistics`);
  for (let i = 0; i < daftar.length; i++) {
    const { periode, file } = daftar[i];
    const blob = await ambil(file.replace(/^https?:\/\/[^/]+/, ""), "blob");
    simpan(blob, `idx_statistik_${periode}.pdf`);
    console.log(`${i + 1}/${daftar.length} ${periode}: ${Math.round(blob.size / 1024)} KB`);
    await tunggu(JEDA);
  }
  console.log("SELESAI");
})();

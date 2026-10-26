(async () => {
  const DARI = __DARI__;
  const JEDA = 1200;
  const BASIS = "/primary/DigitalStatistic/GetApiDataPaginated?urlName=LINK_FINANCIAL_DATA_RATIO&periodType=monthly&isPrint=False&cumulative=false&pageSize=3000&pageNumber=1";
  const KOLOM = ["code", "stockName", "sharia", "sector", "subSector", "fsDate", "fiscalYearEnd", "assets", "liabilities", "equity", "sales", "ebt",
    "profitPeriod", "profitAttrOwner", "eps", "audit", "opini", "bookValue", "per", "priceBV", "deRatio", "roa", "roe", "npm"];
  const tunggu = (ms) => new Promise((r) => setTimeout(r, ms));
  const ambil = async (th, bl) => {
    for (let coba = 1; coba <= 5; coba++) {
      try {
        const r = await fetch(`${BASIS}&periodYear=${th}&periodMonth=${bl}`, { credentials: "include" });
        if (r.ok) return await r.json();
        console.log(`  ${th}-${bl}: status ${r.status}, tunggu ${10 * coba} dtk (coba ${coba}/5)`);
      } catch (e) {
        console.log(`  ${th}-${bl}: gagal ${e.message}, tunggu ${10 * coba} dtk (coba ${coba}/5)`);
      }
      await tunggu(10000 * coba);
    }
    throw new Error(`IDX tidak merespons untuk ${th}-${bl}`);
  };
  const simpan = (isi, nama) => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(isi)], { type: "application/json" }));
    a.download = nama;
    a.click();
  };

  const [th0, bl0] = DARI.split("-").map(Number);
  const kini = new Date();
  const daftar = [];
  for (let th = th0, bl = bl0; th < kini.getFullYear() || (th === kini.getFullYear() && bl <= kini.getMonth() + 1); bl === 12 ? (th++, bl = 1) : bl++) daftar.push([th, bl]);
  console.log(`Mengambil data keuangan & rasio emiten IDX ${DARI} s/d ${kini.getFullYear()}-${kini.getMonth() + 1} (${daftar.length} bulan)`);
  const hasil = [];
  for (let i = 0; i < daftar.length; i++) {
    const [th, bl] = daftar[i];
    const j = await ambil(th, bl);
    const data = (j.data || []).filter((b) => b.code);
    if (data.length) {
      hasil.push({ bulan: `${th}-${String(bl).padStart(2, "0")}`, kolom: KOLOM, data: data.map((b) => KOLOM.map((k) => b[k])) });
      console.log(`${i + 1}/${daftar.length} ${th}-${String(bl).padStart(2, "0")}: ${data.length} emiten`);
    } else {
      console.log(`${i + 1}/${daftar.length} ${th}-${String(bl).padStart(2, "0")}: belum ada data`);
    }
    await tunggu(JEDA);
  }
  if (hasil.length) {
    const nama = `idx_rasio_${hasil[0].bulan.replace("-", "")}_${hasil.at(-1).bulan.replace("-", "")}.json`;
    simpan(hasil, nama);
    console.log(`file ${nama} disimpan (${hasil.length} bulan)`);
  } else {
    console.log("Tidak ada bulan baru.");
  }
  console.log("SELESAI");
})();

(async () => {
  const DARI = __DARI__;
  const JEDA = 1500;
  const BASIS = "https://www.idx.co.id/primary/TradingSummary/GetStockSummary?start=0";
  const KOLOM = ["StockCode", "Remarks", "Previous", "OpenPrice", "High", "Low", "Close", "Volume", "Value", "Frequency", "Offer", "OfferVolume",
    "Bid", "BidVolume", "ListedShares", "TradebleShares", "ForeignBuy", "ForeignSell", "NonRegularVolume", "NonRegularValue"];
  const tunggu = (ms) => new Promise((r) => setTimeout(r, ms));
  const iso = (d) => d.toISOString().slice(0, 10);
  const ambil = async (tgl) => {
    for (let coba = 1; coba <= 5; coba++) {
      try {
        const r = await fetch(`${BASIS}&length=9999&date=${tgl.replaceAll("-", "")}`, { credentials: "include" });
        if (r.ok) return (await r.json()).data || [];
        console.log(`  ${tgl}: status ${r.status}, tunggu ${10 * coba} dtk (coba ${coba}/5)`);
      } catch (e) {
        console.log(`  ${tgl}: gagal ${e.message}, tunggu ${10 * coba} dtk (coba ${coba}/5)`);
      }
      await tunggu(10000 * coba);
    }
    throw new Error(`IDX tidak merespons untuk ${tgl}`);
  };
  const simpan = (isi, nama) => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(isi)], { type: "application/json" }));
    a.download = nama;
    a.click();
  };

  const d = new Date(`${DARI}T00:00:00Z`);
  const akhir = new Date();
  const hasil = [];
  console.log(`Mengambil ringkasan perdagangan IDX dari ${DARI} sampai hari ini`);
  while (d <= akhir) {
    if (d.getUTCDay() !== 0 && d.getUTCDay() !== 6) {
      const t = iso(d);
      const baris = await ambil(t);
      if (baris.length && String(baris[0].Date).slice(0, 10) === t) {
        hasil.push({ tgl: t, kolom: KOLOM, data: baris.map((b) => KOLOM.map((k) => b[k])) });
        console.log(`${t}: ${baris.length} saham`);
      } else {
        console.log(`${t}: libur / belum ada data`);
      }
      await tunggu(JEDA);
    }
    d.setUTCDate(d.getUTCDate() + 1);
  }
  if (hasil.length) {
    const nama = `idx_harian_baru_${hasil[0].tgl.replaceAll("-", "")}_${hasil.at(-1).tgl.replaceAll("-", "")}.json`;
    simpan(hasil, nama);
    console.log(`file ${nama} disimpan (${hasil.length} hari bursa)`);
  } else {
    console.log("Tidak ada hari bursa baru, data sudah terbaru.");
  }
  console.log("SELESAI");
})();

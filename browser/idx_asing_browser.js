(async () => {
  const TAHUN_MULAI = 2021;
  const TAHUN_SELESAI = 2023;
  const SELESAI = "2026-10-20";
  const JEDA = 1000;
  const BASIS =
    "https://www.idx.co.id/primary/TradingSummary/GetStockSummary?start=0";
  const KOLOM = [
    "StockCode",
    "Remarks",
    "Previous",
    "OpenPrice",
    "High",
    "Low",
    "Close",
    "Volume",
    "Value",
    "Frequency",
    "Offer",
    "OfferVolume",
    "Bid",
    "BidVolume",
    "ListedShares",
    "TradebleShares",
    "ForeignBuy",
    "ForeignSell",
    "NonRegularVolume",
    "NonRegularValue",
  ];
  const tunggu = (ms) => new Promise((res) => setTimeout(res, ms));
  const ambil = async (tgl, panjang) => {
    const r = await fetch(
      `${BASIS}&length=${panjang}&date=${tgl.replaceAll("-", "")}`,
      { credentials: "include" },
    );
    if (!r.ok) throw new Error("status " + r.status);
    const j = await r.json();
    return j.data || [];
  };
  const simpan = (isi, nama) => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(
      new Blob([JSON.stringify(isi)], { type: "application/json" }),
    );
    a.download = nama;
    a.click();
  };

  const tersedia = [];
  for (let th = TAHUN_MULAI; th <= TAHUN_SELESAI; th++) {
    let ada = false;
    for (const tg of ["01-15", "02-15", "03-15", "06-15"]) {
      const d = new Date(`${th}-${tg}T00:00:00Z`);
      while (d.getUTCDay() === 0 || d.getUTCDay() === 6)
        d.setUTCDate(d.getUTCDate() + 1);
      const iso = d.toISOString().slice(0, 10);
      try {
        const b = await ambil(iso, 3);
        if (b.length && String(b[0].Date).slice(0, 10) === iso) {
          ada = true;
          break;
        }
      } catch (e) {
        console.log(iso, "gagal:", e.message);
      }
      await tunggu(JEDA);
    }
    console.log(th, ada ? "ADA data" : "tidak ada data");
    if (ada) tersedia.push(th);
  }
  if (!tersedia.length) {
    console.log("tidak ada tahun yang tersedia, berhenti");
    return;
  }

  for (const th of tersedia) {
    const hasil = [];
    const d = new Date(`${th}-01-01T00:00:00Z`);
    const akhir = new Date(
      Math.min(
        new Date(`${th}-12-31T00:00:00Z`),
        new Date(SELESAI + "T00:00:00Z"),
      ),
    );
    let gagalBeruntun = 0;
    while (d <= akhir) {
      if (d.getUTCDay() !== 0 && d.getUTCDay() !== 6) {
        const iso = d.toISOString().slice(0, 10);
        try {
          const baris = await ambil(iso, 9999);
          gagalBeruntun = 0;
          if (baris.length && String(baris[0].Date).slice(0, 10) === iso) {
            hasil.push({
              tgl: iso,
              kolom: KOLOM,
              data: baris.map((b) => KOLOM.map((k) => b[k])),
            });
            console.log(iso, baris.length, "saham");
          } else {
            console.log(iso, "libur / kosong");
          }
        } catch (e) {
          gagalBeruntun += 1;
          console.log(iso, "gagal:", e.message);
          if (gagalBeruntun >= 5) {
            console.log("5 gagal beruntun, simpan yang ada lalu berhenti");
            simpan(hasil, `idx_harian_${th}.json`);
            return;
          }
          await tunggu(JEDA * 5);
        }
        await tunggu(JEDA);
      }
      d.setUTCDate(d.getUTCDate() + 1);
    }
    simpan(hasil, `idx_harian_${th}.json`);
    console.log(`tahun ${th} selesai: ${hasil.length} hari`);
  }
  console.log("SEMUA SELESAI");
})();

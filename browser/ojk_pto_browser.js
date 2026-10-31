(async () => {
  const tunggu = (ms) => new Promise((r) => setTimeout(r, ms));
  const tgl = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  const simpan = (data, nama) => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(data)], { type: "application/json" }));
    a.download = nama;
    a.click();
  };
  const baris = () =>
    [...document.querySelectorAll("tr[id*='DXDataRow']")].map((tr) => [...tr.querySelectorAll("td")].map((td) => td.innerText.trim()));
  const pager = () => [...document.querySelectorAll("a, td.dxpPageNumber, span.dxpPageNumber")];
  if (!/PTOPublic/i.test(location.pathname)) {
    console.error("[ojk_pto] Buka https://reksadana.ojk.go.id/Public/PTOPublic.aspx dulu");
    return;
  }
  const teks = document.body.innerText.match(/Page \d+ of (\d+) \((\d+) items\)/);
  const jumlahHal = teks ? Number(teks[1]) : 1;
  console.log(`[ojk_pto] Daftar Portal Transaksi Online OJK: ${teks ? teks[2] : "?"} sistem, ${jumlahHal} halaman`);
  const hasil = {};
  for (let hal = 1; hal <= jumlahHal; hal++) {
    if (hal > 1) {
      const sebelum = JSON.stringify(baris()[0]);
      const t = pager().find((e) => e.innerText.trim() === String(hal));
      if (!t) {
        console.warn(`[ojk_pto] tombol halaman ${hal} tidak ditemukan, berhenti`);
        break;
      }
      t.click();
      for (let i = 0; i < 40; i++) {
        await tunggu(300);
        if (JSON.stringify(baris()[0]) !== sebelum) break;
      }
      await tunggu(500);
    }
    baris().forEach((r) => {
      if (r.length >= 4 && /^\d+$/.test(r[0])) hasil[r[0]] = { no: Number(r[0]), nama: r[1], url: r[2], pemilik: r[3] };
    });
    console.log(`[ojk_pto] halaman ${hal}/${jumlahHal}: total ${Object.keys(hasil).length}`);
  }
  const sistem = Object.values(hasil).sort((a, b) => a.no - b.no);
  if (!sistem.length) {
    console.error("[ojk_pto] Tidak ada baris terbaca");
    return;
  }
  simpan({ diambil: new Date().toISOString(), sumber: location.href, sistem }, `ojk_pto_${tgl}.json`);
  console.log(`[ojk_pto] SELESAI: ${sistem.length} portal transaksi online`);
})();

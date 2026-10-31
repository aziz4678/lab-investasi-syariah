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
    [...document.querySelectorAll('a[href*="/reksadana/RD"]')].map((a) => {
      const tr = a.closest("tr");
      const sel = tr ? [...tr.querySelectorAll("td")].map((td) => td.innerText.trim()) : [];
      return { kode: a.getAttribute("href").split("/").pop(), nama: a.innerText.split("\n")[0].trim(), jenis: sel[1] || null, url: a.href };
    });
  const tombol = (teks) =>
    [...document.querySelectorAll("body *")]
      .filter((e) => !e.closest("footer") && e.innerText && e.innerText.trim() === teks)
      .sort((a, b) => a.querySelectorAll("*").length - b.querySelectorAll("*").length)[0];
  if (!location.hostname.endsWith("bibit.id") || !location.pathname.startsWith("/reksadana")) {
    console.error("[bibit] Buka https://bibit.id/reksadana dulu");
    return;
  }
  console.log("[bibit] Mengambil daftar reksa dana syariah dari halaman publik Bibit (tanpa login)...");
  for (let i = 0; i < 20 && !baris().length; i++) await tunggu(500);
  const syariah = tombol("Syariah");
  if (!syariah) {
    console.error("[bibit] Tombol filter 'Syariah' tidak ditemukan; tampilan Bibit mungkin berubah");
    return;
  }
  syariah.click();
  await tunggu(3000);
  const hasil = {};
  let hal = 1;
  while (hal < 40) {
    const isi = baris();
    isi.forEach((x) => (hasil[x.kode] = x));
    console.log(`[bibit] halaman ${hal}: ${isi.length} produk (total ${Object.keys(hasil).length})`);
    const lanjut = tombol(String(hal + 1));
    if (!lanjut) break;
    const sebelum = isi.map((x) => x.kode).join(",");
    lanjut.click();
    let berubah = false;
    for (let i = 0; i < 30; i++) {
      await tunggu(400);
      if (baris().map((x) => x.kode).join(",") !== sebelum) {
        berubah = true;
        break;
      }
    }
    if (!berubah) break;
    hal += 1;
    await tunggu(800);
  }
  const produk = Object.values(hasil);
  if (!produk.length) {
    console.error("[bibit] Tidak ada produk terbaca");
    return;
  }
  simpan({ diambil: new Date().toISOString(), filter: "Syariah", sumber: location.href, produk }, `bibit_rd_${tgl}.json`);
  console.log(`[bibit] SELESAI: ${produk.length} reksa dana syariah`);
})();

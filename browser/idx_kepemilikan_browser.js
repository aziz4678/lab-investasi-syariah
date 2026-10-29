(async () => {
  const MAKS = 800;
  const SEMUA = __DAFTAR__;
  const DAFTAR = SEMUA.slice(0, MAKS);
  const SISA_LAIN = Math.max(0, SEMUA.length - MAKS);
  const PER_FILE = 100;
  const PARALEL = 1;
  const JEDA = 1500;
  const BATAS_DITOLAK = 6;
  let ditolak = 0;
  const CAP = new Date().toISOString().slice(0, 16).replace(/[-:]/g, "").replace("T", "_");
  const tunggu = (ms) => new Promise((r) => setTimeout(r, ms));
  const dua = (n) => String(n).padStart(2, "0");
  const keB64 = (blob) => new Promise((ok, gagal) => {
    const r = new FileReader();
    r.onload = () => ok(String(r.result).split(",")[1] || "");
    r.onerror = () => gagal(r.error);
    r.readAsDataURL(blob);
  });
  window.__idxKepemilikan = [];
  window.simpanUlangKepemilikan = async () => {
    for (const [nama, isi] of window.__idxKepemilikan) {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([JSON.stringify(isi)], { type: "application/json" }));
      a.download = nama;
      a.click();
      console.log(`unduh ulang ${nama}`);
      await tunggu(2000);
    }
  };
  const simpan = (item, nomor) => {
    const nama = `idx_kepemilikan_${CAP}_${dua(nomor)}.json`;
    const isi = { dibuat: new Date().toISOString(), item };
    window.__idxKepemilikan.push([nama, isi]);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(isi)], { type: "application/json" }));
    a.download = nama;
    a.click();
    console.log(`file ${nama} disimpan (${item.length} PDF)`);
  };
  const ambil = async ([id, url, jenis]) => {
    for (let coba = 1; coba <= 4; coba++) {
      try {
        const r = await fetch(url, { credentials: "include" });
        if (r.ok) {
          const b = await r.blob();
          if (b.size > 500) return { id, url, jenis, b64: await keB64(b) };
          return { id, url, jenis, gagal: `kosong ${b.size} byte` };
        }
        if (r.status === 404) return { id, url, jenis, gagal: "404" };
        if (r.status === 429 || r.status === 503) {
          ditolak += 1;
          console.log(`  IDX menolak (${r.status}), istirahat ${30 * coba} dtk`);
          await tunggu(30000 * coba);
          continue;
        }
        await tunggu(8000 * coba);
      } catch (e) {
        await tunggu(8000 * coba);
      }
    }
    return { id, url, jenis, gagal: "tidak merespons" };
  };

  console.log(`${DAFTAR.length} PDF akan diunduh (${PARALEL} sekaligus), dibungkus per ${PER_FILE} PDF per file`);
  let bagian = [];
  let nomor = 1;
  let selesai = 0;
  let gagal = 0;
  const mulai = Date.now();
  if (SISA_LAIN) console.log(`${SISA_LAIN} PDF lain menunggu putaran berikutnya (batas ${MAKS} per putaran supaya tidak ditolak IDX)`);
  for (let i = 0; i < DAFTAR.length; i += PARALEL) {
    if (ditolak >= BATAS_DITOLAK * 4) {
      console.log(`IDX terlalu sering menolak (${ditolak}x), berhenti dan simpan yang sudah terkumpul. Lanjutkan nanti.`);
      break;
    }
    const hasil = await Promise.all(DAFTAR.slice(i, i + PARALEL).map(ambil));
    if (hasil.every((h) => !h.gagal)) ditolak = Math.max(0, ditolak - 1);
    for (const h of hasil) {
      bagian.push(h);
      selesai += 1;
      if (h.gagal) gagal += 1;
    }
    if (bagian.length >= PER_FILE) {
      simpan(bagian, nomor++);
      bagian = [];
    }
    if (selesai % 30 === 0 || selesai === DAFTAR.length) {
      const mnt = (Date.now() - mulai) / 60000;
      const sisa = selesai ? (mnt / selesai) * (DAFTAR.length - selesai) : 0;
      console.log(`${selesai}/${DAFTAR.length} PDF · gagal ${gagal} · ${mnt.toFixed(1)} mnt · perkiraan sisa ${sisa.toFixed(0)} mnt`);
    }
    await tunggu(JEDA);
  }
  if (bagian.length) simpan(bagian, nomor++);
  console.log(`${selesai} PDF diproses (${gagal} gagal), ${nomor - 1} file. Kalau file di Downloads kurang, izinkan unduhan otomatis lalu ketik simpanUlangKepemilikan() di Console.`);
  console.log("SELESAI");
})();

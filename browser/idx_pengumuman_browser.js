(async () => {
  const UKURAN = 500;
  const JEDA = 2000;
  const BATAS_KOSONG = 6;
  const PER_FILE = 25000;
  const DARI = __DARI__;
  const CAP = new Date().toISOString().slice(0, 10).replaceAll("-", "");
  const P = "https://www.idx.co.id/primary/ListedCompany/GetAnnouncement";
  const tunggu = (ms) => new Promise((r) => setTimeout(r, ms));
  const dua = (n) => String(n).padStart(2, "0");
  const url = (dari, sampai, mulai) =>
    `${P}?kodeEmiten=&emitenType=*&indexFrom=${mulai}&pageSize=${UKURAN}&dateFrom=${dari}&dateTo=${sampai}&lang=id&keyword=`;
  window.__idxPengumuman = [];
  window.simpanUlangPengumuman = async () => {
    for (const [nama, isi] of window.__idxPengumuman) {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([JSON.stringify(isi)], { type: "application/json" }));
      a.download = nama;
      a.click();
      console.log(`unduh ulang ${nama} (${isi.length} baris)`);
      await new Promise((r) => setTimeout(r, 2000));
    }
    console.log(`unduh ulang selesai: ${window.__idxPengumuman.length} file. Cek folder Downloads.`);
  };
  const simpan = (isi, nama) => {
    window.__idxPengumuman.push([nama, isi]);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(isi)], { type: "application/json" }));
    a.download = nama;
    a.click();
  };
  const ambil = async (u) => {
    for (let coba = 1; coba <= 6; coba++) {
      try {
        const r = await fetch(u, { credentials: "include" });
        if (r.ok) return await r.json();
        console.log(`  status ${r.status}, tunggu ${15 * coba} dtk (coba ${coba}/6)`);
      } catch (e) {
        console.log(`  gagal ${e.message}, tunggu ${15 * coba} dtk (coba ${coba}/6)`);
      }
      await tunggu(15000 * coba);
    }
    throw new Error("IDX tidak merespons setelah 6 kali coba");
  };
  const ringkas = (x) => ({
    id: x.pengumuman?.Id2,
    no: x.pengumuman?.NoPengumuman,
    tgl: x.pengumuman?.TglPengumuman,
    kode: (x.pengumuman?.Kode_Emiten || "").trim(),
    judul: x.pengumuman?.JudulPengumuman,
    jenis: x.pengumuman?.JenisPengumuman,
    lampiran: (x.attachments || []).map((a) => ({ url: a.FullSavePath, nama: a.OriginalFilename, utama: !a.IsAttachment })),
  });

  const kini = new Date();
  let th = kini.getFullYear();
  let bl = kini.getMonth() + 1;
  let kosong = 0;
  let bagian = [];
  let nomorFile = 1;
  let jumlah = 0;
  const mulaiJam = Date.now();
  console.log(DARI ? `Pembaruan: mengambil bulan ini mundur sampai ${DARI.slice(0, 4)}-${DARI.slice(4)} (bulan terakhir di database)` : "Pengambilan pertama: semua riwayat (±30 menit, ±10 file). Izinkan unduhan beberapa file kalau Chrome bertanya.");
  console.log("Mulai mengambil daftar pengumuman IDX per bulan, mundur dari bulan ini");

  while (kosong < BATAS_KOSONG && !(DARI && `${th}${dua(bl)}` < DARI)) {
    const dari = `${th}${dua(bl)}01`;
    const akhir = new Date(th, bl, 0).getDate();
    const sampai = `${th}${dua(bl)}${dua(akhir)}`;
    let total = 0;
    let isiBulan = 0;
    const lihat = new Set();
    let tanpaBaru = 0;
    for (let hal = 0; hal < 200; hal++) {
      const j = await ambil(url(dari, sampai, hal));
      total = j.ResultCount || 0;
      const baru = (j.Replies || []).map(ringkas).filter((x) => !lihat.has(x.id));
      baru.forEach((x) => lihat.add(x.id));
      bagian.push(...baru);
      isiBulan += baru.length;
      jumlah += baru.length;
      await tunggu(JEDA);
      if (total > UKURAN) console.log(`  ${th}-${dua(bl)} halaman ${hal}: +${baru.length} (${isiBulan}/${total})`);
      tanpaBaru = baru.length ? 0 : tanpaBaru + 1;
      if (!(j.Replies || []).length || isiBulan >= total || tanpaBaru >= 2) break;
    }
    const menit = ((Date.now() - mulaiJam) / 60000).toFixed(1);
    console.log(`${th}-${dua(bl)}: ${isiBulan} pengumuman (total server ${total}) · terkumpul ${jumlah} · ${menit} mnt`);
    kosong = isiBulan ? 0 : kosong + 1;
    if (bagian.length >= PER_FILE) {
      simpan(bagian, `idx_pengumuman_${CAP}_${dua(nomorFile)}.json`);
      console.log(`file idx_pengumuman_${CAP}_${dua(nomorFile)}.json disimpan (${bagian.length} baris)`);
      nomorFile += 1;
      bagian = [];
      await tunggu(1500);
    }
    bl -= 1;
    if (bl === 0) {
      bl = 12;
      th -= 1;
    }
  }
  if (bagian.length) {
    simpan(bagian, `idx_pengumuman_${CAP}_${dua(nomorFile)}.json`);
    console.log(`file idx_pengumuman_${CAP}_${dua(nomorFile)}.json disimpan (${bagian.length} baris)`);
  }
  console.log(`Berhenti di ${th}-${dua(bl)}. Total ${jumlah} pengumuman, ${window.__idxPengumuman.length} file.`);
  console.log("Cek folder Downloads: semua file idx_pengumuman_XX.json harus ada. Kalau kurang, izinkan unduhan otomatis untuk idx.co.id lalu ketik simpanUlangPengumuman() di Console (tanpa mengambil ulang).");
  console.log("SELESAI");
})();

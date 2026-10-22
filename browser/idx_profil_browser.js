(async () => {
  const KODE = __KODE__;
  const BASIS = "https://www.idx.co.id/primary/ListedCompany/GetCompanyProfilesDetail";
  const JEDA = 700;
  const JEDA_TOLAK = [30, 60, 120, 240];
  const tunggu = ms => new Promise(r => setTimeout(r, ms));
  const hasil = [];
  let gagalBeruntun = 0;
  const simpan = (data, nama) => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(data)], { type: "application/json" }));
    a.download = nama;
    a.click();
  };
  console.log(`Mengambil profil ${KODE.length} emiten dari IDX...`);
  for (let i = 0; i < KODE.length; i++) {
    const k = KODE[i];
    let ok = false;
    for (let coba = 0; coba <= JEDA_TOLAK.length && !ok; coba++) {
      try {
        const r = await fetch(`${BASIS}?KodeEmiten=${k}&language=id-id`, { credentials: "include" });
        if (r.status === 429 || r.status === 403) throw new Error("ditolak " + r.status);
        if (!r.ok) throw new Error("status " + r.status);
        const j = await r.json();
        if (i === 0) console.log("Format respons (cek):", Object.keys(j), j.Profiles ? Object.keys(j.Profiles[0] || {}) : "tanpa Profiles");
        hasil.push({
          kode: k, profil: (j.Profiles || [])[0] || null, pemegang: j.PemegangSaham || [], direktur: j.Direktur || [],
          komisaris: j.Komisaris || [], sekretaris: j.Sekretaris || [], anak: (j.AnakPerusahaan || []).slice(0, 30),
        });
        ok = true;
        gagalBeruntun = 0;
      } catch (e) {
        if (coba < JEDA_TOLAK.length && String(e.message).startsWith("ditolak")) {
          console.log(`${k}: ${e.message}, tunggu ${JEDA_TOLAK[coba]} detik`);
          await tunggu(JEDA_TOLAK[coba] * 1000);
        } else {
          hasil.push({ kode: k, error: e.message });
          gagalBeruntun++;
          break;
        }
      }
    }
    if (gagalBeruntun >= 15) {
      console.log("15 gagal beruntun, berhenti. Disimpan yang sudah terkumpul.");
      break;
    }
    if ((i + 1) % 10 === 0) console.log(`${i + 1}/${KODE.length} emiten`);
    await tunggu(JEDA);
  }
  simpan(hasil, "idx_profil.json");
  console.log("SELESAI,", hasil.filter(x => x.profil).length, "profil tersimpan ke idx_profil.json");
})();

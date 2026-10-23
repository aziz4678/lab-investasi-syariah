(async () => {
  const JEDA = 150;
  const tunggu = (ms) => new Promise((r) => setTimeout(r, ms));
  const mulaiJam = Date.now();
  const st = (window.__logo = { tahap: "daftar emiten", selesai: 0, total: 0, dapat: 0, gagal: 0, catatan: "" });
  const kotak = document.createElement("div");
  kotak.style.cssText = "position:fixed;right:16px;bottom:16px;z-index:999999;width:360px;background:#0f1f17;color:#e9f7ef;font:13px/1.5 system-ui,sans-serif;border-radius:14px;padding:14px 16px;box-shadow:0 8px 30px rgba(0,0,0,.35)";
  document.body.appendChild(kotak);
  const tampil = () => {
    const persen = st.total ? Math.round((st.selesai / st.total) * 100) : 0;
    const dtk = Math.round((Date.now() - mulaiJam) / 1000);
    kotak.innerHTML = `<div style="font-weight:600;font-size:14px">Logo emiten IDX · ${st.tahap === "SELESAI" ? "SELESAI ✔" : st.tahap}</div>
      <div style="height:8px;background:#22362b;border-radius:9px;overflow:hidden;margin:8px 0"><div style="height:100%;width:${persen}%;background:#1fc37f"></div></div>
      <div>${st.selesai}/${st.total} emiten (${persen}%) · logo didapat <b>${st.dapat}</b> · gagal ${st.gagal}</div>
      <div style="color:#9fb8aa">berjalan ${Math.floor(dtk / 60)} mnt ${dtk % 60} dtk</div>
      ${st.catatan ? `<div style="margin-top:6px;color:#ffd166">${st.catatan}</div>` : ""}
      <div style="margin-top:8px;color:#9fb8aa;font-size:12px">Biarkan tab ini terbuka. Hasil: idx_logo.json di folder Downloads.</div>`;
  };
  const jam = setInterval(tampil, 1000);
  tampil();

  const keBase64 = (blob) => new Promise((ok) => {
    const r = new FileReader();
    r.onload = () => ok(String(r.result).split(",")[1]);
    r.readAsDataURL(blob);
  });

  let daftar = [];
  try {
    const r = await fetch("/primary/ListedCompany/GetCompanyProfiles?emitenType=s&start=0&length=9999", { credentials: "include" });
    const j = await r.json();
    daftar = (j.data || j.Data || []).map((x) => ({ kode: (x.KodeEmiten || "").trim(), logo: x.Logo || "" })).filter((x) => x.kode);
  } catch (e) {
    st.catatan = "Gagal mengambil daftar emiten: " + e.message;
  }
  console.warn(`[logo] ${daftar.length} emiten di IDX`);
  st.total = daftar.length;
  st.tahap = "mengunduh logo";
  const hasil = {};
  for (const x of daftar) {
    const jalur = x.logo || `/Portals/0/StaticData/ListedCompanies/LogoEmiten/${x.kode}.jpg`;
    let ok = false;
    for (let coba = 0; coba < 3 && !ok; coba++) {
      try {
        const r = await fetch(jalur.startsWith("http") ? jalur : jalur, { credentials: "include" });
        if (r.status === 429 || r.status === 403) {
          st.catatan = `IDX menolak (${r.status}), tunggu ${20 * (coba + 1)} detik`;
          await tunggu(20000 * (coba + 1));
          continue;
        }
        if (!r.ok) break;
        const blob = await r.blob();
        if (!blob.type.startsWith("image") || blob.size < 300) break;
        hasil[x.kode] = { jenis: blob.type, isi: await keBase64(blob) };
        ok = true;
        st.catatan = "";
      } catch (e) {
        await tunggu(2000);
      }
    }
    st.selesai += 1;
    if (ok) st.dapat += 1;
    else st.gagal += 1;
    if (st.selesai % 50 === 0) console.warn(`[logo] ${st.selesai}/${st.total}, didapat ${st.dapat}`);
    await tunggu(JEDA);
  }
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([JSON.stringify({ dibuat: new Date().toISOString(), logo: hasil })], { type: "application/json" }));
  a.download = "idx_logo.json";
  a.click();
  st.tahap = "SELESAI";
  tampil();
  clearInterval(jam);
  console.warn(`[logo] SELESAI: ${st.dapat} logo disimpan ke idx_logo.json`);
  return `SELESAI ${st.dapat} logo`;
})();

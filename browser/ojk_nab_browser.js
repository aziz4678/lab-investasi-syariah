(async () => {
  const TAHUN_MULAI = 2014;
  const TAHUN_AKHIR = new Date().getFullYear();
  const BATAS_TUNGGU = 90000;
  const tunggu = (ms) => new Promise((r) => setTimeout(r, ms));
  const kini = new Date();
  const totalBulan = (TAHUN_AKHIR - TAHUN_MULAI) * 12 + kini.getMonth();
  const mulaiJam = Date.now();
  const st = (window.__ojk = { tahap: "mulai", bulan: "", selesai: 0, total: totalBulan, baris: 0, file: [], catatan: "" });
  const simpanan = (window.__ojkData = window.__ojkData || {});

  const kotak = document.createElement("div");
  kotak.style.cssText = "position:fixed;right:16px;bottom:16px;z-index:999999;width:380px;background:#0f1f17;color:#e9f7ef;font:13px/1.5 system-ui,sans-serif;border-radius:14px;padding:14px 16px;box-shadow:0 8px 30px rgba(0,0,0,.35)";
  document.body.appendChild(kotak);
  const menit = (ms) => (ms < 60000 ? `${Math.round(ms / 1000)} dtk` : `${Math.floor(ms / 60000)} mnt ${Math.round((ms % 60000) / 1000)} dtk`);
  const tampil = () => {
    const jalan = Date.now() - mulaiJam;
    const persen = st.total ? Math.round((st.selesai / st.total) * 100) : 0;
    const sisa = st.selesai ? (jalan / st.selesai) * (st.total - st.selesai) : null;
    kotak.innerHTML = `
      <div style="font-weight:600;font-size:14px;margin-bottom:6px">NAB OJK · ${st.tahap === "SELESAI" ? "SELESAI ✔" : "sedang mengambil…"}</div>
      <div style="height:8px;background:#22362b;border-radius:9px;overflow:hidden;margin:6px 0 8px"><div style="height:100%;width:${persen}%;background:#1fc37f"></div></div>
      <div>Bulan: <b>${st.bulan || "-"}</b> · ${st.selesai}/${st.total} bulan (${persen}%)</div>
      <div>Baris terkumpul: <b>${st.baris.toLocaleString("id-ID")}</b></div>
      <div>Berjalan: ${menit(jalan)}${sisa != null && st.tahap !== "SELESAI" ? ` · perkiraan sisa: <b>${menit(sisa)}</b>` : ""}</div>
      <div style="margin-top:6px">File disimpan: ${st.file.length ? st.file.join(", ") : "-"}</div>
      ${st.catatan ? `<div style="margin-top:6px;color:#ffd166">${st.catatan}</div>` : ""}
      <div style="margin-top:8px;color:#9fb8aa;font-size:12px">Biarkan tab ini terbuka. Kalau Chrome menampilkan ikon unduhan diblokir di address bar, klik lalu pilih Izinkan, kemudian ketik <b>__ojkSimpan()</b> di Console untuk mengunduh ulang semua tahun.</div>`;
  };
  const jam = setInterval(tampil, 1000);
  tampil();

  const simpan = (data, nama) => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(data)], { type: "application/json" }));
    a.download = nama;
    a.click();
  };
  window.__ojkSimpan = (th) => {
    const daftar = th ? [String(th)] : Object.keys(simpanan);
    daftar.forEach((t, i) => setTimeout(() => simpan(simpanan[t], `ojk_nab_${t}.json`), i * 1500));
    return `mengunduh ulang ${daftar.length} file: ${daftar.join(", ")}`;
  };
  const angka = (s) => {
    const v = parseFloat(String(s).trim().replace(/\./g, "").replace(",", "."));
    return Number.isFinite(v) ? v : null;
  };
  const bingkai = document.createElement("iframe");
  bingkai.style.cssText = "position:fixed;left:-3000px;top:0;width:1400px;height:900px;";
  document.body.appendChild(bingkai);
  const muatHalaman = (url) => new Promise((ok, gagal) => {
    const t = setTimeout(() => gagal(new Error("halaman tidak termuat")), BATAS_TUNGGU);
    bingkai.onload = () => { clearTimeout(t); ok(); };
    bingkai.src = url;
  });
  const cariGrid = (w) => {
    const k = Object.keys(w).filter((n) => { try { return w[n] && typeof w[n].GetPageCount === "function"; } catch { return false; } });
    return w[k.find((n) => /grd/i.test(n)) || k[k.length - 1]];
  };
  const selesaiCallback = async (g) => {
    const awal = Date.now();
    await tunggu(400);
    while (g.InCallback && g.InCallback() && Date.now() - awal < BATAS_TUNGGU) await tunggu(300);
    await tunggu(300);
  };
  const pilihSemua = async (w, g) => {
    if (g.GetPageCount() <= 1) return true;
    for (const perintah of ["PSP-1", "PSPAll", "PSP0"]) {
      try {
        if (typeof w.aspxGVPagerOnClick === "function") w.aspxGVPagerOnClick(g.name, perintah);
        else if (w.ASPx && typeof w.ASPx.GVPagerOnClick === "function") w.ASPx.GVPagerOnClick(g.name, perintah);
        await selesaiCallback(g);
        if (g.GetPageCount() <= 1) return true;
      } catch (e) {
        st.catatan = "perintah " + perintah + " gagal";
      }
    }
    const item = [...w.document.querySelectorAll("td,div,span,li")].filter((e) => e.children.length === 0 && e.textContent.trim() === "All");
    for (const e of item) {
      for (const jenis of ["mousedown", "mouseup", "click"]) e.dispatchEvent(new w.MouseEvent(jenis, { bubbles: true }));
      await selesaiCallback(g);
      if (g.GetPageCount() <= 1) return true;
    }
    return false;
  };
  const bacaBaris = (w) => [...w.document.querySelectorAll('tr[id*="DXDataRow"]')].map((r) => [...r.cells].map((c) => c.innerText.trim()));

  async function ambilBulan(th, bl) {
    await muatHalaman(`/Public/StatistikNABReksadanaPublicDetail.aspx?year=${th}&month=${bl}`);
    const w = bingkai.contentWindow;
    let g = null;
    for (let i = 0; i < 40 && !g; i++) { g = cariGrid(w); if (!g) await tunggu(250); }
    if (!g) return { baris: [], catatan: "tabel tidak ditemukan" };
    const n = g.GetPageCount();
    if (n === 0) return { baris: [], catatan: "kosong" };
    let semua = [];
    if (await pilihSemua(w, g)) {
      semua = bacaBaris(w);
    } else {
      for (let p = 0; p < g.GetPageCount(); p++) {
        st.catatan = `${th}-${bl}: pilihan All gagal, pindah halaman ${p + 1}/${g.GetPageCount()} (lambat)`;
        if (p > 0) { g.GotoPage(p); await selesaiCallback(g); }
        semua = semua.concat(bacaBaris(w));
      }
      st.catatan = "";
    }
    const hasil = [];
    for (const c of semua) {
      if (c.length < 7) continue;
      const nab = angka(c[5]), unit = angka(c[6]);
      if (!nab || !unit) continue;
      hasil.push([c[0], c[1], c[2], c[3], c[4], nab, unit]);
    }
    return { baris: hasil, total: semua.length };
  }

  for (let th = TAHUN_MULAI; th <= TAHUN_AKHIR; th++) {
    const data = { tahun: th, kolom: ["mi", "bk", "produk", "tipe", "denominasi", "nab", "unit"], bulan: {}, catatan: {} };
    for (let bl = 1; bl <= 12; bl++) {
      if (th === kini.getFullYear() && bl >= kini.getMonth() + 1) break;
      Object.assign(st, { tahap: "ambil", bulan: `${th}-${String(bl).padStart(2, "0")}` });
      let r = null;
      for (let coba = 0; coba < 3 && !r; coba++) {
        try {
          r = await ambilBulan(th, bl);
        } catch (e) {
          st.catatan = `${th}-${bl}: ${e.message}, coba lagi (${coba + 1}/3)`;
          await tunggu(5000 * (coba + 1));
        }
      }
      if (!r) data.catatan[bl] = "gagal";
      else {
        data.bulan[bl] = r.baris;
        if (r.catatan) data.catatan[bl] = r.catatan;
        st.baris += r.baris.length;
        st.catatan = "";
      }
      st.selesai += 1;
      console.log(`[ojk] ${th}-${String(bl).padStart(2, "0")}: ${r ? r.baris.length : 0} produk`);
      await tunggu(500);
    }
    simpanan[th] = data;
    simpan(data, `ojk_nab_${th}.json`);
    st.file.push(String(th));
    await tunggu(1500);
  }
  bingkai.remove();
  st.tahap = "SELESAI";
  st.catatan = `Cek Downloads: harus ada ojk_nab_${TAHUN_MULAI}.json s/d ojk_nab_${TAHUN_AKHIR}.json (${st.file.length} file).`;
  tampil();
  clearInterval(jam);
  return "SELESAI " + st.baris + " baris";
})();

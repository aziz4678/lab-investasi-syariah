(() => {
  if (window.__pantau) window.__pantau.hapus();
  const JUDUL = __JUDUL__;
  const mulai = Date.now();
  const log = [];
  let unduh = 0;
  let status = "jalan";
  let terakhir = Date.now();
  const WARNA = { jalan: "#1fc37f", selesai: "#1fc37f", berhenti: "#ffd166", galat: "#ff6b6b" };
  const LABEL = { jalan: "sedang berjalan", selesai: "SELESAI ✔", berhenti: "BERHENTI", galat: "ADA ERROR" };
  const kotak = document.createElement("div");
  kotak.style.cssText = "position:fixed;right:16px;bottom:16px;z-index:999999;width:400px;background:#0f1f17;color:#e9f7ef;font:13px/1.5 system-ui,sans-serif;border-radius:14px;padding:14px 16px;box-shadow:0 8px 30px rgba(0,0,0,.35)";
  const asli = { log: console.log, warn: console.warn, error: console.error };
  const klikAsli = HTMLAnchorElement.prototype.click;
  const aman = (x) => {
    if (typeof x === "string") return x;
    try { return JSON.stringify(x); } catch { return String(x); }
  };
  const lama = (ms) => (ms < 60000 ? `${Math.round(ms / 1000)} dtk` : `${Math.floor(ms / 60000)} mnt ${Math.round((ms % 60000) / 1000)} dtk`);
  const html = (s) => s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  const tambah = (t) => {
    log.push(t);
    if (log.length > 6) log.shift();
    terakhir = Date.now();
  };
  const gambar = () => {
    const titik = status === "jalan" ? ["●○○", "○●○", "○○●"][Math.floor(Date.now() / 500) % 3] : "";
    const sunyi = Date.now() - terakhir;
    kotak.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
        <b style="font-size:14px">${html(JUDUL)}</b>
        <span style="cursor:pointer;color:#9fb8aa" title="Tutup kotak ini (script tetap jalan)" id="__pantau_tutup">✕</span>
      </div>
      <div style="margin:4px 0 8px;color:${WARNA[status]};font-weight:600">${LABEL[status]} ${titik}</div>
      <div>Berjalan ${lama(Date.now() - mulai)} · file diunduh: <b>${unduh}</b></div>
      <div style="color:#9fb8aa;font-size:12px">pesan terakhir ${lama(sunyi)} lalu${status === "jalan" && sunyi > 120000 ? " — lama tanpa pesan, mungkin sedang menunggu IDX/OJK" : ""}</div>
      <div style="margin-top:8px;background:#162b20;border-radius:10px;padding:8px 10px;font:12px/1.45 ui-monospace,Consolas,monospace;max-height:150px;overflow:hidden">${log.length ? log.map((x) => `<div>${html(x)}</div>`).join("") : "<div>menunggu pesan pertama…</div>"}</div>
      <div style="margin-top:8px;color:#9fb8aa;font-size:12px">Biarkan tab ini terbuka sampai SELESAI. File otomatis masuk folder Downloads. Kalau Chrome menanyakan lokasi atau memblokir unduhan, matikan "Tanyakan lokasi penyimpanan" (chrome://settings/downloads) dan izinkan unduhan otomatis untuk situs ini.</div>`;
    const x = kotak.querySelector("#__pantau_tutup");
    if (x) x.onclick = () => (kotak.style.display = "none");
  };
  const tangkap = (jenis) => (...a) => {
    asli[jenis](...a);
    const t = a.map(aman).join(" ").slice(0, 220);
    tambah(t);
    if (/SELESAI/.test(t)) status = "selesai";
    else if (/BERHENTI|berhenti/.test(t) && status !== "selesai") status = "berhenti";
    if (jenis === "error" && status === "jalan") status = "galat";
    gambar();
  };
  console.log = tangkap("log");
  console.warn = tangkap("warn");
  console.error = tangkap("error");
  HTMLAnchorElement.prototype.click = function () {
    if (this.download) {
      unduh += 1;
      tambah("⬇ diunduh: " + this.download);
      gambar();
    }
    return klikAsli.apply(this, arguments);
  };
  const salah = (e) => {
    status = "galat";
    tambah("ERROR: " + ((e.reason && e.reason.message) || e.message || e.reason || "tidak diketahui"));
    gambar();
  };
  window.addEventListener("unhandledrejection", salah);
  window.addEventListener("error", salah);
  const jam = setInterval(gambar, 1000);
  document.body.appendChild(kotak);
  window.__pantau = {
    hapus() {
      clearInterval(jam);
      kotak.remove();
      Object.assign(console, asli);
      HTMLAnchorElement.prototype.click = klikAsli;
      window.removeEventListener("unhandledrejection", salah);
      window.removeEventListener("error", salah);
    },
  };
  gambar();
})();

export function persen(v, digit = 1, tanda = true) {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  const s = v.toLocaleString("id-ID", { minimumFractionDigits: digit, maximumFractionDigits: digit });
  return (tanda && v > 0 ? "+" : "") + s + "%";
}

export function rupiah(v) {
  return v === null || v === undefined ? "–" : v.toLocaleString("id-ID");
}

export function tanggal(s) {
  return s ? s.slice(0, 10) : "–";
}

export function pecahAngka(s) {
  const m = String(s ?? "").match(/^(.*\d)(,\d+)(\D*)$/);
  return m ? [m[1], m[2] + m[3]] : [String(s ?? ""), ""];
}

export function infoAksi(tglData) {
  const d = new Date();
  const hariIni = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  const kerja = d.getDay() > 0 && d.getDay() < 6;
  if (tglData && hariIni > tglData && kerja) return { judul: "Aksi hari ini", ket: `di open ${hariIni} · tercatat otomatis saat Perbarui setelah 17:00` };
  if (tglData && hariIni > tglData) return { judul: "Aksi di open berikutnya", ket: `sinyal close ${tglData} · tercatat otomatis` };
  return { judul: "Aksi besok", ket: `di open hari bursa berikutnya · sinyal close ${tglData} · tercatat otomatis` };
}

export function ringkas(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  const a = Math.abs(v);
  const f = (x, s) => `${(v < 0 ? "-" : "")}${x.toLocaleString("id-ID", { maximumFractionDigits: 1 })}${s}`;
  if (a >= 1e12) return f(a / 1e12, " T");
  if (a >= 1e9) return f(a / 1e9, " M");
  if (a >= 1e6) return f(a / 1e6, " jt");
  return v.toLocaleString("id-ID");
}

export function kelasPersen(v) {
  if (v === null || v === undefined || Number.isNaN(v) || Math.abs(v) < 0.005) return "";
  return v > 0 ? "text-naik" : "text-turun";
}

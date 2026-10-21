import { ref } from "vue";

export async function ambil(jalur) {
  const r = await fetch(`/api/${jalur}`);
  if (!r.ok) throw new Error(`${jalur}: ${r.status}`);
  return r.json();
}

export function warna(nama) {
  return getComputedStyle(document.documentElement).getPropertyValue(nama).trim();
}

const versiTema = ref(0);
export const modeTema = ref("sistem");
const mq = window.matchMedia("(prefers-color-scheme: dark)");

function terapkan() {
  const el = document.documentElement;
  if (modeTema.value === "sistem") delete el.dataset.theme;
  else el.dataset.theme = modeTema.value === "gelap" ? "dark" : "light";
  versiTema.value += 1;
}

export function setTema(mode) {
  modeTema.value = mode;
  try {
    localStorage.setItem("tema", mode);
  } catch {
    modeTema.value = mode;
  }
  terapkan();
}

export function temaGelap() {
  versiTema.value;
  return modeTema.value === "gelap" || (modeTema.value === "sistem" && mq.matches);
}

try {
  modeTema.value = localStorage.getItem("tema") || "sistem";
} catch {
  modeTema.value = "sistem";
}
terapkan();
mq.addEventListener("change", () => modeTema.value === "sistem" && terapkan());

export function pakaiTema() {
  return versiTema;
}

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

function hexKeRgb(h) {
  const n = parseInt(h.replace("#", ""), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

export function warnaDivergen(v, batas) {
  const t = Math.min(Math.abs(v) / batas, 1);
  const a = hexKeRgb(warna("--netral"));
  const b = hexKeRgb(warna(v >= 0 ? "--pos" : "--neg"));
  const c = a.map((x, i) => Math.round(x + (b[i] - x) * t));
  const terang = (0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]) / 255;
  return { bg: `rgb(${c.join(",")})`, fg: terang > 0.55 ? "#0b0b0b" : "#f0efec" };
}

export function opsiDasar() {
  const muted = warna("--text-muted");
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 400 },
    interaction: { mode: "index", intersect: false },
    layout: { padding: { top: 4 } },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: warna("--surface-3"), titleColor: warna("--text-primary"), bodyColor: warna("--text-secondary"),
        borderWidth: 0, padding: 12, boxPadding: 6, cornerRadius: 12, usePointStyle: true, titleFont: { weight: "500" },
      },
    },
    scales: {
      x: { ticks: { color: muted, maxRotation: 0, autoSkipPadding: 28, padding: 10 }, grid: { color: warna("--grid"), drawTicks: false }, border: { display: false } },
      y: { ticks: { color: muted, padding: 10, maxTicksLimit: 6 }, grid: { display: false }, border: { display: false } },
    },
    elements: { point: { hoverRadius: 5, hoverBorderWidth: 3 } },
  };
}

export function alfa(hex, a) {
  const [r, g, b] = hexKeRgb(hex);
  return `rgba(${r},${g},${b},${a})`;
}

export function gradien(var_, atas = 0.32) {
  return (konteks) => {
    const { ctx, chartArea } = konteks.chart;
    if (!chartArea) return "transparent";
    const w = warna(var_);
    const g = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
    g.addColorStop(0, alfa(w, atas));
    g.addColorStop(1, alfa(w, 0));
    return g;
  };
}

export function pecahAngka(s) {
  const m = String(s ?? "").match(/^(.*\d)(,\d+)(\D*)$/);
  return m ? [m[1], m[2] + m[3]] : [String(s ?? ""), ""];
}

export async function kirim(jalur, body = {}) {
  const r = await fetch(`/api/${jalur}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || `${jalur}: ${r.status}`);
  return j;
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

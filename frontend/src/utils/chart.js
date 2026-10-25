export function warna(nama) {
  return getComputedStyle(document.documentElement).getPropertyValue(nama).trim();
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

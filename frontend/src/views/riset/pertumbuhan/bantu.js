import { persen } from "@/utils/format";

export const pr = (v, d = 1) => (v == null ? "–" : persen(v * 100, d, false));
export const prTanda = (v, d = 1) => (v == null ? "–" : persen(v * 100, d, true));
export const prAngka = (v, d = 1) => (v == null ? "–" : persen(v, d, true));
export const kelasTanda = (v) => (v == null ? "text-muted" : v < 0 ? "text-turun" : "text-naik");
export const dariSeratus = (v) => (v == null ? "–" : Math.round(v * 100));

export const bulanTeks = (s) => {
  if (!s) return "–";
  const [t, b] = String(s).slice(0, 7).split("-").map(Number);
  return new Date(t, b - 1, 1).toLocaleDateString("id-ID", { month: "long", year: "numeric" });
};
export const bulanPendek = (s) => {
  if (!s) return "–";
  const [t, b] = String(s).slice(0, 7).split("-").map(Number);
  return new Date(t, b - 1, 1).toLocaleDateString("id-ID", { month: "short", year: "numeric" });
};
export const tglTeks = (s) => (s ? new Date(s).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }) : "–");

export const KELAS_RISIKO = { Rendah: "bg-naik-bg text-naik", Sedang: "bg-kuning-bg text-kuning", Tinggi: "bg-turun-bg text-turun" };
export const NAMA_PORTO = { "100% IDX": "100% Indonesia", "70/30": "70% Indonesia / 30% global", "50/50": "50/50 (cara ini)", "100% global": "100% global" };
export const NAMA_SUMBER = { indeks: "indeks", kategori: "rata-rata RD sejenis", keranjang: "keranjang produk" };
export const WARNA = { lokal: "--series-2", global: "--series-4", campuran: "--series-1" };
export const NAMA_SERI = { lokal: "100% Indonesia", global: "100% global", campuran: "Campuran 50/50" };
export const lamaPulih = (x) => (x.pulih != null ? `${x.pulih} bulan` : `belum pulih (${x.sejak_puncak} bulan)`);

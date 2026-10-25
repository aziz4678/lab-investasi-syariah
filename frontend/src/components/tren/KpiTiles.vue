<script setup>
import { computed } from "vue";
import { persen } from "@/utils/format";
import Stats from "@/components/common/Stats.vue";

const props = defineProps({ r: Object });

const items = computed(() => {
  const r = props.r;
  if (!r) return [];
  const u = r.undian;
  const UNDI = u ? ` Median dari ${u.n} undian pemilihan saham (aturan sama; undian hanya menentukan saham mana yang diambil saat sinyal lebih banyak dari slot kosong). Rentang p5–p95 = 90% undian ada di dalamnya. Contoh satu undian (seed ${u.contoh_seed}): ` : "";
  const cagr = u ? u.cagr.median : r.cagr;
  const dd = u ? u.dd.median : r.dd_maks;
  return [
    { label: u ? `Return per tahun (median)` : "Return per tahun", nilai: persen(cagr), nada: cagr >= 0 ? "naik" : "turun",
      ket: u ? `p5–p95 ${persen(u.cagr.p5)} s/d ${persen(u.cagr.p95)} · beli-tahan ${persen(r.cagr_beli_tahan)}` : `beli-tahan ${persen(r.cagr_beli_tahan)} · IHSG ${persen(r.cagr_ihsg)}`,
      info: `CAGR: rata-rata pertumbuhan modal per tahun. Dihitung seperti paper: 10 posisi @ 10% ekuitas saat beli, harga pasar harian, dividen dipotong pajak.${u ? `${UNDI}${persen(r.cagr)}.` : ""} IHSG ${persen(r.cagr_ihsg)}.` },
    { label: u ? "Penurunan terburuk (median)" : "Penurunan terburuk", nilai: persen(dd, 1, false), nada: "turun",
      ket: u ? `p5–p95 ${persen(u.dd.p5, 1, false)} s/d ${persen(u.dd.p95, 1, false)}` : "dari puncak modal",
      info: `Seberapa dalam modal pernah turun dari titik tertingginya sebelum pulih.${u ? `${UNDI}${persen(r.dd_maks, 1, false)}.` : ""}` },
    { label: "Win rate", nilai: persen(r.win_rate, 0, false), ket: `${r.trade} trade · ${r.sinyal} sinyal`, info: "Persentase trade yang untung. Trend following wajar di 30-40%." },
    { label: "Menang / kalah", nilai: `${persen(r.rata_menang, 0)} / ${persen(r.rata_kalah, 0)}`, ket: `median trade ${persen(r.median_trade)}`,
      info: "Rata-rata trade untung vs rugi. Median negatif artinya kebanyakan trade rugi kecil." },
    { label: "Rata-rata per trade", nilai: persen(r.net_per_trade, 2), nada: r.net_per_trade >= 0 ? "naik" : "turun", ket: `tahan ±${r.rata_hari} hari bursa`,
      info: "Sudah dipotong biaya: fee beli 0,15% + jual 0,25% + selisih 1 tick per sisi." },
    { label: "Bulan untung", nilai: persen(r.bulan_positif, 0, false), ket: `terbaik ${persen(r.bulan_terbaik)} · terburuk ${persen(r.bulan_terburuk)}`,
      info: "Persentase bulan yang modalnya naik." },
  ];
});
</script>

<template>
  <Stats v-if="r" :items="items" />
</template>

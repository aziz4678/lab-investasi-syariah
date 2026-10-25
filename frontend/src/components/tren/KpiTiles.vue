<script setup>
import { computed } from "vue";
import { persen } from "@/utils/format";
import Stats from "@/components/common/Stats.vue";

const props = defineProps({ r: Object });

const items = computed(() => {
  const r = props.r;
  if (!r) return [];
  return [
    { label: "Return per tahun", nilai: persen(r.cagr), nada: r.cagr >= 0 ? "naik" : "turun", ket: `beli-tahan ${persen(r.cagr_beli_tahan)} · IHSG ${persen(r.cagr_ihsg)}`,
      info: `CAGR: rata-rata pertumbuhan modal per tahun. Dihitung seperti paper: 10 posisi @ 10% ekuitas saat beli, harga pasar harian, dividen dipotong pajak.${r.cagr_metode_lama != null ? ` Cara lama (10% di bulan jual) memberi ${persen(r.cagr_metode_lama)}, terlalu optimis.` : ""}` },
    { label: "Penurunan terburuk", nilai: persen(r.dd_maks, 1, false), nada: "turun", ket: "dari puncak modal",
      info: "Seberapa dalam modal pernah turun dari titik tertingginya sebelum pulih." },
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

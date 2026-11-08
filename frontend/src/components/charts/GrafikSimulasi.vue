<script setup>
import { computed } from "vue";
import { Line } from "vue-chartjs";
import { pakaiTema } from "@/composables/tema";
import { opsiDasar, warna, alfa } from "@/utils/chart";
import { rupiahRingkas } from "@/utils/format";

const props = defineProps({ seri: Array, modal: Number, tinggi: { type: Number, default: 260 } });
const tema = pakaiTema();
const BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
const labelBulan = (s) => `${BULAN[Number(s.slice(5, 7)) - 1]} ${s.slice(0, 4)}`;

const data = computed(() => {
  tema.value;
  const nilai = warna("--series-1");
  const daya = warna("--series-2");
  return {
    labels: props.seri.map((x) => labelBulan(x.bulan)),
    datasets: [
      { label: "Nilai modal (rupiah hari itu)", data: props.seri.map((x) => x.nilai), borderColor: nilai, backgroundColor: alfa(nilai, 0.1), fill: true, borderWidth: 2.5, pointRadius: 0, tension: 0.2 },
      { label: "Daya beli modal (rupiah saat mulai)", data: props.seri.map((x) => x.daya_beli), borderColor: daya, borderWidth: 2, borderDash: [6, 4], pointRadius: 0, tension: 0.2 },
      { label: "Modal awal", data: props.seri.map(() => props.modal), borderColor: warna("--text-muted"), borderWidth: 1, borderDash: [2, 4], pointRadius: 0, pointHoverRadius: 0 },
    ],
  };
});

const opsi = computed(() => {
  tema.value;
  const o = opsiDasar();
  o.interaction = { mode: "index", intersect: false };
  o.scales.x.grid = { display: false };
  o.scales.x.ticks = { ...o.scales.x.ticks, maxTicksLimit: 8, autoSkip: true, maxRotation: 0 };
  o.scales.y.grid = { color: warna("--grid") };
  o.scales.y.beginAtZero = true;
  o.scales.y.ticks.callback = (v) => rupiahRingkas(v);
  o.plugins.legend = { display: true, position: "bottom", labels: { color: warna("--text-secondary"), usePointStyle: true, boxWidth: 8, padding: 14 } };
  o.plugins.tooltip.callbacks = { label: (c) => ` ${c.dataset.label}  ${rupiahRingkas(c.parsed.y)}` };
  return o;
});
</script>

<template>
  <div :style="{ height: `${tinggi}px` }"><Line :data="data" :options="opsi" /></div>
</template>

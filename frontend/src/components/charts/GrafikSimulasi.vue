<script setup>
import { computed } from "vue";
import { Line } from "vue-chartjs";
import { pakaiTema } from "@/composables/tema";
import { opsiDasar, warna, alfa } from "@/utils/chart";
import { rupiahRingkas } from "@/utils/format";

const props = defineProps({ tahun: Array, modal: Number, tinggi: { type: Number, default: 260 } });
const tema = pakaiTema();

const data = computed(() => {
  tema.value;
  const utama = warna("--series-1");
  const buruk = warna("--series-4");
  const rp = (k) => props.tahun.map((x) => x[k] * props.modal);
  return {
    labels: props.tahun.map((x) => (x.tahun === 0 ? "Sekarang" : `Th ${x.tahun}`)),
    datasets: [
      { label: "Kondisi baik (1 dari 10)", data: rp("daya_p90"), borderColor: alfa(utama, 0.35), borderWidth: 1, pointRadius: 0, tension: 0.25 },
      { label: "Rentang kemungkinan", data: rp("daya_p10"), borderColor: "transparent", backgroundColor: alfa(utama, 0.14), fill: "-1", pointRadius: 0, tension: 0.25 },
      { label: "Biasanya", data: rp("daya_p50"), borderColor: utama, borderWidth: 2.5, pointRadius: 2, tension: 0.25 },
      { label: "Kondisi buruk (1 dari 10)", data: rp("daya_p10"), borderColor: buruk, borderWidth: 2, borderDash: [6, 4], pointRadius: 0, tension: 0.25 },
      { label: "Modal awal", data: props.tahun.map(() => props.modal), borderColor: warna("--text-muted"), borderWidth: 1, borderDash: [2, 4], pointRadius: 0, pointHoverRadius: 0 },
    ],
  };
});

const opsi = computed(() => {
  tema.value;
  const o = opsiDasar();
  o.scales.x.grid = { display: false };
  o.scales.x.ticks = { ...o.scales.x.ticks, autoSkip: true, maxTicksLimit: 11 };
  o.scales.y.grid = { color: warna("--grid") };
  o.scales.y.beginAtZero = props.tahun.some((x) => x.daya_p10 < 0.5);
  o.scales.y.ticks.callback = (v) => (Math.abs(v) >= 1e6 && Math.abs(v) < 1e11 ? `Rp${(v / 1e6).toLocaleString("id-ID", { maximumFractionDigits: 0 })} jt` : rupiahRingkas(v));
  o.plugins.legend = { display: true, position: "bottom", labels: { color: warna("--text-secondary"), usePointStyle: true, boxWidth: 8, padding: 14, filter: (l) => l.text !== "Rentang kemungkinan" } };
  o.plugins.tooltip.filter = (c) => c.dataset.label !== "Rentang kemungkinan";
  o.plugins.tooltip.callbacks = { label: (c) => ` ${c.dataset.label}  ${rupiahRingkas(c.parsed.y)}` };
  return o;
});
</script>

<template>
  <div :style="{ height: `${tinggi}px` }"><Line :data="data" :options="opsi" /></div>
</template>

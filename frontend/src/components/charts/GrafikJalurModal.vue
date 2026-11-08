<script setup>
import { computed } from "vue";
import { Line } from "vue-chartjs";
import { pakaiTema } from "@/composables/tema";
import { opsiDasar, warna, alfa } from "@/utils/chart";

const props = defineProps({ tahun: Array, tinggi: { type: Number, default: 240 } });
const tema = pakaiTema();
const persenModal = (v) => `${(v * 100).toLocaleString("id-ID", { maximumFractionDigits: 1 })}%`;

const data = computed(() => {
  tema.value;
  const label = props.tahun.map((x) => (x.tahun === 0 ? "Awal" : `Th ${x.tahun}`));
  const biasa = warna("--series-1");
  const sial = warna("--series-3");
  return {
    labels: label,
    datasets: [
      { label: "Biasanya (median)", data: props.tahun.map((x) => x.median), borderColor: biasa, backgroundColor: alfa(biasa, 0.12), borderWidth: 2.5, pointRadius: 3, tension: 0.25 },
      { label: "Paling sial", data: props.tahun.map((x) => x.terburuk), borderColor: sial, borderDash: [6, 4], borderWidth: 2, pointRadius: 3, tension: 0.25 },
      { label: "Modal awal", data: props.tahun.map(() => 1), borderColor: warna("--text-muted"), borderWidth: 1, borderDash: [2, 4], pointRadius: 0, pointHoverRadius: 0 },
    ],
  };
});

const opsi = computed(() => {
  tema.value;
  const o = opsiDasar();
  o.scales.x.grid = { display: false };
  o.scales.y.grid = { color: warna("--grid") };
  o.scales.y.ticks.callback = persenModal;
  o.plugins.legend = { display: true, position: "bottom", labels: { color: warna("--text-secondary"), usePointStyle: true, boxWidth: 8, padding: 14 } };
  o.plugins.tooltip.callbacks = { label: (c) => ` ${c.dataset.label}  ${persenModal(c.parsed.y)}` };
  return o;
});
</script>

<template>
  <div :style="{ height: `${tinggi}px` }"><Line :data="data" :options="opsi" /></div>
</template>

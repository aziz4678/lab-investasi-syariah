<script setup>
import { computed } from "vue";
import { Bar } from "vue-chartjs";
import { pakaiTema } from "@/composables/tema";
import { opsiDasar, warna, alfa } from "@/utils/chart";

const props = defineProps({ label: Array, nilai: Array, arah: Array, rata: Number, format: Function, tinggi: { type: Number, default: 200 }, nama: { type: String, default: "Nilai" } });
const tema = pakaiTema();

const data = computed(() => {
  tema.value;
  const w = warna("--series-1");
  const n = props.nilai.length;
  const warnaBatang = (i) => (props.arah ? warna(props.arah[i] > 0 ? "--naik" : props.arah[i] < 0 ? "--turun" : "--text-muted") : w);
  const ds = [{
    type: "bar", label: props.nama, data: props.nilai, borderRadius: 4, borderSkipped: false, maxBarThickness: 14, categoryPercentage: 0.9, barPercentage: 0.8,
    backgroundColor: props.nilai.map((_, i) => alfa(warnaBatang(i), i === n - 1 ? 1 : 0.55)), hoverBackgroundColor: props.nilai.map((_, i) => warnaBatang(i)), order: 2,
  }];
  if (props.rata) {
    ds.push({ type: "line", label: "Rata-rata 20 hari", data: props.nilai.map(() => props.rata), borderColor: warna("--series-3"), borderDash: [5, 4],
      borderWidth: 1.5, pointRadius: 0, pointHoverRadius: 0, order: 1 });
  }
  return { labels: props.label, datasets: ds };
});

const opsi = computed(() => {
  tema.value;
  const o = opsiDasar();
  o.scales.x.grid = { display: false };
  o.scales.y.grid = { color: warna("--grid") };
  if (props.format) {
    o.scales.y.ticks.callback = props.format;
    o.plugins.tooltip.callbacks = {
      label: (c) => ` ${c.dataset.label}  ${props.format(c.parsed.y)}`,
      afterBody: (it) => (props.arah && it.length ? `IHSG ${props.arah[it[0].dataIndex] > 0 ? "naik" : props.arah[it[0].dataIndex] < 0 ? "turun" : "tetap"}` : ""),
    };
  }
  return o;
});
</script>

<template>
  <div :style="{ height: `${tinggi}px` }"><Bar :data="data" :options="opsi" /></div>
</template>

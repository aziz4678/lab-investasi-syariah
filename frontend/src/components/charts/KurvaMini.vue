<script setup>
import { computed } from "vue";
import { Line } from "vue-chartjs";
import { pakaiTema } from "@/composables/tema";
import { opsiDasar, warna, gradien } from "@/utils/chart";

const props = defineProps({ label: Array, nilai: Array, pembanding: Array, format: Function, tinggi: { type: Number, default: 220 }, namaNilai: { type: String, default: "Strategi" }, namaPembanding: { type: String, default: "IHSG" } });
const tema = pakaiTema();

const data = computed(() => {
  tema.value;
  const ds = [{
    label: props.namaNilai, data: props.nilai, borderColor: warna("--series-1"), pointBackgroundColor: warna("--series-1"), pointHoverBorderColor: warna("--surface-1"),
    backgroundColor: gradien("--series-1"), fill: "origin", borderWidth: 2.5, pointRadius: 0, tension: 0.4, cubicInterpolationMode: "monotone",
  }];
  if (props.pembanding) {
    ds.push({ label: props.namaPembanding, data: props.pembanding, borderColor: warna("--series-3"), pointBackgroundColor: warna("--series-3"),
      pointHoverBorderColor: warna("--surface-1"), borderDash: [5, 4], borderWidth: 1.5, pointRadius: 0, tension: 0.4, cubicInterpolationMode: "monotone" });
  }
  return { labels: props.label, datasets: ds };
});

const opsi = computed(() => {
  tema.value;
  const o = opsiDasar();
  if (props.format) {
    o.scales.y.ticks.callback = props.format;
    o.plugins.tooltip.callbacks = { label: (c) => ` ${c.dataset.label}  ${props.format(c.parsed.y)}` };
  }
  return o;
});
</script>

<template>
  <div :style="{ height: `${tinggi}px` }"><Line :data="data" :options="opsi" /></div>
</template>

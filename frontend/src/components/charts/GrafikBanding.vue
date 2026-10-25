<script setup>
import { computed } from "vue";
import { Line } from "vue-chartjs";
import { pakaiTema } from "@/composables/tema";
import { opsiDasar, warna } from "@/utils/chart";

const props = defineProps({ label: Array, seri: Object, warnaSeri: Array, tinggi: { type: Number, default: 300 } });
const tema = pakaiTema();

const data = computed(() => {
  tema.value;
  return {
    labels: props.label,
    datasets: Object.entries(props.seri || {}).map(([k, v], i) => ({
      label: k, data: v, borderColor: warna(props.warnaSeri[i]), backgroundColor: warna(props.warnaSeri[i]),
      pointHoverBorderColor: warna("--surface-1"), borderWidth: 2, pointRadius: 0, pointHoverRadius: 4, tension: 0.25, fill: false,
    })),
  };
});

const opsi = computed(() => {
  tema.value;
  const o = opsiDasar();
  o.animation = false;
  o.interaction = { mode: "index", intersect: false };
  o.scales.y.ticks.callback = (v) => v.toLocaleString("id-ID");
  o.plugins.tooltip.callbacks = { label: (c) => ` ${c.dataset.label}  ${c.parsed.y.toLocaleString("id-ID", { maximumFractionDigits: 1 })}` };
  return o;
});
</script>

<template>
  <div :style="{ height: `${tinggi}px` }"><Line :data="data" :options="opsi" /></div>
</template>

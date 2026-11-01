<script setup>
import { computed } from "vue";
import { Scatter } from "vue-chartjs";
import { pakaiTema } from "@/composables/tema";
import { opsiDasar, warna, alfa } from "@/utils/chart";

const props = defineProps({ trade: Array, tinggi: { type: Number, default: 320 } });
const tema = pakaiTema();

const data = computed(() => {
  tema.value;
  const seri = (nama, w, gaya, f) => ({
    label: nama, data: props.trade.filter(f).map((t) => ({ x: t.h, y: t.n, t })), pointStyle: gaya,
    backgroundColor: alfa(warna(w), 0.55), borderColor: warna("--surface-1"), borderWidth: 1, pointRadius: 4.5, pointHoverRadius: 7,
  });
  return {
    datasets: [
      seri("Take profit (untung)", "--naik", "circle", (t) => t.n > 0),
      seri("Cut loss (rugi)", "--turun", "triangle", (t) => t.n <= 0),
    ],
  };
});

const opsi = computed(() => {
  tema.value;
  const o = opsiDasar();
  o.interaction = { mode: "nearest", intersect: true };
  o.scales.x = { ...o.scales.x, type: "linear", grid: { display: false }, title: { display: true, text: "Lama dipegang (hari bursa)", color: warna("--text-muted"), font: { size: 11 } } };
  o.scales.y = { ...o.scales.y, grid: { color: (k) => (k.tick.value === 0 ? warna("--axis") : warna("--grid")) }, title: { display: true, text: "Hasil bersih per trade", color: warna("--text-muted"), font: { size: 11 } } };
  o.scales.y.ticks.callback = (v) => `${v > 0 ? "+" : ""}${v}%`;
  o.plugins.tooltip.callbacks = {
    title: (it) => `${it[0].raw.t.t} · sinyal ${it[0].raw.t.tgl}`,
    label: (k) => ` ${k.raw.t.n > 0 ? "+" : ""}${k.raw.t.n.toFixed(1).replace(".", ",")}% dalam ${k.raw.t.h} hari bursa`,
  };
  return o;
});
</script>

<template>
  <div>
    <div class="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-2">
      <span class="inline-flex items-center gap-1.5"><span class="h-2.5 w-2.5 rounded-full bg-naik" />Take profit (untung)</span>
      <span class="inline-flex items-center gap-1.5"><span class="h-0 w-0 border-x-[5px] border-b-[9px] border-x-transparent border-b-turun" />Cut loss (rugi)</span>
    </div>
    <div :style="{ height: `${tinggi}px` }"><Scatter :data="data" :options="opsi" /></div>
  </div>
</template>

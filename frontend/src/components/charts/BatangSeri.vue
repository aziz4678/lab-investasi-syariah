<script setup>
import { computed } from "vue";
import { Bar } from "vue-chartjs";
import { pakaiTema } from "@/composables/tema";
import { opsiDasar, warna } from "@/utils/chart";

const props = defineProps({
  label: Array, seri: Array, tumpuk: Boolean, mendatar: Boolean, format: Function, satuan: { type: String, default: "" },
  tinggi: { type: Number, default: 220 }, legenda: Boolean,
});
const tema = pakaiTema();

const data = computed(() => {
  tema.value;
  return {
    labels: props.label,
    datasets: props.seri.map((s) => ({
      label: s.nama, data: s.data, backgroundColor: Array.isArray(s.warna) ? s.warna.map(warna) : warna(s.warna),
      borderRadius: 4, borderSkipped: false, borderColor: warna("--surface-1"), borderWidth: props.tumpuk ? { top: 2 } : 0,
      maxBarThickness: props.mendatar ? 16 : 34, categoryPercentage: 0.82, barPercentage: 0.9,
    })),
  };
});

const opsi = computed(() => {
  tema.value;
  const o = opsiDasar();
  const nilai = props.mendatar ? "x" : "y";
  const kategori = props.mendatar ? "y" : "x";
  o.indexAxis = props.mendatar ? "y" : "x";
  o.interaction = { mode: "index", intersect: false, axis: kategori };
  o.scales[kategori] = { ...o.scales[kategori], stacked: props.tumpuk, grid: { display: false }, ticks: { ...o.scales.x.ticks, autoSkip: false, maxRotation: props.mendatar ? 0 : 50 } };
  o.scales[nilai] = { ...o.scales[nilai], stacked: props.tumpuk, grid: { color: warna("--grid") }, ticks: { color: warna("--text-muted"), padding: 8, maxTicksLimit: 6, callback: (v) => (props.format ? props.format(v) : `${v}${props.satuan}`) } };
  if (props.mendatar) o.scales.x.border = { display: false };
  o.plugins.tooltip.callbacks = { label: (k) => ` ${k.dataset.label}  ${props.format ? props.format(k.raw) : `${k.raw}${props.satuan}`}` };
  return o;
});
</script>

<template>
  <div>
    <div v-if="legenda" class="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-2">
      <span v-for="s in seri" :key="s.nama" class="inline-flex items-center gap-1.5">
        <span class="h-2.5 w-2.5 rounded-sm" :style="{ background: `var(${Array.isArray(s.warna) ? s.warna[0] : s.warna})` }" />{{ s.nama }}
      </span>
    </div>
    <div :style="{ height: `${tinggi}px` }"><Bar :data="data" :options="opsi" /></div>
  </div>
</template>

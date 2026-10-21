<script setup>
import { computed } from "vue";
import { Line } from "vue-chartjs";
import { opsiDasar, warna, pakaiTema, gradien, rupiah, persen, kelasPersen } from "../util.js";
import Panel from "./Panel.vue";

const props = defineProps({ ekuitas: Array, modal: Number });
const tema = pakaiTema();
const SERI = [
  { label: "Ekuitas paper", kunci: "ekuitas", var: "--series-1", lebar: 2.5, putus: [], isi: true },
  { label: "IHSG (disetarakan)", kunci: "ihsg", var: "--series-3", lebar: 1.5, putus: [5, 4], isi: false },
];

const data = computed(() => {
  tema.value;
  const e = props.ekuitas || [];
  return {
    labels: e.map((x) => x.tgl.slice(0, 10)),
    datasets: SERI.map((s) => ({
      label: s.label, data: e.map((x) => x[s.kunci]), borderColor: warna(s.var), pointBackgroundColor: warna(s.var),
      pointHoverBorderColor: warna("--surface-1"), backgroundColor: s.isi ? gradien(s.var) : "transparent", fill: s.isi ? "origin" : false,
      borderWidth: s.lebar, borderDash: s.putus, pointRadius: 0, tension: 0.4, cubicInterpolationMode: "monotone",
    })),
  };
});

const opsi = computed(() => {
  tema.value;
  const o = opsiDasar();
  o.scales.y.ticks.callback = (v) => `${(v / 1e6).toFixed(0)} jt`;
  o.plugins.tooltip.callbacks = { label: (c) => ` ${c.dataset.label}  Rp${rupiah(Math.round(c.parsed.y))} (${persen((c.parsed.y / props.modal - 1) * 100)})` };
  return o;
});

const dataDd = computed(() => {
  tema.value;
  const e = props.ekuitas || [];
  return {
    labels: e.map((x) => x.tgl.slice(0, 10)),
    datasets: [{ label: "Penurunan", data: e.map((x) => x.drawdown), borderColor: warna("--turun"), pointBackgroundColor: warna("--turun"),
      pointHoverBorderColor: warna("--surface-1"), backgroundColor: gradien("--turun", 0.05), fill: "origin", borderWidth: 2, pointRadius: 0,
      tension: 0.4, cubicInterpolationMode: "monotone" }],
  };
});

const opsiDd = computed(() => {
  tema.value;
  const o = opsiDasar();
  o.scales.y.max = 0;
  o.scales.y.ticks.callback = (v) => `${v}%`;
  o.scales.y.ticks.maxTicksLimit = 3;
  o.scales.x.ticks.display = false;
  o.plugins.tooltip.callbacks = { label: (c) => ` ${c.parsed.y.toFixed(1)}% dari puncak` };
  return o;
});

const akhir = computed(() => {
  const e = props.ekuitas || [];
  const x = e[e.length - 1];
  return x ? SERI.filter((s) => x[s.kunci] != null).map((s) => ({ ...s, nilai: x[s.kunci] })) : [];
});
</script>

<template>
  <Panel judul="Ekuitas paper" ket="Kas + posisi di harga penutupan · IHSG disetarakan ke modal awal">
    <template #aksi>
      <span v-for="s in akhir" :key="s.label" class="inline-flex items-center gap-2 rounded-full bg-surface-2 py-1.5 pr-3 pl-2.5 text-xs text-ink-2">
        <i class="h-2 w-2 rounded-full" :style="{ background: `var(${s.var})` }"></i>{{ s.label }}
        <b class="font-medium text-ink tabular-nums" :class="kelasPersen((s.nilai / modal - 1) * 100)">{{ persen((s.nilai / modal - 1) * 100) }}</b>
      </span>
    </template>
    <div class="h-[260px]"><Line :data="data" :options="opsi" /></div>
    <div class="label mt-5 mb-1">Penurunan dari puncak</div>
    <div class="h-[100px]"><Line :data="dataDd" :options="opsiDd" /></div>
  </Panel>
</template>

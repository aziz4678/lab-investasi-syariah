<script setup>
import { computed } from "vue";
import { Bar, Line } from "vue-chartjs";
import { opsiDasar, warna, alfa, pakaiTema } from "../util.js";

const props = defineProps({ g: Object, tinggi: { type: Number, default: 220 } });
const tema = pakaiTema();
const SERI = ["--series-1", "--series-2", "--series-4"];
const PEMBANDING = /pembanding|beli-tahan|ihsg/i;

const banyak = computed(() => props.g.seri.length > 1);
const satuan = computed(() => props.g.satuan ?? "");

function fmt(v, tanda = true) {
  if (v === null || v === undefined) return "—";
  const d = props.g.jenis === "kurva" ? 0 : !tanda ? (Math.abs(v) >= 10 || Number.isInteger(v) ? 0 : satuan.value === "%" ? 1 : 2) : Math.abs(v) < 10 && satuan.value !== "%" ? 2 : 1;
  const s = v.toLocaleString("id-ID", { minimumFractionDigits: d, maximumFractionDigits: d });
  return (tanda && v > 0 && props.g.jenis !== "kurva" ? "+" : "") + s + satuan.value;
}

const warnaSeri = (i) => warna(SERI[i % SERI.length]);

const legenda = computed(() => {
  tema.value;
  return props.g.seri.map((s, i) => ({ nama: s.nama, w: warnaSeri(i), putus: props.g.jenis === "kurva" && i > 0 && PEMBANDING.test(s.nama) }));
});

const data = computed(() => {
  tema.value;
  const g = props.g;
  if (g.jenis === "kurva") {
    return {
      labels: g.label,
      datasets: g.seri.map((s, i) => ({
        label: s.nama, data: s.data, borderColor: warnaSeri(i), backgroundColor: warnaSeri(i), borderWidth: 2,
        borderDash: i > 0 && PEMBANDING.test(s.nama) ? [5, 4] : [], pointRadius: 0, pointHoverRadius: 4,
        pointHoverBorderColor: warna("--surface-1"), tension: 0.2, fill: false,
      })),
    };
  }
  const naik = warna("--naik");
  const turun = warna("--turun");
  const abu = warna("--text-muted");
  return {
    labels: g.label,
    datasets: g.seri.map((s, i) => {
      const w = banyak.value ? s.data.map(() => warnaSeri(i)) : s.data.map((v, j) => (PEMBANDING.test(g.label[j]) ? abu : v >= 0 ? naik : turun));
      return {
        label: s.nama, data: s.data, backgroundColor: w.map((x) => alfa(x, 0.85)), hoverBackgroundColor: w, borderRadius: 4, borderSkipped: false,
        maxBarThickness: 28, categoryPercentage: 0.72, barPercentage: 0.86, borderColor: warna("--surface-1"), borderWidth: banyak.value ? 1 : 0,
      };
    }),
  };
});

const opsi = computed(() => {
  tema.value;
  const o = opsiDasar();
  o.animation = false;
  o.scales.y.grid = { color: warna("--grid") };
  o.scales.x.grid = { display: false };
  o.scales.y.ticks.callback = (v) => fmt(v, false);
  if (props.g.jenis === "kurva") o.scales.x.ticks.maxTicksLimit = 6;
  else o.interaction = { mode: "index", intersect: false };
  o.plugins.tooltip.callbacks = { label: (c) => ` ${c.dataset.label}  ${fmt(c.parsed.y)}` };
  return o;
});
</script>

<template>
  <figure class="m-0">
    <figcaption class="mb-2">
      <div class="text-[13px] font-medium">{{ g.judul }}</div>
      <div v-if="banyak" class="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-2">
        <span v-for="l in legenda" :key="l.nama" class="inline-flex items-center gap-1.5">
          <span v-if="g.jenis === 'kurva'" class="inline-block h-0 w-4 border-t-2" :style="{ borderColor: l.w, borderTopStyle: l.putus ? 'dashed' : 'solid' }"></span>
          <span v-else class="inline-block h-2.5 w-2.5 rounded-[3px]" :style="{ background: l.w }"></span>
          {{ l.nama }}
        </span>
      </div>
    </figcaption>
    <div :style="{ height: `${tinggi}px` }">
      <Line v-if="g.jenis === 'kurva'" :data="data" :options="opsi" />
      <Bar v-else :data="data" :options="opsi" />
    </div>
    <p v-if="g.ket" class="m-0 mt-2 text-xs text-muted">{{ g.ket }}</p>
  </figure>
</template>

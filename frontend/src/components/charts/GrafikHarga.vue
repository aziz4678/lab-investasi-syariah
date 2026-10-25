<script setup>
import { computed } from "vue";
import { Line, Bar } from "vue-chartjs";
import { pakaiTema } from "@/composables/tema";
import { opsiDasar, warna, gradien, alfa } from "@/utils/chart";
import { rupiah, ringkas } from "@/utils/format";

const props = defineProps({ grafik: Object, trade: Array, mulai: Number, tinggi: { type: Number, default: 340 } });
const emit = defineEmits(["arah"]);
const tema = pakaiTema();
const LEBAR_Y = 64;

const potong = computed(() => {
  const g = props.grafik;
  const i = Math.max(0, props.mulai || 0);
  const tgl = g.tgl.slice(i);
  const idx = new Map(tgl.map((t, j) => [t, j]));
  const beli = new Array(tgl.length).fill(null);
  const jual = new Array(tgl.length).fill(null);
  for (const t of props.trade || []) {
    if (idx.has(t.tgl_beli)) beli[idx.get(t.tgl_beli)] = t.harga_beli;
    if (t.tgl_jual && idx.has(t.tgl_jual)) jual[idx.get(t.tgl_jual)] = t.harga_jual;
  }
  return { i, tgl, close: g.close.slice(i), maks: g.maks250.slice(i), stop: g.stop.slice(i), volume: g.volume.slice(i), beli, jual };
});

function sumbu(o) {
  o.scales.y.afterFit = (s) => { s.width = LEBAR_Y; };
  o.scales.x.ticks.maxTicksLimit = 8;
  o.onHover = (_, el) => emit("arah", el.length ? potong.value.i + el[0].index : null);
  return o;
}

const data = computed(() => {
  tema.value;
  const p = potong.value;
  const titikGaris = p.tgl.length <= 30 ? 3 : 0;
  const titik = (label, isi, w, gaya) => ({
    label, data: isi, order: 0, showLine: false, pointStyle: gaya, pointRadius: 6, pointHoverRadius: 8,
    pointBackgroundColor: w, pointBorderColor: warna("--surface-1"), pointBorderWidth: 2, borderColor: w, backgroundColor: w,
  });
  return {
    labels: p.tgl,
    datasets: [
      { label: "Close", data: p.close, order: 3, borderColor: warna("--series-1"), backgroundColor: gradien("--series-1", 0.22), fill: "origin",
        borderWidth: 2, pointRadius: titikGaris, pointHoverBorderColor: warna("--surface-1"), pointBackgroundColor: warna("--series-1"), tension: 0.2 },
      { label: "Tertinggi 52 minggu", data: p.maks, order: 2, borderColor: warna("--series-3"), borderDash: [5, 4], borderWidth: 1.5,
        pointRadius: 0, pointBackgroundColor: warna("--series-3"), pointHoverBorderColor: warna("--surface-1"), stepped: true },
      { label: "Trailing stop", data: p.stop, order: 1, borderColor: warna("--turun"), borderWidth: 1.75, pointRadius: 0, spanGaps: false,
        pointBackgroundColor: warna("--turun"), pointHoverBorderColor: warna("--surface-1"), stepped: true },
      titik("Beli", p.beli, warna("--naik"), "triangle"),
      titik("Jual", p.jual, warna("--turun"), "rectRot"),
    ],
  };
});

const opsi = computed(() => {
  tema.value;
  const o = sumbu(opsiDasar());
  o.animation = false;
  o.scales.y.grace = "4%";
  o.scales.y.ticks.callback = (v) => rupiah(v);
  o.plugins.tooltip.filter = (c) => c.parsed.y !== null && c.parsed.y !== undefined;
  o.plugins.tooltip.callbacks = { label: (c) => ` ${c.dataset.label}  ${rupiah(c.parsed.y)}` };
  return o;
});

const dataVol = computed(() => {
  tema.value;
  const p = potong.value;
  return { labels: p.tgl, datasets: [{ label: "Volume (lot)", data: p.volume.map((v) => (v == null ? null : v / 100)),
    backgroundColor: alfa(warna("--series-3"), 0.55), hoverBackgroundColor: warna("--series-1"), borderRadius: 3, borderSkipped: false,
    barPercentage: 0.8, categoryPercentage: 1 }] };
});

const opsiVol = computed(() => {
  tema.value;
  const o = sumbu(opsiDasar());
  o.animation = false;
  o.scales.x.display = false;
  o.scales.x.grid.display = false;
  o.scales.y.ticks.maxTicksLimit = 2;
  o.scales.y.ticks.callback = (v) => ringkas(v);
  o.plugins.tooltip.callbacks = { label: (c) => ` Volume  ${rupiah(c.parsed.y)} lot` };
  return o;
});
</script>

<template>
  <div @mouseleave="emit('arah', null)">
    <div :style="{ height: `${tinggi}px` }"><Line :data="data" :options="opsi" /></div>
    <div class="mt-3 pl-1 text-[11px] text-muted">Volume (lot)</div>
    <div class="h-[96px]"><Bar :data="dataVol" :options="opsiVol" /></div>
  </div>
</template>

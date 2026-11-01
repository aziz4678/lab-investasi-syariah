<script setup>
import { computed } from "vue";
import { Line } from "vue-chartjs";
import { pakaiTema } from "@/composables/tema";
import { opsiDasar, warna, alfa } from "@/utils/chart";

const props = defineProps({ c: Object, jenis: String, tinggi: { type: Number, default: 340 } });
const tema = pakaiTema();
const BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
const tgl = (s) => `${+s.slice(8, 10)} ${BULAN[+s.slice(5, 7) - 1]} ${s.slice(2, 4)}`;
const rp = (v) => (v == null ? "–" : `Rp${Math.round(v).toLocaleString("id-ID")}`);

const tanda = computed(() => {
  const { titik: t, nilai: n } = props.c;
  const jual = props.jenis === "tp" ? "--naik" : "--turun";
  return [
    { i: t.sinyal, y: n.close_sinyal, teks: "Sinyal", w: "--series-2", atas: true },
    { i: t.beli, y: n.harga_beli, teks: "Beli", w: "--text-primary", atas: false },
    { i: t.puncak, y: n.puncak, teks: "Puncak", w: "--naik", atas: true },
    { i: t.jual, y: n.harga_jual, teks: props.jenis === "tp" ? "Jual (TP)" : "Jual (CL)", w: jual, atas: false },
  ];
});

const pluginFase = {
  id: "fase",
  beforeDatasetsDraw(chart) {
    const { ctx, chartArea: a, scales } = chart;
    const { titik } = props.c;
    const x1 = scales.x.getPixelForValue(titik.beli);
    const x2 = scales.x.getPixelForValue(titik.jual);
    ctx.save();
    ctx.fillStyle = alfa(warna("--aksen"), 0.07);
    ctx.fillRect(x1, a.top, x2 - x1, a.bottom - a.top);
    ctx.fillStyle = warna("--text-muted");
    ctx.font = "500 11px Poppins, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(`Hold ${props.c.hari} hari bursa`, (x1 + x2) / 2, a.bottom - 8);
    ctx.textAlign = "left";
    ctx.fillText("Menunggu sinyal", a.left + 4, a.top + 12);
    ctx.restore();
  },
  afterDatasetsDraw(chart) {
    const { ctx, scales } = chart;
    ctx.save();
    ctx.font = "500 11px Poppins, sans-serif";
    for (const m of tanda.value) {
      const x = scales.x.getPixelForValue(m.i);
      const y = scales.y.getPixelForValue(m.y);
      ctx.beginPath();
      ctx.arc(x, y, 5, 0, Math.PI * 2);
      ctx.fillStyle = warna(m.w);
      ctx.strokeStyle = warna("--surface-1");
      ctx.lineWidth = 2;
      ctx.fill();
      ctx.stroke();
      const lebar = ctx.measureText(m.teks).width + 14;
      const ty = m.atas ? y - 24 : y + 10;
      ctx.fillStyle = warna("--surface-3");
      ctx.beginPath();
      ctx.roundRect(x - lebar / 2, ty, lebar, 18, 9);
      ctx.fill();
      ctx.fillStyle = warna("--text-primary");
      ctx.textAlign = "center";
      ctx.fillText(m.teks, x, ty + 13);
    }
    ctx.restore();
  },
};

const data = computed(() => {
  tema.value;
  const c = props.c;
  const beli = c.tgl.map((_, i) => (i >= c.titik.beli && i <= c.titik.jual ? c.nilai.harga_beli : null));
  return {
    labels: c.tgl,
    datasets: [
      { label: "Harga penutupan", data: c.close, borderColor: warna("--series-2"), borderWidth: 2, pointRadius: 0, tension: 0.15, order: 1 },
      { label: "Batas jual", data: c.stop, borderColor: warna("--series-4"), borderWidth: 2, pointRadius: 0, stepped: true, order: 2 },
      { label: "Tertinggi 250 hari sebelumnya", data: c.maks250, borderColor: warna("--series-3"), borderWidth: 1.5, borderDash: [5, 4], pointRadius: 0, stepped: true, order: 3 },
      { label: "Harga beli", data: beli, borderColor: warna("--text-muted"), borderWidth: 1, borderDash: [2, 3], pointRadius: 0, order: 4 },
    ],
  };
});

const opsi = computed(() => {
  tema.value;
  const o = opsiDasar();
  o.layout.padding = { top: 18, right: 8 };
  o.scales.x.ticks.callback = (_, i) => tgl(props.c.tgl[i]);
  o.scales.x.ticks.autoSkipPadding = 40;
  o.scales.x.grid = { display: false };
  o.scales.y.grid = { color: warna("--grid") };
  const semua = [...props.c.close, ...props.c.stop, ...props.c.maks250].filter((v) => v != null);
  const bawah = Math.min(...semua);
  const atas = Math.max(...semua);
  const langkah = 10 ** Math.floor(Math.log10(atas - bawah)) / 2;
  o.scales.y.min = Math.max(0, Math.floor((bawah - (atas - bawah) * 0.05) / langkah) * langkah);
  o.scales.y.max = Math.ceil((atas + (atas - bawah) * 0.1) / langkah) * langkah;
  o.scales.y.ticks.callback = (v) => Math.round(v).toLocaleString("id-ID");
  o.plugins.tooltip.callbacks = {
    title: (it) => tgl(props.c.tgl[it[0].dataIndex]),
    label: (k) => (k.parsed.y == null ? null : ` ${k.dataset.label}  ${rp(k.parsed.y)}`),
  };
  o.plugins.tooltip.filter = (k) => k.parsed.y != null;
  return o;
});

const LEGENDA = [
  ["--series-2", "Harga penutupan", ""],
  ["--series-4", "Batas jual", ""],
  ["--series-3", "Tertinggi 250 hari", "putus"],
  ["--text-muted", "Harga beli", "titik"],
];
</script>

<template>
  <div>
    <div class="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-2">
      <span v-for="[w, l, g] in LEGENDA" :key="l" class="inline-flex items-center gap-1.5">
        <span class="inline-block w-4 border-t-2" :class="g === 'putus' ? 'border-dashed' : g === 'titik' ? 'border-dotted' : ''" :style="{ borderColor: `var(${w})` }" />{{ l }}
      </span>
    </div>
    <div :style="{ height: `${tinggi}px` }"><Line :data="data" :options="opsi" :plugins="[pluginFase]" /></div>
  </div>
</template>

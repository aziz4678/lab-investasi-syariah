<script setup>
import { computed, ref, watch } from "vue";
import { Line } from "vue-chartjs";
import { pakaiTema } from "@/composables/tema";
import { opsiDasar, warna, gradien } from "@/utils/chart";
import { persen, ringkas, kelasPersen } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";

const props = defineProps({ ekuitas: Array, catatan: String });
const tema = pakaiTema();
let modalAwal = 100000000;
try {
  modalAwal = Number(localStorage.getItem("bt_modal")) || 100000000;
} catch {
  modalAwal = 100000000;
}
const modal = ref(modalAwal);
watch(modal, (v) => {
  try {
    localStorage.setItem("bt_modal", String(Number(v) || 0));
  } catch {
    return;
  }
});
const arah = ref(null);
const BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
const namaBulan = (b) => (b ? `${BULAN[Number(b.slice(5, 7)) - 1]} ${b.slice(0, 4)}` : "");
const SERI = [
  { label: "Follow Tren", kunci: "ekuitas", var: "--series-1", lebar: 2.5, putus: [], isi: true },
  { label: "Beli-tahan", kunci: "beli_tahan", var: "--series-2", lebar: 2, putus: [], isi: false },
  { label: "IHSG", kunci: "ihsg", var: "--series-3", lebar: 1.5, putus: [5, 4], isi: false },
];

const dataModal = computed(() => {
  tema.value;
  const e = props.ekuitas || [];
  return {
    labels: e.map((x) => x.bulan),
    datasets: SERI.map((s) => ({
      label: s.label, data: e.map((x) => x[s.kunci]), borderColor: warna(s.var), pointBackgroundColor: warna(s.var),
      pointHoverBorderColor: warna("--surface-1"), backgroundColor: s.isi ? gradien(s.var) : "transparent", fill: s.isi ? "origin" : false,
      borderWidth: s.lebar, borderDash: s.putus, pointRadius: 0, tension: 0.4, cubicInterpolationMode: "monotone",
    })),
  };
});

const opsiModal = computed(() => {
  tema.value;
  const o = opsiDasar();
  o.scales.y.ticks.callback = (v) => `${v.toFixed(1)}x`;
  o.plugins.tooltip.callbacks = { label: (c) => ` ${c.dataset.label}  ${c.parsed.y.toFixed(2)}x` };
  o.onHover = (_, el) => (arah.value = el.length ? el[0].index : null);
  return o;
});

const simulasi = computed(() => {
  const e = props.ekuitas || [];
  if (!e.length) return null;
  const i = arah.value ?? e.length - 1;
  const x = e[i];
  const m = Number(modal.value) || 0;
  const tahun = (i + 1) / 12;
  return {
    dari: namaBulan(e[0].bulan), sampai: namaBulan(x.bulan), kursor: arah.value != null, tahun,
    seri: SERI.map((s) => {
      const v = x[s.kunci];
      return { ...s, nilai: m * v, total: (v - 1) * 100, cagr: tahun >= 1 && v > 0 ? (Math.pow(v, 1 / tahun) - 1) * 100 : null };
    }),
  };
});

const dataDd = computed(() => {
  tema.value;
  const e = props.ekuitas || [];
  return {
    labels: e.map((x) => x.bulan),
    datasets: [{ label: "Penurunan dari puncak", data: e.map((x) => x.drawdown), borderColor: warna("--turun"), pointBackgroundColor: warna("--turun"),
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
  return x ? SERI.map((s) => ({ ...s, nilai: x[s.kunci] })) : [];
});
</script>

<template>
  <Panel judul="Pertumbuhan modal" :ket="`Modal awal = 1x · 10 posisi @ 10% ekuitas saat beli · harga pasar akhir bulan · dihitung sama seperti paper${catatan ? ` · ${catatan}` : ''}`"
    info="Strategi dibandingkan dengan membeli semua saham syariah likuid lalu didiamkan (beli-tahan), dan IHSG.">
    <template #aksi>
      <span v-for="s in akhir" :key="s.label" class="inline-flex items-center gap-2 rounded-full bg-surface-2 py-1.5 pr-3 pl-2.5 text-xs text-ink-2">
        <i class="h-2 w-2 rounded-full" :style="{ background: `var(${s.var})` }"></i>{{ s.label }}
        <b class="font-medium text-ink tabular-nums">{{ s.nilai.toFixed(2) }}x</b>
      </span>
    </template>
    <div v-if="simulasi" class="mb-5 rounded-2xl bg-surface-2 px-5 py-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <label class="flex items-center gap-2 text-[13px] text-ink-2">
          Simulasi modal Rp
          <input v-model.number="modal" type="number" min="0" step="1000000" class="!h-9 w-40 !border !border-garis !bg-surface tabular-nums" />
        </label>
        <span class="text-xs text-muted">{{ simulasi.dari }} → <b class="font-medium text-ink">{{ simulasi.sampai }}</b> · {{ simulasi.tahun.toFixed(1).replace(".", ",") }} tahun{{ simulasi.kursor ? " · ikut kursor" : " · geser kursor di grafik" }}</span>
      </div>
      <div class="mt-4 grid gap-4 sm:grid-cols-3">
        <div v-for="s in simulasi.seri" :key="s.label" class="min-w-0">
          <div class="flex items-center gap-2 text-xs text-muted"><i class="h-2 w-2 rounded-full" :style="{ background: `var(${s.var})` }"></i>{{ s.label }}</div>
          <div class="mt-1 text-[22px] leading-tight font-medium tracking-tight tabular-nums" :class="s.isi ? '' : 'text-ink-2'">Rp{{ ringkas(Math.round(s.nilai)) }}</div>
          <div class="mt-0.5 text-xs tabular-nums">
            <span class="font-medium" :class="kelasPersen(s.total)">{{ persen(s.total, 1) }}</span><span class="text-muted"> total</span>
            <template v-if="s.cagr != null"> · <span :class="kelasPersen(s.cagr)">{{ persen(s.cagr, 1) }}</span><span class="text-muted">/tahun</span></template>
          </div>
        </div>
      </div>
    </div>
    <div class="h-[300px]" @mouseleave="arah = null"><Line :data="dataModal" :options="opsiModal" /></div>
    <div class="label mt-5 mb-1">Penurunan dari puncak</div>
    <div class="h-[110px]"><Line :data="dataDd" :options="opsiDd" /></div>
  </Panel>
</template>

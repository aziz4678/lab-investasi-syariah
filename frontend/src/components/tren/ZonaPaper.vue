<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { Line } from "vue-chartjs";
import { ChevronDown } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { pakaiTema } from "@/composables/tema";
import { opsiDasar, warna, alfa } from "@/utils/chart";
import { persen } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import TeksWarna from "@/components/common/TeksWarna.vue";
import Kerangka from "@/components/common/Kerangka.vue";

const props = defineProps({ muatUlang: Number });
const z = ref(null);
const bukaAturan = ref(false);
const tema = pakaiTema();

async function muat() {
  z.value = await ambil("paper/zona").catch(() => ({ ada: false }));
}
onMounted(muat);
watch(() => props.muatUlang, muat);

const ZONA = {
  normal: { l: "Normal", k: "bg-naik-bg text-naik", t: "Hasil paper masih dalam rentang wajar backtest." },
  waspada: { l: "Waspada", k: "bg-kuning-bg text-kuning", t: "Hasil paper di luar 95% rentang backtest. Tetap jalankan aturan, jangan diubah." },
  gagal: { l: "Gagal", k: "bg-turun-bg text-turun", t: "Sesuai aturan yang dikunci: Follow Tren tidak dilanjutkan ke uang asli." },
  belum: { l: "Belum dinilai", k: "bg-surface-2 text-muted", t: "Penilaian mulai setelah ada hari bursa yang diproses." },
};

const hari = computed(() => z.value?.paper?.hari ?? 0);
const jangkau = computed(() => Math.min(z.value?.horizon || 500, Math.max(63, Math.ceil(hari.value * 1.6) + 10)));

const data = computed(() => {
  tema.value;
  if (!z.value?.ada) return null;
  const n = jangkau.value;
  const pita = (p) => [0, ...z.value.return[p].slice(0, n)];
  const label = Array.from({ length: n + 1 }, (_, i) => i);
  const s1 = warna("--series-1");
  const paper = z.value.paper ? z.value.paper.return : [];
  return {
    labels: label,
    datasets: [
      { label: "Persentil 95", data: pita("p95"), borderWidth: 0, pointRadius: 0, fill: "+4", backgroundColor: alfa(s1, 0.1), order: 5 },
      { label: "Persentil 75", data: pita("p75"), borderWidth: 0, pointRadius: 0, fill: "+2", backgroundColor: alfa(s1, 0.16), order: 5 },
      { label: "Median backtest", data: pita("p50"), borderColor: warna("--series-3"), borderDash: [5, 4], borderWidth: 1.5, pointRadius: 0, order: 3 },
      { label: "Persentil 25", data: pita("p25"), borderWidth: 0, pointRadius: 0, order: 5 },
      { label: "Persentil 5", data: pita("p5"), borderWidth: 0, pointRadius: 0, order: 5 },
      { label: "Batas gagal (persentil 1)", data: pita("p1"), borderColor: warna("--turun"), borderDash: [2, 3], borderWidth: 1.25, pointRadius: 0, order: 2 },
      { label: "Paper", data: paper, borderColor: warna("--series-2"), backgroundColor: warna("--series-2"), borderWidth: 2.5,
        pointRadius: paper.length < 30 ? 3 : 0, pointBorderColor: warna("--surface-1"), pointBorderWidth: 1.5, tension: 0.2, order: 1 },
    ],
  };
});

const opsi = computed(() => {
  tema.value;
  const o = opsiDasar();
  o.animation = false;
  o.scales.x.ticks.maxTicksLimit = 8;
  o.scales.x.ticks.callback = (v) => (v === 0 ? "mulai" : `hari ${v}`);
  o.scales.y.ticks.callback = (v) => `${v}%`;
  o.plugins.tooltip.filter = (c) => !c.dataset.label.startsWith("Persentil 25") && c.parsed.y != null;
  o.plugins.tooltip.callbacks = { title: (c) => `Hari bursa ke-${c[0].label}`, label: (c) => ` ${c.dataset.label}  ${persen(c.parsed.y)}` };
  return o;
});

const baris = computed(() => {
  const p = z.value?.paper;
  const b = z.value?.batas;
  if (!p || !b) return [];
  return [
    { l: "Return", v: persen(p.return.at(-1)), w: `wajar ≥ ${persen(b.ret_p5)} · gagal < ${persen(b.ret_p1)}`, k: p.hari >= 21 ? "" : "dinilai mulai hari ke-21" },
    { l: "Drawdown terdalam", v: persen(Math.min(...p.dd)), w: `wajar ≥ ${persen(b.dd_p5)} · gagal < ${persen(b.dd_p1)}` },
    { l: "Rugi beruntun", v: `${p.beruntun}x`, w: b.beruntun_p95 == null ? "belum ada trade selesai" : `wajar ≤ ${b.beruntun_p95}x · gagal > ${b.beruntun_p99}x` },
  ];
});
</script>

<template>
  <Kerangka v-if="z === null" panel jenis="grafik" :tinggi="240" />
  <Panel v-if="z?.ada" judul="Zona normal" :ket="`Rentang hasil wajar dari backtest, dikunci ${z.dibuat.slice(0, 10)} sebelum paper berjalan`"
    info="Dari 5000 simulasi ulang (bootstrap) kurva harian backtest 2020-2026 versi konservatif, dihitung dengan cara paper. Pita gelap = 50% hasil tengah, pita terang = 90%.">
    <template #aksi>
      <span class="chip !h-7 !px-3 !text-xs" :class="ZONA[z.zona].k">{{ ZONA[z.zona].l }}</span>
    </template>
    <p class="m-0 -mt-1 mb-4 text-[13px] text-ink-2">{{ ZONA[z.zona].t }}</p>
    <ul v-if="z.alasan.length" class="m-0 mb-4 list-disc space-y-1 pl-5 text-[13px]" :class="z.zona === 'gagal' ? 'text-turun' : 'text-kuning'">
      <li v-for="a in z.alasan" :key="a">{{ a }}</li>
    </ul>
    <div class="mb-4 grid gap-2 sm:grid-cols-3">
      <div v-for="b in baris" :key="b.l" class="rounded-2xl bg-surface-2 px-4 py-3">
        <div class="text-xs text-muted">{{ b.l }} · hari ke-{{ hari }}</div>
        <div class="mt-0.5 text-[17px] font-medium tabular-nums"><TeksWarna :teks="b.v" /></div>
        <div class="text-[11px] text-muted"><TeksWarna :teks="b.w" /><span v-if="b.k"> · {{ b.k }}</span></div>
      </div>
    </div>
    <div class="mb-3 flex flex-wrap gap-2 text-xs text-ink-2">
      <span class="inline-flex items-center gap-2 rounded-full bg-surface-2 px-3 py-1"><span class="h-0.5 w-4 rounded bg-s2"></span>Paper</span>
      <span class="inline-flex items-center gap-2 rounded-full bg-surface-2 px-3 py-1"><span class="h-2.5 w-4 rounded-sm bg-s1/20"></span>Rentang wajar 50% / 90%</span>
      <span class="inline-flex items-center gap-2 rounded-full bg-surface-2 px-3 py-1"><span class="w-4 border-t-2 border-dashed border-s3"></span>Median</span>
      <span class="inline-flex items-center gap-2 rounded-full bg-surface-2 px-3 py-1"><span class="w-4 border-t-2 border-dotted border-turun"></span>Batas gagal</span>
    </div>
    <div class="h-[280px]"><Line v-if="data" :data="data" :options="opsi" /></div>
    <button class="mt-4 inline-flex items-center gap-1 text-xs text-muted hover:text-ink" @click="bukaAturan = !bukaAturan">
      Aturan yang dikunci<ChevronDown class="h-3.5 w-3.5 transition-transform" :class="bukaAturan ? 'rotate-180' : ''" />
    </button>
    <ol v-if="bukaAturan" class="m-0 mt-2 list-decimal space-y-1 pl-5 text-xs text-ink-2">
      <li v-for="a in z.aturan" :key="a">{{ a }}</li>
    </ol>
  </Panel>
</template>

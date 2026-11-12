<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { Line } from "vue-chartjs";
import { ambil } from "@/api/client";
import { pakaiTema } from "@/composables/tema";
import { opsiDasar, warna, alfa } from "@/utils/chart";
import { persen } from "@/utils/format";
import Kerangka from "@/components/common/Kerangka.vue";

const props = defineProps({ muatUlang: Number, lama: Boolean });
const z = ref(null);
const tema = pakaiTema();

const muat = async () => {
  z.value = await ambil("paper/zona").catch(() => ({ ada: false }));
};
onMounted(muat);
watch(() => props.muatUlang, muat);

const hari = computed(() => z.value?.paper?.hari ?? 0);
const jangkau = computed(() => Math.min(z.value?.horizon || 500, Math.max(z.value?.v2 ? 100 : 63, Math.ceil(hari.value * 1.6) + 10)));

const data = computed(() => {
  tema.value;
  if (!z.value?.ada) return null;
  const n = jangkau.value;
  const pita = (p) => [0, ...z.value.return[p].slice(0, n)];
  const label = Array.from({ length: n + 1 }, (_, i) => i);
  const s1 = warna("--series-1");
  const paper = z.value.paper ? z.value.paper.return : [];
  const remV2 = z.value.v2
    ? [{
        label: "Batas gagal (aturan v2)",
        data: [null, ...z.value.v2.gagal.ret.slice(0, n).map((v, i) => (i + 1 >= z.value.v2.gagal.mulai_ret ? v : null))],
        borderColor: warna("--turun"), borderWidth: 2, pointRadius: 0, order: 2,
      }]
    : [];
  const batasLama = props.lama
    ? [{ label: "Batas gagal lama", data: pita("p1"), borderColor: warna("--turun"), borderDash: [2, 3], borderWidth: 1.25, pointRadius: 0, order: 2 }]
    : [];
  return {
    labels: label,
    datasets: [
      { label: "Persentil 95", data: pita("p95"), borderWidth: 0, pointRadius: 0, fill: "+4", backgroundColor: alfa(s1, 0.1), order: 5 },
      { label: "Persentil 75", data: pita("p75"), borderWidth: 0, pointRadius: 0, fill: "+2", backgroundColor: alfa(s1, 0.16), order: 5 },
      { label: "Median backtest", data: pita("p50"), borderColor: warna("--series-3"), borderDash: [5, 4], borderWidth: 1.5, pointRadius: 0, order: 3 },
      { label: "Persentil 25", data: pita("p25"), borderWidth: 0, pointRadius: 0, order: 5 },
      { label: "Persentil 5", data: pita("p5"), borderWidth: 0, pointRadius: 0, order: 5 },
      ...batasLama,
      ...remV2,
      {
        label: "Paper", data: paper, borderColor: warna("--series-2"), backgroundColor: warna("--series-2"), borderWidth: 2.5,
        pointRadius: paper.length < 30 ? 3 : 0, pointBorderColor: warna("--surface-1"), pointBorderWidth: 1.5, tension: 0.2, order: 1,
      },
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
</script>

<template>
  <Kerangka v-if="z === null" jenis="grafik" :tinggi="240" />
  <div v-else-if="z.ada" class="mb-2">
    <div class="mb-3 flex flex-wrap gap-2 text-xs text-ink-2">
      <span class="inline-flex items-center gap-2 rounded-full bg-surface-2 px-3 py-1"><span class="h-0.5 w-4 rounded bg-s2"></span>Hasil paper</span>
      <span class="inline-flex items-center gap-2 rounded-full bg-surface-2 px-3 py-1"><span class="h-2.5 w-4 rounded-sm bg-s1/20"></span>Rentang wajar backtest (50% dan 90% hasil)</span>
      <span class="inline-flex items-center gap-2 rounded-full bg-surface-2 px-3 py-1"><span class="w-4 border-t-2 border-dashed border-s3"></span>Hasil tengah backtest</span>
      <span v-if="lama" class="inline-flex items-center gap-2 rounded-full bg-surface-2 px-3 py-1"><span class="w-4 border-t-2 border-dotted border-turun"></span>Batas gagal lama</span>
      <span v-if="z.v2" class="inline-flex items-center gap-2 rounded-full bg-surface-2 px-3 py-1"><span class="w-4 border-t-2 border-turun"></span>Batas gagal v2 (mulai hari ke-{{ z.v2.gagal.mulai_ret }})</span>
    </div>
    <div class="h-[280px]"><Line v-if="data" :data="data" :options="opsi" /></div>
  </div>
</template>

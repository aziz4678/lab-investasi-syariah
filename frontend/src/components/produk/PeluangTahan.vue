<script setup>
import { computed } from "vue";
import { Hourglass } from "lucide-vue-next";
import { persen, kelasPersen } from "@/utils/format";

const props = defineProps({ jendela: { type: Array, default: () => [] }, jendelaRp: { type: Array, default: () => [] }, satuan: { type: String, default: "bulan" } });
const total = (r, th) => (Math.pow(1 + r / 100, th) - 1) * 100;
const rp = (th) => props.jendelaRp.find((j) => j.tahun === th);
const aman = computed(() => props.jendela.find((w) => w.untung >= 95));
const dari100 = (v) => Math.round(v);
const kalimatSial = (w) => {
  if (w.terburuk >= 0) return `masih untung ${persen(w.terburuk, 1, false)} per tahun`;
  if (w.tahun === 1) return `rugi ${persen(-w.terburuk, 1, false)}`;
  return `rugi ${persen(-w.terburuk, 1, false)} per tahun (total ${persen(-total(w.terburuk, w.tahun), 0, false)})`;
};
</script>

<template>
  <div>
    <div class="mb-1 flex items-center gap-2 text-[13px] font-medium"><Hourglass class="h-4 w-4 text-aksen" />Berapa lama sebaiknya ditahan?</div>
    <p class="m-0 mb-3 text-xs leading-relaxed text-muted">Kami coba semua kemungkinan waktu beli sejak data produk ini ada (tiap {{ satuan }}), lalu lihat hasilnya kalau dijual setelah 1, 3, atau 5 tahun.</p>
    <p v-if="!jendela.length" class="m-0 text-[13px] text-muted">Data belum cukup 1 tahun.</p>
    <div v-else class="space-y-3">
      <div v-for="w in jendela" :key="w.tahun" class="rounded-2xl bg-surface-2 px-4 py-3">
        <div class="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
          <div class="text-[13px] font-medium">Ditahan {{ w.tahun }} tahun</div>
          <div class="text-[13px]"><b class="font-medium" :class="w.untung >= 95 ? 'text-naik' : w.untung < 70 ? 'text-turun' : 'text-ink'">untung {{ dari100(w.untung) }} dari 100 kali</b></div>
        </div>
        <div class="mt-2 flex h-2 overflow-hidden rounded-full bg-turun/25">
          <div class="h-full rounded-full bg-naik" :style="{ width: `${w.untung}%` }"></div>
        </div>
        <ul class="m-0 mt-2 space-y-0.5 pl-0 text-[13px] leading-relaxed text-ink-2">
          <li>Biasanya: <b class="font-medium" :class="kelasPersen(w.median)">{{ persen(w.median, 1) }}{{ w.tahun > 1 ? " per tahun" : "" }}</b><span v-if="w.tahun > 1" class="text-muted"> (total ±{{ persen(total(w.median, w.tahun), 0, false) }} dalam {{ w.tahun }} tahun)</span></li>
          <li>Kalau beli di waktu paling sial: <b class="font-medium" :class="kelasPersen(w.terburuk)">{{ kalimatSial(w) }}</b></li>
          <li v-if="rp(w.tahun)" class="text-xs text-muted">Dihitung dalam rupiah: untung {{ dari100(rp(w.tahun).untung) }} dari 100 kali, biasanya {{ persen(rp(w.tahun).median, 1) }}{{ w.tahun > 1 ? "/th" : "" }}.</li>
        </ul>
        <div v-if="w.n < 24" class="mt-1 text-[11px] text-kuning">Baru {{ w.n }} kemungkinan waktu beli; belum cukup mewakili.</div>
      </div>
      <p class="m-0 rounded-2xl border border-garis px-4 py-2.5 text-[13px] text-ink-2">
        <template v-if="aman">Kesimpulan: menurut data masa lalu produk ini, <b class="font-medium text-ink">tahan minimal {{ aman.tahun }} tahun</b> supaya hampir tidak pernah rugi.</template>
        <template v-else>Kesimpulan: dalam data yang ada, produk ini <b class="font-medium text-ink">masih bisa rugi walau ditahan {{ jendela.at(-1).tahun }} tahun</b>. Siapkan waktu lebih lama atau pilih produk lain.</template>
      </p>
    </div>
  </div>
</template>

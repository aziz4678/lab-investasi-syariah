<script setup>
import { computed } from "vue";
import { persen, kelasPersen, ringkas } from "../util.js";

const props = defineProps({ intra: Object, format: Function, uang: Function, catatan: String });
const isi = computed(() => {
  const x = props.intra;
  if (!x) return [];
  return [
    { l: `Harga terakhir · ${x.jam}`, v: props.format(x.terakhir), k: persen(x.ret, 2), kk: kelasPersen(x.ret) },
    { l: "Penutupan sebelumnya", v: props.format(x.tutup_kemarin) },
    { l: "Pembukaan", v: x.buka == null ? "–" : props.format(x.buka) },
    { l: "Tertinggi / terendah", v: `${x.tertinggi == null ? "–" : props.format(x.tertinggi)} / ${x.terendah == null ? "–" : props.format(x.terendah)}` },
    { l: "Volume", v: x.volume == null ? "–" : `${ringkas(x.volume)} unit` },
    { l: "Nilai transaksi", v: x.nilai_transaksi == null ? "–" : props.uang(x.nilai_transaksi) },
  ];
});
</script>

<template>
  <div v-if="intra" class="mt-5">
    <div class="mb-2 text-xs text-muted">Perdagangan {{ intra.sesi }} · data per menit, tertunda ±10 menit{{ catatan ? ` · ${catatan}` : "" }}</div>
    <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-6">
      <div v-for="s in isi" :key="s.l" class="min-w-0 rounded-2xl bg-surface-2 px-4 py-3">
        <div class="truncate text-xs text-muted">{{ s.l }}</div>
        <div class="mt-0.5 truncate text-[15px] font-medium tabular-nums">{{ s.v }}</div>
        <div v-if="s.k" class="text-[11px] font-medium" :class="s.kk">{{ s.k }}</div>
      </div>
    </div>
  </div>
</template>

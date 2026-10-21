<script setup>
import HeaderStrategi from "../components/HeaderStrategi.vue";
import { ref, onMounted } from "vue";
import { ambil } from "../util.js";
import PaperView from "./PaperView.vue";
import BacktestView from "./BacktestView.vue";
import AturanView from "./AturanView.vue";
import RisetView from "./RisetView.vue";

const props = defineProps({ sub: String });
const emit = defineEmits(["sub"]);
const s = ref(null);

const SUB = [["paper", "Paper trade"], ["backtest", "Backtest"], ["aturan", "Aturan & variabel"], ["riset", "Riset"]];

onMounted(async () => {
  const d = await ambil("strategi").catch(() => null);
  s.value = d?.aktif?.[0] || null;
});
</script>

<template>
  <div class="space-y-5">
    <HeaderStrategi :judul="s?.nama || 'Follow Tren'" :ringkas="s?.ringkas" :gaya="s?.gaya" :langkah="s?.langkah" :harapan="s?.harapan" :memuat="!s" :sub="sub" :pilihan="SUB" @sub="emit('sub', $event)"
      :chip="[{ teks: s?.kode || 'H11a', kelas: 'bg-surface-2 text-muted' }, { teks: s?.status_label || 'Paper trade', kelas: 'bg-aksen-lembut text-aksen' }, { teks: s?.kelas || 'Saham syariah IDX', kelas: 'bg-surface-2 text-ink-2' }]" />

    <PaperView v-if="sub === 'paper'" />
    <BacktestView v-else-if="sub === 'backtest'" />
    <AturanView v-else-if="sub === 'aturan'" :s="s" />
    <RisetView v-else />
  </div>
</template>

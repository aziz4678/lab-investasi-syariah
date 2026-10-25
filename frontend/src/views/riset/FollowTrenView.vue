<script setup>
import HeaderStrategi from "@/components/common/HeaderStrategi.vue";
import { ref, onMounted } from "vue";
import { ambil } from "@/api/client";
import PaperTab from "@/views/riset/follow-tren/PaperTab.vue";
import BacktestTab from "@/views/riset/follow-tren/BacktestTab.vue";
import AturanTab from "@/views/riset/follow-tren/AturanTab.vue";
import RisetTab from "@/views/riset/follow-tren/RisetTab.vue";

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

    <PaperTab v-if="sub === 'paper'" />
    <BacktestTab v-else-if="sub === 'backtest'" />
    <AturanTab v-else-if="sub === 'aturan'" :s="s" />
    <RisetTab v-else />
  </div>
</template>

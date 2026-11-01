<script setup>
import HeaderStrategi from "@/components/common/HeaderStrategi.vue";
import { ref, computed, onMounted } from "vue";
import { ambil } from "@/api/client";
import PaperTab from "@/views/riset/strategi/PaperTab.vue";
import PaperBlendTab from "@/views/riset/strategi/PaperBlendTab.vue";
import BacktestTab from "@/views/riset/strategi/BacktestTab.vue";
import AturanTab from "@/views/riset/strategi/AturanTab.vue";

const props = defineProps({ id: String, judul: String, sub: String });
const emit = defineEmits(["sub"]);
const daftar = ref(null);
const s = computed(() => daftar.value?.find((x) => x.id === props.id) || null);

const PAPER = { h11a: PaperTab, h29: PaperBlendTab };
const SUB = [["paper", "Paper trade"], ["backtest", "Backtest"], ["aturan", "Aturan & variabel"]];

onMounted(async () => {
  const d = await ambil("strategi").catch(() => null);
  daftar.value = d?.aktif || [];
});
</script>

<template>
  <div class="space-y-5">
    <HeaderStrategi :judul="s?.nama || judul" :ringkas="s?.ringkas" :gaya="s?.gaya" :langkah="s?.langkah" :detail="s?.detail" :harapan="s?.harapan" :memuat="!s" :sub="sub" :pilihan="s?.tab || SUB" @sub="emit('sub', $event)"
      :chip="s ? [{ teks: s.kode, kelas: 'bg-surface-2 text-muted' }, { teks: s.status_label, kelas: 'bg-aksen-lembut text-aksen' }, { teks: s.kelas, kelas: 'bg-surface-2 text-ink-2' }] : []" />

    <template v-if="s">
      <component :is="PAPER[s.paper]" v-if="sub === 'paper'" :s="s" />
      <BacktestTab v-else-if="sub === 'backtest'" :s="s" />
      <AturanTab v-else :s="s" />
    </template>
  </div>
</template>

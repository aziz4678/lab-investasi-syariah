<script setup>
import { computed } from "vue";
import { Info as IkonInfo, TriangleAlert } from "lucide-vue-next";
import { tanggal } from "@/utils/format";

const props = defineProps({ catatan: { type: Array, default: () => [] } });
const terbaru = computed(() => props.catatan.slice(0, 3));
const manual = (c) => c.hasil === "perlu_cek_manual";
</script>

<template>
  <div v-if="terbaru.length" class="space-y-2">
    <div v-for="c in terbaru" :key="c.tgl + c.ticker" class="flex items-start gap-3 rounded-2xl px-4 py-2.5 text-xs" :class="manual(c) ? 'bg-kuning-bg text-ink-2' : 'bg-surface-2 text-ink-2'">
      <TriangleAlert v-if="manual(c)" class="mt-0.5 h-3.5 w-3.5 shrink-0 text-kuning" />
      <IkonInfo v-else class="mt-0.5 h-3.5 w-3.5 shrink-0 text-aksen" />
      <span class="min-w-0 flex-1 leading-relaxed"><b class="font-medium text-ink">{{ tanggal(c.tgl) }}</b> · {{ c.pesan }}</span>
    </div>
  </div>
</template>

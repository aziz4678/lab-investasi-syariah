<script setup>
import { ArrowRight } from "lucide-vue-next";

defineProps({ teks: { type: String, default: "Lihat data historis, tabel, simulasi, dan cara hitungnya." } });
defineEmits(["buka"]);
</script>

<template>
  <button type="button" class="flex w-full items-center justify-between gap-3 rounded-2xl border border-garis px-4 py-3 text-left transition hover:bg-surface-2" @click="$emit('buka')">
    <span class="min-w-0">
      <span class="block text-[13px] font-medium">Dari mana angka ini?</span>
      <span class="block text-[12px] text-muted">{{ teks }}</span>
    </span>
    <span class="inline-flex shrink-0 items-center gap-1 text-[12px] font-medium text-aksen">Lihat data &amp; perhitungan<ArrowRight class="h-3.5 w-3.5" /></span>
  </button>
</template>

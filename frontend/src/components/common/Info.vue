<script setup>
import { Info } from "lucide-vue-next";
defineProps({ teks: String });
</script>

<template>
  <span class="group relative inline-flex align-middle" tabindex="0">
    <Info class="h-3.5 w-3.5 text-muted transition-colors group-hover:text-ink" />
    <span class="pointer-events-none absolute bottom-full left-1/2 z-30 mb-2 hidden w-64 max-w-[80vw] -translate-x-1/2 rounded-2xl bg-surface-3 px-3.5 py-2.5 text-xs leading-relaxed font-normal text-ink-2 shadow-xl group-hover:block group-focus:block">
      {{ teks }}
    </span>
  </span>
</template>

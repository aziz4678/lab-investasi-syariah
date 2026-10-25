<script setup>
defineProps({ teks: String, ukuran: { type: Number, default: 16 } });
</script>

<template>
  <span class="inline-flex items-center gap-2 text-[13px] text-muted" role="status" aria-live="polite">
    <svg class="shrink-0 motion-safe:animate-spin" :width="ukuran" :height="ukuran" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9.5" stroke="currentColor" stroke-opacity="0.2" stroke-width="3" />
      <path d="M21.5 12a9.5 9.5 0 0 0-9.5-9.5" stroke="var(--aksen)" stroke-width="3" stroke-linecap="round" />
    </svg>
    <span v-if="teks">{{ teks }}</span>
    <span v-else class="sr-only">Memuat...</span>
  </span>
</template>

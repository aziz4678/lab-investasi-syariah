<script setup>
import PaperH29 from "@/components/tren/PaperH29.vue";

defineProps({ s: Object });
</script>

<template>
  <div class="space-y-5">
    <p class="m-0 text-[13px] leading-relaxed text-ink-2">Dua aturan momentum dijalankan ke depan dengan uang pura-pura dalam satu modal, lalu dinilai pada 1 Nov 2027.</p>
    <PaperH29 :biaya-rebalance="s?.fitur?.biaya_rebalance" />
  </div>
</template>

<script setup>
defineProps({
  modelValue: { type: String, default: "rencana" },
  pilihan: { type: Array, default: () => [["rencana", "Rencana"], ["backtest", "Backtest"]] },
});
defineEmits(["update:modelValue"]);
</script>

<template>
  <nav aria-label="Halaman">
    <div class="inline-flex w-full gap-1 rounded-full bg-surface-2 p-1 sm:w-auto">
      <button v-for="[k, l] in pilihan" :key="k" type="button" class="h-8 flex-1 rounded-full px-6 text-[13px] font-medium whitespace-nowrap transition sm:flex-none"
        :class="modelValue === k ? 'bg-aksen text-aksen-teks shadow-sm' : 'text-muted hover:text-ink'" :aria-current="modelValue === k ? 'page' : null" @click="$emit('update:modelValue', k)">{{ l }}</button>
    </div>
  </nav>
</template>

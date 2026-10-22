<script setup>
defineProps({ pilihan: Array, modelValue: String, kecil: Boolean });
defineEmits(["update:modelValue"]);
</script>

<template>
  <div class="inline-flex max-w-full overflow-x-auto rounded-full bg-surface-2 p-1">
    <button v-for="[k, l] in pilihan" :key="k" @click="$emit('update:modelValue', k)"
      class="shrink-0 rounded-full font-medium whitespace-nowrap transition"
      :class="[kecil ? 'h-7 px-3 text-xs' : 'h-8 px-4 text-[13px]', modelValue === k ? 'bg-aksen text-aksen-teks shadow-sm' : 'text-muted hover:text-ink']">
      {{ l }}
    </button>
  </div>
</template>

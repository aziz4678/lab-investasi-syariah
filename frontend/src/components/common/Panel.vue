<script setup>
import Info from "@/components/common/Info.vue";
defineProps({ judul: String, ket: String, info: String, rapat: Boolean });
</script>

<template>
  <section class="panel">
    <header v-if="judul || $slots.aksi" class="flex flex-wrap items-start gap-x-4 gap-y-3 px-6 pt-5">
      <div class="min-w-[min(100%,220px)] flex-1">
        <div class="flex items-center gap-1.5">
          <h2 class="m-0 text-[17px] font-medium">{{ judul }}</h2>
          <Info v-if="info" :teks="info" />
        </div>
        <p v-if="ket" class="m-0 mt-0.5 text-xs text-muted">{{ ket }}</p>
      </div>
      <div v-if="$slots.aksi" class="flex flex-wrap items-center gap-2"><slot name="aksi" /></div>
    </header>
    <div :class="rapat ? 'pt-3 pb-2' : 'px-6 pt-4 pb-6'"><slot /></div>
  </section>
</template>

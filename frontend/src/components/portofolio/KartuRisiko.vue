<script setup>
defineProps({ daftar: { type: Array, default: () => [] }, judul: { type: String, default: "Yang perlu diterima" } });
</script>

<template>
  <section class="panel px-4 py-5 sm:px-6">
    <div class="text-[14px] font-medium">{{ judul }}</div>
    <ul class="m-0 mt-3 grid list-none grid-cols-1 gap-2.5 p-0 sm:grid-cols-2">
      <li v-for="x in daftar.slice(0, 4)" :key="x.judul" class="rounded-2xl bg-surface-2 px-4 py-3">
        <div class="flex items-start justify-between gap-2">
          <span class="text-[13px] font-medium">{{ x.judul }}</span>
          <span v-if="x.angka" class="shrink-0 text-[13px] font-semibold tabular-nums" :class="x.kelas">{{ x.angka }}</span>
        </div>
        <p class="m-0 mt-1 text-[12px] leading-relaxed text-ink-2">{{ x.teks }}</p>
      </li>
    </ul>
    <div v-if="$slots.default" class="mt-3 border-t border-garis pt-3 text-[12px] leading-relaxed text-ink-2">
      <slot />
    </div>
  </section>
</template>

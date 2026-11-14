<script setup>
defineProps({
  judul: { type: String, required: true },
  besar: { type: String, default: "" },
  satuan: { type: String, default: "" },
  kalimat: { type: String, default: "" },
  item: { type: Array, default: () => [] },
  risiko: { type: String, default: "" },
  label: { type: String, default: "Hasil masa lalu, bukan janji." },
});
</script>

<template>
  <section class="panel px-4 py-5 sm:px-6">
    <div class="text-[13px] font-medium text-muted">{{ judul }}</div>
    <div v-if="besar" class="mt-1 text-[34px] leading-tight font-semibold sm:text-[40px]">{{ besar }}<span v-if="satuan" class="ml-2 text-[18px] font-medium text-ink-2">{{ satuan }}</span></div>
    <p v-if="kalimat" class="m-0 mt-1 text-[14px] leading-relaxed text-ink-2">{{ kalimat }}</p>
    <div v-if="item.length" class="mt-4 grid gap-3" :class="item.length > 2 ? 'sm:grid-cols-3' : 'sm:grid-cols-2'">
      <div v-for="x in item" :key="x.label" class="rounded-2xl bg-surface-2 px-4 py-3">
        <div class="text-[11px] text-muted">{{ x.label }}</div>
        <div class="text-[17px] font-semibold tabular-nums" :class="x.kelas">{{ x.nilai }}</div>
        <div v-if="x.ket" class="text-[11px] text-muted">{{ x.ket }}</div>
      </div>
    </div>
    <div v-if="risiko" class="mt-4 rounded-2xl bg-kuning-bg px-4 py-3 text-[13px] leading-relaxed text-kuning">{{ risiko }}</div>
    <slot />
    <div class="mt-3 inline-flex rounded-full bg-surface-2 px-3 py-1 text-[11px] font-medium text-ink-2">{{ label }}</div>
  </section>
</template>

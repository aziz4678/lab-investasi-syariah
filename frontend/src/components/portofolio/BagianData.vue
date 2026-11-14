<script setup>
defineProps({
  id: { type: String, required: true },
  nomor: { type: [String, Number], default: "" },
  judul: { type: String, required: true },
  ket: { type: String, default: "" },
});
</script>

<template>
  <section :id="id" class="scroll-mt-16 space-y-4">
    <div class="flex items-start gap-3 px-1">
      <span v-if="nomor" class="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full bg-aksen-lembut text-[13px] font-semibold text-aksen">{{ nomor }}</span>
      <div class="min-w-0">
        <h3 class="m-0 text-[17px] leading-snug font-semibold">{{ judul }}</h3>
        <p v-if="ket" class="m-0 mt-0.5 text-[12px] leading-relaxed text-muted">{{ ket }}</p>
      </div>
    </div>
    <div class="space-y-5">
      <slot />
    </div>
  </section>
</template>

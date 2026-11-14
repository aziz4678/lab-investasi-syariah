<script setup>
import { ArrowLeft } from "lucide-vue-next";
import NavLengket from "@/components/portofolio/NavLengket.vue";

defineProps({
  atas: { type: String, default: "" },
  judul: { type: String, required: true },
  ringkas: { type: String, default: "" },
  chip: { type: Array, default: () => [] },
  nav: { type: Array, default: () => [] },
});
defineEmits(["kembali"]);
</script>

<template>
  <div class="space-y-5">
    <section class="panel px-4 py-5 sm:px-6">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div class="min-w-0">
          <div v-if="atas" class="text-[11px] font-medium tracking-wide text-muted uppercase">{{ atas }}</div>
          <h2 class="m-0 mt-1 text-[22px] leading-tight font-semibold">{{ judul }}</h2>
        </div>
        <button type="button" class="tombol shrink-0" @click="$emit('kembali')"><ArrowLeft class="h-3.5 w-3.5" />kembali ke rencana</button>
      </div>
      <p v-if="ringkas" class="m-0 mt-2 max-w-3xl text-[13px] leading-relaxed text-ink-2">{{ ringkas }}</p>
      <div v-if="chip.length || $slots.aksi" class="mt-3 flex flex-wrap items-center gap-2">
        <span v-for="c in chip" :key="c.teks" class="chip" :class="c.kelas ?? 'bg-surface-2 text-ink-2'">{{ c.teks }}</span>
        <slot name="aksi" />
      </div>
    </section>
    <NavLengket v-if="nav.length" :item="nav" />
    <slot />
  </div>
</template>

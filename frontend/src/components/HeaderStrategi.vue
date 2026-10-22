<script setup>
import Segmen from "./Segmen.vue";
import Kerangka from "./Kerangka.vue";

defineProps({ judul: String, chip: Array, ringkas: String, gaya: String, sub: String, pilihan: Array, langkah: Array, harapan: String, memuat: Boolean });
const emit = defineEmits(["sub"]);
</script>

<template>
  <div class="panel overflow-hidden">
    <div class="px-6 pt-5 pb-5">
      <div class="flex flex-wrap items-center gap-2">
        <span class="mr-1 text-[19px] font-medium">{{ judul }}</span>
        <span v-for="c in chip" :key="c.teks" class="chip" :class="c.kelas">{{ c.teks }}</span>
      </div>
      <template v-if="memuat">
        <Kerangka class="mt-3" :n="2" />
        <Kerangka class="mt-4" jenis="kartu" :n="4" kolom="sm:grid-cols-2 xl:grid-cols-4" />
      </template>
      <p v-if="ringkas" class="m-0 mt-2 text-[13px] leading-relaxed text-ink-2">{{ ringkas }}</p>
      <ol v-if="langkah?.length" class="m-0 mt-4 grid list-none gap-2.5 p-0 sm:grid-cols-2 xl:grid-cols-4">
        <li v-for="(l, i) in langkah" :key="l.judul" class="flex gap-3 rounded-2xl bg-surface-2 px-4 py-3">
          <span class="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-aksen-lembut text-xs font-medium text-aksen">{{ i + 1 }}</span>
          <div class="min-w-0">
            <div class="text-[13px] font-medium">{{ l.judul }}</div>
            <div class="mt-0.5 text-xs leading-relaxed text-ink-2">{{ l.teks }}</div>
          </div>
        </li>
      </ol>
      <p v-if="harapan" class="m-0 mt-3 rounded-2xl border border-garis px-4 py-3 text-xs leading-relaxed text-ink-2">
        <span class="font-medium text-ink">Yang bisa diharapkan:</span> {{ harapan }}
      </p>
      <p v-if="gaya" class="m-0 mt-3 text-xs text-muted">{{ gaya }}</p>
    </div>
    <div class="overflow-x-auto border-t border-garis px-4 py-3">
      <Segmen :model-value="sub" :pilihan="pilihan" @update:model-value="emit('sub', $event)" />
    </div>
  </div>
</template>

<script setup>
import Segmen from "@/components/common/Segmen.vue";
import Kerangka from "@/components/common/Kerangka.vue";

defineProps({ judul: String, chip: Array, ringkas: String, gaya: String, sub: String, pilihan: Array, langkah: Array, detail: Object, harapan: String, memuat: Boolean });
const emit = defineEmits(["sub"]);
const JENIS = { cl: { label: "CL", kelas: "bg-turun-bg text-turun" }, tp: { label: "TP", kelas: "bg-naik-bg text-naik" } };
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
            <div class="flex items-center gap-1.5 text-[13px] font-medium">
              {{ l.judul }}
              <span v-if="JENIS[l.jenis]" class="rounded-full px-1.5 text-[10px] leading-4 font-medium" :class="JENIS[l.jenis].kelas">{{ JENIS[l.jenis].label }}</span>
            </div>
            <div class="mt-0.5 text-xs leading-relaxed text-ink-2">{{ l.teks }}</div>
          </div>
        </li>
      </ol>
      <p v-if="harapan" class="m-0 mt-3 rounded-2xl border border-garis px-4 py-3 text-xs leading-relaxed text-ink-2">
        <span class="font-medium text-ink">Yang bisa diharapkan:</span> {{ harapan }}
      </p>
      <div v-if="gaya || detail" class="mt-3 flex flex-wrap items-center justify-between gap-x-4 gap-y-1 text-xs">
        <span v-if="gaya" class="text-muted">{{ gaya }}</span>
        <button v-if="detail && !memuat" class="text-aksen hover:underline" @click="emit('sub', detail.sub)">{{ detail.teks }}</button>
      </div>
    </div>
    <div class="overflow-x-auto border-t border-garis px-4 py-3">
      <Segmen :model-value="sub" :pilihan="pilihan" @update:model-value="emit('sub', $event)" />
    </div>
  </div>
</template>

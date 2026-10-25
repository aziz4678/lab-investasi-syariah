<script setup>
const props = defineProps({
  jenis: { type: String, default: "baris" },
  n: { type: Number, default: 3 },
  tinggi: { type: Number, default: 220 },
  kolom: { type: String, default: "grid-cols-2 md:grid-cols-4" },
  panel: Boolean,
  judul: { type: Boolean, default: true },
  logo: Boolean,
});
const LEBAR = ["92%", "78%", "86%", "64%", "72%", "58%", "81%"];
const lebar = (i) => LEBAR[i % LEBAR.length];
</script>

<template>
  <component :is="panel ? 'section' : 'div'" :class="panel ? 'panel overflow-hidden' : ''" role="status" aria-live="polite" aria-label="Memuat">
    <div v-if="panel && judul" class="px-6 pt-5">
      <div class="tulang h-4 w-40"></div>
      <div class="tulang mt-2 h-3 w-64 max-w-full"></div>
    </div>
    <div :class="panel ? (jenis === 'tabel' ? 'pt-3 pb-2' : 'px-6 pt-4 pb-6') : ''">
      <div v-if="jenis === 'baris'" class="space-y-2.5">
        <div v-for="i in n" :key="i" class="tulang h-3" :style="{ width: lebar(i) }"></div>
      </div>

      <div v-else-if="jenis === 'tabel'">
        <div v-for="i in n" :key="i" class="flex items-center gap-3 border-b border-garis px-6 py-3 last:border-b-0">
          <div v-if="logo" class="tulang h-7 w-7 shrink-0 !rounded-full"></div>
          <div class="min-w-0 flex-1 space-y-1.5">
            <div class="tulang h-3" :style="{ width: `${30 + ((i * 17) % 35)}%` }"></div>
            <div v-if="logo" class="tulang h-2.5 w-1/4"></div>
          </div>
          <div class="tulang h-3 w-14"></div>
          <div class="tulang h-3 w-12"></div>
        </div>
      </div>

      <div v-else-if="jenis === 'grafik'" class="relative overflow-hidden rounded-2xl" :style="{ height: `${tinggi}px` }">
        <div class="absolute inset-0 flex flex-col justify-between py-1">
          <div v-for="i in 5" :key="i" class="border-t border-garis"></div>
        </div>
        <svg class="tulang-svg absolute inset-0 h-full w-full" viewBox="0 0 400 100" preserveAspectRatio="none" aria-hidden="true">
          <path d="M0 70 C 40 60, 60 78, 100 62 S 160 30, 200 46 S 270 70, 300 40 S 360 22, 400 30 L 400 100 L 0 100 Z" />
        </svg>
      </div>

      <div v-else-if="jenis === 'stat'" class="grid gap-2" :class="kolom">
        <div v-for="i in n" :key="i" class="rounded-[18px] px-4 py-4">
          <div class="tulang h-2.5 w-20"></div>
          <div class="tulang mt-3 h-6 w-28 max-w-full"></div>
          <div class="tulang mt-2.5 h-2.5 w-24 max-w-full"></div>
        </div>
      </div>

      <div v-else-if="jenis === 'kartu'" class="grid gap-3" :class="kolom">
        <div v-for="i in n" :key="i" class="rounded-2xl bg-surface-2 px-4 py-4">
          <div class="tulang tulang-kontras h-3 w-1/2"></div>
          <div class="tulang tulang-kontras mt-3 h-2.5 w-4/5"></div>
          <div class="tulang tulang-kontras mt-2 h-2.5 w-2/3"></div>
        </div>
      </div>
    </div>
    <span class="sr-only">Memuat...</span>
  </component>
</template>

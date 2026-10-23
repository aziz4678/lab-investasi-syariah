<script setup>
import { computed } from "vue";
import { CircleCheck, TriangleAlert, CircleX, Sparkles } from "lucide-vue-next";

const props = defineProps({ k: Object });
const WARNA = { naik: "bg-naik-bg text-naik", kuning: "bg-kuning-bg text-kuning", turun: "bg-turun-bg text-turun", netral: "bg-surface-2 text-ink-2" };
const KOLOM = computed(() => [
  { kunci: "kekuatan", judul: "Kelebihan", ikon: CircleCheck, warna: "text-naik", kosong: "Tidak ada indikator yang menonjol di atas produk sekategori." },
  { kunci: "waspada", judul: "Perlu diwaspadai", ikon: TriangleAlert, warna: "text-kuning", kosong: "Tidak ditemukan hal yang perlu diwaspadai secara khusus." },
  { kunci: "kelemahan", judul: "Kekurangan", ikon: CircleX, warna: "text-turun", kosong: "Tidak ada indikator yang tertinggal dari produk sekategori." },
]);
</script>

<template>
  <div v-if="k" class="panel px-6 py-5">
    <div class="flex flex-wrap items-center gap-3">
      <Sparkles class="h-4 w-4 text-aksen" />
      <span class="text-[15px] font-medium">Kesimpulan</span>
      <span class="chip text-[13px] font-semibold" :class="WARNA[k.nada] || WARNA.netral">{{ k.nilai }}</span>
    </div>
    <p class="m-0 mt-3 max-w-[960px] text-[14px] leading-relaxed text-ink">{{ k.ringkasan }}</p>
    <div class="mt-5 grid gap-4 lg:grid-cols-3">
      <div v-for="c in KOLOM" :key="c.kunci" class="rounded-2xl bg-surface-2 px-4 py-4">
        <div class="mb-3 flex items-center gap-2 text-[13px] font-medium">
          <component :is="c.ikon" class="h-4 w-4" :class="c.warna" />{{ c.judul }}
          <span class="ml-auto text-xs font-normal text-muted">{{ k[c.kunci].length }}</span>
        </div>
        <ul v-if="k[c.kunci].length" class="m-0 list-none space-y-3 p-0">
          <li v-for="pt in k[c.kunci]" :key="pt.judul" class="text-[13px] leading-relaxed">
            <div class="font-medium">{{ pt.judul }}</div>
            <div class="text-ink-2">{{ pt.teks }}</div>
          </li>
        </ul>
        <p v-else class="m-0 text-xs text-muted">{{ c.kosong }}</p>
      </div>
    </div>
    <p class="m-0 mt-4 text-[11px] leading-relaxed text-muted">{{ k.catatan }}</p>
  </div>
</template>

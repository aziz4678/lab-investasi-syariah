<script setup>
import { ref } from "vue";
import { ShieldCheck } from "lucide-vue-next";
import Logo from "@/components/common/Logo.vue";
import { pakaiPlatform } from "@/composables/platformRD";

defineProps({ platform: { type: Array, default: () => [] }, kecil: Boolean, lengkap: Boolean });
const { nama, izin } = pakaiPlatform();
const gagal = ref({});
const SKALA = { ajaib: 1.45 };
const tinggi = (k, dasar) => ({ height: `${Math.round(dasar * (SKALA[k] || 1))}px` });
</script>

<template>
  <div v-if="lengkap">
    <div v-if="platform.length" class="flex flex-wrap gap-2">
      <a v-for="x in platform" :key="x.kode" :href="x.url" target="_blank" rel="noopener" class="inline-flex h-9 items-center rounded-full border border-garis bg-white px-3.5 transition hover:-translate-y-0.5 hover:border-aksen" :title="`Buka ${nama(x.kode)}${izin(x.kode) ? ' · berizin OJK' : ''}`" @click.stop>
        <img v-if="!gagal[x.kode]" :src="`/api/logo/merek/${x.kode}`" :alt="nama(x.kode)" class="w-auto max-w-[96px] object-contain" :style="tinggi(x.kode, 16)" @error="gagal[x.kode] = true" />
        <span v-else class="flex items-center gap-1.5"><Logo jenis="platform" :kunci="x.kode" :teks="nama(x.kode)" :ukuran="20" /><span class="text-[13px] font-medium text-[#1a1a1a]">{{ nama(x.kode) }}</span></span>
      </a>
    </div>
    <div v-if="platform.length" class="mt-1.5 flex items-center gap-1 text-[11px] text-muted" title="Ditemukan di katalog platform; ketersediaan bisa berubah, pastikan lagi di aplikasinya"><ShieldCheck class="h-3 w-3 text-naik" />berizin OJK · cek lagi di aplikasinya</div>
    <div v-else class="max-w-[260px] text-xs text-muted">Belum ditemukan di Bibit, Ajaib, atau Makmur. Tanyakan ke manajer investasinya.</div>
  </div>
  <div v-else-if="platform.length" class="flex flex-wrap items-center gap-1.5">
    <a v-for="x in platform" :key="x.kode" :href="x.url" target="_blank" rel="noopener" class="inline-flex items-center rounded-full border border-garis bg-white transition hover:-translate-y-0.5 hover:border-aksen" :class="kecil ? 'h-6 px-2' : 'h-7 px-2.5'" :title="`Buka di ${nama(x.kode)}`" :aria-label="`Buka di ${nama(x.kode)}`" @click.stop>
      <img v-if="!gagal[x.kode]" :src="`/api/logo/merek/${x.kode}`" :alt="nama(x.kode)" class="w-auto max-w-[72px] object-contain" :style="tinggi(x.kode, kecil ? 12 : 14)" @error="gagal[x.kode] = true" />
      <span v-else class="text-[11px] font-medium text-[#1a1a1a]">{{ nama(x.kode) }}</span>
    </a>
  </div>
  <span v-else class="text-[11px] text-muted">–</span>
</template>

<script>
import { ref } from "vue";

const tersedia = ref(null);
let dimuat = null;

function muatDaftar() {
  if (!dimuat) {
    dimuat = fetch("/api/logo/ada")
      .then((r) => (r.ok ? r.json() : []))
      .then((x) => (tersedia.value = new Set(x)))
      .catch(() => (tersedia.value = new Set()));
  }
  return dimuat;
}

export function kunciMi(nama) {
  return (nama || "").toLowerCase().replace(/[^a-z0-9]/g, "");
}
</script>

<script setup>
import { computed } from "vue";

const props = defineProps({ jenis: String, kunci: String, teks: String, ukuran: { type: Number, default: 32 } });
const gagal = ref(false);
muatDaftar();

const jalur = computed(() => `${props.jenis}/${props.kunci}`);
const pakaiGambar = computed(() => !gagal.value && props.kunci && tersedia.value?.has(jalur.value));
const WARNA = ["bg-aksen-lembut text-aksen", "bg-kuning-bg text-kuning", "bg-naik-bg text-naik", "bg-surface-3 text-ink-2", "bg-turun-bg text-turun"];
const inisial = computed(() => {
  const t = (props.teks || props.kunci || "?").replace(/\b(PT|Tbk|Reksa Dana|RD|Syariah)\b/gi, "").trim();
  const kata = t.split(/\s+/).filter(Boolean);
  if (/^[A-Z0-9.]{2,6}$/.test(t)) return t.replace(".L", "").slice(0, 4);
  return (kata.length > 1 ? kata[0][0] + kata[1][0] : t.slice(0, 2)).toUpperCase();
});
const warna = computed(() => {
  let h = 0;
  for (const c of props.kunci || props.teks || "") h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return WARNA[h % WARNA.length];
});
const gaya = computed(() => ({ width: `${props.ukuran}px`, height: `${props.ukuran}px`, fontSize: `${Math.max(9, Math.round(props.ukuran * (inisial.value.length > 2 ? 0.28 : 0.36)))}px` }));
</script>

<template>
  <span v-if="pakaiGambar" class="inline-grid shrink-0 place-items-center overflow-hidden rounded-[30%] border border-garis bg-white" :style="gaya">
    <img :src="`/api/logo/${jalur}`" :alt="teks || kunci" class="h-[78%] w-[78%] object-contain" loading="lazy" @error="gagal = true" />
  </span>
  <span v-else class="inline-grid shrink-0 place-items-center rounded-[30%] font-semibold tracking-tight" :class="warna" :style="gaya">{{ inisial }}</span>
</template>

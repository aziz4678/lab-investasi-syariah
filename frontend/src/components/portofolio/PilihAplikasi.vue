<script setup>
import { computed, ref } from "vue";
import { Check } from "lucide-vue-next";

const model = defineModel({ type: Array, default: () => [] });
const props = defineProps({
  pilihan: { type: Array, default: () => [["bibit", "Bibit"], ["ajaib", "Ajaib"], ["makmur", "Makmur"], ["stockbit", "Stockbit"]] },
  catatan: { type: String, default: "Stockbit hanya untuk beli ETF (akun saham)." },
  kanan: Boolean,
});

const IKON_SAJA = ["stockbit"];
const SKALA = { ajaib: 1.45 };
const gagal = ref({});
const hidup = computed(() => new Set(model.value));
const tinggi = (k) => ({ height: `${Math.round(16 * (SKALA[k] || 1))}px` });
const balik = (k) => {
  const baru = new Set(model.value);
  if (baru.has(k)) baru.delete(k);
  else baru.add(k);
  model.value = props.pilihan.map(([x]) => x).filter((x) => baru.has(x));
};
</script>

<template>
  <div>
    <div class="flex flex-wrap gap-2" :class="kanan ? 'sm:justify-end' : ''" role="group" aria-label="Aplikasi yang kamu punya">
      <button v-for="[k, l] in pilihan" :key="k" type="button" :aria-pressed="hidup.has(k)" :aria-label="l" :title="l"
        class="relative inline-flex h-9 items-center gap-1.5 rounded-full border bg-white px-3.5 transition hover:-translate-y-0.5"
        :class="hidup.has(k) ? 'border-aksen ring-1 ring-aksen' : 'border-garis opacity-50 grayscale'" @click="balik(k)">
        <template v-if="!gagal[k]">
          <img v-if="IKON_SAJA.includes(k)" :src="`/api/logo/merek/${k}`" :alt="l" class="h-5 w-5 rounded-md object-contain" @error="gagal[k] = true" />
          <img v-else :src="`/api/logo/merek/${k}`" :alt="l" class="w-auto max-w-[72px] object-contain" :style="tinggi(k)" @error="gagal[k] = true" />
          <span v-if="IKON_SAJA.includes(k)" class="text-[13px] font-medium text-[#1a1a1a]">{{ l }}</span>
        </template>
        <span v-else class="text-[13px] font-medium text-[#1a1a1a]">{{ l }}</span>
        <span v-if="hidup.has(k)" class="absolute -top-1 -right-1 grid h-4 w-4 place-items-center rounded-full bg-aksen text-white"><Check class="h-2.5 w-2.5" /></span>
      </button>
    </div>
    <div class="mt-1.5 text-[11px] text-muted">{{ model.length ? catatan : "Pilih minimal satu aplikasi supaya daftar belanja muncul." }}</div>
  </div>
</template>

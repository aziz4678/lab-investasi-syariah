<script setup>
import { computed } from "vue";
import { Check } from "lucide-vue-next";

const model = defineModel({ type: Array, default: () => [] });
const props = defineProps({
  pilihan: { type: Array, default: () => [["bibit", "Bibit"], ["ajaib", "Ajaib"], ["makmur", "Makmur"], ["stockbit", "Stockbit"]] },
  catatan: { type: String, default: "Stockbit hanya untuk beli ETF (akun saham)." },
});

const hidup = computed(() => new Set(model.value));
const balik = (k) => {
  const baru = new Set(model.value);
  if (baru.has(k)) baru.delete(k);
  else baru.add(k);
  model.value = props.pilihan.map(([x]) => x).filter((x) => baru.has(x));
};
</script>

<template>
  <div>
    <div class="flex flex-wrap gap-1.5" role="group" aria-label="Aplikasi yang kamu punya">
      <button v-for="[k, l] in pilihan" :key="k" type="button" :aria-pressed="hidup.has(k)" class="inline-flex h-8 items-center gap-1 rounded-full border px-3.5 text-[13px] font-medium transition"
        :class="hidup.has(k) ? 'border-aksen bg-aksen-lembut text-aksen' : 'border-garis text-muted hover:text-ink'" @click="balik(k)">
        <Check v-if="hidup.has(k)" class="h-3.5 w-3.5" />{{ l }}
      </button>
    </div>
    <div class="mt-1 text-[11px] text-muted">{{ model.length ? catatan : "Pilih minimal satu aplikasi supaya daftar belanja muncul." }}</div>
  </div>
</template>

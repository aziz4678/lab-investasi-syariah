<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { CheckCircle2, Circle } from "lucide-vue-next";

const props = defineProps({ kunci: { type: String, required: true }, langkah: { type: Array, default: () => [] } });
const selesai = ref([]);

const bulan = () => {
  const t = new Date();
  return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}`;
};
const kunciPenyimpanan = () => `checklist:${props.kunci}:${bulan()}`;
const baca = () => {
  try {
    const mentah = localStorage.getItem(kunciPenyimpanan());
    const x = mentah ? JSON.parse(mentah) : [];
    return Array.isArray(x) ? x : [];
  } catch {
    return [];
  }
};
const simpan = () => {
  try {
    localStorage.setItem(kunciPenyimpanan(), JSON.stringify(selesai.value));
  } catch {
    return;
  }
};
const balik = (id) => {
  selesai.value = selesai.value.includes(id) ? selesai.value.filter((x) => x !== id) : [...selesai.value, id];
  simpan();
};
onMounted(() => {
  selesai.value = baca();
});
watch(() => props.kunci, () => {
  selesai.value = baca();
});

const jumlah = computed(() => props.langkah.filter((x) => selesai.value.includes(x.id)).length);
const semua = computed(() => props.langkah.length > 0 && jumlah.value === props.langkah.length);
</script>

<template>
  <section class="panel px-4 py-5 sm:px-6">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div class="text-[14px] font-medium">Checklist bulan ini</div>
      <span class="chip" :class="semua ? 'bg-naik-bg text-naik' : 'bg-surface-2 text-ink-2'">{{ jumlah }} dari {{ langkah.length }} selesai</span>
    </div>
    <p class="m-0 mt-1 text-[12px] text-muted">Centang yang sudah kamu lakukan. Tersimpan di perangkat ini dan mulai kosong lagi tiap bulan.</p>
    <ol v-if="langkah.length" class="m-0 mt-3 list-none space-y-2 p-0">
      <li v-for="(l, i) in langkah" :key="l.id">
        <button type="button" class="flex w-full items-start gap-3 rounded-2xl border border-garis px-4 py-3 text-left transition hover:bg-surface-2" :aria-pressed="selesai.includes(l.id)" @click="balik(l.id)">
          <CheckCircle2 v-if="selesai.includes(l.id)" class="mt-0.5 h-5 w-5 shrink-0 text-naik" />
          <Circle v-else class="mt-0.5 h-5 w-5 shrink-0 text-muted" />
          <span class="min-w-0 text-[13px] leading-snug" :class="selesai.includes(l.id) ? 'text-muted line-through' : 'text-ink'"><b class="font-medium">{{ i + 1 }}.</b> {{ l.teks }}</span>
        </button>
      </li>
    </ol>
    <p v-else class="m-0 mt-3 text-[13px] text-muted">Belum ada langkah belanja untuk pilihan aplikasi ini.</p>
  </section>
</template>

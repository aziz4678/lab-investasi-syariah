<script setup>
import { computed, ref, watch, nextTick } from "vue";

const props = defineProps({ kerja: Object, galat: String });
const penuh = ref(false);
const kotak = ref(null);

const STATUS = {
  berjalan: { l: "Berjalan", k: "bg-aksen-lembut text-aksen" },
  selesai: { l: "Selesai", k: "bg-naik-bg text-naik" },
  gagal: { l: "Gagal", k: "bg-turun-bg text-turun" },
  terputus: { l: "Terputus", k: "bg-surface-2 text-muted" },
};

const log = computed(() => {
  const l = props.kerja?.log || [];
  return penuh.value ? l : l.slice(-10);
});

const durasi = computed(() => {
  const k = props.kerja;
  if (!k) return "";
  const akhir = k.selesai ? new Date(k.selesai) : new Date();
  return `${Math.max(0, Math.round((akhir - new Date(k.mulai)) / 1000))} dtk`;
});

watch(log, async () => {
  await nextTick();
  if (kotak.value) kotak.value.scrollTop = kotak.value.scrollHeight;
});
</script>

<template>
  <div v-if="galat" class="panel px-5 py-3.5 text-turun">{{ galat }}</div>
  <div v-if="kerja" class="panel">
    <div class="flex flex-wrap items-center gap-2 px-6 pt-4 pb-2">
      <span class="font-medium">{{ kerja.label }}</span>
      <span class="chip" :class="STATUS[kerja.status]?.k">
        <span
          v-if="kerja.status === 'berjalan'"
          class="h-1.5 w-1.5 animate-pulse rounded-full bg-aksen"
        ></span
        >{{ STATUS[kerja.status]?.l }}
      </span>
      <span class="text-xs text-muted tabular-nums">{{ durasi }}</span>
      <button
        v-if="(kerja.log || []).length > 10"
        class="ml-auto text-xs text-aksen hover:underline"
        @click="penuh = !penuh"
      >
        {{ penuh ? "Ringkas" : `Semua log (${kerja.log.length})` }}
      </button>
    </div>
    <pre
      ref="kotak"
      class="m-0 mx-4 mb-4 max-h-[280px] overflow-auto rounded-2xl bg-surface-2 px-4 py-3 font-mono text-[12px] leading-relaxed whitespace-pre-wrap text-ink-2"
      >{{ log.join("\n") || "menunggu output..." }}</pre
    >
  </div>
</template>

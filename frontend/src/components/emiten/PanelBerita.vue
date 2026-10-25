<script setup>
import { ref, computed, watch } from "vue";
import { ExternalLink, Newspaper } from "lucide-vue-next";
import { ambil } from "@/api/client";
import Panel from "@/components/common/Panel.vue";
import Kerangka from "@/components/common/Kerangka.vue";

const props = defineProps({ kode: String });
const d = ref(null);
const semua = ref(false);

watch(() => props.kode, async (k) => {
  d.value = null;
  semua.value = false;
  if (!k) return;
  const r = await ambil(`berita/${k}`).catch(() => ({ item: [], galat: "Berita tidak bisa dimuat" }));
  if (k === props.kode) d.value = r;
}, { immediate: true });

const tampil = computed(() => (d.value?.item || []).slice(0, semua.value ? 40 : 8));
function kapan(t) {
  if (!t) return "";
  const jam = (Date.now() - new Date(t).getTime()) / 36e5;
  if (jam < 1) return "baru saja";
  if (jam < 24) return `${Math.floor(jam)} jam lalu`;
  if (jam < 48) return "kemarin";
  return new Date(t).toLocaleDateString("id-ID", { day: "numeric", month: "short" });
}
</script>

<template>
  <Panel judul="Berita terbaru" :ket="`Judul berita ${d?.hari || 30} hari terakhir dari Google News yang menyebut ${kode} · klik untuk membaca di situs aslinya`" rapat>
    <Kerangka v-if="!d" class="px-6 pb-5" jenis="baris" :n="4" />
    <template v-else>
      <p v-if="d.galat" class="m-0 px-6 pb-3 text-xs text-kuning">{{ d.galat }}</p>
      <p v-if="!d.item.length" class="m-0 px-6 pb-5 text-[13px] text-muted">Tidak ada berita yang menyebut {{ kode }} dalam {{ d.hari }} hari terakhir.</p>
      <a v-for="x in tampil" :key="x.url" :href="x.url" target="_blank" rel="noopener"
        class="group flex items-start gap-3 border-t border-garis px-6 py-3 no-underline hover:bg-surface-2/50">
        <Newspaper class="mt-0.5 h-4 w-4 shrink-0 text-muted" />
        <div class="min-w-0 flex-1">
          <div class="text-[13px] leading-snug text-ink group-hover:text-aksen">{{ x.judul }}</div>
          <div class="mt-0.5 text-xs text-muted">{{ x.sumber || "–" }} · {{ kapan(x.tgl) }}</div>
        </div>
        <ExternalLink class="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted opacity-0 transition group-hover:opacity-100" />
      </a>
      <div v-if="d.item.length > 8" class="border-t border-garis px-6 py-3 text-xs">
        <button type="button" class="text-muted hover:underline" @click="semua = !semua">{{ semua ? "Tampilkan 8 terbaru" : `Tampilkan semua ${d.item.length} berita` }}</button>
      </div>
    </template>
  </Panel>
</template>

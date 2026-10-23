<script setup>
import { ref, computed, onMounted } from "vue";
import { CalendarClock } from "lucide-vue-next";
import { ambil, rupiah } from "../util.js";
import Panel from "./Panel.vue";
import Kerangka from "./Kerangka.vue";
import KodeSaham from "./KodeSaham.vue";

const emit = defineEmits(["buka"]);
const data = ref(null);
const pilihanku = ref([]);

onMounted(async () => {
  try {
    pilihanku.value = JSON.parse(localStorage.getItem("kalk_kode") || "[]");
  } catch {
    pilihanku.value = [];
  }
  data.value = await ambil("dividen/pengingat?hari=7").catch(() => ({ data: [] }));
});

const daftar = computed(() =>
  (data.value?.data || [])
    .map((x) => ({ ...x, milikku: pilihanku.value.includes(x.kode) }))
    .sort((a, b) => Number(b.milikku || b.paper) - Number(a.milikku || a.paper) || a.sisa_hari - b.sisa_hari),
);
const pendek = (t) => (t ? new Date(t).toLocaleDateString("id-ID", { day: "numeric", month: "short" }) : "–");
const sisa = (n) => (n === 0 ? "hari ini" : n === 1 ? "besok" : `${n} hari lagi`);
</script>

<template>
  <Panel judul="Cum date dividen" ket="Saham syariah · 7 hari ke depan · beli paling lambat di tanggal cum"
    info="Dari kalender IDX. Ditandai kalau saham ada di kalkulator dividenmu, di uji maju, atau di pratinjau pilihan uji maju.">
    <Kerangka v-if="!data" jenis="kartu" :n="3" kolom="grid-cols-1" />
    <p v-else-if="!daftar.length" class="m-0 text-[13px] text-muted">Tidak ada cum date saham syariah dalam 7 hari ke depan.</p>
    <div v-else class="space-y-2.5">
      <div v-for="x in daftar.slice(0, 6)" :key="x.kode + x.cum" class="flex items-center gap-3 rounded-2xl px-3.5 py-3" :class="x.milikku || x.paper ? 'bg-aksen-lembut' : 'bg-surface-2'">
        <CalendarClock class="h-4 w-4 shrink-0" :class="x.sisa_hari <= 2 ? 'text-kuning' : 'text-muted'" />
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-1.5">
            <KodeSaham :kode="x.kode" />
            <span v-if="x.milikku" class="chip !h-5 !px-2 !text-[10px] bg-surface text-aksen">kalkulatormu</span>
            <span v-if="x.paper" class="chip !h-5 !px-2 !text-[10px] bg-surface text-aksen">uji maju</span>
            <span v-else-if="x.pratinjau" class="chip !h-5 !px-2 !text-[10px] bg-surface text-ink-2">pratinjau 2027</span>
          </div>
          <div class="text-xs leading-relaxed text-muted">cum <b class="font-medium text-ink-2">{{ pendek(x.cum) }}</b> ({{ sisa(x.sisa_hari) }}) · cair {{ pendek(x.bayar) }}<template v-if="x.per_lembar"> · Rp{{ rupiah(x.per_lembar) }}/lembar</template></div>
        </div>
      </div>
      <button class="flex w-full items-center justify-center text-xs text-muted hover:underline" @click="emit('buka')">
        {{ daftar.length > 6 ? `+${daftar.length - 6} lainnya · ` : "" }}Lihat jadwal lengkap →
      </button>
    </div>
  </Panel>
</template>

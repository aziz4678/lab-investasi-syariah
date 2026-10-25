<script setup>
import { ref, computed, watch } from "vue";
import { FileText, Paperclip, ExternalLink } from "lucide-vue-next";
import { ambil } from "@/api/client";
import Panel from "@/components/common/Panel.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import Pemutar from "@/components/common/Pemutar.vue";

const props = defineProps({ kode: String });
const UKURAN = 15;
const WARNA = {
  dividen: "bg-naik-bg text-naik", buyback: "bg-naik-bg text-naik", split: "bg-aksen-lembut text-aksen", hmetd: "bg-kuning-bg text-kuning",
  rups: "bg-surface-2 text-ink-2", tender: "bg-kuning-bg text-kuning", suspensi: "bg-turun-bg text-turun", delisting: "bg-turun-bg text-turun",
  pemantauan: "bg-turun-bg text-turun", uma: "bg-kuning-bg text-kuning", penjelasan: "bg-kuning-bg text-kuning", kepemilikan: "bg-aksen-lembut text-aksen",
  aksi: "bg-aksen-lembut text-aksen", fakta: "bg-aksen-lembut text-aksen",
};
const pilih = ref("penting");
const data = ref(null);
const isi = ref([]);
const memuat = ref(false);
const halaman = ref(0);

async function muat(lanjut = false) {
  memuat.value = true;
  const h = lanjut ? halaman.value + 1 : 0;
  const k = props.kode;
  const r = await ambil(`pengumuman?kode=${k}&kategori=${pilih.value}&halaman=${h}&ukuran=${UKURAN}`).catch(() => null);
  if (k !== props.kode) return;
  memuat.value = false;
  if (!r) return;
  data.value = r;
  halaman.value = h;
  isi.value = lanjut ? [...isi.value, ...r.data] : r.data;
}
watch(() => props.kode, () => {
  data.value = null;
  isi.value = [];
  pilih.value = "penting";
  if (props.kode) muat();
}, { immediate: true });
watch(pilih, () => muat());

const pilihan = computed(() => {
  const d = data.value;
  if (!d) return [];
  return [{ id: "penting", label: "Penting", n: d.penting }, { id: "semua", label: "Semua", n: d.semua }, ...d.kategori];
});
const tgl = (t) => new Date(t).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
const jam = (t) => new Date(t).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" });
const sisa = computed(() => (data.value ? data.value.total - isi.value.length : 0));
const ket = computed(() => {
  const d = data.value;
  if (!d) return "Keterbukaan informasi IDX";
  const dari = d.dari ? new Date(d.dari).toLocaleDateString("id-ID", { month: "short", year: "numeric" }) : "";
  return `Keterbukaan informasi IDX sejak ${dari} · ${d.semua.toLocaleString("id-ID")} pengumuman · "Penting" menyembunyikan laporan rutin, laporan keuangan, dan obligasi`;
});
</script>

<template>
  <Panel judul="Pengumuman & aksi korporasi" :ket="ket" rapat>
    <Kerangka v-if="!data" class="px-6 pb-5" jenis="baris" :n="5" />
    <template v-else-if="data.semua">
      <div class="flex flex-wrap gap-1.5 px-6 pb-4">
        <button v-for="c in pilihan" :key="c.id" type="button" class="h-7 rounded-full border px-3 text-xs transition"
          :class="pilih === c.id ? 'border-aksen bg-aksen-lembut text-aksen' : 'border-garis text-muted hover:text-ink'" @click="pilih = c.id">
          {{ c.label }} <span class="tabular-nums opacity-70">{{ c.n }}</span>
        </button>
      </div>
      <div class="relative">
        <div v-if="memuat && !isi.length" class="px-6 pb-5"><Pemutar teks="Memuat pengumuman..." /></div>
        <p v-else-if="!isi.length" class="m-0 px-6 pb-5 text-[13px] text-muted">Tidak ada pengumuman di kategori ini.</p>
        <div v-for="x in isi" :key="x.id" class="flex gap-4 border-t border-garis px-6 py-3">
          <div class="w-[88px] shrink-0 text-xs text-muted tabular-nums">
            <div class="text-ink-2">{{ tgl(x.tgl) }}</div>
            <div>{{ jam(x.tgl) }}</div>
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-start gap-2">
              <span class="chip shrink-0" :class="WARNA[x.kategori] || 'bg-surface-2 text-ink-2'">{{ x.label }}</span>
              <span class="min-w-0 text-[13px] leading-snug">{{ x.judul }}</span>
            </div>
            <div v-if="x.lampiran.length" class="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-xs">
              <a v-for="(a, i) in x.lampiran" :key="a.url" :href="a.url" target="_blank" rel="noopener" :title="a.nama"
                class="inline-flex items-center gap-1 text-muted hover:text-aksen">
                <component :is="a.utama ? FileText : Paperclip" class="h-3.5 w-3.5" />{{ a.utama ? "Dokumen" : `Lampiran ${x.lampiran.slice(0, i + 1).filter((z) => !z.utama).length}` }}<ExternalLink class="h-3 w-3 opacity-60" />
              </a>
            </div>
          </div>
        </div>
      </div>
      <div class="flex items-center justify-between gap-3 border-t border-garis px-6 py-3 text-xs text-muted">
        <span>Menampilkan {{ isi.length }} dari {{ data.total.toLocaleString("id-ID") }}</span>
        <button v-if="sisa > 0" type="button" class="tombol" :disabled="memuat" @click="muat(true)">{{ memuat ? "Memuat..." : `Muat ${Math.min(UKURAN, sisa)} lagi` }}</button>
      </div>
    </template>
    <p v-else class="m-0 px-6 pb-5 text-[13px] text-muted">Belum ada pengumuman untuk emiten ini. Data pengumuman diimpor lewat Sumber data di Beranda.</p>
  </Panel>
</template>

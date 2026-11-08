<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { ambil } from "@/api/client";
import { pakaiPekerjaan } from "@/composables/pekerjaan";
import HeaderStrategi from "@/components/common/HeaderStrategi.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import Panel from "@/components/common/Panel.vue";
import RencanaTab from "@/views/riset/pertumbuhan/RencanaTab.vue";
import HistorisTab from "@/views/riset/pertumbuhan/HistorisTab.vue";
import CaraTab from "@/views/riset/pertumbuhan/CaraTab.vue";
import { pr, bulanTeks } from "@/views/riset/pertumbuhan/bantu";

defineProps({ sub: { type: String, default: "rencana" } });
const emit = defineEmits(["sub"]);

const SUB = [["rencana", "Rencana & daftar belanja"], ["historis", "Data historis"], ["cara", "Cara kerja & aturan"]];
const LANGKAH = [
  { judul: "Setor tiap bulan", teks: "Jumlah tetap, tanggal yang sama. Paling mudah lewat beli rutin otomatis di aplikasi." },
  { judul: "Bagi separuh-separuh", teks: "Separuh ke reksa dana saham syariah Indonesia, separuh ke reksa dana saham syariah global." },
  { judul: "Seimbangkan tiap Desember", teks: "Kalau satu bagian sudah lebih besar, pindahkan selisihnya supaya kembali 50/50." },
  { judul: "Tahan minimal 5 tahun", teks: "Jangan dijual saat turun. Daftar produk dicek ulang tiap Januari." },
];

const dasar = ref(null);
const rencana = ref(null);
const siap = ref(false);
const memuat = ref(false);
const kerja = pakaiPekerjaan();
const setoran = ref(1000000);
const modalAwal = ref(0);
const aplikasi = ref("semua");

const muatDasar = async () => {
  dasar.value = await ambil("pertumbuhan").catch(() => null);
};
const muatRencana = async () => {
  memuat.value = true;
  const q = new URLSearchParams({ setoran: setoran.value || 0, modal_awal: modalAwal.value || 0, aplikasi: aplikasi.value });
  rencana.value = await ambil(`pertumbuhan/rencana?${q}`).catch(() => null);
  memuat.value = false;
  siap.value = true;
};
const muatSemua = async () => {
  await Promise.all([muatDasar(), muatRencana()]);
};
let jeda = null;
watch([setoran, modalAwal, aplikasi], () => {
  clearTimeout(jeda);
  jeda = setTimeout(muatRencana, 300);
});
onMounted(async () => {
  await muatSemua();
  await kerja.lanjutkan("pertumbuhan_hitung", muatSemua);
});
const hitungUlang = () => kerja.mulai("aksi/pertumbuhan_hitung", {}, muatSemua);

const ada = computed(() => rencana.value?.ada && dasar.value?.ada);
const harapan = computed(() => {
  const i = dasar.value?.indeks?.["50/50"];
  if (!i) return "";
  return `di data indeks Jun 2001 – Okt 2026, campuran 50/50 rata-rata ${pr(i.cagr)} per tahun dalam rupiah dan tidak pernah rugi dalam periode 10 tahun mana pun, tapi pernah turun ${pr(Math.abs(i.dd), 0)} dari puncak. Data reksa dana nyata baru ada sejak 2016. Hasil masa lalu, bukan janji.`;
});
const chip = computed(() => [
  { teks: "Lolos uji setelah data diketahui · bukan jaminan", kelas: "bg-kuning-bg text-kuning" },
  { teks: "Risiko tinggi · minimal 5 tahun", kelas: "bg-turun-bg text-turun" },
  ...(dasar.value?.ada ? [{ teks: `Data s/d ${bulanTeks(dasar.value.periode.kategori[1])}`, kelas: "bg-surface-2 text-ink-2" }] : []),
]);
</script>

<template>
  <div class="space-y-5">
    <HeaderStrategi judul="Portofolio Pertumbuhan Syariah" :chip="chip" :sub="sub" :pilihan="SUB" :langkah="LANGKAH" :harapan="harapan" @sub="emit('sub', $event)"
      ringkas="Cara investasi jangka panjang (bukan trading): setor rutin tiap bulan ke reksa dana saham syariah Indonesia dan global, masing-masing separuh, dihitung dalam rupiah. Tujuannya uang tumbuh dan tidak bergantung ke nasib satu negara saja." />
    <Kerangka v-if="!siap" jenis="kartu" :n="3" kolom="grid-cols-1 md:grid-cols-3" />
    <template v-else-if="ada">
      <RencanaTab v-if="sub === 'rencana'" v-model:setoran="setoran" v-model:modal-awal="modalAwal" v-model:aplikasi="aplikasi" :r="rencana" :d="dasar" :memuat="memuat" @sub="emit('sub', $event)" />
      <HistorisTab v-else-if="sub === 'historis'" :r="rencana" :d="dasar" />
      <CaraTab v-else :d="dasar" :kerja="kerja" @hitung="hitungUlang" />
    </template>
    <template v-else>
      <Panel judul="Belum ada hasil hitungan"><p class="m-0 text-[13px] text-ink-2">Tekan "Hitung ulang" di bawah (±1 menit).</p></Panel>
      <CaraTab :d="null" :kerja="kerja" @hitung="hitungUlang" />
    </template>
  </div>
</template>

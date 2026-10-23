<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { X, Plus } from "lucide-vue-next";
import { ambil, persen, kelasPersen } from "../util.js";
import Panel from "./Panel.vue";
import Kerangka from "./Kerangka.vue";
import Pemutar from "./Pemutar.vue";
import Segmen from "./Segmen.vue";
import Logo from "./Logo.vue";
import GrafikBanding from "./GrafikBanding.vue";

const MAKS = 4;
const WARNA = ["--series-1", "--series-2", "--series-4", "--series-3"];
const KELAS_WARNA = ["bg-s1", "bg-s2", "bg-s4", "bg-s3"];
const baca = (k, awal) => {
  try {
    const v = localStorage.getItem(k);
    return v == null ? awal : JSON.parse(v);
  } catch {
    return awal;
  }
};
const simpan = (k, v) => {
  try {
    localStorage.setItem(k, JSON.stringify(v));
  } catch {
    return;
  }
};

const pilihan = ref([]);
const kode = ref(baca("etf_banding", ["SPUS", "SPY"]));
const periode = ref(baca("etf_banding_periode", "5y"));
const rupiah = ref(baca("etf_banding_rupiah", false));
const tambah = ref("");
const hasil = ref(null);
const memuat = ref(false);

onMounted(async () => {
  pilihan.value = await ambil("etf/pilihan").catch(() => []);
});

async function muat() {
  simpan("etf_banding", kode.value);
  simpan("etf_banding_periode", periode.value);
  simpan("etf_banding_rupiah", rupiah.value);
  if (kode.value.length < 2) {
    hasil.value = null;
    return;
  }
  memuat.value = true;
  hasil.value = await ambil(`etf/banding?kode=${kode.value.join(",")}&periode=${periode.value}&rupiah=${rupiah.value}`).catch(() => ({ error: "Gagal memuat" }));
  memuat.value = false;
}
watch([kode, periode, rupiah], muat, { deep: true, immediate: true });
watch(tambah, (k) => {
  if (k && !kode.value.includes(k) && kode.value.length < MAKS) kode.value = [...kode.value, k];
  tambah.value = "";
});
const hapus = (k) => (kode.value = kode.value.filter((x) => x !== k));
const info = (k) => pilihan.value.find((p) => p.kode === k) || { kode: k };
const tersisa = computed(() => pilihan.value.filter((p) => !kode.value.includes(p.kode)));
const kelompok = computed(() => [
  ["ETF Indonesia (syariah)", tersisa.value.filter((p) => p.sumber === "idx")],
  ["Luar negeri · syariah", tersisa.value.filter((p) => p.sumber === "luar" && p.syariah)],
  ["Luar negeri · bukan syariah", tersisa.value.filter((p) => p.sumber === "luar" && !p.syariah)],
]);
const urutTampil = computed(() => (hasil.value?.seri ? Object.keys(hasil.value.seri) : []));
const warnaDari = (k) => WARNA[kode.value.indexOf(k)] || WARNA[0];
const kelasDari = (k) => KELAS_WARNA[kode.value.indexOf(k)] || KELAS_WARNA[0];

const BARIS = [
  ["total", "Total hasil", "Kalau membeli di awal periode lalu ditahan sampai sekarang (termasuk dividen)", 1],
  ["per_tahun", "Rata-rata per tahun", "Pertumbuhan rata-rata tiap tahun (CAGR)", 1],
  ["dd", "Turun terdalam", "Penurunan terbesar dari titik tertinggi. Gambaran 'paling sakit' yang pernah terjadi", 1],
  ["vol", "Gejolak per tahun", "Seberapa liar naik-turunnya (volatilitas). Makin kecil makin tenang", 0],
  ["tahun_terbaik", "Tahun terbaik", "", 1],
  ["tahun_terburuk", "Tahun terburuk", "", 1],
];
const terbaik = (kunci, lebihBesar = true) => {
  const m = hasil.value?.metrik;
  if (!m) return null;
  const v = Object.entries(m).filter(([, x]) => x[kunci] != null);
  if (!v.length) return null;
  return v.sort((a, b) => (lebihBesar ? b[1][kunci] - a[1][kunci] : a[1][kunci] - b[1][kunci]))[0][0];
};
const ringkas = computed(() => {
  const m = hasil.value?.metrik;
  if (!m) return [];
  const t = terbaik("per_tahun"), s = terbaik("dd"), v = terbaik("vol", false);
  const r = [];
  if (t) r.push(`Paling tinggi hasilnya: ${t} (${persen(m[t].per_tahun, 1)} per tahun).`);
  if (s) r.push(`Paling tahan saat pasar jatuh: ${s} (turun terdalam ${persen(m[s].dd, 1)}).`);
  if (v && v !== s) r.push(`Paling tenang geraknya: ${v}.`);
  const k = hasil.value.korelasi;
  const pasangan = [];
  for (let i = 0; i < urutTampil.value.length; i++) for (let j = i + 1; j < urutTampil.value.length; j++) pasangan.push([urutTampil.value[i], urutTampil.value[j], k[urutTampil.value[i]][urutTampil.value[j]]]);
  const mirip = pasangan.filter((p) => p[2] >= 0.9);
  const beda = pasangan.filter((p) => p[2] < 0.5);
  if (mirip.length) r.push(`${mirip.map((p) => `${p[0]} dan ${p[1]}`).join(", ")} bergerak hampir sama (korelasi ≥ 0,9): memegang keduanya tidak banyak menambah penyebaran risiko.`);
  if (beda.length) r.push(`${beda.map((p) => `${p[0]} dan ${p[1]}`).join(", ")} geraknya jauh berbeda (korelasi < 0,5): menggabungkannya membantu menyebar risiko.`);
  return r;
});
const warnaKor = (v) => (v >= 0.9 ? "bg-turun-bg text-turun" : v >= 0.7 ? "bg-kuning-bg text-kuning" : "bg-naik-bg text-naik");
</script>

<template>
  <div class="space-y-5">
    <div class="panel space-y-4 px-6 py-5">
      <div>
        <div class="text-[15px] font-medium">Pilih ETF yang mau dibandingkan</div>
        <p class="m-0 mt-1 text-[13px] text-ink-2">Minimal 2, maksimal {{ MAKS }}. Semua dihitung dari tanggal yang sama supaya adil, termasuk dividen.</p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <span v-for="k in kode" :key="k" class="inline-flex items-center gap-2 rounded-full border border-garis bg-surface py-1 pr-2 pl-1.5">
          <span class="h-3 w-3 rounded-full" :class="kelasDari(k)"></span>
          <Logo :jenis="info(k).sumber === 'idx' ? 'emiten' : 'etf'" :kunci="k" :teks="k" :ukuran="22" />
          <span class="text-[13px] font-medium">{{ k }}</span>
          <span v-if="!info(k).syariah && info(k).sumber" class="chip !h-4 !px-1.5 !text-[10px] bg-turun-bg text-turun">bukan syariah</span>
          <button class="grid h-5 w-5 place-items-center rounded-full text-muted hover:bg-surface-2 hover:text-ink" :title="`Hapus ${k}`" @click="hapus(k)"><X class="h-3.5 w-3.5" /></button>
        </span>
        <label v-if="kode.length < MAKS" class="relative inline-flex items-center">
          <Plus class="pointer-events-none absolute left-3 h-3.5 w-3.5 text-muted" />
          <select v-model="tambah" class="!h-9 !pl-8 text-[13px]">
            <option value="">Tambah ETF…</option>
            <optgroup v-for="[judul, isi] in kelompok" :key="judul" :label="judul">
              <option v-for="p in isi" :key="p.kode" :value="p.kode">{{ p.kode }} · {{ p.nama.slice(0, 50) }}</option>
            </optgroup>
          </select>
        </label>
      </div>
      <div class="flex flex-wrap items-center gap-3">
        <Segmen v-model="periode" kecil :pilihan="[['1y', '1 tahun'], ['3y', '3 tahun'], ['5y', '5 tahun'], ['10y', '10 tahun'], ['maks', 'Semua data']]" />
        <Segmen :model-value="rupiah ? 'rp' : 'asli'" kecil :pilihan="[['asli', 'Mata uang asli'], ['rp', 'Dalam rupiah']]" @update:model-value="rupiah = $event === 'rp'" />
      </div>
    </div>

    <p v-if="kode.length < 2" class="panel m-0 px-6 py-4 text-[13px] text-ink-2">Tambahkan minimal 2 ETF.</p>
    <p v-else-if="hasil?.error" class="panel m-0 px-6 py-4 text-[13px] text-turun">{{ hasil.error }}</p>
    <template v-else-if="!hasil">
      <Kerangka panel jenis="grafik" :tinggi="300" />
      <Kerangka panel jenis="tabel" :n="4" />
    </template>
    <template v-else-if="hasil">
      <div v-if="memuat" class="px-1"><Pemutar teks="Menghitung ulang perbandingan..." /></div>
      <Panel :judul="`Kalau modal 100 ditanam sejak ${hasil.mulai}`" :ket="`${hasil.tahun} tahun data bersama · semua dimulai dari 100 · ${hasil.rupiah ? 'dihitung dalam rupiah (ikut kurs)' : 'mata uang asli masing-masing'}${memuat ? ' · memuat…' : ''}`">
        <div class="mb-3 flex flex-wrap gap-2 text-xs text-ink-2">
          <span v-for="k in urutTampil" :key="k" class="inline-flex items-center gap-2 rounded-full bg-surface-2 px-3 py-1">
            <span class="h-0.5 w-4 rounded" :class="kelasDari(k)"></span>{{ k }}
            <b class="font-medium" :class="kelasPersen(hasil.metrik[k].total)">{{ persen(hasil.metrik[k].total, 0) }}</b>
          </span>
        </div>
        <GrafikBanding :label="hasil.tgl" :seri="hasil.seri" :warna-seri="urutTampil.map(warnaDari)" />
        <p class="m-0 mt-3 text-xs text-muted">Periode dimulai dari tanggal ETF termuda yang dipilih, supaya semua dihitung dari titik yang sama.</p>
      </Panel>

      <div v-if="ringkas.length" class="panel px-6 py-4">
        <div class="mb-2 text-[13px] font-medium">Ringkasnya</div>
        <ul class="m-0 list-disc space-y-1 pl-5 text-[13px] text-ink-2">
          <li v-for="r in ringkas" :key="r">{{ r }}</li>
        </ul>
      </div>

      <div class="grid gap-5 xl:grid-cols-[1.6fr_1fr]">
        <Panel judul="Perbandingan angka" ket="Arahkan kursor ke nama baris untuk penjelasannya" rapat>
          <div class="overflow-x-auto">
            <table class="tabel">
              <thead>
                <tr><th></th><th v-for="k in urutTampil" :key="k" class="!text-right"><span class="inline-flex items-center gap-1.5"><span class="h-2.5 w-2.5 rounded-full" :class="kelasDari(k)"></span>{{ k }}</span></th></tr>
              </thead>
              <tbody>
                <tr v-for="[kunci, label, ket, bertanda] in BARIS" :key="kunci">
                  <td class="text-ink-2" :title="ket">{{ label }}</td>
                  <td v-for="k in urutTampil" :key="k" class="text-right font-medium" :class="bertanda ? kelasPersen(hasil.metrik[k][kunci]) : ''">
                    {{ hasil.metrik[k][kunci] == null ? "–" : persen(hasil.metrik[k][kunci], 1, !!bertanda) }}
                  </td>
                </tr>
                <tr>
                  <td class="text-ink-2" title="Berapa tahun kalender yang hasilnya positif">Tahun yang naik</td>
                  <td v-for="k in urutTampil" :key="k" class="text-right">{{ hasil.metrik[k].tahun_naik }} dari {{ hasil.metrik[k].tahun_dihitung }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </Panel>
        <Panel judul="Seberapa mirip geraknya" ket="Korelasi mingguan: 1 = selalu bergerak bersama, 0 = tidak berhubungan" rapat>
          <div class="overflow-x-auto">
            <table class="tabel">
              <thead><tr><th></th><th v-for="k in urutTampil" :key="k" class="!text-center">{{ k }}</th></tr></thead>
              <tbody>
                <tr v-for="a in urutTampil" :key="a">
                  <td class="font-medium">{{ a }}</td>
                  <td v-for="b in urutTampil" :key="b" class="text-center">
                    <span v-if="a !== b" class="chip" :class="warnaKor(hasil.korelasi[a][b])">{{ hasil.korelasi[a][b].toLocaleString("id-ID") }}</span>
                    <span v-else class="text-muted">–</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="m-0 px-6 py-3 text-xs text-muted">Merah = geraknya hampir sama (kurang menyebar risiko). Hijau = geraknya berbeda (bagus untuk dikombinasikan).</p>
        </Panel>
      </div>
      <p class="m-0 text-xs text-muted">Hasil masa lalu tidak menjamin hasil ke depan. ETF bukan syariah ditampilkan sebagai pembanding. Bukan nasihat keuangan.</p>
    </template>
  </div>
</template>

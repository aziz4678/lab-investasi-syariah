<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { ambil } from "@/api/client";
import { pakaiPekerjaan } from "@/composables/pekerjaan";
import PanelPekerjaan from "@/components/sistem/PanelPekerjaan.vue";
import Panel from "@/components/common/Panel.vue";
import Segmen from "@/components/common/Segmen.vue";
import KpiTiles from "@/components/tren/KpiTiles.vue";
import KurvaModal from "@/components/charts/KurvaModal.vue";
import HeatmapBulanan from "@/components/charts/HeatmapBulanan.vue";
import Distribusi from "@/components/charts/Distribusi.vue";
import TabelTrade from "@/components/tren/TabelTrade.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import Pemutar from "@/components/common/Pemutar.vue";
import TeksWarna from "@/components/common/TeksWarna.vue";
import { persen } from "@/utils/format";

const daftar = ref([]);
const KET = {
  h11a_2020: { pendek: "2020-2026", isi: "Uji utama: saham syariah menurut DES OJK pada tanggal itu." },
  h11a_2020_konservatif: { pendek: "2020-2026 konservatif", isi: "Beli dibatalkan saat ARA terkunci, jual menunggu kalau ARB terkunci. Lebih realistis." },
  h11a_dev: { pendek: "2010-2019", isi: "Data pengembangan (daftar 217 saham, ada bias survivorship). Dipakai menyusun aturan." },
};
const versi = ref("");
const ringkasan = ref(null);
const ekuitas = ref([]);
const distribusi = ref([]);
const trade = ref([]);
const galat = ref("");
const muat = ref(false);
const contoh = computed(() => `contoh 1 simulasi Monte Carlo (seed ${ringkasan.value?.monte_carlo?.contoh_seed ?? 7})`);

async function isi(v) {
  muat.value = true;
  galat.value = "";
  try {
    [ringkasan.value, ekuitas.value, distribusi.value, trade.value] = await Promise.all([
      ambil(`ringkasan/${v}`), ambil(`ekuitas/${v}`), ambil(`distribusi/${v}`), ambil(`trade/${v}`),
    ]);
  } catch (e) {
    galat.value = `Gagal memuat data: ${e.message}. Pastikan API jalan (python -m uvicorn backend.api.main:app --port 8765).`;
  } finally {
    muat.value = false;
  }
}

const { kerja, galat: galatKerja, sibuk, mulai, lanjutkan } = pakaiPekerjaan();

async function muatVersi() {
  try {
    daftar.value = await ambil("versi");
    if (!daftar.value.some((d) => d.versi === versi.value)) versi.value = daftar.value[0]?.versi || "";
    else await isi(versi.value);
  } catch (e) {
    galat.value = `API tidak bisa dihubungi: ${e.message}`;
  }
}

function jalankan(jenis) {
  mulai(`aksi/${jenis}`, {}, jenis === "isi_backtest" ? muatVersi : null);
}

onMounted(async () => {
  await muatVersi();
  await lanjutkan("isi_backtest", muatVersi);
  if (!sibuk.value) await lanjutkan("impor_fundamental");
});

watch(versi, (v) => v && isi(v));
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <p class="m-0 min-w-0 flex-1 text-[13px] leading-relaxed text-ink-2">{{ KET[versi]?.isi || "Simulasi aturan di data masa lalu." }}<template v-if="ringkasan"> Periode {{ ringkasan.mulai }} s/d {{ ringkasan.akhir }}.</template> Bukan jaminan hasil ke depan.</p>
      <Pemutar v-if="muat && ringkasan" teks="Memuat versi..." />
      <Segmen v-model="versi" :pilihan="daftar.map((d) => [d.versi, KET[d.versi]?.pendek || d.label])" />
    </div>
    <div v-if="galat" class="panel px-5 py-3.5 text-turun">{{ galat }}</div>
    <template v-if="!ringkasan && !galat">
      <Kerangka panel jenis="stat" :n="6" :judul="false" kolom="grid-cols-2 md:grid-cols-3 xl:grid-cols-6" />
      <Kerangka panel jenis="grafik" :tinggi="320" />
      <Kerangka panel jenis="grafik" :tinggi="200" />
      <div class="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <Kerangka panel jenis="grafik" :tinggi="220" />
        <Kerangka panel :n="4" />
      </div>
      <Kerangka panel jenis="tabel" :n="6" logo />
    </template>
    <div v-else class="space-y-5 transition-opacity" :class="muat ? 'opacity-50' : ''">
    <KpiTiles :r="ringkasan" />
    <details v-if="ringkasan?.monte_carlo" class="group -mt-2 rounded-2xl bg-surface-2/60 px-4 py-2.5 text-xs leading-relaxed text-ink-2">
      <summary class="flex cursor-pointer list-none items-center gap-2 text-muted [&::-webkit-details-marker]:hidden">
        <span>Return per tahun dan penurunan terburuk = median {{ ringkasan.monte_carlo.n }} simulasi Monte Carlo. Angka lain, kurva, peta bulanan, dan tabel trade = {{ contoh }}.</span>
        <span class="ml-auto shrink-0 font-medium text-aksen group-open:hidden">Apa itu?</span><span class="ml-auto hidden shrink-0 font-medium text-aksen group-open:inline">Tutup</span>
      </summary>
      <div class="mt-2 space-y-1.5 border-t border-garis pt-2">
        <p class="m-0"><b class="font-medium text-ink">Kenapa perlu simulasi?</b> Follow Tren memegang maksimal 10 saham. Kalau sinyal beli lebih banyak dari slot kosong (misal 5 sinyal, slot tinggal 2), saham dipilih acak karena aturan tidak memberi prioritas. Pilihan acak ini ikut menentukan hasil: kebetulan dapat saham yang naik 500% atau yang kena stop.</p>
        <p class="m-0"><b class="font-medium text-ink">Caranya:</b> backtest diulang {{ ringkasan.monte_carlo.n }} kali dengan aturan sama, tiap kali memakai seed berbeda (seed = angka awal pengacak; seed sama selalu menghasilkan pilihan sama, jadi bisa diulang persis).</p>
        <p class="m-0"><b class="font-medium text-ink">Cara membaca:</b> median = hasil tengah dari {{ ringkasan.monte_carlo.n }} simulasi. p5–p95 = rentang tempat 90 dari {{ ringkasan.monte_carlo.n }} simulasi berada. Contoh seed {{ ringkasan.monte_carlo.contoh_seed }}: CAGR <TeksWarna :teks="persen(ringkasan.monte_carlo.contoh.cagr, 1)" />, DD <TeksWarna :teks="persen(ringkasan.monte_carlo.contoh.dd, 1)" />.</p>
        <p class="m-0"><b class="font-medium text-ink">Artinya untuk paper trade:</b> paper juga memilih acak (seed = tanggal), jadi hasil nyata bisa jatuh di mana saja dalam rentang ini, atau di luarnya.</p>
      </div>
    </details>
    <KurvaModal :ekuitas="ekuitas" :catatan="ringkasan?.monte_carlo ? contoh : ''" />
    <HeatmapBulanan :ekuitas="ekuitas" :per-tahun="ringkasan?.per_tahun" :catatan="ringkasan?.monte_carlo ? contoh : ''" />
    <div class="grid gap-4 lg:grid-cols-[2fr_1fr]">
      <Distribusi :distribusi="distribusi" />
      <Panel judul="Cara membaca">
        <div class="space-y-3 text-ink-2">
          <p class="m-0 mb-3">Kebanyakan trade berakhir rugi kecil. Untung datang dari sedikit trade besar di sisi kanan grafik sebaran.</p>
          <p class="m-0 mb-3">Itu sebabnya tidak ada target untung dan stop tidak dilonggarkan: memotong trade besar merusak strategi.</p>
          <p class="m-0">Bulan merah beruntun dan penurunan 30-40% dari puncak adalah bagian normal strategi ini.</p>
        </div>
      </Panel>
    </div>
    <TabelTrade :trade="trade" />
    </div>
    <Panel judul="Olah ulang data" ket="Pakai setelah ada data atau aturan baru · hitung ulang butuh beberapa menit">
      <template #aksi>
        <button class="tombol" :disabled="sibuk" @click="jalankan('impor_fundamental')">Impor fundamental</button>
        <button class="tombol" :disabled="sibuk" @click="jalankan('isi_backtest')">Hitung ulang backtest</button>
      </template>
      <p class="m-0 text-muted">Hasil di halaman ini otomatis diperbarui setelah perhitungan selesai.</p>
    </Panel>
    <PanelPekerjaan :kerja="kerja" :galat="galatKerja" />
  </div>
</template>

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
import HipotesisTren from "@/components/tren/HipotesisTren.vue";
import CaraKerjaTrade from "@/components/tren/CaraKerjaTrade.vue";
import IstilahTren from "@/components/tren/IstilahTren.vue";
import TabelTrade from "@/components/tren/TabelTrade.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import Pemutar from "@/components/common/Pemutar.vue";
import TeksWarna from "@/components/common/TeksWarna.vue";
import CaraKerjaBlend from "@/components/tren/CaraKerjaBlend.vue";
import { TriangleAlert } from "lucide-vue-next";
import { persen } from "@/utils/format";

const props = defineProps({ s: Object });
const b = computed(() => props.s?.backtest || {});
const blend = computed(() => b.value.cara_kerja === "blend");
const OLAH = computed(() => b.value.olah || []);
const daftar = ref([]);
const KET = computed(() => b.value.versi || {});
const versi = ref("");
const ringkasan = ref(null);
const ekuitas = ref([]);
const contohTrade = ref(undefined);
const tabel = ref(null);
const trade = ref([]);
const galat = ref("");
const muat = ref(false);
const periode = computed(() => (ringkasan.value ? `${ringkasan.value.mulai.slice(0, 4)}-${ringkasan.value.akhir.slice(0, 4)}` : ""));
const contoh = computed(() => `contoh 1 simulasi Monte Carlo (seed ${ringkasan.value?.monte_carlo?.contoh_seed ?? 7})`);

async function isi(v) {
  muat.value = true;
  galat.value = "";
  try {
    contohTrade.value = undefined;
    if (!blend.value) ambil(`tren52/contoh/${v}`).then((c) => { if (versi.value === v) contohTrade.value = c; }).catch(() => { if (versi.value === v) contohTrade.value = null; });
    [ringkasan.value, ekuitas.value, trade.value] = await Promise.all([ambil(`ringkasan/${v}`), ambil(`ekuitas/${v}`), ambil(`trade/${v}`)]);
  } catch (e) {
    galat.value = `Gagal memuat data: ${e.message}. Pastikan API jalan (python -m uvicorn backend.api.main:app --port 8765).`;
  } finally {
    muat.value = false;
  }
}

const { kerja, galat: galatKerja, sibuk, mulai, lanjutkan } = pakaiPekerjaan();

async function muatVersi() {
  try {
    daftar.value = (await ambil("versi")).filter((d) => KET.value[d.versi]);
    if (!daftar.value.some((d) => d.versi === versi.value)) versi.value = daftar.value[0]?.versi || "";
    else await isi(versi.value);
  } catch (e) {
    galat.value = `API tidak bisa dihubungi: ${e.message}`;
  }
}

function jalankan(jenis) {
  mulai(`aksi/${jenis}`, {}, jenis.startsWith("isi_backtest") ? muatVersi : null);
}

onMounted(async () => {
  await muatVersi();
  for (const [jenis] of OLAH.value) {
    if (sibuk.value) break;
    await lanjutkan(jenis, jenis.startsWith("isi_backtest") ? muatVersi : null);
  }
});

watch(versi, (v) => v && isi(v));
</script>

<template>
  <div class="space-y-5">
    <HipotesisTren :h="s?.hipotesis" :perjalanan="s?.perjalanan" />
    <p v-if="b.peringatan" class="m-0 flex items-start gap-2.5 rounded-2xl bg-kuning-bg px-5 py-3.5 text-[13px] leading-relaxed text-ink-2">
      <TriangleAlert class="mt-0.5 h-4 w-4 shrink-0 text-kuning" /><span>{{ b.peringatan }}</span>
    </p>
    <div class="flex flex-wrap items-center justify-between gap-3 pt-1">
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
    <KpiTiles :r="ringkasan" :jii="KET[versi]?.jii ?? ringkasan?.cagr_jii" />
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
        <p v-if="b.mc_catatan" class="m-0"><b class="font-medium text-ink">Khusus strategi ini:</b> {{ b.mc_catatan }}</p>
      </div>
    </details>
    <div class="flex items-center gap-3 pt-3"><span class="text-[15px] font-medium">Cara kerjanya</span><span class="text-xs text-muted">{{ b.cara_ket || "beli → hold → take profit / cut loss" }}, dengan data backtest {{ periode }}</span><span class="h-px flex-1 bg-garis" /></div>
    <CaraKerjaBlend v-if="blend" :r="ringkasan" :periode="periode" />
    <CaraKerjaTrade v-else :trade="trade" :r="ringkasan" :contoh="contohTrade" :periode="periode" />
    <div class="flex items-center gap-3 pt-3"><span class="text-[15px] font-medium">Hasil portofolio</span><span class="text-xs text-muted">semua trade digabung jadi satu modal</span><span class="h-px flex-1 bg-garis" /></div>
    <KurvaModal :ekuitas="ekuitas" :catatan="ringkasan?.monte_carlo ? contoh : ''" :seri="b.seri" :ket="b.kurva_ket" :info="b.kurva_info" />
    <HeatmapBulanan :ekuitas="ekuitas" :per-tahun="ringkasan?.per_tahun" :catatan="ringkasan?.monte_carlo ? contoh : ''" :trade="trade"
      :terpilih="{ tahun: tabel?.tahun || '', bulan: +(tabel?.bulan || 0) }" @pilih="(th, bl) => tabel?.saring(th, bl)" />
    <TabelTrade ref="tabel" :trade="trade" :ekuitas="ekuitas" :versi="versi" />
    </div>
    <IstilahTren :tambahan="s?.istilah" :nama="s?.nama" />
    <Panel judul="Olah ulang data" :ket="b.olah_ket || 'Pakai setelah ada data atau aturan baru · hitung ulang butuh beberapa menit'">
      <template #aksi>
        <button v-for="[jenis, label] in OLAH" :key="jenis" class="tombol" :disabled="sibuk" @click="jalankan(jenis)">{{ label }}</button>
      </template>
      <p class="m-0 text-muted">Hasil di halaman ini otomatis diperbarui setelah perhitungan selesai.</p>
    </Panel>
    <PanelPekerjaan :kerja="kerja" :galat="galatKerja" />
  </div>
</template>

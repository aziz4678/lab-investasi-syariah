<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { CircleAlert, TriangleAlert, Info, ChevronDown, RefreshCw } from "lucide-vue-next";
import { ambil, kirim } from "@/api/client";
import { statusHeartbeat } from "@/utils/heartbeat";

const data = ref(null);
const gagalAkses = ref(false);
const sekarang = ref(new Date());
const buka = ref(false);
const jalan = ref(false);
let waktu = null;

const muat = async () => {
  sekarang.value = new Date();
  try {
    data.value = await ambil("cek-kesehatan");
    gagalAkses.value = false;
  } catch {
    gagalAkses.value = true;
  }
};

onMounted(() => {
  muat();
  waktu = setInterval(muat, 300000);
});
onUnmounted(() => clearInterval(waktu));

const urutan = { gagal: 0, peringatan: 1, info: 2 };

const peta = {
  pemeriksa_tidak_jalan: { judul: "Pemeriksa otomatis", kalimat: (x) => x.pesan },
  pemeriksa_tidak_terjangkau: { judul: "Server", kalimat: () => "Server tidak bisa dihubungi, status uji maju tidak bisa dicek." },
  emas_telat: { judul: "Data emas", kalimat: () => "Data harga emas pembanding telat; selisih paper vs model tidak bisa dipercaya." },
  job_jadwal: { judul: "Jadwal harian", kalimat: (x) => (x.status === "gagal" ? "Ada pekerjaan penting di jadwal harian yang gagal atau tidak tercatat." : "Ada pekerjaan di jadwal harian yang gagal atau dilewati.") },
  seri_data: { judul: "Data harga", kalimat: (x) => (x.status === "gagal" ? "Ada data harga uji maju yang sudah lama tidak diperbarui." : "Ada data harga uji maju yang telat diperbarui.") },
  belum_mulai: { judul: "Sebelum 1 Des", kalimat: () => "Data uji maju sudah terisi atau aturan berubah padahal belum waktunya mulai." },
  pilih_etf_awal: { judul: "ETF emas awal", kalimat: (x) => (x.status === "gagal" ? "ETF emas awal belum terpilih dengan benar." : "ETF emas awal dipilih lewat cadangan, periksa alasannya.") },
  transaksi_pertama: { judul: "Transaksi pertama", kalimat: () => "Transaksi pertama H35/H37 belum masuk, padahal sudah lewat batas hari bursa ke-2." },
  batas_20_persen: { judul: "Batas 20%", kalimat: () => "Ada pembelian emas yang melewati batas 20% nilai transaksi ETF." },
  rem_15_hari: { judul: "Rem 15 hari", kalimat: () => "Pembelian emas belum selesai dalam 15 hari bursa." },
  hari_bolong: { judul: "Hari bolong", kalimat: () => "Ada hari bursa yang tidak tercatat di valuasi harian." },
  ketertinggalan: { judul: "Pencatatan tertinggal", kalimat: (x) => (x.status === "gagal" ? "Pencatatan harian tertinggal jauh dan tidak dikejar otomatis." : "Pencatatan harian tertinggal, akan dikejar jadwal berikutnya.") },
  kalender_libur: { judul: "Kalender libur", kalimat: (x) => (x.status === "peringatan" ? "Kalender libur bursa tahun berikutnya belum diisi." : "Kalender libur bursa belum diverifikasi ke kalender resmi IDX.") },
  parameter_mesin: { judul: "Parameter aturan", kalimat: () => "Parameter di kode tidak sama dengan aturan yang sudah dikunci." },
  sidik_paper: { judul: "Jejak data paper", kalimat: (x) => (x.status === "gagal" ? "Data paper lama berubah atau hilang." : "Jejak data paper perlu diperiksa.") },
};

const tentukan = (x) => {
  if (x.nama_cek?.startsWith("pengingat_")) {
    const kode = x.nama_cek.slice(10).toUpperCase();
    return { judul: `Pengingat ${kode}`, kalimat: () => `Evaluasi ${kode} sudah dekat. Siapkan waktu untuk meninjaunya.` };
  }
  return peta[x.nama_cek] || { judul: null, kalimat: (y) => y.pesan };
};
const judul = (x) => tentukan(x).judul || "Cek lain";
const kalimat = (x) => tentukan(x).kalimat(x) || x.pesan;

const heartbeat = computed(() => (data.value ? statusHeartbeat(data.value.waktu_cek_terakhir, sekarang.value, data.value.libur || [], data.value.pemasangan) : null));
const butirHeartbeat = computed(() => {
  if (gagalAkses.value) return { tanggal: null, nama_cek: "pemeriksa_tidak_terjangkau", status: "gagal", pesan: "" };
  if (heartbeat.value?.mati) return { tanggal: heartbeat.value.sejak, nama_cek: "pemeriksa_tidak_jalan", status: "gagal", pesan: heartbeat.value.pesan };
  if (heartbeat.value?.belum) return { tanggal: null, nama_cek: "pemeriksa_tidak_jalan", status: "info", pesan: heartbeat.value.pesan };
  return null;
});
const aktif = computed(() => {
  const dasar = gagalAkses.value ? [] : (data.value?.terbaru || []).filter((x) => x.status !== "ok");
  return [...(butirHeartbeat.value ? [butirHeartbeat.value] : []), ...dasar].sort((a, b) => (urutan[a.status] ?? 9) - (urutan[b.status] ?? 9));
});
const tertinggi = computed(() => aktif.value[0]?.status || "ok");
const tampil = computed(() => aktif.value.length > 0);
const utama = computed(() => aktif.value[0]);

const gaya = {
  gagal: { kotak: "border-red-200 bg-red-50 text-red-900 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-200", titik: "bg-red-500" },
  peringatan: { kotak: "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200", titik: "bg-amber-500" },
  info: { kotak: "border-sky-200 bg-sky-50 text-sky-900 dark:border-sky-500/30 dark:bg-sky-500/10 dark:text-sky-200", titik: "bg-sky-500" },
};
const ikon = computed(() => ({ gagal: CircleAlert, peringatan: TriangleAlert, info: Info })[tertinggi.value] || Info);

const relatif = (tgl) => {
  if (!tgl) return "";
  const a = new Date(`${String(tgl).slice(0, 10)}T00:00:00`);
  const h = new Date(sekarang.value);
  h.setHours(0, 0, 0, 0);
  const n = Math.round((h - a) / 86400000);
  if (n <= 0) return "hari ini";
  if (n === 1) return "kemarin";
  return `${n} hari lalu`;
};

const daftarDetail = computed(() => {
  const dasar = gagalAkses.value ? [] : data.value?.riwayat || [];
  const ada = butirHeartbeat.value && !dasar.some((x) => x.nama_cek === butirHeartbeat.value.nama_cek && x.tanggal === butirHeartbeat.value.tanggal);
  return [...(ada ? [butirHeartbeat.value] : []), ...dasar];
});

const jalankan = async () => {
  jalan.value = true;
  try {
    await kirim("aksi/cek_kesehatan_uji_maju");
    await new Promise((r) => setTimeout(r, 12000));
  } catch {
  } finally {
    await muat();
    jalan.value = false;
  }
};
</script>

<template>
  <section v-if="tampil" class="rounded-2xl border" :class="gaya[tertinggi].kotak" :data-status="tertinggi">
    <div class="flex items-center gap-3 px-4 py-2.5">
      <component :is="ikon" class="h-[18px] w-[18px] shrink-0" />
      <p class="m-0 min-w-0 flex-1 text-[13px] leading-snug">
        {{ kalimat(utama) }}
        <span v-if="aktif.length > 1" class="ml-1 whitespace-nowrap font-medium opacity-80">+{{ aktif.length - 1 }} lainnya</span>
      </p>
      <button type="button" class="inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-1 text-[12px] font-medium hover:bg-black/5 dark:hover:bg-white/10" :aria-expanded="buka" @click="buka = !buka">
        Detail
        <ChevronDown class="h-3.5 w-3.5 transition-transform" :class="buka ? 'rotate-180' : ''" />
      </button>
    </div>
    <div v-if="buka" class="space-y-2 border-t border-current/15 px-4 py-3 text-ink">
      <div class="flex items-start justify-between gap-3">
        <div class="flex items-center gap-1.5 text-[12px] font-medium text-ink-2">
          Cek kesehatan uji maju H35 &amp; H37
          <span class="inline-flex cursor-help" title="Pemeriksa hanya membaca; hasilnya disimpan di koleksi cek_kesehatan dan tidak pernah menulis ke data paper."><Info class="h-3.5 w-3.5 text-muted" /></span>
        </div>
        <div class="flex flex-col items-end gap-0.5">
          <button type="button" class="inline-flex items-center gap-1 rounded-full bg-surface-2 px-2.5 py-1 text-[11px] text-ink-2 disabled:opacity-60" :disabled="jalan" @click="jalankan">
            <RefreshCw class="h-3 w-3" :class="jalan ? 'animate-spin' : ''" />{{ jalan ? "Menjalankan…" : "Jalankan cek sekarang" }}
          </button>
          <span class="text-[10px] text-muted">Tidak dihitung sebagai jadwal</span>
        </div>
      </div>
      <p v-if="!daftarDetail.length" class="m-0 text-[13px] text-ink-2">Tidak ada masalah 30 hari terakhir.</p>
      <ul v-else class="m-0 list-none space-y-1.5 p-0">
        <li v-for="(x, i) in daftarDetail" :key="`${x.tanggal}|${x.nama_cek}|${i}`" class="flex items-start gap-2 text-[13px]">
          <span class="mt-1.5 h-2 w-2 shrink-0 rounded-full" :class="gaya[x.status].titik" />
          <div class="min-w-0 flex-1">
            <span class="font-medium">{{ judul(x) }}</span>
            <span class="text-ink-2"> · {{ kalimat(x) }}</span>
          </div>
          <span class="shrink-0 whitespace-nowrap text-[11px] text-muted">{{ relatif(x.tanggal) }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>

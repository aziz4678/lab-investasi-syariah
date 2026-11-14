<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { CircleAlert, TriangleAlert, Info, ChevronDown, RefreshCw } from "lucide-vue-next";
import { ambil, kirim } from "@/api/client";
import { tanggal } from "@/utils/format";
import { statusHeartbeat } from "@/utils/heartbeat";

const data = ref(null);
const gagalAkses = ref(false);
const sekarang = ref(new Date());
const buka = ref(false);
const jalan = ref(false);
let waktu = null;

async function muat() {
  sekarang.value = new Date();
  try {
    data.value = await ambil("cek-kesehatan");
    gagalAkses.value = false;
  } catch {
    gagalAkses.value = true;
  }
}

onMounted(() => {
  muat();
  waktu = setInterval(muat, 300000);
});
onUnmounted(() => clearInterval(waktu));

const heartbeat = computed(() => (data.value ? statusHeartbeat(data.value.waktu_cek_terakhir, sekarang.value, data.value.libur || []) : null));
const butirHeartbeat = computed(() => {
  if (gagalAkses.value) return { tanggal: null, nama_cek: "pemeriksa_tidak_terjangkau", status: "gagal", pesan: "Tidak bisa mengakses /api/cek-kesehatan — server atau pemeriksa bermasalah." };
  if (heartbeat.value?.mati) return { tanggal: heartbeat.value.sejak, nama_cek: "pemeriksa_tidak_jalan", status: "gagal", pesan: heartbeat.value.pesan };
  return null;
});
const aktif = computed(() => [...(butirHeartbeat.value ? [butirHeartbeat.value] : []), ...(gagalAkses.value ? [] : (data.value?.terbaru || []).filter((x) => x.status !== "ok"))]);
const tertinggi = computed(() => (butirHeartbeat.value ? "gagal" : data.value?.tertinggi || "ok"));
const tampil = computed(() => gagalAkses.value || (data.value && tertinggi.value !== "ok"));
const kelas = computed(() => ({ gagal: "bg-turun-bg text-turun", peringatan: "bg-kuning-bg text-kuning", info: "bg-surface-2 text-ink-2" })[tertinggi.value]);
const ikon = computed(() => ({ gagal: CircleAlert, peringatan: TriangleAlert, info: Info })[tertinggi.value] || Info);
const label = { gagal: "Gagal", peringatan: "Peringatan", info: "Info" };
const lencana = { gagal: "bg-turun-bg text-turun", peringatan: "bg-kuning-bg text-kuning", info: "bg-surface-2 text-ink-2" };

const perTanggal = computed(() => {
  const m = new Map();
  for (const x of data.value?.riwayat || []) {
    if (!m.has(x.tanggal)) m.set(x.tanggal, []);
    m.get(x.tanggal).push(x);
  }
  return [...m.entries()];
});

async function jalankan() {
  jalan.value = true;
  try {
    await kirim("aksi/cek_kesehatan_uji_maju");
    await new Promise((r) => setTimeout(r, 12000));
  } catch {
  } finally {
    await muat();
    jalan.value = false;
  }
}
</script>

<template>
  <section v-if="tampil" class="overflow-hidden rounded-3xl border border-border bg-surface" :data-status="tertinggi">
    <button type="button" class="flex w-full items-start gap-3 px-4 py-3.5 text-left" :class="kelas" :aria-expanded="buka" @click="buka = !buka">
      <component :is="ikon" class="mt-0.5 h-5 w-5 shrink-0" />
      <div class="min-w-0 flex-1">
        <div class="text-[14px] font-semibold">Cek kesehatan uji maju H35 &amp; H37<template v-if="data?.tanggal"> · {{ tanggal(data.tanggal) }}</template></div>
        <ul class="m-0 mt-1 list-none space-y-0.5 p-0 text-[13px]">
          <li v-for="x in aktif.slice(0, 3)" :key="x.nama_cek"><span class="font-medium">{{ x.nama_cek }}</span>: {{ x.pesan }}</li>
          <li v-if="aktif.length > 3" class="opacity-80">+ {{ aktif.length - 3 }} lainnya</li>
        </ul>
      </div>
      <ChevronDown class="mt-0.5 h-4 w-4 shrink-0 transition-transform" :class="buka ? 'rotate-180' : ''" />
    </button>
    <div v-if="buka" class="space-y-3 px-4 py-4 text-ink">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div class="text-[13px] font-medium">Riwayat 30 hari (hanya yang tidak ok)</div>
        <button type="button" class="inline-flex items-center gap-1.5 rounded-full bg-surface-2 px-3 py-1.5 text-[12px] text-ink-2 disabled:opacity-60" :disabled="jalan" @click="jalankan">
          <RefreshCw class="h-3.5 w-3.5" :class="jalan ? 'animate-spin' : ''" />{{ jalan ? "Menjalankan…" : "Jalankan cek sekarang" }}
        </button>
      </div>
      <p v-if="data?.waktu_cek_terakhir" class="m-0 text-[12px] text-muted">Cek terakhir berjalan {{ data.waktu_cek_terakhir.replace("T", " ") }}.</p>
      <div v-for="[tgl, daftar] in perTanggal" :key="tgl" class="rounded-2xl bg-surface-2 px-3.5 py-3">
        <div class="text-[12px] font-medium text-muted">{{ tanggal(tgl) }}</div>
        <div v-for="x in daftar" :key="x.nama_cek" class="mt-1.5 flex flex-wrap items-baseline gap-x-2 text-[13px]">
          <span class="rounded-full px-2 py-0.5 text-[11px] font-medium" :class="lencana[x.status]">{{ label[x.status] }}</span>
          <span class="font-medium">{{ x.nama_cek }}</span>
          <span class="text-ink-2">{{ x.pesan }}</span>
        </div>
      </div>
      <p class="m-0 text-[12px] text-muted">Pemeriksa hanya membaca; hasilnya disimpan di koleksi cek_kesehatan dan tidak pernah menulis ke data paper.</p>
    </div>
  </section>
</template>

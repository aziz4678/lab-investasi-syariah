<script setup>
import { ref, inject, onMounted } from "vue";
import { CalendarClock, ShieldCheck, FileCheck2, DatabaseBackup, ChevronDown } from "lucide-vue-next";
import { ambil, kirim } from "../util.js";
import { pakaiPekerjaan } from "../pekerjaan.js";
import Panel from "./Panel.vue";
import Kerangka from "./Kerangka.vue";
import PanelPekerjaan from "./PanelPekerjaan.vue";

const status = inject("status");
const muatStatus = inject("muatStatus");
const jadwal = ref(null);
const siap = ref(false);
const sibukJadwal = ref(false);
const galatJadwal = ref("");
const cadangan = ref([]);
const bukaPulih = ref(false);
const pilihan = ref("");
const konfirmasi = ref("");
const { kerja, galat, sibuk, mulai, lanjutkan } = pakaiPekerjaan();

async function muat() {
  [jadwal.value, cadangan.value] = await Promise.all([ambil("jadwal").catch(() => null), ambil("cadangan").catch(() => [])]);
  siap.value = true;
  if (!pilihan.value && cadangan.value.length) pilihan.value = cadangan.value[0].nama;
}

async function setelah() {
  await Promise.all([muat(), muatStatus()]);
}

function jalankan(jenis) {
  mulai(`aksi/${jenis}`, {}, setelah);
}

async function pulihkan() {
  await mulai("aksi_pulihkan", { nama: pilihan.value, konfirmasi: konfirmasi.value }, setelah);
  konfirmasi.value = "";
  bukaPulih.value = false;
}

async function alihJadwal() {
  sibukJadwal.value = true;
  galatJadwal.value = "";
  try {
    jadwal.value = await kirim("aksi_jadwal", { aktif: !jadwal.value?.ada });
  } catch (e) {
    galatJadwal.value = e.message;
  } finally {
    sibukJadwal.value = false;
  }
}

onMounted(async () => {
  await muat();
  for (const j of ["paper_cek", "des_perbarui", "cadangan", "pulihkan"]) {
    await lanjutkan(j, setelah);
    if (sibuk.value) break;
  }
});

function waktu(s) {
  return s ? new Date(s).toLocaleString("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "belum pernah";
}
</script>

<template>
  <Panel judul="Perawatan" ket="Otomatis harian dan keamanan data" rapat>
    <Kerangka v-if="!siap" jenis="tabel" :n="4" logo />
    <div v-else class="space-y-1 px-3 pb-3">
      <div class="rounded-2xl px-3 py-3 transition-colors hover:bg-surface-2/60">
        <div class="flex items-center gap-3">
          <CalendarClock class="h-4.5 w-4.5 shrink-0 text-muted" />
          <div class="min-w-0 flex-1">
            <div class="text-[13px] font-medium">Perbarui otomatis</div>
            <div class="text-xs text-muted">
              <template v-if="jadwal?.ada">Sen–Jum {{ jadwal.jam }} · berikutnya {{ waktu(jadwal.berikut) }}</template>
              <template v-else>Mati · perbarui manual tiap sore</template>
            </div>
          </div>
          <button role="switch" :aria-checked="!!jadwal?.ada" :disabled="sibukJadwal || !jadwal" @click="alihJadwal"
            class="relative h-6 w-11 shrink-0 rounded-full transition disabled:opacity-50" :class="jadwal?.ada ? 'bg-aksen' : 'bg-surface-3'">
            <span class="absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform" :class="jadwal?.ada ? 'translate-x-5' : ''"></span>
          </button>
        </div>
        <p v-if="jadwal?.ada" class="m-0 mt-2 pl-[30px] text-[11px] leading-snug text-muted">Perbarui paper, reksa dana & ETF, lalu data IDX/OJK yang perlu diperbarui lewat Chrome Lab, lalu backup. Komputer harus menyala; kalau mati, jalan saat komputer hidup lagi.<span v-if="jadwal.terakhir"> Terakhir {{ waktu(jadwal.terakhir) }}.</span></p>
        <p v-if="galatJadwal" class="m-0 mt-2 pl-[30px] text-xs text-turun">{{ galatJadwal }}</p>
      </div>

      <div class="flex items-center gap-3 rounded-2xl px-3 py-3 transition-colors hover:bg-surface-2/60">
        <ShieldCheck class="h-4.5 w-4.5 shrink-0 text-muted" />
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2 text-[13px] font-medium">Cek ulang paper
            <span v-if="status?.paper_cek" class="chip" :class="status.paper_cek.cocok ? 'bg-naik-bg text-naik' : 'bg-turun-bg text-turun'">{{ status.paper_cek.cocok ? "cocok" : `${status.paper_cek.jumlah_beda} beda` }}</span>
          </div>
          <div class="text-xs text-muted">{{ status?.paper_cek ? `${waktu(status.paper_cek.waktu)} · s/d ${status.paper_cek.sampai}` : "belum pernah" }}</div>
        </div>
        <button class="tombol shrink-0" :disabled="sibuk" @click="jalankan('paper_cek')">Cek</button>
      </div>

      <div class="flex items-center gap-3 rounded-2xl px-3 py-3 transition-colors hover:bg-surface-2/60">
        <FileCheck2 class="h-4.5 w-4.5 shrink-0 text-muted" />
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2 text-[13px] font-medium">DES OJK
            <span v-if="status?.des_perlu_update" class="chip bg-kuning-bg text-kuning">cek</span>
          </div>
          <div class="truncate text-xs text-muted">{{ (status?.des_periode || "–").replace("/D.04/", "/") }} · dicek {{ waktu(status?.des_dicek) }}</div>
        </div>
        <button class="tombol shrink-0" :disabled="sibuk" @click="jalankan('des_perbarui')">Cek</button>
      </div>

      <div class="rounded-2xl px-3 py-3 transition-colors hover:bg-surface-2/60">
        <div class="flex items-center gap-3">
          <DatabaseBackup class="h-4.5 w-4.5 shrink-0 text-muted" />
          <div class="min-w-0 flex-1">
            <div class="text-[13px] font-medium">Backup database</div>
            <div class="text-xs text-muted">{{ cadangan.length }} backup · terakhir {{ waktu(status?.backup_terakhir) }}</div>
          </div>
          <button class="tombol shrink-0" :disabled="sibuk" @click="jalankan('cadangan')">Backup</button>
        </div>
        <button v-if="cadangan.length" class="mt-2 ml-[30px] inline-flex items-center gap-1 text-xs text-muted hover:text-ink" @click="bukaPulih = !bukaPulih">
          Pulihkan dari backup<ChevronDown class="h-3.5 w-3.5 transition-transform" :class="bukaPulih ? 'rotate-180' : ''" />
        </button>
        <div v-if="bukaPulih" class="mt-2 ml-[30px] space-y-2">
          <select v-model="pilihan" class="w-full">
            <option v-for="c in cadangan" :key="c.nama" :value="c.nama">{{ waktu(c.waktu) }} · {{ c.alasan }} · {{ c.dokumen.toLocaleString("id-ID") }} dok</option>
          </select>
          <p class="m-0 text-[11px] leading-snug text-muted">Semua data diganti isi backup ini. Kondisi sekarang dibackup dulu otomatis. Ketik <b class="text-ink">PULIHKAN</b>.</p>
          <div class="flex gap-2">
            <input v-model="konfirmasi" placeholder="PULIHKAN" class="min-w-0 flex-1" />
            <button class="tombol shrink-0 !bg-turun-bg !text-turun" :disabled="sibuk || konfirmasi !== 'PULIHKAN' || !pilihan" @click="pulihkan">Pulihkan</button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="kerja || galat" class="px-3 pb-3"><PanelPekerjaan :kerja="kerja" :galat="galat" /></div>
  </Panel>
</template>

<script setup>
import { ref, computed, onMounted, inject } from "vue";
import { ChevronDown, RefreshCw, Zap, MousePointerClick, Globe, Copy, Check, ExternalLink, CalendarClock, CircleAlert, CircleCheck, Bot } from "lucide-vue-next";
import { ambil } from "../util.js";
import { pakaiPekerjaan } from "../pekerjaan.js";
import Panel from "./Panel.vue";
import Kerangka from "./Kerangka.vue";
import PanelPekerjaan from "./PanelPekerjaan.vue";

const muatStatus = inject("muatStatus", null);
const data = ref([]);
const siap = ref(false);
const buka = ref(new Set());
const skrip = ref({});
const lihatSkrip = ref(new Set());
const tersalin = ref("");
const galatSalin = ref("");
const { kerja, galat, sibuk, mulai, lanjutkan } = pakaiPekerjaan();

const CARA = {
  otomatis: { l: "Otomatis", ikon: Zap },
  tombol: { l: "Lewat tombol", ikon: MousePointerClick },
  browser: { l: "Manual lewat browser", ikon: Globe },
};

const jumlahPerlu = computed(() => data.value.filter((s) => s.perlu).length);

async function muat() {
  data.value = await ambil("sumber_data").catch(() => []);
  siap.value = true;
  if (muatStatus) await muatStatus();
}

function alih(set, id) {
  const s = new Set(set.value);
  if (s.has(id)) s.delete(id);
  else s.add(id);
  set.value = s;
}

async function ambilSkrip(nama) {
  if (!skrip.value[nama]) {
    const r = await fetch(`/api/skrip/${nama}`);
    if (!r.ok) throw new Error(`script ${nama} tidak bisa dimuat`);
    skrip.value = { ...skrip.value, [nama]: await r.text() };
  }
  return skrip.value[nama];
}

async function salin(nama) {
  galatSalin.value = "";
  try {
    const isi = await ambilSkrip(nama);
    await navigator.clipboard.writeText(isi);
    tersalin.value = nama;
    setTimeout(() => (tersalin.value = tersalin.value === nama ? "" : tersalin.value), 2500);
  } catch (e) {
    galatSalin.value = `Gagal menyalin: ${e.message}. Buka 'Lihat script' lalu salin manual.`;
  }
}

async function alihSkrip(nama) {
  await ambilSkrip(nama).catch(() => null);
  alih(lihatSkrip, nama);
}

function jalankan(jenis) {
  mulai(`aksi/${jenis}`, {}, muat);
}

const lab = ref(null);
const membukaLab = ref(false);
const galatLab = ref("");
async function muatLab() {
  lab.value = await ambil("chrome_lab").catch(() => ({ jalan: false }));
}
async function bukaLab() {
  membukaLab.value = true;
  galatLab.value = "";
  try {
    const r = await fetch("/api/chrome_lab/buka", { method: "POST" });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `status ${r.status}`);
    lab.value = await r.json();
  } catch (e) {
    galatLab.value = `Chrome Lab gagal dibuka: ${e.message}`;
  }
  membukaLab.value = false;
}
function otomatis(id) {
  mulai(`otomatis/${id}`, {}, async () => {
    await muat();
    await muatLab();
  });
}

function waktu(s) {
  return s ? new Date(s).toLocaleString("id-ID", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : null;
}

onMounted(async () => {
  muatLab();
  await muat();
  buka.value = new Set(data.value.filter((s) => s.perlu && s.cara === "browser").map((s) => s.id));
  for (const s of data.value) {
    if (!s.tombol) continue;
    await lanjutkan(s.tombol, muat);
    if (sibuk.value) break;
  }
  if (!sibuk.value) await lanjutkan("otomatis", muat);
});
</script>

<template>
  <Panel judul="Sumber data & cara pembaruan" ket="Status dihitung dari jadwal terbit tiap data. Data tanpa API diambil lewat browser, lalu diimpor dengan tombol" rapat>
    <template #aksi>
      <span v-if="data.length" class="chip !h-7 !px-3 !text-xs" :class="jumlahPerlu ? 'bg-kuning-bg text-kuning' : 'bg-naik-bg text-naik'">
        {{ jumlahPerlu ? `${jumlahPerlu} perlu diperbarui` : "Semua terbaru" }}
      </span>
    </template>
    <div class="mx-6 mb-3 flex flex-wrap items-center gap-3 rounded-2xl bg-surface-2 px-4 py-3">
      <Globe class="h-5 w-5 shrink-0 text-muted" />
      <div class="min-w-[220px] flex-1">
        <div class="text-[13px] font-medium">Chrome Lab <span class="chip ml-1" :class="lab?.jalan ? 'bg-naik-bg text-naik' : 'bg-surface text-muted'">{{ lab == null ? "…" : lab.jalan ? (lab.idx_siap ? "terbuka · IDX siap" : "terbuka") : "tertutup" }}</span></div>
        <div class="text-xs text-muted">Chrome terpisah (profil khusus) untuk menjalankan script IDX/OJK otomatis lewat tombol "Ambil otomatis". Jangan login akun pribadi di Chrome ini.</div>
        <div v-if="galatLab" class="text-xs text-turun">{{ galatLab }}</div>
      </div>
      <button class="tombol !bg-surface" :disabled="membukaLab || lab?.jalan" @click="bukaLab">{{ lab?.jalan ? "Sudah terbuka" : membukaLab ? "Membuka..." : "Buka Chrome Lab" }}</button>
      <button class="text-xs text-muted hover:text-ink" @click="muatLab">Cek</button>
    </div>
    <Kerangka v-if="!siap" jenis="tabel" :n="6" logo />
    <div class="px-3 pb-2">
      <div v-for="s in data" :key="s.id" class="border-t border-garis first:border-t-0">
        <div class="flex flex-wrap items-center gap-x-4 gap-y-2 px-3 py-3.5">
          <component :is="s.perlu ? CircleAlert : CircleCheck" class="h-5 w-5 shrink-0" :class="s.perlu ? 'text-kuning' : 'text-naik'" />
          <div class="min-w-[240px] flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <span class="font-medium">{{ s.nama }}</span>
              <span class="chip" :class="s.perlu ? 'bg-kuning-bg text-kuning' : 'bg-naik-bg text-naik'">{{ s.perlu ? "Perlu diperbarui" : "Terbaru" }}</span>
              <span class="chip bg-surface-2 text-muted"><component :is="CARA[s.cara].ikon" class="h-3 w-3" />{{ CARA[s.cara].l }}</span>
            </div>
            <div class="mt-0.5 text-xs" :class="s.perlu ? 'text-kuning' : 'text-muted'">
              {{ s.alasan || `${s.terakhir || "belum ada"}` }}
            </div>
            <div class="mt-0.5 flex flex-wrap items-center gap-x-3 text-[11px] text-muted">
              <span v-if="s.alasan">Sekarang: {{ s.terakhir || "belum ada" }}</span>
              <span v-if="s.diimpor">diimpor {{ waktu(s.diimpor) }}</span>
              <span v-else-if="s.dicek">dicek {{ waktu(s.dicek) }}</span>
              <span class="inline-flex items-center gap-1"><CalendarClock class="h-3 w-3" />berikutnya {{ s.berikutnya }}</span>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button v-if="s.otomatis" class="tombol" :class="s.perlu ? '!bg-aksen !text-aksen-teks' : ''" :disabled="sibuk" @click="otomatis(s.id)"
              title="Jalankan script di Chrome Lab lalu impor otomatis"><Bot class="h-3.5 w-3.5" />Ambil otomatis</button>
            <button v-if="s.tombol" class="tombol" :class="s.perlu && s.cara !== 'browser' ? '!bg-aksen !text-aksen-teks' : ''" :disabled="sibuk" @click="jalankan(s.tombol)">
              <RefreshCw v-if="s.cara !== 'browser'" class="h-3.5 w-3.5" />{{ s.label_tombol }}
            </button>
            <button class="grid h-9 w-9 place-items-center rounded-full text-muted hover:bg-surface-2 hover:text-ink" :aria-label="`Cara pembaruan ${s.nama}`" @click="alih(buka, s.id)">
              <ChevronDown class="h-4 w-4 transition-transform" :class="buka.has(s.id) ? 'rotate-180' : ''" />
            </button>
          </div>
        </div>
        <div v-if="buka.has(s.id)" class="mx-3 mb-3 rounded-2xl bg-surface-2 px-5 py-4">
          <div class="mb-2 text-xs text-muted">Sumber: {{ s.sumber }} · dipakai: {{ s.dipakai.join(", ") }} · jadwal: {{ s.frekuensi }}</div>
          <ol class="m-0 list-decimal space-y-1.5 pl-5 text-[13px] text-ink-2">
            <li v-for="l in s.langkah" :key="l" class="break-words">{{ l }}</li>
          </ol>
          <div v-if="s.skrip" class="mt-4 flex flex-wrap items-center gap-2">
            <a :href="s.url" target="_blank" rel="noopener" class="tombol !bg-surface no-underline"><ExternalLink class="h-3.5 w-3.5" />Buka halaman {{ s.url.includes('ojk.go.id') ? 'OJK' : 'IDX' }}</a>
            <button class="tombol-utama" @click="salin(s.skrip)">
              <component :is="tersalin === s.skrip ? Check : Copy" class="h-3.5 w-3.5" />{{ tersalin === s.skrip ? "Tersalin, tempel di Console" : "Salin script" }}
            </button>
            <button class="tombol !bg-surface" :disabled="sibuk" @click="jalankan(s.tombol)">{{ s.label_tombol }}</button>
            <button class="text-xs text-muted hover:text-ink" @click="alihSkrip(s.skrip)">{{ lihatSkrip.has(s.skrip) ? "Sembunyikan script" : "Lihat script" }}</button>
          </div>
          <p v-if="galatSalin" class="m-0 mt-2 text-xs text-turun">{{ galatSalin }}</p>
          <pre v-if="s.skrip && lihatSkrip.has(s.skrip)" class="m-0 mt-3 max-h-72 overflow-auto rounded-xl bg-surface px-4 py-3 font-mono text-[11px] leading-relaxed whitespace-pre-wrap break-all text-ink-2">{{ skrip[s.skrip] || "memuat..." }}</pre>
        </div>
      </div>
    </div>
    <div v-if="kerja || galat" class="px-3 pb-3"><PanelPekerjaan :kerja="kerja" :galat="galat" /></div>
  </Panel>
</template>

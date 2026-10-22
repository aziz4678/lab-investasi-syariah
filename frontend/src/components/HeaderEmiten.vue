<script setup>
import Logo from "./Logo.vue";
import { ref, computed, watch, inject } from "vue";
import { Building2, Users, UserRound, Globe, MapPin, Phone, CalendarDays, ArrowRight } from "lucide-vue-next";
import { ambil, rupiah, ringkas } from "../util.js";
import Kerangka from "./Kerangka.vue";

const props = defineProps({ kode: String, syariah: Boolean, kini: Object, posisi: Object, labelPosisi: String, memuat: Boolean });
const pindahTab = inject("pindahTab");
const f = ref(null);
const penuh = ref(false);
const asli = ref(false);

watch(() => props.kode, async (k) => {
  f.value = null;
  penuh.value = false;
  if (k) f.value = await ambil(`profil/${k}`).catch(() => ({ ada: false }));
}, { immediate: true });

const idk = ref(null);
watch(() => props.kode, async (k) => {
  idk.value = null;
  if (!k) return;
  const r = await ambil(`indeks/${k}`).catch(() => null);
  if (k === props.kode) idk.value = r;
}, { immediate: true });
const bulanTh = (t) => new Date(t).toLocaleDateString("id-ID", { month: "short", year: "numeric" });
const indeksKini = computed(() => (idk.value?.indeks || []).filter((x) => x.anggota));
const keluarBaru = computed(() => {
  const kini = new Set(indeksKini.value.map((x) => x.indeks));
  return (idk.value?.keluar || []).filter((x) => !kini.has(x.indeks) && Date.now() - new Date(x.mulai) < 400 * 864e5).slice(0, 3);
});
const judulIndeks = (x) => `${x.indeks}: ${x.ket || ""}. Anggota sejak ${bulanTh(x.sejak)}${x.sejak_awal_data ? " atau lebih awal (data evaluasi indeks mulai 2024)" : ""}${x.bobot != null ? ` · bobot ${(x.bobot * 100).toLocaleString("id-ID", { maximumFractionDigits: 2 })}%` : ""}`;

const umur = computed(() => {
  const t = f.value?.tanggal_pencatatan;
  if (!t) return null;
  return Math.floor((Date.now() - new Date(t)) / (365.25 * 86400000));
});

const mcap = computed(() => (f.value?.ksei?.saham && props.kini?.close ? f.value.ksei.saham * props.kini.close : null));

const pemegang = computed(() => {
  const d = f.value;
  if (!d) return [];
  if (d.pemegang?.length) {
    const gabung = new Map();
    for (const x of d.pemegang) {
      const kunci = x.nama.trim().toUpperCase();
      const ada = gabung.get(kunci);
      if (ada) ada.persen = (ada.persen || 0) + (x.persen || 0);
      else gabung.set(kunci, { nama: x.nama.trim(), persen: x.persen, ket: x.kategori });
    }
    return [...gabung.values()].filter((x) => x.persen > 0).sort((a, b) => b.persen - a.persen).slice(0, 6);
  }
  const k = d.ksei;
  if (!k) return [];
  return [
    { nama: "Di luar data KSEI (umumnya pengendali)", persen: k.di_luar },
    { nama: "Korporasi lokal", persen: k.korporasi_lokal },
    { nama: "Asing", persen: k.asing },
    { nama: "Ritel lokal", persen: k.ritel },
    { nama: "Institusi lokal", persen: k.institusi_lokal },
  ].filter((x) => x.persen > 0.05).sort((a, b) => b.persen - a.persen);
});

const manajemen = computed(() => {
  const d = f.value;
  if (!d) return [];
  if (d.direksi?.length || d.komisaris?.length) return [...(d.komisaris || []).slice(0, 2), ...(d.direksi || []).slice(0, 4)];
  return (d.pejabat || []).slice(0, 5).map((x) => ({ nama: x.nama?.replace(/^(Mr\.|Ms\.|Mrs\.|Dr\.)\s*/, ""), jabatan: x.jabatan }));
});

const klasifikasi = computed(() => {
  const d = f.value;
  if (!d) return "";
  return d.klasifikasi_idx?.length ? d.klasifikasi_idx.join(" › ") : [d.sektor, d.industri].filter(Boolean).join(" · ");
});

function persenTeks(n) {
  return n == null ? "–" : `${n.toLocaleString("id-ID", { maximumFractionDigits: 2 })}%`;
}
</script>

<template>
  <div class="panel px-6 py-5" :class="memuat ? 'opacity-60' : ''">
    <div class="flex flex-wrap items-start gap-x-5 gap-y-3">
      <Logo jenis="emiten" :kunci="kode" :teks="kode" :ukuran="56" />
      <div class="min-w-0 flex-1">
        <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
          <h2 class="m-0 text-[22px] leading-tight font-medium">{{ f?.nama || kode }}</h2>
          <span class="chip bg-surface-2 text-ink-2">{{ kode }}</span>
          <span v-if="f?.papan" class="chip bg-surface-2 text-muted">Papan {{ f.papan }}</span>
        </div>
        <div class="mt-1 text-xs text-muted">{{ klasifikasi || "Sektor belum ada" }}</div>
      </div>
      <div class="flex flex-wrap gap-2">
        <span class="chip" :class="syariah ? 'bg-naik-bg text-naik' : 'bg-turun-bg text-turun'">{{ syariah ? "Syariah (DES terbaru)" : "Bukan syariah sekarang" }}</span>
        <span v-if="kini?.sinyal" class="chip bg-lime text-lime-teks">Sinyal BELI {{ kini.tgl }}</span>
        <span v-else-if="kini" class="chip bg-surface-2 text-muted">Tidak ada sinyal {{ kini.tgl }}</span>
        <span v-if="posisi" class="chip bg-aksen-lembut text-aksen">{{ labelPosisi }}</span>
      </div>
      <div v-if="indeksKini.length || keluarBaru.length" class="flex w-full flex-wrap items-center gap-1.5">
        <span class="text-xs text-muted">Anggota indeks:</span>
        <span v-for="x in indeksKini" :key="x.indeks" class="chip cursor-help" :class="x.syariah ? 'bg-naik-bg text-naik' : 'bg-surface-2 text-ink-2'" :title="judulIndeks(x)">
          {{ x.indeks }}<span v-if="!x.sejak_awal_data" class="opacity-70"> · sejak {{ bulanTh(x.sejak) }}</span>
        </span>
        <span v-for="x in keluarBaru" :key="`k-${x.indeks}`" class="chip bg-turun-bg text-turun" :title="`Keluar dari ${x.indeks} mulai ${bulanTh(x.mulai)}`">keluar {{ x.indeks }} {{ bulanTh(x.mulai) }}</span>
      </div>
    </div>

    <template v-if="f === null">
      <Kerangka class="mt-4" :n="3" />
      <Kerangka class="mt-5" jenis="kartu" :n="3" kolom="md:grid-cols-3" />
    </template>
    <template v-if="f?.ada">
      <div v-if="f.deskripsi" class="mt-4">
        <div class="mb-1 flex items-center gap-2 text-xs text-muted"><Building2 class="h-3.5 w-3.5" />Bidang usaha
          <span v-if="f.bahasa === 'en'" class="chip bg-surface-2 text-muted">Bahasa Inggris · Yahoo Finance (terjemahan belum tersedia, coba lagi besok)</span>
          <span v-else-if="f.bahasa === 'mesin'" class="chip bg-surface-2 text-muted">Terjemahan mesin dari Yahoo Finance</span>
        </div>
        <p class="m-0 max-w-[980px] text-[13px] leading-relaxed text-ink-2" :class="penuh ? '' : 'line-clamp-3'">{{ f.deskripsi }}</p>
        <div class="mt-1 flex flex-wrap gap-3">
          <button v-if="f.deskripsi.length > 260" class="text-xs text-muted hover:text-ink" @click="penuh = !penuh">{{ penuh ? "Ringkas" : "Selengkapnya" }}</button>
          <button v-if="f.bahasa === 'mesin' && f.deskripsi_en" class="text-xs text-muted hover:text-ink" @click="asli = !asli">{{ asli ? "Sembunyikan teks asli" : "Lihat teks asli (Inggris)" }}</button>
        </div>
        <p v-if="asli && f.deskripsi_en" class="m-0 mt-2 max-w-[980px] rounded-xl bg-surface-2 px-4 py-3 text-xs leading-relaxed text-muted">{{ f.deskripsi_en }}</p>
      </div>

      <div class="mt-5 grid gap-4 lg:grid-cols-3">
        <div class="rounded-2xl bg-surface-2 px-4 py-3.5">
          <div class="mb-2 flex items-center gap-2 text-xs text-muted"><Users class="h-3.5 w-3.5" />Pemegang saham
            <span class="ml-auto">{{ f.pemegang?.length ? "IDX" : f.ksei ? `KSEI ${f.ksei.tgl}` : "" }}</span>
          </div>
          <div v-if="pemegang.length" class="space-y-2">
            <div v-for="x in pemegang" :key="x.nama">
              <div class="flex items-baseline justify-between gap-3 text-[13px]">
                <span class="min-w-0 truncate" :title="x.nama">{{ x.nama }}</span>
                <span class="shrink-0 font-medium tabular-nums">{{ persenTeks(x.persen) }}</span>
              </div>
              <div class="mt-1 h-1.5 rounded-full bg-surface-3"><div class="h-full rounded-full bg-s1" :style="{ width: `${Math.min(100, x.persen || 0)}%` }"></div></div>
            </div>
          </div>
          <p v-else class="m-0 text-[13px] text-muted">Belum ada data.</p>
          <p v-if="!f.pemegang?.length && f.orang_dalam != null" class="m-0 mt-2.5 text-[11px] leading-snug text-muted">
            Yahoo: orang dalam/pengendali {{ persenTeks(f.orang_dalam * 100) }}, institusi {{ persenTeks(f.institusi * 100) }}. Nama pemegang saham ada di profil IDX.
          </p>
        </div>

        <div class="rounded-2xl bg-surface-2 px-4 py-3.5">
          <div class="mb-2 flex items-center gap-2 text-xs text-muted"><UserRound class="h-3.5 w-3.5" />Manajemen</div>
          <div v-if="manajemen.length" class="space-y-1.5">
            <div v-for="m in manajemen" :key="m.nama + m.jabatan" class="text-[13px] leading-snug">
              <div class="font-medium">{{ m.nama }}</div>
              <div class="text-xs text-muted">{{ m.jabatan }}</div>
            </div>
          </div>
          <p v-else class="m-0 text-[13px] text-muted">Belum ada data.</p>
        </div>

        <div class="rounded-2xl bg-surface-2 px-4 py-3.5 text-[13px]">
          <div class="mb-2 flex items-center gap-2 text-xs text-muted"><Building2 class="h-3.5 w-3.5" />Perusahaan</div>
          <div class="space-y-1.5">
            <div class="flex justify-between gap-3"><span class="text-muted">Kapitalisasi</span><span class="font-medium tabular-nums">{{ mcap ? `Rp${ringkas(mcap)}` : "–" }}</span></div>
            <div class="flex justify-between gap-3"><span class="text-muted">Saham beredar</span><span class="tabular-nums">{{ f.ksei ? `${ringkas(f.ksei.saham)} lembar` : "–" }}</span></div>
            <div v-if="f.karyawan" class="flex justify-between gap-3"><span class="text-muted">Karyawan</span><span class="tabular-nums">{{ rupiah(f.karyawan) }}</span></div>
            <div v-if="f.tanggal_pencatatan" class="flex items-start gap-2"><CalendarDays class="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted" /><span>Tercatat di bursa {{ f.tanggal_pencatatan }}<span v-if="umur != null" class="text-muted"> · {{ umur }} tahun</span></span></div>
            <div v-if="f.website" class="flex items-start gap-2"><Globe class="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted" /><a :href="f.website.startsWith('http') ? f.website : `https://${f.website}`" target="_blank" rel="noopener" class="truncate text-aksen hover:underline">{{ f.website.replace(/^https?:\/\//, "") }}</a></div>
            <div v-if="f.alamat" class="flex items-start gap-2"><MapPin class="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted" /><span class="text-ink-2">{{ f.alamat }}</span></div>
            <div v-if="f.telepon" class="flex items-start gap-2"><Phone class="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted" /><span class="text-ink-2">{{ f.telepon }}</span></div>
          </div>
        </div>
      </div>

      <div class="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted">
        <span>Sumber: {{ f.idx_diimpor ? `profil IDX (diimpor ${f.idx_diimpor.slice(0, 10)})` : "Yahoo Finance" }}{{ f.ksei ? ` · kepemilikan KSEI ${f.ksei.tgl}` : "" }}</span>
        <button v-if="!f.idx_diimpor" class="inline-flex items-center gap-1 text-aksen hover:underline" @click="pindahTab('beranda', 'data')">
          Impor profil IDX untuk nama pemegang saham & deskripsi Bahasa Indonesia<ArrowRight class="h-3 w-3" />
        </button>
      </div>
    </template>
  </div>
</template>

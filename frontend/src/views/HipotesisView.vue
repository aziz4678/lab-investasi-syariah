<script setup>
import { ref, computed, onMounted, nextTick, watch } from "vue";
import { Search, X, ChevronLeft, ChevronRight, ChevronDown, ArrowUp } from "lucide-vue-next";
import { ambil, persen } from "../util.js";
import Panel from "../components/Panel.vue";
import Stats from "../components/Stats.vue";
import Segmen from "../components/Segmen.vue";
import Kerangka from "../components/Kerangka.vue";
import TeksWarna from "../components/TeksWarna.vue";
import SectionHipotesis from "../components/SectionHipotesis.vue";
import GrafikHipotesis from "../components/GrafikHipotesis.vue";

const data = ref(null);
const siap = ref(false);
const cari = ref("");
const fStatus = ref("semua");
const fKategori = ref("semua");
const pilih = ref(null);
const semuaPelajaran = ref(false);
const detailEl = ref(null);
const daftarEl = ref(null);
const tabelEl = ref(null);

const WARNA = {
  turun: "bg-turun-bg text-turun",
  naik: "bg-naik-bg text-naik",
  aksen: "bg-aksen-lembut text-aksen",
  kuning: "bg-kuning-bg text-kuning",
  abu: "bg-surface-2 text-ink-2",
  garis: "border border-dashed border-garis text-muted",
};
const WARNA_LENCANA = {
  dev_gagal: "bg-turun-bg text-turun",
  holdout_pengecualian: "bg-kuning-bg text-kuning",
  pasca_hasil: "border border-kuning/60 text-kuning",
};
const ARTI_LENCANA = {
  dev_gagal: "Gagal di dev, tetap dilanjutkan sebagai paper/uji maju.",
  holdout_pengecualian: "Holdout dibuka atas keputusan user walau dev gagal.",
  pasca_hasil: "Ide muncul setelah melihat hasil; bobot buktinya lebih lemah.",
};

function bacaSimpan() {
  try {
    return localStorage.getItem("hipotesis_pilih");
  } catch {
    return null;
  }
}

onMounted(async () => {
  data.value = await ambil("hipotesis").catch(() => null);
  siap.value = true;
  const dariHash = location.hash.replace("#", "").split("/")[1];
  const ada = (k) => k && hip.value.some((h) => h.kode === k);
  if (ada(dariHash)) {
    pilih.value = dariHash;
    await nextTick();
    gulirKeDetail(false);
  } else pilih.value = ada(bacaSimpan()) ? bacaSimpan() : hip.value.find((h) => h.status === "paper")?.kode || hip.value[0]?.kode;
});

function gulirBaris() {
  const wadah = daftarEl.value;
  const el = wadah && [...wadah.querySelectorAll(`[data-kode="${pilih.value}"]`)].find((x) => x.offsetParent);
  if (!el) return;
  const a = el.getBoundingClientRect();
  const w = wadah.getBoundingClientRect();
  if (a.top < w.top + 40 || a.bottom > w.bottom) wadah.scrollTop += a.top - w.top - wadah.clientHeight / 3;
}

watch(pilih, async (k) => {
  if (!k) return;
  history.replaceState(null, "", `#hipotesis/${k}`);
  await nextTick();
  gulirBaris();
  try {
    localStorage.setItem("hipotesis_pilih", k);
  } catch {
    return;
  }
});

const hip = computed(() => data.value?.hipotesis || []);
const statusMap = computed(() => Object.fromEntries((data.value?.status || []).map((s) => [s.id, s])));
const katMap = computed(() => Object.fromEntries((data.value?.kategori || []).map((s) => [s.id, s.label])));
const kelasStatus = (id) => WARNA[statusMap.value[id]?.warna] || WARNA.abu;
const labelStatus = (id) => statusMap.value[id]?.label || id;
const kelasLencana = (id) => WARNA_LENCANA[id] || "bg-surface-2 text-muted";
const hitung = (id) => hip.value.filter((h) => h.status === id).length;
const utama = (h) => (h.angka || []).find((x) => x.utama) || (h.angka || [])[0] || {};

const stat = computed(() => [
  { label: "Total hipotesis", nilai: String(hip.value.length), ket: `H0 s/d ${hip.value[hip.value.length - 1]?.kode || ""}, termasuk sub` },
  ...(data.value?.status || []).map((s) => ({ label: s.label, nilai: String(hitung(s.id)), nada: s.id === "gagal" ? "turun" : s.id === "paper" ? "naik" : undefined })),
]);
const pelajaran = computed(() => (semuaPelajaran.value ? data.value?.pelajaran || [] : (data.value?.pelajaran || []).slice(0, 3)));

const pilihanStatus = computed(() => [["semua", `Semua ${hip.value.length}`], ...(data.value?.status || []).filter((s) => hitung(s.id)).map((s) => [s.id, `${s.label} ${hitung(s.id)}`])]);
const tersaring = computed(() => {
  const q = cari.value.trim().toLowerCase();
  return hip.value.filter((h) => {
    if (fStatus.value !== "semua" && h.status !== fStatus.value) return false;
    if (fKategori.value !== "semua" && h.kategori !== fKategori.value) return false;
    return !q || [h.kode, h.nama, h.awam, katMap.value[h.kategori], labelStatus(h.status)].join(" ").toLowerCase().includes(q);
  });
});
const adaFilter = computed(() => cari.value || fStatus.value !== "semua" || fKategori.value !== "semua");
const ukuranKeluarga = computed(() => {
  const n = {};
  hip.value.forEach((h) => (n[h.keluarga] = (n[h.keluarga] || 0) + 1));
  return n;
});
const daftar = computed(() => {
  const out = [];
  let kel = null;
  tersaring.value.forEach((h) => {
    if (h.keluarga !== kel && ukuranKeluarga.value[h.keluarga] > 1) out.push({ grup: h.keluarga, judul: data.value?.keluarga?.[h.keluarga]?.judul, id: `g-${h.keluarga}` });
    kel = h.keluarga;
    out.push({ h, id: h.kode });
  });
  return out;
});

const aktif = computed(() => hip.value.find((h) => h.kode === pilih.value) || null);
const urutan = computed(() => (tersaring.value.some((h) => h.kode === pilih.value) ? tersaring.value : hip.value));
const posisi = computed(() => urutan.value.findIndex((h) => h.kode === pilih.value));
const sebelum = computed(() => urutan.value[posisi.value - 1] || null);
const sesudah = computed(() => urutan.value[posisi.value + 1] || null);

const keluarga = computed(() => {
  const h = aktif.value;
  if (!h || ukuranKeluarga.value[h.keluarga] < 2) return null;
  const info = data.value?.keluarga?.[h.keluarga];
  const anggota = hip.value.filter((x) => x.keluarga === h.keluarga);
  const edge = anggota.map((x) => [x.kode, utama(x)]).filter(([, a]) => a.kotor != null && a.net != null && a.net_ket === "/trade");
  const grafik = edge.length >= 2 ? {
    jenis: "batang", judul: "Kotor vs bersih per trade", satuan: "%", label: edge.map((e) => e[0]),
    seri: [{ nama: "Kotor (sebelum biaya)", data: edge.map((e) => e[1].kotor) }, { nama: "Bersih (setelah biaya)", data: edge.map((e) => e[1].net) }],
    ket: "Jarak antara dua batang = biaya ±1,2% per trade.",
  } : null;
  return { kode: h.keluarga, info, anggota, grafik };
});

const offsetAtas = () => (window.innerWidth < 768 ? 112 : 16);

function gulirKeDetail(halus = true) {
  const el = detailEl.value;
  if (!el) return;
  window.scrollTo({ top: window.scrollY + el.getBoundingClientRect().top - offsetAtas(), behavior: halus ? "smooth" : "auto" });
}

function reset() {
  cari.value = "";
  fStatus.value = "semua";
  fKategori.value = "semua";
}

async function buka(kode) {
  if (!hip.value.some((h) => h.kode === kode)) return;
  pilih.value = kode;
  await nextTick();
  gulirKeDetail();
}

function keDaftar() {
  const el = tabelEl.value?.$el || tabelEl.value;
  if (el) window.scrollTo({ top: window.scrollY + el.getBoundingClientRect().top - offsetAtas(), behavior: "smooth" });
}
</script>

<template>
  <div class="space-y-5">
    <template v-if="!siap">
      <Kerangka panel jenis="stat" :n="7" :judul="false" kolom="grid-cols-2 sm:grid-cols-4 xl:grid-cols-7" />
      <Kerangka panel jenis="tabel" :n="10" />
      <Kerangka panel jenis="grafik" :tinggi="320" />
    </template>

    <p v-else-if="!data" class="m-0 rounded-2xl bg-turun-bg px-4 py-3 text-turun">Data hipotesis gagal dimuat.</p>

    <template v-else>
      <p class="m-0 max-w-[820px] text-[13px] leading-relaxed text-ink-2">
        Semua hipotesis yang pernah diuji. Kriteria ditulis sebelum uji, dicek di data lama (dev), lalu data baru (holdout) dibuka sekali hanya kalau dev lulus. Klik baris di daftar untuk melihat detailnya di bawah.
      </p>
      <Stats :items="stat" kolom="grid-cols-2 sm:grid-cols-4 xl:grid-cols-7" />

      <Panel judul="Pelajaran besar" ket="Didukung hasil uji, urut dari yang paling penting">
        <template #aksi>
          <button class="tombol !h-8 text-xs" @click="semuaPelajaran = !semuaPelajaran">{{ semuaPelajaran ? "Tampilkan 3 teratas" : `Lihat semua ${data.pelajaran.length}` }}</button>
        </template>
        <ol class="m-0 grid list-none gap-3 p-0 md:grid-cols-3">
          <li v-for="(x, i) in pelajaran" :key="x.judul" class="flex gap-3 rounded-2xl bg-surface-2/60 px-4 py-3.5">
            <span class="grid h-6 w-6 shrink-0 place-items-center rounded-full text-[11px] font-medium" :class="i < 3 ? 'bg-aksen text-aksen-teks' : 'bg-surface-3 text-ink-2'">{{ i + 1 }}</span>
            <div class="min-w-0 flex-1">
              <div class="text-[14px] leading-snug font-medium">{{ x.judul }}</div>
              <p class="m-0 mt-1 text-[13px] text-ink-2"><TeksWarna :teks="x.isi" /></p>
              <div class="mt-2 flex flex-wrap gap-x-2 gap-y-1">
                <button v-for="b in x.bukti" :key="b" class="text-[11px] font-medium text-aksen hover:underline" @click="buka(b)">{{ b }}</button>
              </div>
            </div>
          </li>
        </ol>
      </Panel>

      <details class="panel group px-5 py-3.5">
        <summary class="flex cursor-pointer list-none items-center gap-3 text-[13px] [&::-webkit-details-marker]:hidden">
          <span class="font-medium">Arti status & lencana</span>
          <span class="hidden min-w-0 flex-1 flex-wrap gap-1 sm:flex">
            <span v-for="s in data.status" :key="s.id" class="chip" :class="WARNA[s.warna]">{{ s.label }}</span>
            <span v-for="(l, k) in data.lencana" :key="k" class="chip" :class="WARNA_LENCANA[k]">{{ l }}</span>
          </span>
          <ChevronDown class="ml-auto h-4 w-4 shrink-0 text-muted transition-transform group-open:rotate-180" />
        </summary>
        <div class="mt-3 grid gap-x-6 gap-y-2 border-t border-garis pt-3 md:grid-cols-2">
          <div v-for="s in data.status" :key="s.id" class="grid grid-cols-[104px_1fr] items-start gap-3">
            <span class="chip justify-self-start" :class="WARNA[s.warna]">{{ s.label }}</span>
            <span class="text-xs leading-relaxed text-ink-2">{{ s.arti }}</span>
          </div>
          <div v-for="(l, k) in data.lencana" :key="k" class="grid grid-cols-[104px_1fr] items-start gap-3">
            <span class="chip !h-auto min-h-6 justify-self-start !whitespace-normal py-0.5" :class="WARNA_LENCANA[k]">{{ l }}</span>
            <span class="text-xs leading-relaxed text-ink-2">{{ ARTI_LENCANA[k] }}</span>
          </div>
        </div>
      </details>

      <Panel ref="tabelEl" judul="Daftar hipotesis" :ket="`${tersaring.length} dari ${hip.length} ditampilkan · klik baris untuk detail`" rapat>
        <template #aksi>
          <label class="relative w-full sm:w-56">
            <Search class="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-muted" />
            <input v-model="cari" type="search" placeholder="Cari kode / nama" class="w-full !pl-9" />
          </label>
          <select v-model="fKategori" class="w-full sm:w-auto">
            <option value="semua">Semua kategori</option>
            <option v-for="c in data.kategori" :key="c.id" :value="c.id">{{ c.label }}</option>
          </select>
          <button v-if="adaFilter" class="tombol !h-9 !px-3 text-xs" @click="reset"><X class="h-3.5 w-3.5" />Reset</button>
        </template>

        <div class="px-4 pb-3 sm:px-6"><Segmen v-model="fStatus" :pilihan="pilihanStatus" kecil /></div>

        <p v-if="!tersaring.length" class="m-0 border-t border-garis px-6 py-8 text-center text-muted">Tidak ada hipotesis yang cocok.</p>

        <div v-else ref="daftarEl" class="max-h-[560px] overflow-y-auto border-t border-garis">
          <table class="tabel hidden md:table">
            <thead class="sticky top-0 z-[1] bg-surface">
              <tr>
                <th class="w-16">Kode</th>
                <th>Nama</th>
                <th>Kategori</th>
                <th>Status</th>
                <th>Kriteria</th>
                <th class="!text-right">CAGR</th>
                <th class="!text-right">Max DD</th>
                <th class="!text-right">Bersih</th>
                <th>Diuji</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="r in daftar" :key="r.id">
                <tr v-if="r.grup" class="hover:!bg-transparent">
                  <td colspan="9" class="!h-8 bg-surface-2/40 text-[10.5px] font-medium tracking-wide text-muted uppercase">{{ r.grup }}<template v-if="r.judul"> · {{ r.judul }}</template></td>
                </tr>
                <tr v-else :data-kode="r.h.kode" class="cursor-pointer" :class="pilih === r.h.kode ? '!bg-aksen-lembut' : ''" @click="buka(r.h.kode)">
                  <td class="font-medium" :class="pilih === r.h.kode ? 'text-aksen' : ''">{{ r.h.kode }}</td>
                  <td class="!h-auto !whitespace-normal py-2.5">
                    <div class="font-medium">{{ r.h.nama }}</div>
                    <div v-if="r.h.lencana?.length" class="mt-1 flex flex-wrap gap-1">
                      <span v-for="l in r.h.lencana" :key="l" class="chip !h-5 !text-[10px]" :class="kelasLencana(l)">{{ data.lencana[l] }}</span>
                    </div>
                  </td>
                  <td class="text-ink-2">{{ katMap[r.h.kategori] }}</td>
                  <td><span class="chip" :class="kelasStatus(r.h.status)">{{ labelStatus(r.h.status) }}</span></td>
                  <td class="!whitespace-normal text-xs text-ink-2">{{ r.h.skor }}</td>
                  <td class="text-right"><TeksWarna v-if="utama(r.h).cagr != null" :teks="persen(utama(r.h).cagr, 1)" /><span v-else class="text-muted" title="tidak tercatat">—</span></td>
                  <td class="text-right"><TeksWarna v-if="utama(r.h).dd != null" :teks="persen(utama(r.h).dd, 1)" /><span v-else class="text-muted" title="tidak tercatat">—</span></td>
                  <td class="text-right">
                    <template v-if="utama(r.h).net != null"><TeksWarna :teks="persen(utama(r.h).net, 2)" /><div class="text-[10px] text-muted">{{ utama(r.h).net_ket }}</div></template>
                    <span v-else class="text-muted" title="tidak tercatat">—</span>
                  </td>
                  <td class="text-xs text-muted">{{ r.h.tgl_uji || "—" }}</td>
                </tr>
              </template>
            </tbody>
          </table>

          <div class="px-2 py-2 md:hidden">
            <template v-for="r in daftar" :key="r.id">
              <div v-if="r.grup" class="px-3 pt-3 pb-1 text-[10.5px] font-medium tracking-wide text-muted uppercase">{{ r.grup }}<template v-if="r.judul"> · {{ r.judul }}</template></div>
              <button v-else :data-kode="r.h.kode" class="flex w-full items-start gap-3 rounded-xl px-3 py-2.5 text-left" :class="pilih === r.h.kode ? 'bg-aksen-lembut' : ''" @click="buka(r.h.kode)">
                <span class="w-11 shrink-0 text-[13px] font-medium" :class="pilih === r.h.kode ? 'text-aksen' : ''">{{ r.h.kode }}</span>
                <span class="min-w-0 flex-1">
                  <span class="block text-[13px] font-medium">{{ r.h.nama }}</span>
                  <span class="mt-1 flex flex-wrap items-center gap-1">
                    <span class="chip !h-5 !text-[10px]" :class="kelasStatus(r.h.status)">{{ labelStatus(r.h.status) }}</span>
                    <span v-for="l in r.h.lencana || []" :key="l" class="chip !h-5 !text-[10px]" :class="kelasLencana(l)">{{ data.lencana[l] }}</span>
                  </span>
                  <span class="mt-1 flex flex-wrap gap-x-3 text-[11px] text-muted">
                    <span>{{ r.h.skor }}</span>
                    <span v-if="utama(r.h).cagr != null">CAGR <TeksWarna :teks="persen(utama(r.h).cagr, 1)" /></span>
                    <span v-if="utama(r.h).dd != null">DD <TeksWarna :teks="persen(utama(r.h).dd, 1)" /></span>
                  </span>
                </span>
              </button>
            </template>
          </div>
        </div>
      </Panel>

      <div v-if="aktif" ref="detailEl" class="space-y-4">
        <div class="flex flex-wrap items-center gap-2">
          <div class="mr-auto min-w-0">
            <div class="text-[11px] font-medium tracking-wide text-muted uppercase">Detail hipotesis</div>
            <div class="text-[20px] font-medium tracking-tight">{{ aktif.kode }} · {{ aktif.nama }}</div>
          </div>
          <button class="tombol !h-8 text-xs" @click="keDaftar"><ArrowUp class="h-3.5 w-3.5" />Daftar</button>
          <button class="tombol !h-8 text-xs" :disabled="!sebelum" @click="sebelum && buka(sebelum.kode)"><ChevronLeft class="h-3.5 w-3.5" />{{ sebelum?.kode || "—" }}</button>
          <button class="tombol !h-8 text-xs" :disabled="!sesudah" @click="sesudah && buka(sesudah.kode)">{{ sesudah?.kode || "—" }}<ChevronRight class="h-3.5 w-3.5" /></button>
        </div>

        <div v-if="keluarga" class="@container panel px-5 py-4">
          <div class="grid gap-4" :class="keluarga.grafik ? '@3xl:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]' : ''">
            <div class="min-w-0">
              <div class="text-[11px] font-medium tracking-wide text-muted uppercase">Keluarga {{ keluarga.kode }}</div>
              <div class="text-[16px] font-medium">{{ keluarga.info?.judul }}</div>
              <p v-if="keluarga.info?.ket" class="m-0 mt-1 text-[13px] text-ink-2">{{ keluarga.info.ket }}</p>
              <div class="mt-2.5 flex flex-wrap gap-1">
                <button v-for="a in keluarga.anggota" :key="a.kode" class="chip" :class="a.kode === pilih ? 'bg-aksen text-aksen-teks' : 'bg-surface-2 text-ink-2 hover:bg-surface-3'" @click="buka(a.kode)">{{ a.kode }}</button>
              </div>
            </div>
            <div v-if="keluarga.grafik" class="min-w-0"><GrafikHipotesis :g="keluarga.grafik" :tinggi="150" /></div>
          </div>
        </div>

        <SectionHipotesis :key="aktif.kode" :h="aktif" :kategori="katMap[aktif.kategori]" :kelas-status="kelasStatus" :label-status="labelStatus"
          :lencana="data.lencana" :kelas-lencana="kelasLencana" @buka="buka" />

        <div class="grid grid-cols-2 gap-3">
          <button v-if="sebelum" class="panel flex min-w-0 items-center gap-2 px-4 py-3 text-left transition hover:bg-surface-2/60" @click="buka(sebelum.kode)">
            <ChevronLeft class="h-4 w-4 shrink-0 text-muted" />
            <span class="min-w-0"><span class="block text-[11px] text-muted">Sebelumnya · {{ sebelum.kode }}</span><span class="block truncate text-[13px] font-medium">{{ sebelum.nama }}</span></span>
          </button>
          <span v-else></span>
          <button v-if="sesudah" class="panel flex min-w-0 items-center justify-end gap-2 px-4 py-3 text-right transition hover:bg-surface-2/60" @click="buka(sesudah.kode)">
            <span class="min-w-0"><span class="block text-[11px] text-muted">Berikutnya · {{ sesudah.kode }}</span><span class="block truncate text-[13px] font-medium">{{ sesudah.nama }}</span></span>
            <ChevronRight class="h-4 w-4 shrink-0 text-muted" />
          </button>
        </div>
      </div>

      <Panel judul="Analisis pendukung" ket="Deskriptif, bukan uji strategi. Tidak dihitung dalam jumlah hipotesis.">
        <div class="grid gap-3 md:grid-cols-2">
          <div v-for="x in data.analisis" :key="x.id" class="rounded-2xl bg-surface-2/60 px-4 py-3.5">
            <div class="flex flex-wrap items-baseline justify-between gap-2">
              <span class="text-[14px] font-medium">{{ x.nama }}</span>
              <span class="text-xs text-muted">{{ x.tgl }}</span>
            </div>
            <p class="m-0 mt-1 text-[13px] text-ink-2"><TeksWarna :teks="x.isi" /></p>
            <div class="mt-2 flex flex-wrap items-center gap-1 text-xs">
              <button v-for="t in x.terkait" :key="t" class="chip bg-surface text-ink-2 ring-1 ring-garis hover:bg-surface-3" @click="buka(t)">{{ t }}</button>
              <span class="ml-1 text-muted">{{ x.sumber }}</span>
            </div>
          </div>
        </div>
      </Panel>
    </template>
  </div>
</template>

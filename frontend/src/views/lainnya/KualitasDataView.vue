<script setup>
import { ref, computed, onMounted } from "vue";
import { ScanSearch, ShieldCheck, TriangleAlert, ChevronDown } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { pakaiPekerjaan } from "@/composables/pekerjaan";
import { tanggal } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import KodeSaham from "@/components/common/KodeSaham.vue";
import PanelPekerjaan from "@/components/sistem/PanelPekerjaan.vue";

const k = ref(null);
const siap = ref(false);
const { kerja, galat, sibuk, mulai, lanjutkan } = pakaiPekerjaan();

async function muat() {
  k.value = await ambil("kualitas").catch(() => null);
  siap.value = true;
}

onMounted(async () => {
  await muat();
  for (const j of ["kualitas_data", "koreksi_ekspor", "koreksi_impor"]) {
    await lanjutkan(j, muat);
    if (sibuk.value) break;
  }
});

function jalankan(jenis = "kualitas_data") {
  mulai(`aksi/${jenis}`, {}, muat);
}

function impor() {
  if (confirm("Pulihkan registry koreksi harga dari data/koreksi_harga.jsonl? Aturan di database diganti dengan isi file (per aturan). Data harga tidak diubah.")) jalankan("koreksi_impor");
}

function waktu(s) {
  if (!s) return "–";
  const d = new Date(s);
  return `${d.toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" })} ${d.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" })}`;
}

const cek = computed(() => k.value?.cek || null);
const NAMA_JENIS = { faktor: "Faktor aksi korporasi", sel: "Ganti nilai", hapus: "Buang baris", hapus_rentang: "Buang rentang beku", label: "Label (tidak dikoreksi)", periksa: "Perlu diperiksa" };
const NAMA_STATUS = { aktif: "diterapkan", tahan: "ditahan", label: "label", periksa: "periksa" };
const koreksi = computed(() => [...(k.value?.koreksi || [])].sort((a, b) => (a.kategori || "Z").localeCompare(b.kategori || "Z") || b.jumlah - a.jumlah));
const totalAktif = computed(() => koreksi.value.filter((x) => x.status === "aktif").reduce((a, x) => a + x.jumlah, 0));
const temuan = computed(() => cek.value?.temuan || []);
const tahan = computed(() => k.value?.tahan || []);
const labelTak = computed(() => (k.value?.label || []).filter((x) => x.status_label === "tidak terverifikasi"));
const labelLain = computed(() => (k.value?.label || []).filter((x) => x.status_label !== "tidak terverifikasi"));
const terbuka = computed(() => temuan.value.length + tahan.value.length + (k.value?.periksa?.length || 0));

function detail(x) {
  if (x.kategori === "K2") return `faktor IDX ${x.faktor_idx}`;
  if (x.kategori === "K4") return `lompat ${x.rasio}× (${x.sebelum} → ${x.sesudah})`;
  if (x.kategori === "K3" || x.kategori === "IDX5") return `Yahoo ${x.yahoo_close} vs IDX ${x.idx_close}`;
  if (x.jumlah) return `${x.jumlah} baris s/d ${x.sampai}`;
  return x.cara || "";
}
</script>

<template>
  <div class="space-y-5">
    <p class="m-0 max-w-[820px] text-muted">Harga Yahoo dicek tiap hari ke data resmi IDX. Kesalahan yang terbukti diperbaiki lewat registry koreksi (nilai asli + alasan + bukti disimpan), dan semua riset, backtest, serta paper membaca harga yang sudah dikoreksi.</p>

    <Kerangka v-if="!siap" :baris="6" />
    <template v-else>
      <Panel judul="Status cek terakhir" :ket="cek ? `${waktu(cek.waktu)} · data IDX s/d ${cek.cakupan?.idx_sampai || '–'}` : 'Belum pernah dijalankan'">
        <template #aksi>
          <button class="tombol" :disabled="sibuk" @click="jalankan('koreksi_ekspor')">Ekspor registry</button>
          <button class="tombol" :disabled="sibuk" @click="impor">Pulihkan dari file</button>
          <button class="tombol" :disabled="sibuk" @click="jalankan()"><ScanSearch class="h-3.5 w-3.5" /> Cek kualitas data</button>
        </template>
        <div class="grid gap-3 sm:grid-cols-4">
          <div class="rounded-2xl px-4 py-3" :class="!cek ? 'bg-surface-2' : cek.status === 'LULUS' ? 'bg-naik-bg' : 'bg-kuning-bg'">
            <div class="label">Status</div>
            <div class="mt-1 flex items-center gap-2 text-lg font-medium" :class="!cek ? 'text-ink-2' : cek.status === 'LULUS' ? 'text-naik' : 'text-kuning'">
              <ShieldCheck v-if="cek?.status === 'LULUS'" class="h-5 w-5" /><TriangleAlert v-else class="h-5 w-5" />{{ cek?.status || "belum dicek" }}
            </div>
          </div>
          <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="label">Temuan baru</div><div class="mt-1 text-lg font-medium tabular-nums">{{ cek?.jumlah_temuan ?? "–" }}</div></div>
          <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="label">Koreksi ditahan</div><div class="mt-1 text-lg font-medium tabular-nums">{{ tahan.length }}</div></div>
          <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="label">Koreksi diterapkan</div><div class="mt-1 text-lg font-medium tabular-nums">{{ totalAktif.toLocaleString("id-ID") }}</div></div>
        </div>
        <p v-if="k?.jadwal" class="m-0 mt-3 text-xs text-muted">Jadwal terakhir {{ waktu(k.jadwal.mulai) }}: data IDX {{ k.jadwal.idx_lengkap ? "lengkap" : "belum lengkap (paper memakai cadangan Yahoo untuk hari itu)" }}<span v-if="k.jadwal.idx_terakhir">, terakhir {{ tanggal(k.jadwal.idx_terakhir) }}</span>.</p>
        <PanelPekerjaan :kerja="kerja" :galat="galat" />
      </Panel>

      <Panel judul="Cakupan pemeriksaan" ket="Bagian data yang bisa dicek ke sumber resmi dan yang tidak">
        <div class="grid gap-3 sm:grid-cols-3">
          <div v-for="c in k.cakupan" :key="c.periode" class="rounded-2xl bg-surface-2 px-4 py-3">
            <div class="flex items-center gap-2 text-[13px] font-medium">{{ c.periode }}
              <span class="chip" :class="c.status === 'terverifikasi' ? 'bg-naik-bg text-naik' : c.status === 'sebagian' ? 'bg-kuning-bg text-kuning' : 'bg-turun-bg text-turun'">{{ c.status }}</span>
            </div>
            <p class="m-0 mt-1 text-xs text-ink-2">{{ c.cara }}</p>
          </div>
        </div>
      </Panel>

      <Panel judul="Masalah terbuka" :ket="terbuka ? `${terbuka} hal menunggu tindakan atau keputusan` : 'Tidak ada'" rapat>
        <div v-if="temuan.length" class="overflow-x-auto">
          <p class="m-0 px-6 pb-2 text-xs text-muted">Temuan baru dari cek terakhir (belum ada di registry koreksi). Perbaiki dengan bukti sebelum dipakai uji hipotesis.</p>
          <table class="tabel min-w-[640px]">
            <thead><tr><th>Kategori</th><th>Saham</th><th>Data</th><th>Tanggal</th><th>Rincian</th></tr></thead>
            <tbody>
              <tr v-for="(x, i) in temuan.slice(0, 200)" :key="i">
                <td class="text-xs">{{ k.kategori[x.kategori] || x.kategori }}</td>
                <td><KodeSaham :kode="x.kode" /></td>
                <td class="text-xs text-ink-2">{{ x.koleksi }}</td>
                <td class="text-ink-2">{{ x.tgl ? tanggal(x.tgl) : "–" }}</td>
                <td class="text-xs text-ink-2">{{ detail(x) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="tahan.length" class="overflow-x-auto">
          <p class="m-0 px-6 pt-3 pb-2 text-xs text-muted">Koreksi ditahan (tidak diterapkan otomatis karena ekstrem atau tidak cocok dengan data lain): perlu keputusan user.</p>
          <table class="tabel min-w-[640px]">
            <thead><tr><th>Saham</th><th>Jenis</th><th>Tanggal</th><th>Alasan ditahan</th></tr></thead>
            <tbody><tr v-for="x in tahan" :key="x._id"><td><KodeSaham :kode="x.kode" /></td><td class="text-xs">{{ NAMA_JENIS[x.jenis] || x.jenis }}</td><td class="text-ink-2">{{ tanggal(x.tgl || x.ex_date) }}</td><td class="!whitespace-normal text-xs text-ink-2">{{ x.keputusan }}</td></tr></tbody>
          </table>
        </div>
        <div v-if="k.periksa?.length" class="overflow-x-auto">
          <p class="m-0 px-6 pt-3 pb-2 text-xs text-muted">Perubahan harga acuan IDX &lt; 10% tanpa penyesuaian Yahoo: bisa aksi korporasi kecil atau reset harga acuan saham suspensi. Tidak dikoreksi.</p>
          <table class="tabel min-w-[560px]">
            <thead><tr><th>Saham</th><th>Tanggal</th><th class="!text-right">Faktor IDX</th><th class="!text-right">Yahoo/IDX</th></tr></thead>
            <tbody><tr v-for="x in k.periksa" :key="x._id"><td><KodeSaham :kode="x.kode" /></td><td class="text-ink-2">{{ tanggal(x.ex_date) }}</td><td class="text-right tabular-nums">{{ x.faktor_idx }}</td><td class="text-right tabular-nums">{{ x.rasio_yahoo_idx }}</td></tr></tbody>
          </table>
        </div>
        <details class="px-6 pt-3 pb-4">
          <summary class="flex cursor-pointer items-center gap-1 text-[13px] text-ink"><ChevronDown class="h-3.5 w-3.5" />Lompatan sebelum 2020 yang tidak terverifikasi ({{ labelTak.length }}) dan yang diberi label lain ({{ labelLain.length }})</summary>
          <p class="m-0 mt-2 text-xs text-muted">Lompatan harga di luar batas ARA/ARB tanpa split tercatat. Hanya dikoreksi kalau ada bukti dokumen; tanpa bukti dibiarkan dan diberi label.</p>
          <ul class="m-0 mt-2 list-disc space-y-0.5 pl-5 text-xs text-ink-2">
            <li v-for="x in [...labelTak, ...labelLain]" :key="x.kode + x.tgl">{{ x.kode }} {{ tanggal(x.tgl) }} · {{ x.rasio }}× · {{ x.status_label }}</li>
          </ul>
        </details>
      </Panel>

      <Panel judul="Koreksi per kategori" ket="Registry koreksi_harga: setiap aturan menyimpan nilai asli, nilai baru, alasan, dan bukti" rapat>
        <div class="overflow-x-auto">
          <table class="tabel min-w-[560px]">
            <thead><tr><th>Kategori</th><th>Jenis</th><th>Status</th><th class="!text-right">Aturan</th><th class="!text-right">Saham</th></tr></thead>
            <tbody>
              <tr v-for="(x, i) in koreksi" :key="i">
                <td class="text-xs">{{ k.kategori[x.kategori] || x.kategori || "–" }}</td>
                <td class="text-xs text-ink-2">{{ NAMA_JENIS[x.jenis] || x.jenis }}</td>
                <td><span class="chip" :class="x.status === 'aktif' ? 'bg-naik-bg text-naik' : x.status === 'tahan' ? 'bg-kuning-bg text-kuning' : 'bg-surface-2 text-ink-2'">{{ NAMA_STATUS[x.status] || x.status }}</span></td>
                <td class="text-right tabular-nums">{{ x.jumlah.toLocaleString("id-ID") }}</td>
                <td class="text-right tabular-nums">{{ x.saham }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel judul="Log koreksi aksi korporasi otomatis" ket="Faktor resmi IDX yang wajar diterapkan otomatis; yang ekstrem atau tidak cocok ditahan" rapat>
        <ul v-if="k.log_otomatis?.length" class="m-0 list-none space-y-1 px-6 pb-4 text-xs text-ink-2">
          <li v-for="(x, i) in k.log_otomatis" :key="i">{{ waktu(x.waktu) }} · diterapkan {{ x.jumlah_aktif }}<span v-if="x.aktif?.length"> ({{ x.aktif.map((a) => a._id).join(", ") }})</span> · ditahan {{ x.jumlah_tahan }}</li>
        </ul>
        <p v-else class="m-0 px-6 pb-4 text-xs text-muted">Belum ada putaran otomatis.</p>
      </Panel>
    </template>
  </div>
</template>

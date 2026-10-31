<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { X, Plus, Search, TriangleAlert } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { persen, ringkas as singkat, kelasPersen } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import Pemutar from "@/components/common/Pemutar.vue";
import Segmen from "@/components/common/Segmen.vue";
import GrafikBanding from "@/components/charts/GrafikBanding.vue";

const MAKS = 5;
const SARAN = 3;
const AWAL = ["rd:4406", "rd:2605", "x:deposito"];
const WARNA = ["--series-1", "--series-2", "--series-4", "--series-5", "--series-3"];
const KELAS_WARNA = ["bg-s1", "bg-s2", "bg-s4", "bg-s5", "bg-s3"];
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

const pilihan = ref(null);
const kunci = ref(baca("rd_banding", AWAL));
const periode = ref(baca("rd_banding_periode", "5y"));
const rupiah = ref(baca("rd_banding_rupiah", true));
const cari = ref("");
const buka = ref(false);
const hasil = ref(null);
const memuat = ref(false);

onMounted(async () => {
  pilihan.value = await ambil("rd/bandingkan/pilihan").catch(() => ({ rd: [], pembanding: [] }));
});

async function muat() {
  simpan("rd_banding", kunci.value);
  simpan("rd_banding_periode", periode.value);
  simpan("rd_banding_rupiah", rupiah.value);
  if (kunci.value.length < 2) {
    hasil.value = null;
    return;
  }
  memuat.value = true;
  hasil.value = await ambil(`rd/bandingkan?id=${kunci.value.join(",")}&periode=${periode.value}&rupiah=${rupiah.value}`).catch(() => ({ error: "Gagal memuat" }));
  memuat.value = false;
}
watch([kunci, periode, rupiah], muat, { deep: true, immediate: true });

const semua = computed(() => [...(pilihan.value?.pembanding || []).map((p) => ({ ...p, pembanding: true })), ...(pilihan.value?.rd || [])]);
const info = (k) => semua.value.find((p) => p.id === k) || { id: k, nama: hasil.value?.nama?.[k] || k };
const cocok = computed(() => {
  const q = cari.value.trim().toLowerCase();
  const sisa = (pilihan.value?.rd || []).filter((p) => !kunci.value.includes(p.id));
  return (q ? sisa.filter((p) => `${p.nama} ${p.mi} ${p.kategori_label}`.toLowerCase().includes(q)) : sisa).slice(0, 8);
});
const tambah = (k) => {
  if (!kunci.value.includes(k) && kunci.value.length < MAKS) kunci.value = [...kunci.value, k];
  cari.value = "";
  buka.value = false;
};
const hapus = (k) => (kunci.value = kunci.value.filter((x) => x !== k));
const tutupNanti = () => setTimeout(() => (buka.value = false), 150);
const urut = computed(() => (hasil.value?.seri ? Object.keys(hasil.value.seri) : []));
const kelasDari = (k) => KELAS_WARNA[kunci.value.indexOf(k)] || KELAS_WARNA[0];
const warnaDari = (k) => WARNA[kunci.value.indexOf(k)] || WARNA[0];
const pendek = (k) => {
  const n = hasil.value?.nama?.[k] || info(k).nama || k;
  return n.length > 26 ? `${n.slice(0, 25)}…` : n;
};
const adaUsd = computed(() => kunci.value.some((k) => info(k).mata_uang === "USD"));
const m = (k) => hasil.value?.metrik?.[k] || {};

const BARIS = [
  ["total", "Total hasil", "Kalau membeli di awal periode lalu ditahan sampai sekarang", true],
  ["per_tahun", "Rata-rata per tahun", "Pertumbuhan rata-rata tiap tahun (CAGR)", true],
  ["dd", "Turun terdalam", "Penurunan terbesar dari titik tertinggi (dilihat per akhir bulan)", true],
  ["vol", "Gejolak per tahun", "Seberapa besar naik-turun bulanannya (volatilitas). Makin kecil makin tenang", false],
  ["tahun_terbaik", "Tahun terbaik", "Tahun kalender penuh di dalam periode", true],
  ["tahun_terburuk", "Tahun terburuk", "Tahun kalender penuh di dalam periode", true],
];
const terbaik = (kolom, besar = true) => {
  const v = urut.value.filter((k) => m(k)[kolom] != null);
  if (!v.length) return null;
  return v.sort((a, b) => (besar ? m(b)[kolom] - m(a)[kolom] : m(a)[kolom] - m(b)[kolom]))[0];
};
const kesimpulan = computed(() => {
  if (!hasil.value?.metrik) return [];
  const r = [];
  const kol = urut.value.some((k) => m(k).per_tahun != null) ? "per_tahun" : "total";
  const t = terbaik(kol), s = terbaik("dd"), v = terbaik("vol", false);
  if (t) r.push(`Hasil paling tinggi: ${pendek(t)} (${persen(m(t)[kol], 1)}${kol === "per_tahun" ? " per tahun" : " total"}).`);
  if (s) r.push(`Paling tahan saat turun: ${pendek(s)} (turun terdalam ${persen(m(s).dd, 1)}).`);
  if (v && v !== s) r.push(`Paling tenang geraknya: ${pendek(v)}.`);
  const kalah = urut.value.filter((k) => m(k).tahun_inflasi && m(k).kalahkan_inflasi < m(k).tahun_inflasi);
  if (kalah.length) r.push(`Pernah kalah dari inflasi dalam setahun penuh: ${kalah.map((k) => `${pendek(k)} (${m(k).tahun_inflasi - m(k).kalahkan_inflasi} dari ${m(k).tahun_inflasi} th)`).join(", ")}.`);
  const peringatan = urut.value.filter((k) => m(k).peringatan?.length);
  if (peringatan.length) r.push(`Perlu dicek dulu: ${peringatan.map((k) => `${pendek(k)} (${m(k).peringatan.map((w) => w.label).join(", ")})`).join("; ")}.`);
  return r;
});
const warnaKor = (v) => (v >= 0.9 ? "bg-turun-bg text-turun" : v >= 0.7 ? "bg-kuning-bg text-kuning" : "bg-naik-bg text-naik");
</script>

<template>
  <div class="space-y-5">
    <div class="panel space-y-4 px-6 py-5">
      <div>
        <div class="text-[15px] font-medium">Bandingkan produk</div>
        <p class="m-0 mt-1 text-[13px] text-ink-2">Pilih 2 sampai {{ MAKS }} (disarankan {{ SARAN }} supaya grafik tetap mudah dibaca). Semua dihitung dari bulan yang sama, memakai NAV akhir bulan setelah biaya.</p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <span v-for="k in kunci" :key="k" class="inline-flex max-w-full items-center gap-2 rounded-full border border-garis bg-surface py-1 pr-2 pl-2.5">
          <span class="h-3 w-3 shrink-0 rounded-full" :class="kelasDari(k)"></span>
          <span class="truncate text-[13px] font-medium" :title="info(k).nama">{{ info(k).nama }}</span>
          <span v-if="info(k).pembanding" class="chip !h-4 !px-1.5 !text-[10px] bg-surface-2 text-muted">pembanding</span>
          <span v-else-if="info(k).mata_uang === 'USD'" class="chip !h-4 !px-1.5 !text-[10px] bg-surface-2 text-muted">USD</span>
          <button class="grid h-5 w-5 shrink-0 place-items-center rounded-full text-muted hover:bg-surface-2 hover:text-ink" :title="`Hapus ${info(k).nama}`" @click="hapus(k)"><X class="h-3.5 w-3.5" /></button>
        </span>
      </div>
      <div v-if="kunci.length < MAKS" class="flex flex-wrap items-start gap-2">
        <div class="relative w-full sm:w-80">
          <Search class="pointer-events-none absolute top-1/2 left-3 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
          <input v-model="cari" type="text" placeholder="Cari reksa dana untuk ditambahkan…" class="!h-9 w-full !pl-8 text-[13px]" @focus="buka = true" @blur="tutupNanti" />
          <div v-if="buka && pilihan" class="absolute z-20 mt-1 max-h-80 w-full overflow-y-auto rounded-2xl border border-garis bg-surface py-1 shadow-lg">
            <button v-for="p in cocok" :key="p.id" class="block w-full px-3 py-2 text-left hover:bg-surface-2" @mousedown.prevent="tambah(p.id)">
              <div class="truncate text-[13px] font-medium">{{ p.nama }}</div>
              <div class="truncate text-[11px] text-muted">{{ p.kategori_label }} · {{ p.mi }}{{ p.mata_uang === "USD" ? " · USD" : "" }} · data {{ String(p.tahun_data).replace(".", ",") }} th</div>
            </button>
            <div v-if="!cocok.length" class="px-3 py-2 text-[13px] text-muted">Tidak ditemukan.</div>
          </div>
        </div>
        <button v-for="p in (pilihan?.pembanding || []).filter((p) => !kunci.includes(p.id))" :key="p.id" class="tombol" :title="p.ket" @click="tambah(p.id)">
          <Plus class="h-3.5 w-3.5" />{{ p.nama }}
        </button>
      </div>
      <p v-if="kunci.length > SARAN" class="m-0 text-xs text-kuning">{{ kunci.length }} produk dipilih: grafik jadi lebih ramai. Tabel di bawah tetap lengkap.</p>
      <div class="flex flex-wrap items-center gap-3">
        <Segmen v-model="periode" kecil :pilihan="[['1y', '1 tahun'], ['3y', '3 tahun'], ['5y', '5 tahun'], ['10y', '10 tahun'], ['maks', 'Semua data']]" />
        <Segmen v-if="adaUsd" :model-value="rupiah ? 'rp' : 'asli'" kecil :pilihan="[['rp', 'RD dolar dalam rupiah'], ['asli', 'RD dolar dalam USD']]" @update:model-value="rupiah = $event === 'rp'" />
      </div>
    </div>

    <p v-if="kunci.length < 2" class="panel m-0 px-6 py-4 text-[13px] text-ink-2">Tambahkan minimal 2 produk.</p>
    <p v-else-if="hasil?.error" class="panel m-0 px-6 py-4 text-[13px] text-turun">{{ hasil.error }}</p>
    <template v-else-if="!hasil">
      <Kerangka panel jenis="grafik" :tinggi="300" />
      <Kerangka panel jenis="tabel" :n="4" />
    </template>
    <template v-else>
      <div v-if="memuat" class="px-1"><Pemutar teks="Menghitung ulang perbandingan..." /></div>
      <Panel :judul="`Kalau modal 100 ditanam sejak ${hasil.mulai}`" :ket="`${String(hasil.tahun).replace('.', ',')} tahun data bersama · semua dimulai dari 100 · NAV akhir bulan`">
        <div class="mb-3 flex flex-wrap gap-2 text-xs text-ink-2">
          <span v-for="k in urut" :key="k" class="inline-flex max-w-full items-center gap-2 rounded-full bg-surface-2 px-3 py-1">
            <span class="h-0.5 w-4 shrink-0 rounded" :class="kelasDari(k)"></span><span class="truncate">{{ pendek(k) }}</span>
            <b class="font-medium" :class="kelasPersen(m(k).total)">{{ persen(m(k).total, 1) }}</b>
          </span>
        </div>
        <GrafikBanding :label="hasil.tgl" :seri="Object.fromEntries(urut.map((k) => [pendek(k), hasil.seri[k]]))" :warna-seri="urut.map(warnaDari)" />
        <p v-if="hasil.penentu_mulai.length" class="m-0 mt-3 text-xs text-muted">Periode dimulai {{ hasil.mulai }} karena data {{ hasil.penentu_mulai.join(", ") }} baru ada sejak itu; semua dihitung dari titik yang sama.</p>
        <p v-if="hasil.tidak_ada.length" class="m-0 mt-2 flex gap-1.5 text-xs text-kuning"><TriangleAlert class="mt-0.5 h-3.5 w-3.5 shrink-0" />{{ hasil.tidak_ada.map((k) => info(k).nama).join(", ") }} belum punya data cukup, tidak ikut dihitung.</p>
      </Panel>

      <div v-if="kesimpulan.length" class="panel px-6 py-4">
        <div class="mb-2 text-[13px] font-medium">Ringkasnya</div>
        <ul class="m-0 list-disc space-y-1 pl-5 text-[13px] text-ink-2">
          <li v-for="r in kesimpulan" :key="r">{{ r }}</li>
        </ul>
      </div>

      <Panel judul="Perbandingan angka" ket="Arahkan kursor ke nama baris untuk penjelasannya" rapat>
        <div class="overflow-x-auto">
          <table class="tabel">
            <thead>
              <tr>
                <th></th>
                <th v-for="k in urut" :key="k" class="!text-right"><span class="inline-flex items-center gap-1.5"><span class="h-2.5 w-2.5 shrink-0 rounded-full" :class="kelasDari(k)"></span>{{ pendek(k) }}</span></th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="text-ink-2">Jenis</td>
                <td v-for="k in urut" :key="k" class="text-right text-ink-2">{{ m(k).kategori }}{{ m(k).mata_uang === "USD" ? " · USD" : "" }}</td>
              </tr>
              <tr v-for="[kolom, label, ket, bertanda] in BARIS" :key="kolom">
                <td class="text-ink-2" :title="ket">{{ label }}</td>
                <td v-for="k in urut" :key="k" class="text-right font-medium tabular-nums" :class="bertanda ? kelasPersen(m(k)[kolom]) : ''">{{ m(k)[kolom] == null ? "–" : persen(m(k)[kolom], 1, bertanda) }}</td>
              </tr>
              <tr>
                <td class="text-ink-2" title="Berapa bulan yang nilainya turun dibanding bulan sebelumnya">Bulan turun</td>
                <td v-for="k in urut" :key="k" class="text-right tabular-nums">{{ m(k).bulan_turun }} dari {{ m(k).bulan_dihitung }}</td>
              </tr>
              <tr>
                <td class="text-ink-2" title="Tahun kalender penuh yang hasilnya positif">Tahun yang naik</td>
                <td v-for="k in urut" :key="k" class="text-right tabular-nums">{{ m(k).tahun_dihitung ? `${m(k).tahun_naik} dari ${m(k).tahun_dihitung}` : "–" }}</td>
              </tr>
              <tr>
                <td class="text-ink-2" title="Tahun kalender penuh yang hasilnya di atas inflasi Desember ke Desember">Kalahkan inflasi</td>
                <td v-for="k in urut" :key="k" class="text-right tabular-nums">{{ m(k).tahun_inflasi ? `${m(k).kalahkan_inflasi} dari ${m(k).tahun_inflasi} th` : "–" }}</td>
              </tr>
              <tr>
                <td class="text-ink-2" title="Biaya tahunan dari fund fact sheet terakhir (sudah dipotong dari NAV)">Biaya per tahun</td>
                <td v-for="k in urut" :key="k" class="text-right tabular-nums">{{ m(k).biaya == null ? "–" : persen(m(k).biaya, 2, false) }}</td>
              </tr>
              <tr>
                <td class="text-ink-2" title="Dana kelolaan terakhir">Dana kelolaan</td>
                <td v-for="k in urut" :key="k" class="text-right tabular-nums">{{ m(k).aum == null ? "–" : `${m(k).mata_uang === "USD" ? "US$" : "Rp"}${singkat(m(k).aum)}` }}</td>
              </tr>
              <tr>
                <td class="text-ink-2">Peringatan</td>
                <td v-for="k in urut" :key="k" class="text-right">
                  <span v-for="w in m(k).peringatan || []" :key="w.kode" class="chip ml-1 !py-0 bg-kuning-bg text-[10.5px] text-kuning" :title="w.ket">{{ w.label }}</span>
                  <span v-if="!m(k).peringatan?.length" class="text-muted">–</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </Panel>

      <div class="grid gap-5 2xl:grid-cols-2 [&>*]:min-w-0">
        <Panel judul="Hasil per tahun" :ket="`Tahun kalender penuh di dalam periode · kolom terakhir inflasi Desember ke Desember`" rapat>
          <div v-if="hasil.tahun_list.length" class="overflow-x-auto">
            <table class="tabel">
              <thead>
                <tr>
                  <th>Tahun</th>
                  <th v-for="k in urut" :key="k" class="!text-right"><span class="inline-flex items-center gap-1.5"><span class="h-2.5 w-2.5 shrink-0 rounded-full" :class="kelasDari(k)"></span>{{ pendek(k) }}</span></th>
                  <th class="!text-right">Inflasi</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="t in hasil.tahun_list" :key="t">
                  <td class="text-ink-2">{{ t }}</td>
                  <td v-for="k in urut" :key="k" class="text-right tabular-nums" :class="[kelasPersen(m(k).per_th[t]), m(k).per_th[t] != null && hasil.inflasi[t] != null && m(k).per_th[t] <= hasil.inflasi[t] ? 'underline decoration-dotted' : '']">{{ m(k).per_th[t] == null ? "–" : persen(m(k).per_th[t], 1) }}</td>
                  <td class="text-right tabular-nums text-ink-2">{{ hasil.inflasi[t] == null ? "–" : persen(hasil.inflasi[t], 1, false) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else class="m-0 px-6 pb-4 text-[13px] text-muted">Belum ada tahun kalender penuh di periode ini. Pilih periode lebih panjang.</p>
          <p v-if="hasil.tahun_list.length" class="m-0 px-6 py-3 text-xs text-muted">Angka bergaris titik-titik = tidak mengalahkan inflasi tahun itu.</p>
        </Panel>
        <Panel judul="Seberapa mirip geraknya" ket="Korelasi bulanan: 1 = selalu bergerak bersama, 0 = tidak berhubungan" rapat>
          <div v-if="hasil.korelasi" class="overflow-x-auto">
            <table class="tabel">
              <thead><tr><th></th><th v-for="k in urut" :key="k" class="!text-center"><span class="mx-auto block h-2.5 w-2.5 rounded-full" :class="kelasDari(k)" :title="pendek(k)"></span></th></tr></thead>
              <tbody>
                <tr v-for="a in urut" :key="a">
                  <td class="font-medium"><span class="inline-flex items-center gap-1.5"><span class="h-2.5 w-2.5 shrink-0 rounded-full" :class="kelasDari(a)"></span>{{ pendek(a) }}</span></td>
                  <td v-for="b in urut" :key="b" class="text-center">
                    <span v-if="a !== b" class="chip" :class="warnaKor(hasil.korelasi[a][b])">{{ hasil.korelasi[a][b].toLocaleString("id-ID") }}</span>
                    <span v-else class="text-muted">–</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="m-0 px-6 py-3 text-xs text-muted">Merah = geraknya hampir sama (kurang menyebar risiko). Hijau = geraknya berbeda. Untuk produk yang geraknya sangat kecil (pasar uang, deposito), angka korelasi kurang bermakna.</p>
        </Panel>
      </div>
      <p class="m-0 text-xs text-muted">Hasil RD dari NAV saja: RD yang membagi dividen tunai terlihat lebih kecil dari hasil sebenarnya. JII tanpa dividen, emas tanpa biaya simpan dan selisih jual-beli, deposito = perkiraan. Hasil masa lalu tidak menjamin hasil ke depan. Bukan nasihat keuangan.</p>
    </template>
  </div>
</template>

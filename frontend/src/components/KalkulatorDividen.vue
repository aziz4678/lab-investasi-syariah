<script setup>
import { ref, computed, watch } from "vue";
import { Bar } from "vue-chartjs";
import { X, Plus } from "lucide-vue-next";
import { ambil, opsiDasar, warna, alfa, pakaiTema, persen, rupiah, ringkas } from "../util.js";
import Panel from "./Panel.vue";
import Kerangka from "./Kerangka.vue";
import Stats from "./Stats.vue";
import Segmen from "./Segmen.vue";
import KodeSaham from "./KodeSaham.vue";

const props = defineProps({ daftar: Array, tandaKet: Object });
const tema = pakaiTema();
const BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
const FEE_BELI = 0.0015;

function baca(kunci, awal) {
  try {
    const v = localStorage.getItem(kunci);
    return v ? JSON.parse(v) : awal;
  } catch {
    return awal;
  }
}
function simpan(kunci, v) {
  try {
    localStorage.setItem(kunci, JSON.stringify(v));
  } catch {
    return;
  }
}

const modal = ref(baca("kalk_modal", 100000000));
const kode = ref(baca("kalk_kode", []));
const dasar = ref(baca("kalk_dasar", "konservatif"));
const pajak = ref(baca("kalk_pajak", 10));
const sukuk = ref(baca("kalk_sukuk", 6));
const tambah = ref("");
const data = ref([]);
const adaIdx = ref(false);
const memuat = ref(false);

watch([modal, kode, dasar, pajak, sukuk], () => {
  simpan("kalk_modal", modal.value);
  simpan("kalk_kode", kode.value);
  simpan("kalk_dasar", dasar.value);
  simpan("kalk_pajak", pajak.value);
  simpan("kalk_sukuk", sukuk.value);
}, { deep: true });

watch(kode, async (k) => {
  if (!k.length) {
    data.value = [];
    return;
  }
  memuat.value = true;
  const r = await ambil(`dividen/kalkulator?kode=${k.join(",")}`).catch(() => ({ data: [] }));
  data.value = r.data;
  adaIdx.value = !!r.idx;
  memuat.value = false;
}, { immediate: true, deep: true });

function tambahKode(k) {
  const x = (k || tambah.value).trim().toUpperCase();
  if (x && !kode.value.includes(x) && kode.value.length < 30) kode.value = [...kode.value, x];
  tambah.value = "";
}
function hapus(k) {
  kode.value = kode.value.filter((x) => x !== k);
}
function isi(jenis) {
  const d = (props.daftar || []).filter((s) => s.dps12 > 0 && s.beruntun >= 3);
  const urut = jenis === "aman" ? d.filter((s) => !s.tanda.length).sort((a, b) => b.yield - a.yield) : [...d].sort((a, b) => b.beruntun - a.beruntun || b.yield - a.yield);
  kode.value = urut.slice(0, 10).map((s) => s.kode);
}
const pernahDisimpan = baca("kalk_kode", null) !== null;
watch(() => props.daftar, (d) => {
  if (!pernahDisimpan && !kode.value.length && d?.length) isi("aman");
}, { immediate: true });

const saran = computed(() => {
  const q = tambah.value.trim().toUpperCase();
  if (!q) return [];
  return (props.daftar || []).filter((s) => s.kode.startsWith(q) && !kode.value.includes(s.kode)).slice(0, 6);
});

const DASAR = [["konservatif", "Konservatif"], ["12bln", "12 bulan terakhir"], ["rata3", "Rata-rata 3 tahun"]];

const baris = computed(() => {
  const n = data.value.length;
  if (!n) return [];
  const jatah = (Number(modal.value) || 0) / n;
  const t = 1 - pajak.value / 100;
  return data.value.map((s) => {
    const lot = Math.max(0, Math.floor(jatah / (s.harga * 100 * (1 + FEE_BELI))));
    const lembar = lot * 100;
    const pakai12 = dasar.value === "12bln" || (dasar.value === "konservatif" && s.dps12 <= s.dps_avg3);
    const dps = pakai12 ? s.dps12 : s.dps_avg3;
    const adaBayar = !!s.bayar12;
    const pola = adaBayar ? (pakai12 ? s.bayar12 : s.bayar3) : pakai12 ? s.bulan12 : s.bulan3;
    const totalPola = Object.values(pola).reduce((a, b) => a + b, 0) || 1;
    const perBulan = Array.from({ length: 12 }, (_, i) => {
      const b = adaBayar ? i + 1 : ((i + 11) % 12) + 1;
      return (lembar * dps * t * (pola[b] || 0)) / totalPola;
    });
    const rasio = s.terburuk == null ? 0.5 : Math.min(1, s.terburuk);
    return { ...s, lot, nilai: lembar * s.harga * (1 + FEE_BELI), dps, tahunan: lembar * dps * t, perBulan, rasio, terburukTahunan: lembar * dps * t * rasio };
  });
});

const ketCair = computed(() => {
  const b = baris.value;
  const n = b.reduce((a, s) => a + (s.jumlah_dividen || 0), 0);
  const r = b.reduce((a, s) => a + (s.bayar_resmi || 0), 0);
  if (!adaIdx.value) return "Perkiraan per bulan: bulan ex-date + 1 bulan (jadwal resmi IDX belum diimpor)";
  return `Per bulan uang masuk: tanggal bayar resmi IDX bila ada, sisanya ex-date + jeda bayar biasa saham itu · ${r} dari ${n} pembayaran memakai tanggal resmi`;
});

const ringkasan = computed(() => {
  const b = baris.value;
  const inv = b.reduce((a, s) => a + s.nilai, 0);
  const tahunan = b.reduce((a, s) => a + s.tahunan, 0);
  const buruk = b.reduce((a, s) => a + s.terburukTahunan, 0);
  const sk = (Number(modal.value) || 0) * (sukuk.value / 100) * 0.9;
  return { inv, sisa: (Number(modal.value) || 0) - inv, tahunan, bulanan: tahunan / 12, yield: inv ? (tahunan / inv) * 100 : 0, buruk, sukuk: sk };
});

const stat = computed(() => {
  const r = ringkasan.value;
  if (!baris.value.length) return [];
  return [
    { label: "Terinvestasi", nilai: `Rp${ringkas(Math.round(r.inv))}`, ket: `sisa kas Rp${rupiah(Math.round(r.sisa))}` },
    { label: "Dividen per tahun", nilai: `Rp${ringkas(Math.round(r.tahunan))}`, ket: `yield ${persen(r.yield, 1, false)} ${pajak.value ? "setelah pajak 10%" : "tanpa pajak"}` },
    { label: "Rata-rata per bulan", nilai: `Rp${ringkas(Math.round(r.bulanan))}`, ket: "tapi cair tidak merata, lihat grafik" },
    { label: "Skenario terburuk", nilai: `Rp${ringkas(Math.round(r.buruk))}`, nada: "turun", ket: "tiap saham kena penurunan dividen terparah dalam sejarahnya" },
    { label: `Sukuk ${sukuk.value}%`, nilai: `Rp${ringkas(Math.round(r.sukuk))}`, ket: "per tahun, modal sama, pajak 10%, dibayar bulanan" },
  ];
});

const grafik = computed(() => {
  tema.value;
  const b = baris.value;
  if (!b.length) return null;
  const dasarBulan = Array.from({ length: 12 }, (_, i) => b.reduce((a, s) => a + s.perBulan[i], 0));
  const burukBulan = Array.from({ length: 12 }, (_, i) => b.reduce((a, s) => a + s.perBulan[i] * s.rasio, 0));
  const sk = ringkasan.value.sukuk / 12;
  return {
    labels: BULAN,
    datasets: [
      { type: "bar", label: "Perkiraan dividen cair", data: dasarBulan, backgroundColor: warna("--series-1"), borderRadius: 6, borderSkipped: false, maxBarThickness: 30, order: 2 },
      { type: "bar", label: "Skenario terburuk", data: burukBulan, backgroundColor: alfa(warna("--turun"), 0.55), borderRadius: 6, borderSkipped: false, maxBarThickness: 30, order: 2 },
      { type: "line", label: `Sukuk ${sukuk.value}% per bulan`, data: BULAN.map(() => sk), borderColor: warna("--series-2"), borderDash: [5, 4], borderWidth: 2, pointRadius: 0, order: 1 },
    ],
  };
});
const opsi = computed(() => {
  tema.value;
  const o = opsiDasar();
  o.animation = false;
  o.scales.y.ticks.callback = (n) => `Rp${ringkas(n)}`;
  o.plugins.tooltip.callbacks = { label: (c) => ` ${c.dataset.label}  Rp${rupiah(Math.round(c.parsed.y))}` };
  return o;
});
</script>

<template>
  <div class="space-y-5">
    <Panel judul="Kalkulator penghasilan dividen" ket="Perkiraan dari riwayat dividen, bukan janji. Dibagi rata ke semua saham, dibulatkan per lot (100 lembar), termasuk fee beli 0,15%.">
      <div class="grid gap-5 lg:grid-cols-[1fr_1.2fr]">
        <div class="space-y-4">
          <label class="block">
            <span class="text-xs text-muted">Modal (Rp)</span>
            <input v-model.number="modal" type="number" min="1000000" step="1000000" class="mt-1 w-full tabular-nums" />
          </label>
          <div>
            <div class="mb-1 text-xs text-muted">Dasar perkiraan dividen</div>
            <Segmen v-model="dasar" :pilihan="DASAR" kecil />
            <p class="m-0 mt-1 text-[11px] text-muted">Konservatif = yang lebih kecil antara 12 bulan terakhir dan rata-rata 3 tahun (dividen spesial tidak dianggap berulang).</p>
          </div>
          <div class="flex flex-wrap items-end gap-4">
            <div>
              <div class="mb-1 text-xs text-muted">Pajak dividen</div>
              <Segmen v-model="pajak" :pilihan="[[10, '10%'], [0, 'Bebas (diinvestasikan ulang)']]" kecil />
            </div>
            <label>
              <span class="block text-xs text-muted">Kupon sukuk pembanding (%/th)</span>
              <input v-model.number="sukuk" type="number" min="0" max="15" step="0.05" class="mt-1 w-28 tabular-nums" />
            </label>
          </div>
          <p class="m-0 text-[11px] leading-relaxed text-muted">Dividen individu dalam negeri bisa bebas pajak kalau diinvestasikan kembali di Indonesia (UU HPP); kalau tidak, final 10%. Isi kupon sukuk sesuai seri SR/ST yang sedang ditawarkan.</p>
        </div>
        <div>
          <div class="mb-1 text-xs text-muted">Saham ({{ kode.length }}/30)</div>
          <div class="flex min-h-[44px] flex-wrap gap-1.5 rounded-2xl bg-surface-2 p-2">
            <span v-for="k in kode" :key="k" class="inline-flex h-7 items-center gap-1 rounded-full bg-surface px-2.5 text-xs font-medium">
              {{ k }}<button class="text-muted hover:text-turun" :aria-label="`Hapus ${k}`" @click="hapus(k)"><X class="h-3 w-3" /></button>
            </span>
            <span v-if="!kode.length" class="px-2 py-1 text-xs text-muted">Belum ada saham. Tambah kode atau pakai tombol isi cepat.</span>
          </div>
          <div class="relative mt-2 flex gap-2">
            <input v-model="tambah" class="min-w-0 flex-1 uppercase" placeholder="Tambah kode, mis. TLKM" @keydown.enter="tambahKode()" />
            <button class="tombol" @click="tambahKode()"><Plus class="h-3.5 w-3.5" />Tambah</button>
            <div v-if="saran.length" class="absolute top-full left-0 z-10 mt-1 w-64 overflow-hidden rounded-2xl bg-surface-3 py-1 shadow-lg">
              <button v-for="s in saran" :key="s.kode" class="flex w-full items-center justify-between px-4 py-1.5 text-left text-xs hover:bg-surface-2" @click="tambahKode(s.kode)">
                <span class="font-medium">{{ s.kode }}</span><span class="text-muted">yield {{ persen(s.yield, 1, false) }}</span>
              </button>
            </div>
          </div>
          <div class="mt-2 flex flex-wrap gap-2">
            <button class="tombol !h-8 !text-xs" @click="isi('aman')">Isi 10 yield tertinggi tanpa tanda bahaya</button>
            <button class="tombol !h-8 !text-xs" @click="isi('konsisten')">Isi 10 paling konsisten</button>
            <button v-if="kode.length" class="tombol !h-8 !text-xs" @click="kode = []">Kosongkan</button>
          </div>
        </div>
      </div>
    </Panel>

    <template v-if="baris.length">
      <Stats :items="stat" kolom="grid-cols-2 md:grid-cols-3 xl:grid-cols-5" />

      <Panel judul="Kapan dividen cair" :ket="ketCair">
        <div class="h-[260px]"><Bar v-if="grafik" :data="grafik" :options="opsi" /></div>
        <p class="m-0 mt-2 text-xs text-muted">Dividen saham terkumpul di beberapa bulan (umumnya Mei–Agustus); sukuk membayar rata tiap bulan. Untuk penghasilan bulanan yang rata, sisihkan dividen untuk dibagi ke bulan-bulan kosong.</p>
      </Panel>

      <Panel judul="Rincian per saham" rapat>
        <div class="overflow-x-auto">
          <table class="tabel min-w-[980px]">
            <thead><tr><th>Saham</th><th class="!text-right">Harga</th><th class="!text-right">Lot</th><th class="!text-right">Nilai</th><th class="!text-right">Dividen/lembar</th><th class="!text-right">Dividen/tahun</th><th class="!text-right">Yield</th><th class="!text-right">Terburuk</th><th>Catatan</th></tr></thead>
            <tbody>
              <tr v-for="s in baris" :key="s.kode">
                <td class="!h-auto py-2.5"><KodeSaham :kode="s.kode" /><div class="max-w-[180px] truncate text-[11px] text-muted">{{ s.nama || s.sektor || "" }}</div></td>
                <td class="text-right tabular-nums">{{ rupiah(s.harga) }}</td>
                <td class="text-right tabular-nums" :class="s.lot ? '' : 'text-turun'">{{ s.lot }}</td>
                <td class="text-right tabular-nums">Rp{{ ringkas(Math.round(s.nilai)) }}</td>
                <td class="text-right tabular-nums">Rp{{ rupiah(Math.round(s.dps)) }}</td>
                <td class="text-right font-medium tabular-nums">Rp{{ ringkas(Math.round(s.tahunan)) }}</td>
                <td class="text-right">{{ persen(s.harga ? (s.dps / s.harga) * 100 : 0, 1, false) }}</td>
                <td class="text-right text-xs" :class="s.rasio < 0.7 ? 'text-turun' : 'text-muted'" :title="s.tahun_terburuk ? `penurunan terparah ${s.tahun_terburuk}` : 'riwayat kurang, diasumsikan turun 50%'">{{ s.terburuk != null ? `${Math.round(s.rasio * 100)}%` : "50%?" }}</td>
                <td class="!h-auto !whitespace-normal py-2.5 text-xs">
                  <span v-if="!s.syariah" class="chip mr-1 bg-turun-bg text-turun">bukan syariah</span>
                  <span v-if="!s.lot" class="chip mr-1 bg-turun-bg text-turun">modal kurang untuk 1 lot</span>
                  <span v-if="!s.dps" class="chip mr-1 bg-surface-2 text-muted">belum ada dividen</span>
                  <span v-if="s.tanda.length" class="chip bg-kuning-bg text-kuning" :title="s.tanda.map((t) => '• ' + (tandaKet?.[t] || t)).join('\n')">{{ s.tanda.length }} tanda bahaya</span>
                  <span v-else-if="s.dps" class="chip bg-naik-bg text-naik">aman</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="m-0 px-6 py-3 text-xs text-muted">Terburuk = dividen tahun berikutnya kalau terulang penurunan terparah saham itu dalam 10 tahun (mis. 59% = dividen jadi 59% dari sebelumnya). Harga saham juga bisa turun; kalkulator ini hanya menghitung penghasilan dividen.</p>
      </Panel>
    </template>
    <template v-else-if="memuat">
      <Kerangka panel jenis="stat" :n="4" kolom="grid-cols-2 md:grid-cols-4" />
      <Kerangka panel jenis="tabel" :n="4" logo />
    </template>
  </div>
</template>

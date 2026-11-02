<script setup>
import { ref, computed, inject, onMounted, onUnmounted, watch } from "vue";
import { Line } from "vue-chartjs";
import { RefreshCw, Lock, Radio, BookOpen, ArrowRight, TriangleAlert } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { pakaiTema } from "@/composables/tema";
import { pakaiPekerjaan } from "@/composables/pekerjaan";
import { opsiDasar, warna, gradien } from "@/utils/chart";
import { rupiah, persen, tanggal, kelasPersen } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import Stats from "@/components/common/Stats.vue";
import KodeSaham from "@/components/common/KodeSaham.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import PanelPekerjaan from "@/components/sistem/PanelPekerjaan.vue";
import PeringatanKualitas from "@/components/sistem/PeringatanKualitas.vue";

const props = defineProps({ s: Object });
const pindahTab = inject("pindahTab");
const statusApp = inject("status");
const tema = pakaiTema();
const r = ref(null);
const ft = ref(null);
const ftTransaksi = ref([]);
const langsung = ref(null);
const siap = ref(false);
const galat = ref("");
const { kerja, galat: galatKerja, sibuk, mulai, lanjutkan } = pakaiPekerjaan();
let detak = null;

async function muat() {
  try {
    [r.value, ft.value, ftTransaksi.value] = await Promise.all([
      ambil("paper/h29"), ambil("paper/ringkasan").catch(() => null), ambil("paper/transaksi?batas=1000").catch(() => []),
    ]);
    siap.value = true;
  } catch (e) {
    galat.value = `API tidak bisa dihubungi: ${e.message}`;
  }
}
async function muatLangsung() {
  langsung.value = await ambil("paper/h29/langsung").catch(() => langsung.value);
}
const perbarui = () => mulai("aksi/paper_h22", {}, muat);

onMounted(async () => {
  await muat();
  muatLangsung();
  detak = setInterval(() => statusApp?.value?.bursa_buka && muatLangsung(), 60000);
  await lanjutkan("paper_h22", muat);
});
onUnmounted(() => clearInterval(detak));

const biaya = computed(() => props.s?.fitur?.biaya_rebalance);
const seri = computed(() => r.value?.seri || []);
const rk = computed(() => r.value?.ringkas || {});
const akhir = computed(() => seri.value[seri.value.length - 1] || null);
const posisiFt = computed(() => (ft.value?.posisi || []).filter((p) => p.status === "aktif" || p.status === "jual_besok"));
const adaLangsung = computed(() => langsung.value?.ada && langsung.value.sesi > (r.value?.tgl_terakhir || ""));

const stat = computed(() => {
  const x = r.value;
  if (!x?.ada) return [];
  const e = akhir.value;
  return [
    { label: "Ekuitas Momentum Blend", nilai: `Rp${rupiah(Math.round(e?.h29 ?? 1e8))}`, ket: "modal Rp100.000.000",
      info: "Nilai gabungan: 50% hasil bagian Follow Tren + 50% hasil bagian RS 12-1, disamakan lagi tiap akhir bulan. Uang pura-pura." },
    { label: "Return sejak mulai", nilai: persen(rk.value.h29?.return_pct ?? 0), nada: (rk.value.h29?.return_pct ?? 0) >= 0 ? "naik" : "turun",
      ket: biaya.value ? `setelah biaya pindah ${persen(rk.value.h29_biaya?.return_pct ?? 0)}` : `sejak ${tanggal(x.mulai)}`,
      info: "Dihitung dari titik awal close 30 Okt 2026. Angka kedua sudah dipotong perkiraan biaya saat porsi dikembalikan ke 50/50." },
    { label: "Bagian Follow Tren", nilai: persen(rk.value.h11a?.return_pct ?? 0), nada: (rk.value.h11a?.return_pct ?? 0) >= 0 ? "naik" : "turun",
      ket: `${posisiFt.value.length} / 10 saham dipegang`, info: "Bagian ini = paper Follow Tren yang sudah berjalan sejak 21 Okt 2026, dihitung dari 30 Okt." },
    { label: "Bagian RS 12-1", nilai: persen(rk.value.h22?.return_pct ?? 0), nada: (rk.value.h22?.return_pct ?? 0) >= 0 ? "naik" : "turun",
      ket: `${x.posisi.length} / ${x.rencana?.n || x.rebalance?.n || "±22"} saham dipegang`, info: "Bagian momentum bulanan dengan modal Rp100 jt sendiri, lot 100." },
    { label: "Turun terdalam", nilai: persen(rk.value.h29?.dd_maks_pct ?? 0, 1, false), nada: "turun", ket: "batas gagal -45%",
      info: "Penurunan terbesar dari titik tertinggi sejak mulai. Kalau lebih dalam dari -45%, paper Momentum Blend dinyatakan gagal." },
    { label: "Rebalance RS 12-1 berikutnya", nilai: tanggal(x.rebalance_berikutnya), ket: "otomatis di harga pembukaan",
      info: "Hari bursa pertama bulan berikutnya. Tanggal ini perkiraan; kalau hari itu libur bursa, dieksekusi di hari bursa berikutnya." },
  ];
});

const SERI = computed(() => [
  { kunci: "h29", label: "Momentum Blend", var: "--series-1", lebar: 2.5, putus: [], isi: true },
  ...(biaya.value ? [{ kunci: "h29_biaya", label: "Setelah biaya pindah", var: "--series-1", lebar: 1.5, putus: [4, 3] }] : []),
  { kunci: "h11a", label: "Bagian Follow Tren", var: "--series-2", lebar: 1.5, putus: [] },
  { kunci: "h22", label: "Bagian RS 12-1", var: "--series-4", lebar: 1.5, putus: [] },
  { kunci: "ew", label: "Bobot sama syariah", var: "--series-3", lebar: 1.5, putus: [5, 4] },
  { kunci: "jii", label: "JII", var: "--series-5", lebar: 1.5, putus: [2, 3] },
]);
const dataKurva = computed(() => {
  tema.value;
  return {
    labels: seri.value.map((x) => x.tgl.slice(0, 10)),
    datasets: SERI.value.map((s) => ({
      label: s.label, data: seri.value.map((x) => x[s.kunci]), borderColor: warna(s.var), pointBackgroundColor: warna(s.var), pointHoverBorderColor: warna("--surface-1"),
      backgroundColor: s.isi ? gradien(s.var) : "transparent", fill: s.isi ? "origin" : false, borderWidth: s.lebar, borderDash: s.putus,
      pointRadius: seri.value.length < 3 ? 3 : 0, tension: 0.35, cubicInterpolationMode: "monotone", spanGaps: true,
    })),
  };
});
const opsiKurva = computed(() => {
  tema.value;
  const o = opsiDasar();
  o.scales.y.ticks.callback = (v) => `${(v / 1e6).toFixed(0)} jt`;
  o.plugins.tooltip.callbacks = { label: (c) => ` ${c.dataset.label}  Rp${rupiah(Math.round(c.parsed.y))} (${persen((c.parsed.y / 1e8 - 1) * 100)})` };
  return o;
});
const dataDd = computed(() => {
  tema.value;
  let puncak = 0;
  const dd = seri.value.map((x) => { puncak = Math.max(puncak, x.h29); return (x.h29 / puncak - 1) * 100; });
  return {
    labels: seri.value.map((x) => x.tgl.slice(0, 10)),
    datasets: [
      { label: "Penurunan dari puncak", data: dd, borderColor: warna("--turun"), backgroundColor: gradien("--turun", 0.05), fill: "origin", borderWidth: 2, pointRadius: seri.value.length < 3 ? 3 : 0, tension: 0.3 },
      { label: "Batas gagal -45%", data: dd.map(() => -45), borderColor: warna("--turun"), borderDash: [2, 3], borderWidth: 1, pointRadius: 0 },
    ],
  };
});
const opsiDd = computed(() => {
  tema.value;
  const o = opsiDasar();
  o.scales.y.max = 0;
  o.scales.y.min = -50;
  o.scales.y.ticks.callback = (v) => `${v}%`;
  o.scales.y.ticks.maxTicksLimit = 4;
  o.scales.x.ticks.display = false;
  o.plugins.tooltip.callbacks = { label: (c) => ` ${c.dataset.label}: ${c.parsed.y.toFixed(1)}%` };
  return o;
});
const kartuAkhir = computed(() => SERI.value.map((s) => ({ ...s, x: rk.value[s.kunci === "ew" ? "ew" : s.kunci] })).filter((s) => s.x));

const status = computed(() => r.value?.evaluasi?.status || {});
const NAMA_ZONA = { normal: "zona normal", waspada: "zona waspada", gagal: "zona GAGAL", belum: "zona belum dinilai" };

const rencanaBaris = computed(() => {
  const x = r.value?.rencana;
  if (!x) return [];
  const pr = Object.fromEntries((x.peringkat || []).map((p, i) => [p.ticker, { no: i + 1, m: p.momentum_pct }]));
  return [...x.beli.map((t) => ({ aksi: "beli", t, ...pr[t] })), ...x.jual.map((t) => ({ aksi: "jual", t, ...pr[t] }))];
});
const tunda = computed(() => Object.keys(r.value?.tunda_beli || {}));

const AKSI = { beli: "Beli", jual: "Jual", pangkas: "Pangkas", dividen: "Dividen", split: "Split", batal_kas: "Batal · kas kurang", batal_tunda: "Batal · tertunda",
  batal_ARA: "Batal · ARA terkunci" };
const riwayat = computed(() => {
  const rs = (r.value?.transaksi || []).map((t) => ({ ...t, bagian: "RS 12-1", lot: t.lembar ? Math.round(t.lembar / 100) : null, hasil: t.net_pct, rp: t.untung_rp ?? t.nilai_rp }));
  const jual = ftTransaksi.value.filter((t) => String(t.tgl) >= "2026-10-30");
  const beliFt = [...jual.filter((t) => t.aksi === "jual" && t.tgl_masuk), ...posisiFt.value]
    .filter((t) => String(t.tgl_masuk) >= "2026-10-30")
    .map((t) => ({ tgl: t.tgl_masuk, aksi: "beli", ticker: t.ticker, bagian: "Follow Tren", lot: t.lot, harga: t.harga_masuk, hasil: null, rp: null }));
  const lainFt = jual.map((t) => ({ tgl: t.tgl, aksi: t.aksi, ticker: t.ticker, bagian: "Follow Tren", lot: t.lot, harga: t.harga_keluar, hasil: t.net_pct, rp: t.untung_rp }));
  return [...rs, ...beliFt, ...lainFt].sort((a, b) => (String(a.tgl) < String(b.tgl) ? 1 : -1));
});
const saringBagian = ref("");
const saringAksi = ref("");
const hal = ref(1);
const PER = 25;
const riwayatTersaring = computed(() => riwayat.value.filter((t) => (!saringBagian.value || t.bagian === saringBagian.value) && (!saringAksi.value || t.aksi === saringAksi.value)));
const riwayatTampil = computed(() => riwayatTersaring.value.slice((hal.value - 1) * PER, hal.value * PER));
const jumlahHal = computed(() => Math.max(1, Math.ceil(riwayatTersaring.value.length / PER)));
watch([saringBagian, saringAksi], () => (hal.value = 1));
function hasil(t) {
  if (t.hasil != null) return { teks: persen(t.hasil), kelas: kelasPersen(t.hasil) };
  if (t.rp == null) return { teks: "–", kelas: "text-muted" };
  if (t.aksi === "dividen") return { teks: `+Rp${rupiah(t.rp)}`, kelas: "text-naik" };
  if (t.aksi === "beli") return { teks: `Rp${rupiah(t.rp)} dibelanjakan`, kelas: "text-ink-2 font-normal" };
  if (t.aksi === "pangkas") return { teks: `Rp${rupiah(t.rp)} diterima`, kelas: "text-ink-2 font-normal" };
  return { teks: `Rp${rupiah(t.rp)}`, kelas: "text-ink-2 font-normal" };
}
</script>

<template>
  <div class="space-y-5">
    <PeringatanKualitas bagian="h22" />
    <div class="flex flex-wrap items-center justify-between gap-3">
      <p class="m-0 min-w-0 flex-1 text-[13px] leading-relaxed text-ink-2">Dua aturan momentum dijalankan ke depan dengan uang pura-pura dalam satu modal, lalu dinilai pada 1 Nov 2027. Tidak perlu beli manual: semuanya tercatat otomatis.</p>
      <button v-if="r?.ada" class="tombol-utama" :disabled="sibuk" @click="perbarui">
        <RefreshCw class="h-3.5 w-3.5" :class="sibuk ? 'animate-spin' : ''" />{{ sibuk ? "Memperbarui..." : "Perbarui hari ini" }}
      </button>
    </div>
    <div v-if="galat" class="panel px-5 py-3.5 text-turun">{{ galat }}</div>
    <PanelPekerjaan :kerja="kerja" :galat="galatKerja" />

    <template v-if="!siap && !galat">
      <Kerangka panel jenis="stat" :n="6" :judul="false" kolom="grid-cols-2 md:grid-cols-3 xl:grid-cols-6" />
      <Kerangka panel jenis="grafik" :tinggi="260" />
      <Kerangka panel jenis="tabel" :n="4" logo />
    </template>

    <Panel v-else-if="r && !r.ada" judul="Paper Momentum Blend belum dimulai">
      <p class="m-0 text-ink-2">Tekan "Perbarui hari ini" untuk menyiapkan bagian RS 12-1 (titik awal close 30 Okt 2026, rebalance pertama di open 2 Nov 2026).</p>
      <button class="tombol-utama mt-3" :disabled="sibuk" @click="perbarui">Siapkan paper</button>
    </Panel>

    <template v-else-if="r">
      <Stats :items="stat" />

      <details class="group rounded-2xl bg-surface-2/60 px-5 py-3 text-[13px] leading-relaxed text-ink-2">
        <summary class="flex cursor-pointer list-none items-center gap-2 font-medium text-ink [&::-webkit-details-marker]:hidden">
          <BookOpen class="h-4 w-4 text-aksen" />Cara membaca halaman ini
          <span class="ml-auto text-xs font-normal text-aksen group-open:hidden">Buka</span><span class="ml-auto hidden text-xs font-normal text-aksen group-open:inline">Tutup</span>
        </summary>
        <ul class="m-0 mt-2 list-disc space-y-1.5 pl-5">
          <li><b class="font-medium text-ink">Modal Rp100 jt dibagi dua.</b> Separuh ikut Follow Tren (beli saham yang mencetak rekor tertinggi setahun), separuh ikut RS 12-1 (tiap bulan pegang saham yang paling naik 12 bulan).</li>
          <li><b class="font-medium text-ink">Bagian Follow Tren</b> bisa beli/jual hari apa saja. <b class="font-medium text-ink">Bagian RS 12-1</b> hanya bertransaksi sekali sebulan, di hari bursa pertama tiap bulan.</li>
          <li><b class="font-medium text-ink">Tiap akhir bulan</b> porsi kedua bagian disamakan lagi jadi 50/50, jadi bagian yang naik lebih banyak "menyumbang" ke bagian yang tertinggal.</li>
          <li><b class="font-medium text-ink">Rugi beberapa bulan itu normal.</b> Strategi momentum hidup dari sedikit saham yang naik besar. Yang dihitung gagal hanya kalau turun lebih dalam dari -45% dari puncak, atau ada kesalahan eksekusi.</li>
          <li><b class="font-medium text-ink">Ini bukan rekomendasi beli.</b> Ide ini dibuat setelah melihat data lama, jadi kita menunggu bukti dari paper ini sampai Nov 2027.</li>
        </ul>
      </details>

      <div v-if="adaLangsung" class="panel px-6 py-4">
        <div class="flex flex-wrap items-center gap-x-6 gap-y-2">
          <div class="flex items-center gap-2 text-[13px] font-medium"><Radio class="h-4 w-4 text-aksen" />Pantauan hari ini</div>
          <div v-if="langsung.gabung_hari_ini_pct != null"><span class="text-xs text-muted">Momentum Blend</span><span class="ml-2 text-[17px] font-medium tabular-nums" :class="kelasPersen(langsung.gabung_hari_ini_pct)">{{ persen(langsung.gabung_hari_ini_pct, 2) }}</span></div>
          <div v-if="langsung.h11a_hari_ini_pct != null" class="text-xs text-muted">Follow Tren <span class="font-medium tabular-nums" :class="kelasPersen(langsung.h11a_hari_ini_pct)">{{ persen(langsung.h11a_hari_ini_pct, 2) }}</span></div>
          <div v-if="langsung.h22_hari_ini_pct != null" class="text-xs text-muted">RS 12-1 <span class="font-medium tabular-nums" :class="kelasPersen(langsung.h22_hari_ini_pct)">{{ persen(langsung.h22_hari_ini_pct, 2) }}</span></div>
          <span class="ml-auto text-xs text-muted">harga per menit Yahoo, pukul {{ langsung.jam }} · tertunda ±10 menit · resmi masuk paper setelah 17:00</span>
        </div>
      </div>

      <Panel judul="Aksi berikutnya" :ket="r.rencana ? `Rebalance RS 12-1 · sinyal close ${tanggal(r.rencana.sinyal)} · dieksekusi di harga pembukaan hari bursa berikutnya` : `Bagian RS 12-1 baru bertransaksi lagi di rebalance ${tanggal(r.rebalance_berikutnya)}`" rapat
        info="Daftar ini dibuat otomatis dari peringkat kenaikan 12 bulan. Tidak perlu beli manual. Aksi bagian Follow Tren ada di menu Follow Tren.">
        <div v-if="rencanaBaris.length" class="overflow-x-auto">
          <p class="m-0 px-6 pb-2 text-xs text-muted">{{ r.rencana.lolos }} saham syariah lolos syarat · pegang {{ r.rencana.n }} teratas · ±Rp{{ rupiah(r.rencana.anggaran_rp) }} per saham baru</p>
          <table class="tabel min-w-[560px]">
            <thead><tr><th class="w-20">Aksi</th><th>Saham</th><th class="!text-right">Peringkat</th><th class="!text-right">Naik 12 bulan</th><th>Alasan</th></tr></thead>
            <tbody>
              <tr v-for="b in rencanaBaris" :key="b.aksi + b.t">
                <td><span class="chip" :class="b.aksi === 'jual' ? 'bg-turun-bg text-turun' : 'bg-aksen-lembut text-aksen'">{{ b.aksi === "jual" ? "JUAL" : "BELI" }}</span></td>
                <td><KodeSaham :kode="b.t" /></td>
                <td class="text-right tabular-nums">{{ b.no ?? "–" }}</td>
                <td class="text-right tabular-nums" :class="kelasPersen(b.m)">{{ b.m != null ? persen(b.m, 1) : "–" }}</td>
                <td class="text-xs text-ink-2">{{ b.aksi === "jual" ? `peringkat jatuh ke luar ${r.rencana.n * 2} teratas atau tidak lolos syarat lagi` : `masuk ${r.rencana.n} teratas, slot kosong` }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="m-0 px-6 pt-1 pb-4 text-muted">Tidak ada aksi RS 12-1 sampai rebalance berikutnya. Pegang posisi yang ada.</p>
        <p v-if="tunda.length" class="m-0 px-6 pb-4 text-xs text-muted">Beli tertunda (saham terkunci atau tidak ada transaksi, dicoba lagi tiap hari): {{ tunda.join(", ") }}</p>
        <div v-if="r.rencana?.koreksi?.length" class="mx-6 mb-4 rounded-2xl bg-surface-2 px-4 py-3 text-xs leading-relaxed text-ink-2">
          <div class="mb-1 flex items-center gap-2 font-medium text-ink"><TriangleAlert class="h-3.5 w-3.5 text-aksen" />Koreksi data di sinyal ini</div>
          <p class="m-0">{{ r.rencana.koreksi[0]?.alasan }}</p>
          <p v-if="r.rencana.koreksi_dampak" class="m-0 mt-1">{{ r.rencana.koreksi_dampak.dihitung_ulang }} saham dihitung ulang. Dampak ke {{ r.rencana.n }} teratas: masuk <b class="font-medium">{{ r.rencana.koreksi_dampak.masuk.join(", ") || "–" }}</b>, keluar <b class="font-medium">{{ r.rencana.koreksi_dampak.keluar.join(", ") || "–" }}</b>.</p>
          <details class="mt-2">
            <summary class="cursor-pointer text-ink">Peringkat yang berubah ({{ r.rencana.koreksi.length }} saham)</summary>
            <ul class="m-0 mt-1 list-disc space-y-0.5 pl-5">
              <li v-for="k in r.rencana.koreksi" :key="k.ticker">{{ k.ticker }}: peringkat {{ k.peringkat_yahoo ?? "–" }} → {{ k.peringkat_koreksi ?? "–" }}, naik 12 bulan {{ persen(k.momentum_yahoo_pct, 1) }} → {{ persen(k.momentum_koreksi_pct, 1) }} · {{ k.penyebab }}</li>
            </ul>
          </details>
          <p class="m-0 mt-1 text-muted">Bukti per saham (close IDX, ex-date, faktor) tersimpan di koleksi paper_h22_koreksi.</p>
        </div>
      </Panel>

      <Panel judul="Ekuitas paper" ket="Semua garis dimulai Rp100 jt pada close 30 Okt 2026 · bobot sama tanpa biaya · JII tanpa dividen">
        <template #aksi>
          <span v-for="k in kartuAkhir" :key="k.kunci" class="inline-flex items-center gap-2 rounded-full bg-surface-2 py-1.5 pr-3 pl-2.5 text-xs text-ink-2">
            <i class="h-2 w-2 rounded-full" :style="{ background: `var(${k.var})` }"></i>{{ k.label }}
            <b class="font-medium tabular-nums" :class="kelasPersen(k.x.return_pct)">{{ persen(k.x.return_pct) }}</b>
          </span>
        </template>
        <div class="h-[260px]"><Line :data="dataKurva" :options="opsiKurva" /></div>
        <div class="label mt-5 mb-1">Penurunan Momentum Blend dari puncak</div>
        <div class="h-[110px]"><Line :data="dataDd" :options="opsiDd" /></div>
        <p v-if="seri.length < 3" class="m-0 mt-2 text-xs text-muted">Grafik masih pendek: paper baru dimulai. Titik bertambah tiap hari bursa setelah 17:00.</p>
        <div class="mt-5 rounded-2xl bg-surface-2 px-5 py-4">
          <div class="mb-2 flex items-center gap-2 text-[13px] font-medium"><Lock class="h-3.5 w-3.5 text-aksen" />Kriteria evaluasi (dikunci 2026-11-01)</div>
          <ul class="m-0 list-disc space-y-1 pl-5 text-xs leading-relaxed text-ink-2">
            <li v-for="k in r.evaluasi?.kriteria || []" :key="k">{{ k }}</li>
          </ul>
          <div class="mt-3 flex flex-wrap gap-2 text-xs">
            <span v-for="(v, k) in status" :key="k" class="chip !h-auto !whitespace-normal py-1 leading-snug" :class="v.gagal ? 'bg-turun-bg text-turun' : 'bg-aksen-lembut text-aksen'">
              {{ k === "h29" ? "Momentum Blend" : "Follow Tren" }} · {{ v.gagal ? `GAGAL: ${v.alasan.join("; ")}` : "belum gagal" }}<template v-if="v.dd_maks_pct != null"> · turun terdalam {{ persen(v.dd_maks_pct, 1) }} (batas -45%)</template><template v-if="v.zona"> · {{ NAMA_ZONA[v.zona] || v.zona }} h11a_v1</template>
            </span>
          </div>
          <p v-if="biaya" class="m-0 mt-3 text-xs text-muted">Angka kedua "setelah biaya pindah" memotong {{ persen(r.evaluasi?.biaya_pindah_pct, 2, false) }} dari nilai yang dipindah tiap akhir bulan (fee jual 0,25% + beli 0,15% + 2 × tick rata-rata {{ persen(r.evaluasi?.tick_estimasi_pct, 2, false) }}): {{ rk.kali_rebalance || 0 }} kali, total Rp{{ rupiah(Math.round(rk.biaya_rebalance_rp || 0)) }}. Laporan saja, bukan syarat.</p>
          <p v-if="r.cek" class="m-0 mt-1 text-xs" :class="r.cek.cocok ? 'text-muted' : 'text-turun'">Cek ulang bagian RS 12-1 ({{ tanggal(r.cek.sampai) }}, {{ r.cek.hari }} hari): {{ r.cek.cocok ? "COCOK, identik dengan hasil jalankan ulang dari nol" : `${r.cek.jumlah_beda} BEDA, periksa log job Cek ulang paper H29` }}.</p>
        </div>
      </Panel>

      <Panel judul="Posisi bagian RS 12-1" :ket="`${r.posisi.length} saham · bobot = nilai saham dibanding ekuitas bagian RS 12-1 · peringkat dari rebalance terakhir`" rapat
        info="Saham dipegang selama peringkatnya masih di 2N teratas. Tidak ada stop dan target untung: keluar hanya di rebalance bulanan.">
        <div v-if="r.posisi.length" class="overflow-x-auto">
          <table class="tabel min-w-[820px]">
            <thead><tr><th>Saham</th><th>Tanggal masuk</th><th class="!text-right">Lot</th><th class="!text-right">Harga masuk</th><th class="!text-right">Close</th>
              <th v-if="adaLangsung" class="!text-right">Sekarang</th><th class="!text-right">Untung</th><th class="!text-right">Bobot</th><th class="!text-right">Peringkat</th><th class="!text-right">Nilai</th></tr></thead>
            <tbody>
              <tr v-for="p in r.posisi" :key="p.ticker">
                <td><KodeSaham :kode="p.ticker" /></td>
                <td class="text-ink-2">{{ tanggal(p.tgl_masuk) }}</td>
                <td class="text-right tabular-nums">{{ rupiah(Math.round(p.lembar / 100)) }}</td>
                <td class="text-right tabular-nums">{{ rupiah(Math.round(p.harga_masuk)) }}</td>
                <td class="text-right tabular-nums">{{ p.close != null ? rupiah(Math.round(p.close)) : "–" }}</td>
                <td v-if="adaLangsung" class="text-right tabular-nums" :class="kelasPersen(langsung.posisi?.[p.ticker]?.untung_pct)">{{ langsung.posisi?.[p.ticker] ? rupiah(Math.round(langsung.posisi[p.ticker].harga)) : "–" }}</td>
                <td class="text-right font-medium tabular-nums" :class="kelasPersen(p.untung_pct)">{{ p.untung_pct != null ? persen(p.untung_pct) : "–" }}</td>
                <td class="text-right tabular-nums">{{ p.bobot_pct != null ? persen(p.bobot_pct, 1, false) : "–" }}</td>
                <td class="text-right tabular-nums text-ink-2">{{ p.peringkat ?? "–" }}</td>
                <td class="text-right tabular-nums">{{ p.nilai_rp != null ? `Rp${rupiah(Math.round(p.nilai_rp))}` : "–" }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="m-0 px-6 pt-1 pb-4 text-muted">Belum ada posisi. Pembelian pertama di harga pembukaan {{ tanggal(r.rebalance_berikutnya) }}{{ r.rencana ? ` (${r.rencana.beli.length} saham, lihat Aksi berikutnya)` : "" }}.</p>
      </Panel>

      <Panel judul="Posisi bagian Follow Tren" :ket="`${posisiFt.length} / 10 saham · sama dengan paper Follow Tren`" rapat>
        <template #aksi><button class="tombol" @click="pindahTab('tren52', 'paper')">Detail di Follow Tren <ArrowRight class="h-3.5 w-3.5" /></button></template>
        <div v-if="posisiFt.length" class="overflow-x-auto">
          <table class="tabel min-w-[640px]">
            <thead><tr><th>Saham</th><th>Tanggal masuk</th><th class="!text-right">Lot</th><th class="!text-right">Harga masuk</th><th class="!text-right">Close</th><th class="!text-right">Untung</th><th class="!text-right">Batas jual</th></tr></thead>
            <tbody>
              <tr v-for="p in posisiFt" :key="p.ticker">
                <td><KodeSaham :kode="p.ticker" /><span v-if="p.status === 'jual_besok'" class="ml-2 chip bg-turun-bg text-turun">jual besok</span></td>
                <td class="text-ink-2">{{ tanggal(p.tgl_masuk) }}</td>
                <td class="text-right tabular-nums">{{ p.lot }}</td>
                <td class="text-right tabular-nums">{{ rupiah(Math.round(p.harga_masuk)) }}</td>
                <td class="text-right tabular-nums">{{ p.close != null ? rupiah(Math.round(p.close)) : "–" }}</td>
                <td class="text-right font-medium tabular-nums" :class="kelasPersen(p.untung_pct)">{{ p.untung_pct != null ? persen(p.untung_pct) : "–" }}</td>
                <td class="text-right tabular-nums">{{ p.stop ? rupiah(Math.round(p.stop)) : "–" }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="m-0 px-6 pt-1 pb-4 text-muted">Bagian Follow Tren belum memegang saham.</p>
      </Panel>

      <Panel judul="Riwayat rebalance RS 12-1" ket="Satu baris per bulan · saham yang dibeli dan dijual di hari bursa pertama bulan itu" rapat>
        <div v-if="r.rebalance_riwayat.length" class="overflow-x-auto">
          <table class="tabel min-w-[760px]">
            <thead><tr><th>Eksekusi</th><th class="!text-right">Lolos</th><th class="!text-right">N</th><th>Dibeli</th><th>Dijual</th><th class="!text-right">Tetap</th><th class="!text-right">Ekuitas bagian</th></tr></thead>
            <tbody>
              <tr v-for="x in r.rebalance_riwayat" :key="x.eksekusi" class="align-top">
                <td class="!h-auto py-3 text-ink-2">{{ tanggal(x.eksekusi) }}<div class="text-[11px] text-muted">sinyal {{ tanggal(x.sinyal) }}</div>
                  <div v-if="x.koreksi_tercatat" class="mt-1 max-w-[220px] !whitespace-normal text-[11px] text-ink-2" :title="x.koreksi_tercatat.alasan">koreksi data: peringkat dihitung ulang dari close IDX × faktor aksi korporasi ({{ x.koreksi_tercatat.dihitung_ulang }} saham, {{ x.koreksi_tercatat.berubah }} berubah) · masuk <b class="font-medium">{{ x.koreksi_tercatat.masuk.join(", ") || "–" }}</b>, keluar <b class="font-medium">{{ x.koreksi_tercatat.keluar.join(", ") || "–" }}</b><span v-if="x.koreksi_tercatat.disetujui" class="block text-muted">disetujui {{ x.koreksi_tercatat.disetujui }}</span></div>
                  <div v-else-if="x.koreksi?.length" class="mt-1 max-w-[220px] !whitespace-normal text-[11px] text-ink-2">koreksi data: peringkat dihitung ulang dari close IDX ({{ x.koreksi_dampak?.dihitung_ulang ?? x.koreksi.length }} saham, {{ x.koreksi.length }} berubah)<template v-if="x.koreksi_dampak"> · masuk {{ x.koreksi_dampak.masuk.join(", ") || "–" }}, keluar {{ x.koreksi_dampak.keluar.join(", ") || "–" }}</template></div></td>
                <td class="!h-auto py-3 text-right tabular-nums">{{ x.lolos }}</td>
                <td class="!h-auto py-3 text-right tabular-nums">{{ x.n }}</td>
                <td class="!h-auto !whitespace-normal py-3"><div class="flex flex-wrap gap-1"><KodeSaham v-for="t in x.baru" :key="t" :kode="t" /><span v-if="!x.baru?.length" class="text-muted">–</span></div></td>
                <td class="!h-auto !whitespace-normal py-3"><div class="flex flex-wrap gap-1"><KodeSaham v-for="t in x.jual" :key="t" :kode="t" /><span v-if="!x.jual?.length" class="text-muted">–</span></div></td>
                <td class="!h-auto py-3 text-right tabular-nums">{{ x.tetap?.length ?? 0 }}</td>
                <td class="!h-auto py-3 text-right tabular-nums">Rp{{ rupiah(x.ekuitas_dasar) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="m-0 px-6 pt-1 pb-4 text-muted">Belum ada rebalance. Yang pertama di harga pembukaan {{ tanggal(r.rebalance_berikutnya) }}.</p>
      </Panel>

      <Panel judul="Riwayat transaksi" ket="Kedua bagian, terbaru di atas · hasil jual (%) sudah termasuk biaya dan dividen · beli = uang yang dibelanjakan" rapat>
        <template #aksi>
          <select v-model="saringBagian"><option value="">Kedua bagian</option><option value="Follow Tren">Follow Tren</option><option value="RS 12-1">RS 12-1</option></select>
          <select v-model="saringAksi"><option value="">Semua aksi</option><option value="beli">Beli</option><option value="jual">Jual</option><option value="pangkas">Pangkas</option><option value="dividen">Dividen</option></select>
        </template>
        <div v-if="riwayatTersaring.length" class="overflow-x-auto">
          <table class="tabel min-w-[640px]">
            <thead><tr><th>Tanggal</th><th>Bagian</th><th>Aksi</th><th>Saham</th><th class="!text-right">Lot</th><th class="!text-right">Harga</th><th class="!text-right">Hasil / nilai</th></tr></thead>
            <tbody>
              <tr v-for="(t, i) in riwayatTampil" :key="i">
                <td class="text-ink-2">{{ tanggal(t.tgl) }}</td>
                <td><span class="chip" :class="t.bagian === 'RS 12-1' ? 'bg-kuning-bg text-ink-2' : 'bg-aksen-lembut text-aksen'">{{ t.bagian }}</span></td>
                <td>{{ AKSI[t.aksi] || t.aksi }}</td>
                <td><KodeSaham :kode="t.ticker" /></td>
                <td class="text-right tabular-nums">{{ t.lot ?? "–" }}</td>
                <td class="text-right tabular-nums">{{ t.harga ? rupiah(Math.round(t.harga)) : "–" }}</td>
                <td class="text-right font-medium tabular-nums" :class="hasil(t).kelas">{{ hasil(t).teks }}</td>
              </tr>
            </tbody>
          </table>
          <div class="flex items-center justify-end gap-2 px-6 pt-2 pb-3 text-xs text-muted">
            <span>{{ riwayatTersaring.length }} transaksi · halaman {{ hal }} dari {{ jumlahHal }}</span>
            <button class="tombol !h-8 !w-8 !justify-center !px-0" :disabled="hal <= 1" @click="hal--">‹</button>
            <button class="tombol !h-8 !w-8 !justify-center !px-0" :disabled="hal >= jumlahHal" @click="hal++">›</button>
          </div>
        </div>
        <p v-else class="m-0 flex items-start gap-2 px-6 pt-1 pb-4 text-muted"><TriangleAlert class="mt-0.5 h-4 w-4 shrink-0" />Belum ada transaksi sejak Momentum Blend dimulai. Transaksi pertama bagian RS 12-1 di harga pembukaan {{ tanggal(r.rebalance_berikutnya) }}.</p>
      </Panel>
    </template>
  </div>
</template>

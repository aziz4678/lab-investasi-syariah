<script setup>
import TeksWarna from "@/components/common/TeksWarna.vue";
import { ref, computed, watch, onMounted, onUnmounted, inject } from "vue";
import { Search, ArrowUpRight, ArrowDownRight } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { persen, rupiah, ringkas, kelasPersen } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import Pemutar from "@/components/common/Pemutar.vue";
import Stats from "@/components/common/Stats.vue";
import GrafikHarga from "@/components/charts/GrafikHarga.vue";
import GrafikRentang from "@/components/charts/GrafikRentang.vue";
import PanelKepemilikan from "@/components/emiten/PanelKepemilikan.vue";
import PanelValuasi from "@/components/emiten/PanelValuasi.vue";
import PanelDividen from "@/components/emiten/PanelDividen.vue";
import PanelPengumuman from "@/components/emiten/PanelPengumuman.vue";
import PanelOrangDalam from "@/components/emiten/PanelOrangDalam.vue";
import PanelBerita from "@/components/emiten/PanelBerita.vue";
import HeaderEmiten from "@/components/emiten/HeaderEmiten.vue";
import Logo from "@/components/common/Logo.vue";

const kodeAktif = inject("kodeEmiten");
const daftar = ref([]);
const cari = ref("");
const p = ref(null);
const galat = ref("");
const memuat = ref(false);
const rentang = ref("1D");
const intra = ref(null);
const arahIntra = ref(null);
const statusApp = inject("status");
let detakIntra = null;
async function muatIntra(kode) {
  const x = await ambil(`pasar/intraday?kode=${kode}`).catch(() => null);
  if (p.value?.kode === kode) intra.value = x?.tgl?.length ? x : null;
}
onUnmounted(() => clearInterval(detakIntra));
const pakaiIntra = computed(() => rentang.value === "1D" && !!intra.value);
const arah = ref(null);
const semuaSinyal = ref(false);
const semuaLapkeu = ref(false);


const RENTANG = [
  { k: "1D", ket: "vs close sebelumnya" }, { k: "1W", ket: "1 minggu terakhir", hari: 7 }, { k: "1M", ket: "1 bulan terakhir", bulan: 1 },
  { k: "3M", ket: "3 bulan terakhir", bulan: 3 }, { k: "YTD", ket: "sejak awal tahun" }, { k: "1Y", ket: "1 tahun terakhir", bulan: 12 },
  { k: "3Y", ket: "3 tahun terakhir", bulan: 36 }, { k: "5Y", ket: "5 tahun terakhir", bulan: 60 }, { k: "ALL", ket: "sejak awal data" },
];
const SUMBER = { h11a_dev: "Backtest 2010-2019", h11a_2020: "Backtest 2020-2026", paper: "Paper trade" };

async function muat(kode) {
  kode = (kode || "").toUpperCase().trim();
  if (!kode) return;
  memuat.value = true;
  galat.value = "";
  try {
    intra.value = null;
    p.value = await ambil(`emiten/${kode}`);
    muatIntra(kode);
    arah.value = null;
    cari.value = kode;
    try { localStorage.setItem("emiten", kode); } catch { galat.value = ""; }
    history.replaceState(null, "", `#emiten/${kode}`);
  } catch {
    galat.value = `Data ${kode} tidak ditemukan. Ketik kode saham IDX, misalnya AALI.`;
  } finally {
    memuat.value = false;
  }
}

onMounted(async () => {
  detakIntra = setInterval(() => statusApp?.value?.bursa_buka && p.value && muatIntra(p.value.kode), 60000);
  ambil("emiten").then((d) => (daftar.value = d)).catch(() => (daftar.value = []));
  let awal = kodeAktif.value;
  if (!awal) {
    try { awal = localStorage.getItem("emiten"); } catch { awal = null; }
  }
  muat(awal || "AALI");
});
watch(kodeAktif, (k) => k && k !== p.value?.kode && muat(k));

const saran = computed(() => {
  const q = cari.value.toUpperCase().trim();
  if (!q || q === p.value?.kode) return [];
  const awal = daftar.value.filter((d) => d.kode.startsWith(q));
  const nama = daftar.value.filter((d) => !d.kode.startsWith(q) && (d.nama || "").toUpperCase().includes(q));
  return [...awal, ...nama].slice(0, 8);
});

function isoTgl(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

const dasar = computed(() => {
  const tgl = p.value?.grafik.tgl || [];
  const n = tgl.length;
  if (n < 2) return 0;
  const r = RENTANG.find((x) => x.k === rentang.value);
  if (r.k === "1D") return n - 2;
  if (r.k === "ALL") return 0;
  const akhir = new Date(tgl[n - 1]);
  let batas;
  if (r.k === "YTD") batas = `${akhir.getFullYear() - 1}-12-31`;
  else {
    const d = new Date(akhir);
    if (r.hari) d.setDate(d.getDate() - r.hari);
    else d.setMonth(d.getMonth() - r.bulan);
    batas = isoTgl(d);
  }
  let i = n - 1;
  while (i > 0 && tgl[i] > batas) i -= 1;
  return i;
});

const mulai = computed(() => {
  const n = p.value?.grafik.tgl.length || 0;
  return rentang.value === "1D" ? Math.max(0, n - 5) : dasar.value;
});

const kepala = computed(() => {
  if (pakaiIntra.value) {
    const x = intra.value;
    const harga = arahIntra.value?.harga ?? x.terakhir;
    const jam = (arahIntra.value?.tgl || x.tgl[x.tgl.length - 1]).slice(11, 16).replace(":", ".");
    return { harga, selisih: harga - x.tutup_kemarin, pct: (harga / x.tutup_kemarin - 1) * 100,
      ket: `${arahIntra.value ? "pukul" : "hari ini"} ${jam} · ${x.sesi} · dari penutupan kemarin ${rupiah(x.tutup_kemarin)}` };
  }
  const g = p.value?.grafik;
  if (!g) return null;
  const n = g.tgl.length;
  const i = arah.value ?? n - 1;
  const b = rentang.value === "1D" && arah.value != null ? Math.max(0, i - 1) : dasar.value;
  const harga = g.close[i];
  const awal = g.close[b];
  const selisih = harga - awal;
  const r = RENTANG.find((x) => x.k === rentang.value);
  return {
    harga, selisih, pct: awal ? (selisih / awal) * 100 : null,
    ket: arah.value == null ? `${r.ket} · ${g.tgl[n - 1]}` : `${g.tgl[i]} · dari ${g.tgl[b]}`,
  };
});

const statPeriode = computed(() => {
  const g = p.value?.grafik;
  if (!g) return [];
  const n = g.tgl.length;
  if (rentang.value === "1D") {
    const i = n - 1;
    return [
      ["Open", rupiah(g.open[i])], ["Tertinggi", rupiah(g.high[i])], ["Terendah", rupiah(g.low[i])],
      ["Volume", `${ringkas((g.volume[i] || 0) / 100)} lot`], ["Nilai", `Rp${ringkas((g.volume[i] || 0) * g.close[i])}`],
      ["IHSG", persen(g.ihsg[i - 1] ? (g.ihsg[i] / g.ihsg[i - 1] - 1) * 100 : null, 2)],
    ];
  }
  const a = dasar.value;
  if (a >= n - 1) return [];
  const hi = g.high.slice(a + 1);
  const lo = g.low.slice(a + 1);
  const nilai = g.close.slice(a + 1).map((c, j) => c * (g.volume[a + 1 + j] || 0));
  const iMax = hi.indexOf(Math.max(...hi));
  const iMin = lo.indexOf(Math.min(...lo));
  const ih = g.ihsg[a] ? (g.ihsg[n - 1] / g.ihsg[a] - 1) * 100 : null;
  const sh = g.close[a] ? (g.close[n - 1] / g.close[a] - 1) * 100 : null;
  return [
    ["Tertinggi", `${rupiah(hi[iMax])}`, g.tgl[a + 1 + iMax]], ["Terendah", `${rupiah(lo[iMin])}`, g.tgl[a + 1 + iMin]],
    ["Dari tertinggi", persen(hi[iMax] ? (g.close[n - 1] / hi[iMax] - 1) * 100 : null)],
    ["IHSG periode ini", persen(ih)], ["Selisih vs IHSG", persen(sh != null && ih != null ? sh - ih : null), "belum termasuk dividen"],
    ["Rata-rata transaksi", `Rp${ringkas(nilai.reduce((x, y) => x + y, 0) / Math.max(1, nilai.length))}/hari`],
  ];
});

const tradeGrafik = computed(() => (p.value?.trade || []).filter((t) => t.sumber !== "h11a_2020_konservatif" && t.dipilih));
const tradeTabel = computed(() => (p.value?.trade || [])
  .filter((t) => t.sumber !== "h11a_2020_konservatif" && (semuaSinyal.value || t.dipilih))
  .slice().reverse());

const k = computed(() => p.value?.kini);

const hariIni = computed(() => {
  const x = intra.value;
  const g = p.value?.grafik;
  if (x) {
    return { sumber: `per menit · pukul ${x.jam}`, baris: [
      ["Buka", rupiah(x.buka)], ["Tertinggi", rupiah(x.tertinggi)], ["Terendah", rupiah(x.terendah)], ["Tutup kemarin", rupiah(x.tutup_kemarin)],
      ["Volume", `${ringkas((x.volume || 0) / 100)} lot`], ["Nilai transaksi", `Rp${ringkas(x.nilai_transaksi || 0)}`],
    ] };
  }
  if (!g?.tgl?.length) return null;
  const i = g.tgl.length - 1;
  return { sumber: `penutupan ${g.tgl[i]}`, baris: [
    ["Buka", rupiah(g.open[i])], ["Tertinggi", rupiah(g.high[i])], ["Terendah", rupiah(g.low[i])], ["Tutup kemarin", rupiah(g.close[i - 1])],
    ["Volume", `${ringkas((g.volume[i] || 0) / 100)} lot`], ["Nilai transaksi", `Rp${ringkas((g.volume[i] || 0) * g.close[i])}`],
  ] };
});

const rentang52 = computed(() => {
  const g = p.value?.grafik;
  if (!g?.tgl?.length) return null;
  const n = g.tgl.length;
  const a = Math.max(0, n - 250);
  const tinggi = Math.max(...g.high.slice(a).filter((v) => v != null));
  const rendah = Math.min(...g.low.slice(a).filter((v) => v != null));
  const kini = intra.value?.terakhir ?? g.close[n - 1];
  return { tinggi, rendah, kini, posisi: tinggi > rendah ? ((kini - rendah) / (tinggi - rendah)) * 100 : 50 };
});

const pendukung = computed(() => {
  const f = p.value?.info || {};
  const kn = k.value || {};
  const y = f.dividendYield;
  return [
    ["Kapitalisasi pasar", f.marketCap ? `Rp${ringkas(f.marketCap)}` : "–"],
    ["PER", f.trailingPE ? `${f.trailingPE.toFixed(1).replace(".", ",")}x` : "–"],
    ["PBV", f.priceToBook ? `${f.priceToBook.toFixed(2).replace(".", ",")}x` : "–"],
    ["Yield dividen", y != null ? persen(y > 1 ? y : y * 100, 1, false) : "–"],
    ["Transaksi/hari (20 hr)", kn.nilai_transaksi ? `Rp${ringkas(kn.nilai_transaksi)}/hari` : "–"],
    ["Gerak harian (ATR)", kn.atr_pct != null ? `±${persen(kn.atr_pct, 1, false)}` : "–"],
  ];
});
const stat = computed(() => {
  if (!k.value) return [];
  const r = p.value.ringkasan_trade;
  return [
    { label: "Tertinggi 52 minggu", nilai: rupiah(k.value.maks250), ket: k.value.jarak_maks == null ? "–" : k.value.jarak_maks >= 0 ? `ditembus ${persen(k.value.jarak_maks)}` : `${persen(k.value.jarak_maks)} di bawahnya`,
      info: "Close tertinggi 250 hari bursa sebelumnya. Sinyal BELI Follow Tren muncul saat close menembus garis ini." },
    { label: "ATR 14 hari", nilai: persen(k.value.atr_pct, 1, false), ket: `Rp${rupiah(k.value.atr)} per hari`, info: "Rata-rata gerak harian. Jarak stop = 3 × ATR." },
    { label: "Stop kalau beli", nilai: persen(k.value.stop_jika_beli_pct), nada: "turun", ket: `di Rp${rupiah(k.value.stop_jika_beli)}`, info: "Perkiraan stop awal kalau dibeli di close terakhir: close − 3×ATR." },
    { label: "Transaksi 20 hari", nilai: ringkas(k.value.nilai_transaksi), ket: k.value.likuid ? "lolos syarat likuid" : "tidak lolos syarat", info: "Rata-rata nilai transaksi harian. Saham yang tidak lolos syarat likuiditas/ATR/harga tidak bisa memberi sinyal." },
    { label: "Trade Follow Tren", nilai: String(r.jumlah), ket: r.jumlah ? `win ${persen(r.win_rate, 0, false)} · rata ${persen(r.rata)}` : "belum pernah", info: "Trade backtest yang masuk portofolio (2010-2026), sudah dipotong biaya." },
  ];
});

const syariah = computed(() => {
  const hasil = [];
  for (const r of p.value?.periode_syariah || []) {
    const akhir = hasil.at(-1);
    const sambung = akhir && new Date(r.mulai) - new Date(akhir.akhir) <= 2 * 86400000;
    if (sambung) akhir.akhir = r.akhir;
    else hasil.push({ ...r });
  }
  return hasil;
});

const posisi = computed(() => p.value?.paper_posisi);
const terbit = computed(() => Object.fromEntries((p.value?.lapkeu || []).map((l) => [`${l.tahun}${l.periode}`, l])));
const fundTampil = computed(() => {
  const f = (p.value?.fundamental || []).slice().reverse();
  return semuaLapkeu.value ? f : f.slice(0, 8);
});
const unitFund = computed(() => {
  const u = new Set((p.value?.fundamental || []).map((f) => f.unit));
  return u.size ? [...u].join(" / ") : "IDR";
});
function uang(v, unit) {
  return v == null ? "–" : `${unit === "USD" ? "US$" : "Rp"}${ringkas(v)}`;
}
const STATUS_POS = { beli_besok: "Antre beli di open berikutnya", aktif: "Dipegang di paper trade", jual_besok: "Antre jual di open berikutnya" };
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <p class="m-0 min-w-0 flex-1 truncate text-[13px] text-ink-2">Riset per saham: profil, valuasi, harga, dividen, laporan keuangan, dan kepemilikan</p>
      <form class="relative w-full sm:w-72" @submit.prevent="muat(cari)">
        <Search class="pointer-events-none absolute top-1/2 left-4 h-4 w-4 -translate-y-1/2 text-muted" />
        <input v-model="cari" class="!h-10 w-full !border !border-garis !bg-surface !pl-10 uppercase shadow-kartu" placeholder="Kode saham, misal AALI" list="" autocomplete="off" />
        <div v-if="saran.length" class="absolute top-full right-0 left-0 z-10 mt-2 overflow-hidden rounded-2xl bg-surface-3 py-1.5 shadow-lg">
          <button v-for="s in saran" :key="s.kode" type="button" class="flex w-full items-center gap-3 px-4 py-2.5 text-left hover:bg-surface-2" @click="muat(s.kode)">
            <Logo jenis="emiten" :kunci="s.kode" :teks="s.kode" :ukuran="34" />
            <span class="min-w-0 flex-1">
              <span class="block font-medium">{{ s.kode }}</span>
              <span class="block truncate text-xs text-muted">{{ s.nama || s.sektor || "" }}</span>
            </span>
            <span class="chip" :class="s.syariah ? 'bg-naik-bg text-naik' : 'bg-surface-2 text-muted'">{{ s.syariah ? "syariah" : "bukan" }}</span>
          </button>
        </div>
      </form>
    </div>

    <div v-if="galat" class="panel px-6 py-4 text-turun">{{ galat }}</div>
    <template v-if="memuat && !p">
      <Kerangka panel :n="3" />
      <Kerangka panel jenis="stat" :n="4" kolom="grid-cols-2 md:grid-cols-4" />
      <Kerangka panel jenis="grafik" :tinggi="320" />
    </template>
    <div v-if="memuat && p" class="-mb-2 px-1"><Pemutar teks="Memuat data saham..." /></div>

    <template v-if="p">
      <HeaderEmiten :kode="p.kode" :syariah="p.syariah_kini" :kini="k" :posisi="posisi" :label-posisi="posisi ? STATUS_POS[posisi.status] || posisi.status : ''" :memuat="memuat" />

      <Panel judul="Harga" :ket="pakaiIntra ? 'Harga per menit hari ini dari Yahoo (tertunda ±10 menit) · geser kursor untuk melihat harga per menit' : 'Harga pasar harian · geser kursor di grafik untuk melihat harga per tanggal'">
        <div class="grid gap-6 xl:grid-cols-[minmax(0,1fr)_280px]">
        <div class="min-w-0">
        <div class="-mt-1 mb-4 flex flex-wrap items-end justify-between gap-3">
          <div v-if="kepala" class="min-w-0">
            <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <span class="text-[32px] leading-none font-medium tracking-tight tabular-nums">{{ rupiah(kepala.harga) }}</span>
              <span class="inline-flex items-center gap-1 text-[15px] font-medium tabular-nums" :class="kepala.selisih > 0 ? 'text-naik' : kepala.selisih < 0 ? 'text-turun' : 'text-muted'">
                <ArrowUpRight v-if="kepala.selisih > 0" class="h-4 w-4" :stroke-width="2.4" />
                <ArrowDownRight v-else-if="kepala.selisih < 0" class="h-4 w-4" :stroke-width="2.4" />
                {{ rupiah(Math.abs(kepala.selisih)) }} ({{ persen(kepala.pct, 2) }})
              </span>
              <span class="text-[13px] text-muted">{{ kepala.ket }}</span>
            </div>
          </div>
        </div>
        <div class="mb-4 flex flex-wrap gap-1.5">
          <button v-for="r in RENTANG" :key="r.k" type="button" @click="rentang = r.k"
            class="h-8 min-w-12 rounded-full border px-3 text-xs font-medium transition"
            :class="rentang === r.k ? 'border-aksen bg-aksen-lembut text-aksen' : 'border-garis text-muted hover:border-ink-2 hover:text-ink'">{{ r.k === "ALL" ? "Semua" : r.k }}</button>
        </div>
        <div v-if="!pakaiIntra" class="mb-3 flex flex-wrap gap-2 text-xs text-ink-2">
          <span class="inline-flex items-center gap-2 rounded-full bg-surface-2 px-3 py-1"><span class="h-0.5 w-4 rounded bg-s1"></span>Close</span>
          <span class="inline-flex items-center gap-2 rounded-full bg-surface-2 px-3 py-1"><span class="w-4 border-t-2 border-dashed border-s3"></span>Tertinggi 52 minggu</span>
          <span class="inline-flex items-center gap-2 rounded-full bg-surface-2 px-3 py-1"><span class="h-0.5 w-4 rounded bg-turun"></span>Trailing stop</span>
          <span class="inline-flex items-center gap-2 rounded-full bg-surface-2 px-3 py-1"><span class="text-naik">▲</span>Beli <span class="ml-1 text-turun">◆</span>Jual</span>
        </div>
        <GrafikRentang v-if="pakaiIntra" :tgl="[]" :harga="[]" :intraday="intra" awal="1D" polos :nama="p.kode" :tinggi="320"
          :format="(v) => rupiah(Math.round(v))" @arah="arahIntra = $event" />
        <GrafikHarga v-else :grafik="p.grafik" :trade="tradeGrafik" :mulai="mulai" @arah="arah = $event" />
        <p v-if="rentang === '1D' && !intra" class="m-0 mt-2 text-xs text-muted">Data per menit belum tersedia untuk saham ini: grafik menampilkan 5 hari bursa terakhir.</p>
        <div v-if="!pakaiIntra" class="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
          <div v-for="s in statPeriode" :key="s[0]" class="rounded-2xl bg-surface-2 px-4 py-3">
            <div class="text-xs text-muted">{{ s[0] }}</div>
            <div class="mt-0.5 font-medium tabular-nums"><TeksWarna :teks="s[1]" /></div>
            <div v-if="s[2]" class="text-[11px] text-muted">{{ s[2] }}</div>
          </div>
        </div>
        </div>
        <aside class="min-w-0 space-y-5 xl:border-l xl:border-garis xl:pl-6">
          <div v-if="hariIni">
            <div class="flex items-baseline justify-between gap-2"><span class="text-[13px] font-medium">Hari ini</span><span class="text-[11px] text-muted">{{ hariIni.sumber }}</span></div>
            <dl class="m-0 mt-2 grid grid-cols-2 gap-x-4 gap-y-2.5 text-[13px] xl:grid-cols-1">
              <div v-for="b in hariIni.baris" :key="b[0]" class="flex justify-between gap-3"><dt class="text-muted">{{ b[0] }}</dt><dd class="m-0 font-medium tabular-nums">{{ b[1] }}</dd></div>
            </dl>
          </div>
          <div v-if="rentang52">
            <div class="text-[13px] font-medium">Rentang 52 minggu</div>
            <div class="relative mt-3 h-1.5 rounded-full bg-surface-2">
              <span class="absolute inset-y-0 left-0 rounded-full bg-aksen-lembut" :style="{ width: `${rentang52.posisi}%` }"></span>
              <span class="absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-surface bg-aksen shadow" :style="{ left: `${Math.min(100, Math.max(0, rentang52.posisi))}%` }"></span>
            </div>
            <div class="mt-2 flex justify-between text-xs tabular-nums"><span class="text-turun">{{ rupiah(rentang52.rendah) }}</span><span class="text-naik">{{ rupiah(rentang52.tinggi) }}</span></div>
            <div class="mt-1 text-xs text-muted"><span :class="kelasPersen((rentang52.kini / rentang52.tinggi - 1) * 100)">{{ persen((rentang52.kini / rentang52.tinggi - 1) * 100, 1) }}</span> dari tertinggi</div>
          </div>
          <div>
            <div class="text-[13px] font-medium">Data pendukung</div>
            <dl class="m-0 mt-2 grid grid-cols-2 gap-x-4 gap-y-2.5 text-[13px] xl:grid-cols-1">
              <div v-for="b in pendukung" :key="b[0]" class="flex justify-between gap-3"><dt class="text-muted">{{ b[0] }}</dt><dd class="m-0 font-medium tabular-nums">{{ b[1] }}</dd></div>
            </dl>
          </div>
        </aside>
        </div>
      </Panel>

      <PanelValuasi :kode="p.kode" :yahoo="p.info" />



      <PanelDividen :kode="p.kode" />

      <Panel judul="Fundamental" :ket="`Laporan keuangan IDX ${p.fundamental.length ? p.fundamental[0].tahun + '–' + p.fundamental.at(-1).tahun : ''} · angka kumulatif sejak awal tahun · mata uang laporan ${unitFund} · terbit = tanggal publikasi di IDX`" rapat
        info="Tumbuh = dibanding periode yang sama tahun lalu. DER = liabilitas / ekuitas.">
        <p v-if="!p.fundamental.length" class="m-0 px-6 pt-1 pb-4 text-muted">Belum ada data fundamental untuk saham ini<template v-if="p.lapkeu.length"> (laporan terakhir terbit {{ p.lapkeu[0].tgl }})</template>.</p>
        <div v-else class="overflow-x-auto">
          <table class="tabel min-w-[900px]">
            <thead><tr><th>Periode</th><th class="!text-right">Pendapatan</th><th class="!text-right">Tumbuh</th><th class="!text-right">Laba</th><th class="!text-right">Tumbuh</th><th class="!text-right">Ekuitas</th><th class="!text-right">DER</th><th class="!text-right">Arus kas operasi</th><th class="!text-right">EPS</th><th class="!text-right">Terbit</th></tr></thead>
            <tbody>
              <tr v-for="f in fundTampil" :key="f.tahun + f.periode">
                <td><span class="font-medium">{{ f.tahun }}</span> <span class="text-ink-2">{{ f.periode === "AUDIT" ? "Tahunan" : f.periode }}</span></td>
                <td class="text-right">{{ uang(f.pendapatan, f.unit) }}</td>
                <td class="text-right" :class="f.tumbuh_pendapatan >= 0 ? 'text-naik' : 'text-turun'">{{ persen(f.tumbuh_pendapatan) }}</td>
                <td class="text-right" :class="f.laba < 0 ? 'text-turun' : ''">{{ uang(f.laba, f.unit) }}</td>
                <td class="text-right" :class="f.tumbuh_laba >= 0 ? 'text-naik' : 'text-turun'">{{ persen(f.tumbuh_laba) }}</td>
                <td class="text-right">{{ uang(f.ekuitas, f.unit) }}</td>
                <td class="text-right text-ink-2">{{ f.der == null ? "–" : f.der.toLocaleString("id-ID") }}</td>
                <td class="text-right" :class="f.arus_kas_operasi < 0 ? 'text-turun' : ''">{{ uang(f.arus_kas_operasi, f.unit) }}</td>
                <td class="text-right text-ink-2">{{ f.eps == null ? "–" : f.eps.toLocaleString("id-ID") }}</td>
                <td class="text-right text-xs tabular-nums text-muted" :title="terbit[f.tahun + f.periode] ? `${terbit[f.tahun + f.periode].jeda} hari setelah akhir periode` : ''">{{ terbit[f.tahun + f.periode]?.tgl || "–" }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <button v-if="p.fundamental.length > 8" class="mx-6 mt-2 mb-2 text-xs text-muted hover:text-ink" @click="semuaLapkeu = !semuaLapkeu">
          {{ semuaLapkeu ? "Tampilkan 8 terakhir" : `Tampilkan semua ${p.fundamental.length} laporan` }}
        </button>
      </Panel>

      <PanelKepemilikan :data="p.kepemilikan" />

      <PanelOrangDalam :kode="p.kode" />

      <PanelBerita :kode="p.kode" />

      <PanelPengumuman :kode="p.kode" />

      <Panel judul="Follow Tren" :ket="`Strategi utama · ${p.ringkasan_trade.jumlah} trade masuk portofolio · ${p.sinyal_tidak_dipilih} sinyal lain tidak terpilih karena slot penuh`" rapat>
        <template #aksi>
          <label class="flex cursor-pointer items-center gap-2 text-xs text-ink-2"><input v-model="semuaSinyal" type="checkbox" class="accent-[var(--aksen)]" />Tampilkan sinyal tidak terpilih</label>
        </template>
        <div class="px-6 pb-4"><Stats :items="stat" polos kolom="grid-cols-2 md:grid-cols-3 xl:grid-cols-5" /></div>
        <div class="flex flex-wrap items-center gap-2 px-6 pb-4 text-xs text-ink-2">
          <span class="text-muted">Status syariah (DES OJK, data sejak Des 2019):</span>
          <span v-if="!syariah.length" class="chip bg-turun-bg text-turun">tidak pernah masuk DES</span>
          <span v-for="x in syariah" :key="x.mulai" class="chip bg-naik-bg text-naik">{{ x.mulai }} – {{ x.akhir > "2090" ? "sekarang" : x.akhir }}</span>
          <span v-if="syariah.length > 1" class="text-muted">· ada jeda: selama keluar dari DES, Follow Tren tidak membeli saham ini</span>
        </div>
        <p v-if="!tradeTabel.length" class="m-0 px-6 pt-1 pb-4 text-muted">Belum pernah ada trade Follow Tren di saham ini.</p>
        <div v-else class="overflow-x-auto">
          <table class="tabel min-w-[760px]">
            <thead><tr><th>Sumber</th><th>Beli</th><th class="!text-right">Harga</th><th>Jual</th><th class="!text-right">Harga</th><th class="!text-right">Hari</th><th class="!text-right">Stop awal</th><th class="!text-right">Hasil net</th></tr></thead>
            <tbody>
              <tr v-for="t in tradeTabel" :key="t.sumber + t.tgl_beli" :class="t.dipilih ? '' : 'opacity-55'">
                <td class="!h-auto py-2.5 text-ink-2">{{ SUMBER[t.sumber] }}<span v-if="!t.dipilih" class="text-xs text-muted"> · tidak terpilih</span><div v-if="t.sumber !== 'paper' && t.status === 'terbuka'" class="text-[11px] text-muted">data s/d {{ t.tgl_akhir_data }}</div></td>
                <td class="tabular-nums">{{ t.tgl_beli }}</td>
                <td class="text-right">{{ rupiah(t.harga_beli) }}</td>
                <td class="tabular-nums">
                  <span v-if="t.status === 'terbuka'" class="chip" :class="t.sumber === 'paper' ? 'bg-aksen-lembut text-aksen' : 'bg-surface-2 text-ink-2'"
                    :title="t.sumber === 'paper' ? 'Posisi paper trade yang masih dipegang' : `Backtest berhenti karena data habis (${t.tgl_akhir_data}); belum ada sinyal jual, jadi bukan penjualan`">
                    {{ t.sumber === "paper" ? (t.status_paper === "jual_besok" ? "Antre jual besok" : "Masih dipegang") : "Dipegang di akhir data" }}
                  </span>
                  <template v-else>{{ t.tgl_jual }}</template>
                </td>
                <td class="text-right">
                  <template v-if="t.status === 'terbuka'"><span class="text-ink-2">{{ rupiah(t.harga_akhir) }}</span><div class="text-[11px] text-muted">close {{ t.tgl_akhir_data }}</div></template>
                  <template v-else>{{ rupiah(t.harga_jual) }}</template>
                </td>
                <td class="text-right text-ink-2">{{ t.hari ?? "–" }}</td>
                <td class="text-right text-turun/80">{{ t.stop_awal_pct == null ? "–" : persen(-t.stop_awal_pct) }}</td>
                <td class="text-right font-medium" :class="t.net >= 0 ? 'text-naik' : 'text-turun'">{{ persen(t.net) }}<div v-if="t.status === 'terbuka'" class="text-[11px] font-normal text-muted">{{ t.sumber === "paper" ? "berjalan · kotor" : "berjalan" }}</div></td>
              </tr>
            </tbody>
          </table>
        </div>
      </Panel>




      <p class="m-0 text-xs text-muted">Halaman ini untuk riset. Aturan Follow Tren tidak melihat fundamental atau grafik: memilih atau melewatkan sinyal berdasarkan halaman ini membuat hasil tidak lagi sebanding dengan backtest. Bukan nasihat keuangan.</p>
    </template>
  </div>
</template>

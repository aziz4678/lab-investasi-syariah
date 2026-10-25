<script setup>
import TeksWarna from "@/components/common/TeksWarna.vue";
import KodeSaham from "@/components/common/KodeSaham.vue";
import { ref, computed, inject, onMounted, onUnmounted } from "vue";
import { ArrowRight, DollarSign, Gem, Droplet, ChartLine, Globe, Activity } from "lucide-vue-next";
import Logo, { kunciMi } from "@/components/common/Logo.vue";
import { ambil } from "@/api/client";
import { persen, rupiah, tanggal, ringkas, kelasPersen } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import KurvaMini from "@/components/charts/KurvaMini.vue";
import GrafikRentang from "@/components/charts/GrafikRentang.vue";
import GrafikBatang from "@/components/charts/GrafikBatang.vue";
import Stats from "@/components/common/Stats.vue";
import Segmen from "@/components/common/Segmen.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import PanelPerawatan from "@/components/sistem/PanelPerawatan.vue";
import PengingatDividen from "@/components/dividen/PengingatDividen.vue";
import PanelSumberData from "@/components/sistem/PanelSumberData.vue";

const status = inject("status");
const muatStatus = inject("muatStatus");
const pindahTab = inject("pindahTab");
const paper = ref(null);
const bt = ref(null);
const btKons = ref(null);
const ekBt = ref([]);
const ekPaper = ref([]);
const transaksi = ref([]);
const div = ref(null);
const divSiap = ref(false);
const rd = ref(null);
const etf = ref(null);
const etfLuar = ref(null);
const pasar = ref(null);
const siap = ref(false);
const intra = ref(null);
let detak = null;
async function muatIntra() {
  intra.value = await ambil("pasar/intraday").catch(() => intra.value);
}
const periode = ref("1H");
const PERIODE = [["1H", "Hari ini"], ["1M", "1 minggu"], ["1B", "1 bulan"], ["3B", "3 bulan"]];

async function muat() {
  ambil("ringkasan/h11a_2020_konservatif").then((x) => (btKons.value = x)).catch(() => null);
  ambil("ekuitas/h11a_2020").then((x) => (ekBt.value = x)).catch(() => null);
  ambil("dividen/daftar").then((x) => (div.value = x)).catch(() => null).finally(() => (divSiap.value = true));
  [pasar.value, paper.value, bt.value, rd.value, etf.value, etfLuar.value] = await Promise.all([
    ambil("pasar").catch(() => ({})), ambil("paper/ringkasan").catch(() => null), ambil("ringkasan/h11a_2020").catch(() => null),
    ambil("rd/daftar").catch(() => null), ambil("etf/daftar").catch(() => null), ambil("etf/luar").catch(() => null),
  ]);
  if (paper.value?.mulai) {
    [ekPaper.value, transaksi.value] = await Promise.all([ambil("paper/ekuitas").catch(() => []), ambil("paper/transaksi?batas=8").catch(() => [])]);
  }
  siap.value = true;
  await muatStatus();
}

const IKON_GLOBAL = { usdidr: [DollarSign, "bg-naik-bg text-naik"], emas: [Gem, "bg-kuning-bg text-kuning"], minyak: [Droplet, "bg-surface-3 text-ink"],
  sp500: [ChartLine, "bg-aksen-lembut text-aksen"], em: [Globe, "bg-aksen-lembut text-aksen"], vix: [Activity, "bg-turun-bg text-turun"] };
const triliun = (v) => `Rp${(v / 1e12).toLocaleString("id-ID", { maximumFractionDigits: 2 })} T`;
const miliar = (v) => (!v ? "0" : v >= 1e12 ? triliun(v) : `Rp${(v / 1e9).toLocaleString("id-ID", { maximumFractionDigits: 0 })} M`);
const angka = (v, d = 2) => (v == null ? "–" : v.toLocaleString("id-ID", { maximumFractionDigits: d }));

const statIhsg = computed(() => {
  const i = pasar.value?.ihsg;
  if (!i) return [];
  return [
    intra.value && intra.value.sesi > i.tgl_terakhir
      ? { label: "Hari ini", nilai: persen(intra.value.ret, 2), ket: `berjalan ${angka(intra.value.terakhir)} · pukul ${intra.value.jam}` }
      : { label: "Hari ini", nilai: persen(i.ret_1h, 2), ket: `ditutup ${angka(i.terakhir)}` },
    { label: "Sejak awal tahun", nilai: persen(i.ytd) },
    { label: "Dari puncak 52 minggu", nilai: persen(i.dari_puncak_52), ket: `puncak ${angka(i.tinggi_52, 0)} · dasar ${angka(i.rendah_52, 0)}` },
    { label: "vs rata-rata 200 hari", nilai: persen(i.vs_ma200), ket: i.vs_ma200 >= 0 ? `di atas ${angka(i.ma200, 0)} · tren naik` : `di bawah ${angka(i.ma200, 0)} · tren turun` },
  ];
});
const luas = computed(() => {
  const l = pasar.value?.luas;
  if (!l) return null;
  const n = l.naik + l.turun + l.tetap || 1;
  return { ...l, n, pn: (l.naik / n) * 100, pt: (l.turun / n) * 100 };
});
const nilaiBanding = computed(() => (pasar.value ? (pasar.value.nilai.hari_ini / pasar.value.nilai.rata20 - 1) * 100 : null));
const top = computed(() => pasar.value?.top?.[periode.value]);
const daftarTop = computed(() => [["Paling naik", top.value?.naik || [], "ret"], ["Paling turun", top.value?.turun || [], "ret"], ["Paling ramai hari ini", pasar.value?.nilai?.teraktif || [], "nilai"]]);
const sektor = computed(() => pasar.value?.sektor?.[periode.value] || []);
const sektorMaks = computed(() => Math.max(1, ...sektor.value.map((x) => Math.abs(x.ret))));
const labelPeriode = computed(() => Object.fromEntries(PERIODE)[periode.value].toLowerCase());

onUnmounted(() => clearInterval(detak));
onMounted(async () => {
  muatIntra();
  detak = setInterval(() => status.value?.bursa_buka && muatIntra(), 60000);
  await muat();
});

const posisi = computed(() => paper.value?.posisi || []);
const aktif = computed(() => posisi.value.filter((p) => p.status !== "beli_besok"));
const aksiBeli = computed(() => posisi.value.filter((p) => p.status === "beli_besok").length);
const aksiJual = computed(() => posisi.value.filter((p) => p.status === "jual_besok").length);

const kurvaTren = computed(() => {
  const e = ekPaper.value;
  if (e.length < 2) return null;
  const m = paper.value.modal_awal;
  return { label: e.map((x) => x.tgl.slice(0, 10)), nilai: e.map((x) => x.ekuitas / m), pembanding: e.map((x) => (x.ihsg ?? m) / m) };
});

const btTotal = computed(() => (ekBt.value.length ? (ekBt.value[ekBt.value.length - 1].ekuitas - 1) * 100 : null));
const btIhsg = computed(() => (ekBt.value.length ? (ekBt.value[ekBt.value.length - 1].ihsg - 1) * 100 : null));
const divYield = computed(() => {
  const y = divPilihan.value.map((x) => x.yield).filter((v) => v != null);
  return y.length ? y.reduce((a, b) => a + b, 0) / y.length : null;
});
const divPilihan = computed(() => (div.value?.data || []).filter((x) => x.beruntun >= 3 && x.yield != null).sort((a, b) => b.yield - a.yield).slice(0, 10));

const rdTerbaik = computed(() => {
  const d = rd.value?.data || [];
  return ["pasar_uang", "pendapatan_tetap", "campuran", "saham"]
    .map((k) => d.filter((x) => x.kategori === k && x.ret_1th != null && !x.etf).sort((a, b) => (b.skor ?? -1e9) - (a.skor ?? -1e9))[0])
    .filter(Boolean);
});
const rdJumlah = computed(() => (rd.value?.data || []).filter((x) => !x.etf).length);

const etfSyariah = computed(() => {
  const idx = (etf.value?.data || []).filter((x) => x.cocok && x.kode).map((x) => ({ kode: x.kode, nama: x.nama, ret: x.ret_1th, asal: "IDX", logo: ["mi", kunciMi(x.mi), x.mi] }));
  const luar = (etfLuar.value?.data || []).filter((x) => x.syariah).map((x) => ({ kode: x.kode, nama: x.nama, ret: x.ret_1th_rp ?? x.ret_1th, asal: "Luar", logo: ["etf", x.kode, x.penerbit || x.kode] }));
  return { idx: idx.length, luar: luar.length, atas: [...idx, ...luar].filter((x) => x.ret != null).sort((a, b) => b.ret - a.ret).slice(0, 4) };
});

const aktivitas = computed(() => {
  const a = (status.value?.pekerjaan || []).map((p) => ({ waktu: p.mulai, teks: p.label, ket: p.status, warna: p.status === "selesai" ? "border-naik" : p.status === "gagal" ? "border-turun" : "border-muted" }));
  const t = transaksi.value.map((x) => ({
    waktu: x.tgl, teks: `${x.aksi === "jual" ? "Jual" : x.aksi === "dividen" ? "Dividen" : "Batal"} ${x.ticker}`,
    ket: x.aksi === "jual" ? persen(x.net_pct) : x.aksi === "dividen" ? `Rp${rupiah(x.untung_rp)}` : x.aksi, warna: "border-aksen",
  }));
  return [...a, ...t].sort((x, y) => (x.waktu < y.waktu ? 1 : -1)).slice(0, 7);
});

function waktu(s) {
  return new Date(s).toLocaleString("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}
</script>

<template>
  <div class="space-y-5">

    <template v-if="!pasar">
      <div class="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
        <Kerangka panel jenis="grafik" :tinggi="560" />
        <div class="flex min-w-0 flex-col gap-5">
          <Kerangka panel jenis="grafik" :tinggi="170" />
          <Kerangka panel :n="4" />
        </div>
      </div>
      <Kerangka panel jenis="tabel" :n="8" logo />
      <div class="grid gap-5 lg:grid-cols-2 xl:grid-cols-3">
        <Kerangka panel :n="7" />
        <Kerangka panel jenis="tabel" :n="5" />
        <Kerangka panel jenis="kartu" :n="3" kolom="grid-cols-1" />
      </div>
    </template>
    <template v-else-if="pasar.ihsg">
      <div class="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
        <Panel class="h-full" judul="IHSG" :ket="`Indeks Harga Saham Gabungan · harian s/d ${tanggal(pasar.ihsg.tgl_terakhir)}${intra ? ` · 1D per menit dari Yahoo (tertunda beberapa menit), terakhir ${intra.jam}` : ''}`">
          <GrafikRentang :tgl="pasar.ihsg.tgl" :harga="pasar.ihsg.nilai" :intraday="intra" awal="1D" nama="IHSG" :tinggi="330" :format="(v) => angka(v, 0)" />
          <Stats class="mt-5" polos :items="statIhsg" kolom="grid-cols-2 lg:grid-cols-4" />
        </Panel>
        <div class="flex min-w-0 flex-col gap-5">
          <Panel class="h-full" judul="Perputaran uang" :ket="`Nilai transaksi harian ${pasar.jumlah_saham} saham syariah · 6 bulan terakhir`">
            <div class="mb-3 flex flex-wrap items-end gap-x-3 gap-y-1">
              <span class="text-[26px] leading-none font-medium tracking-tight tabular-nums">{{ triliun(pasar.nilai.hari_ini) }}</span>
              <span class="pb-0.5 text-xs text-muted"><span :class="kelasPersen(nilaiBanding)">{{ persen(nilaiBanding, 0) }}</span> dibanding rata-rata 20 hari ({{ triliun(pasar.nilai.rata20) }})</span>
            </div>
            <div class="mb-2 flex flex-wrap gap-3 text-xs text-ink-2">
              <span class="inline-flex items-center gap-1.5"><span class="h-2.5 w-2.5 rounded-sm bg-naik"></span>IHSG naik</span>
              <span class="inline-flex items-center gap-1.5"><span class="h-2.5 w-2.5 rounded-sm bg-turun"></span>IHSG turun</span>
              <span class="inline-flex items-center gap-1.5"><span class="w-4 border-t-2 border-dashed border-muted"></span>rata-rata 20 hari</span>
            </div>
            <GrafikBatang :label="pasar.nilai.tgl" :nilai="pasar.nilai.nilai" :arah="pasar.nilai.arah" :rata="pasar.nilai.rata20" nama="Nilai transaksi" :format="miliar" :tinggi="150" />
          </Panel>
          <Panel class="h-full" judul="Naik vs turun" :ket="`${tanggal(pasar.tgl)} · ${luas.n} saham syariah yang diperdagangkan`">
            <div class="flex items-end justify-between">
              <div><div class="text-[28px] leading-none font-medium text-naik tabular-nums">{{ luas.naik }}</div><div class="mt-1 text-xs text-muted">naik</div></div>
              <div class="text-center"><div class="text-[20px] leading-none font-medium text-muted tabular-nums">{{ luas.tetap }}</div><div class="mt-1 text-xs text-muted">tetap</div></div>
              <div class="text-right"><div class="text-[28px] leading-none font-medium text-turun tabular-nums">{{ luas.turun }}</div><div class="mt-1 text-xs text-muted">turun</div></div>
            </div>
            <div class="mt-4 flex h-3 gap-0.5 overflow-hidden rounded-full bg-surface-2">
              <span class="bg-naik" :style="{ width: `${luas.pn}%` }"></span><span class="flex-1"></span><span class="bg-turun" :style="{ width: `${luas.pt}%` }"></span>
            </div>
            <p class="m-0 mt-4 text-[13px] leading-relaxed text-ink-2">
              {{ luas.naik > luas.turun * 1.5 ? "Mayoritas saham naik: pasar sedang semangat." : luas.turun > luas.naik * 1.5 ? "Mayoritas saham turun: pasar sedang tertekan." : "Saham naik dan turun berimbang." }}
              Sekitar {{ luas.ara_kira }} saham naik ≥ 20% dan {{ luas.arb_kira }} turun ≥ 15% (kira-kira ARA/ARB).
            </p>
          </Panel>
        </div>
      </div>

      <Panel judul="Saham paling naik & turun" :ket="`Saham syariah likuid (${pasar.jumlah_likuid} saham: transaksi rata-rata ≥ Rp1 M/hari, harga ≥ Rp50) · ${labelPeriode}`" rapat>
        <template #aksi><Segmen v-model="periode" :pilihan="PERIODE" kecil /></template>
        <div class="grid gap-x-2 md:grid-cols-3">
          <div v-for="d in daftarTop" :key="d[0]" class="min-w-0">
            <div class="px-6 pt-1 pb-1 text-xs font-medium text-muted">{{ d[0] }}</div>
            <table class="tabel">
              <tbody>
                <tr v-for="x in d[1]" :key="x.kode">
                  <td><KodeSaham :kode="x.kode" /></td>
                  <td class="text-right text-xs text-muted tabular-nums">{{ d[2] === "nilai" ? miliar(x.nilai) : angka(x.close, 0) }}</td>
                  <td class="text-right font-medium tabular-nums" :class="kelasPersen(x.ret)">{{ persen(x.ret) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <p class="m-0 px-6 pt-2 pb-3 text-xs text-muted">Persen sudah memperhitungkan dividen dan pemecahan saham. Daftar ini informasi, bukan sinyal beli.</p>
      </Panel>

      <div class="grid gap-5 lg:grid-cols-2 xl:grid-cols-3">
        <Panel class="h-full" judul="Sektor" :ket="`Perubahan median saham syariah likuid per sektor · ${labelPeriode} (ikut pilihan di atas)`">
          <div class="space-y-2.5">
            <div v-for="x in sektor" :key="x.sektor" class="grid grid-cols-[minmax(0,170px)_1fr_56px] items-center gap-3 text-[13px]">
              <span class="truncate text-ink-2" :title="`${x.sektor} · ${x.naik} dari ${x.n} saham naik`">{{ x.sektor }}</span>
              <div class="h-2.5 overflow-hidden rounded-full bg-surface-2">
                <span class="block h-full rounded-full" :class="x.ret >= 0 ? 'bg-naik' : 'bg-turun'" :style="{ width: `${Math.max(2, (Math.abs(x.ret) / sektorMaks) * 100)}%` }"></span>
              </div>
              <span class="text-right font-medium tabular-nums" :class="kelasPersen(x.ret)">{{ persen(x.ret) }}</span>
            </div>
          </div>
        </Panel>
        <Panel class="h-full" judul="Pasar dunia" ket="Ikut menggerakkan IHSG · perubahan 1 hari dan 1 bulan" rapat>
          <table class="tabel">
            <tbody>
              <tr v-for="g in pasar.global" :key="g.kode">
                <td class="w-full max-w-0"><div class="flex items-center gap-3"><span class="grid h-8 w-8 shrink-0 place-items-center rounded-[30%]" :class="IKON_GLOBAL[g.kode]?.[1] || 'bg-surface-2 text-muted'"><component :is="IKON_GLOBAL[g.kode]?.[0] || Globe" class="h-4 w-4" /></span><div class="min-w-0"><div class="truncate text-[13px]" :title="g.label">{{ g.label }}</div><div class="text-xs text-muted">{{ tanggal(g.tgl) }}</div></div></div></td>
                <td class="text-right tabular-nums whitespace-nowrap">
                  <div>{{ g.satuan }}{{ angka(g.nilai, g.nilai > 1000 ? 0 : 2) }} <span class="ml-1 font-medium" :class="kelasPersen(g.ret_1h)">{{ persen(g.ret_1h) }}</span></div>
                  <div class="text-xs"><span :class="kelasPersen(g.ret_1b)">{{ persen(g.ret_1b) }}</span> <span class="text-muted">1 bln</span></div>
                </td>
              </tr>
            </tbody>
          </table>
        </Panel>
        <PengingatDividen class="h-full lg:col-span-2 xl:col-span-1" @buka="pindahTab('dividen', 'daftar')" />
      </div>
    </template>

    <div class="flex items-baseline gap-3 px-1 pt-3"><h2 class="m-0 text-[17px] font-medium">Riset / Strategi</h2><span class="text-xs text-muted">aturan yang diuji dengan uang pura-pura</span></div>
    <div class="grid gap-5 lg:grid-cols-2">
      <Panel class="h-full" judul="Follow Tren" ket="Strategi saham syariah · paper trade (uang pura-pura)">
        <template #aksi><button class="tombol" @click="pindahTab('tren52', 'paper')">Buka <ArrowRight class="h-3.5 w-3.5" /></button></template>
        <Kerangka v-if="!siap" jenis="stat" :n="4" kolom="grid-cols-2" />
        <template v-else-if="paper?.mulai">
          <div class="grid grid-cols-2 gap-x-4 gap-y-3">
            <div><div class="text-xs text-muted">Nilai modal</div><div class="text-[17px] font-medium tabular-nums">Rp{{ ringkas(Math.round(paper.ekuitas)) }}</div></div>
            <div><div class="text-xs text-muted">Hasil sejak {{ tanggal(paper.tgl_mulai) }}</div><div class="text-[17px] font-medium tabular-nums" :class="kelasPersen(paper.return_pct)">{{ persen(paper.return_pct, 2) }}</div></div>
            <div><div class="text-xs text-muted">Saham dipegang</div><div class="text-[17px] font-medium tabular-nums">{{ aktif.length }} <span class="text-[13px] font-normal text-muted">/ 10</span></div></div>
            <div><div class="text-xs text-muted">Aksi besok pagi</div><div class="text-[17px] font-medium tabular-nums">
              <template v-if="aksiBeli || aksiJual"><span v-if="aksiBeli" class="text-naik">{{ aksiBeli }} beli</span><span v-if="aksiBeli && aksiJual" class="text-muted"> · </span><span v-if="aksiJual" class="text-turun">{{ aksiJual }} jual</span></template>
              <span v-else class="text-[13px] font-normal text-muted">tidak ada</span>
            </div></div>
          </div>
          <KurvaMini v-if="kurvaTren" class="mt-4" :label="kurvaTren.label" :nilai="kurvaTren.nilai" :pembanding="kurvaTren.pembanding" :format="(v) => `${v.toFixed(2)}x`" :tinggi="120" nama-nilai="Follow Tren" />
        </template>
        <p v-else class="m-0 text-[13px] text-muted">Paper trade belum dimulai.</p>
        <div v-if="bt" class="mt-4 rounded-2xl bg-surface-2 px-4 py-3">
          <div class="flex items-baseline justify-between gap-2">
            <span class="text-xs font-medium text-ink-2">Backtest {{ bt.mulai?.slice(0, 4) }}–{{ bt.akhir?.slice(0, 4) }}</span>
            <button class="text-[11px] text-muted hover:text-ink" @click="pindahTab('tren52', 'backtest')">detail & simulasi →</button>
          </div>
          <div class="mt-2 grid grid-cols-2 gap-x-4 gap-y-2.5 sm:grid-cols-4">
            <div><div class="text-[11px] text-muted">Total</div><div class="font-medium tabular-nums" :class="kelasPersen(btTotal)">{{ persen(btTotal, 0) }}</div><div class="text-[11px] text-muted">IHSG <span :class="kelasPersen(btIhsg)">{{ persen(btIhsg, 0) }}</span></div></div>
            <div><div class="text-[11px] text-muted">Per tahun</div><div class="font-medium tabular-nums" :class="kelasPersen(bt.cagr)">{{ persen(bt.cagr, 1) }}</div><div class="text-[11px] text-muted">konservatif <span :class="kelasPersen(btKons?.cagr)">{{ persen(btKons?.cagr, 1) }}</span></div></div>
            <div><div class="text-[11px] text-muted">Turun terdalam</div><div class="font-medium text-turun tabular-nums">{{ persen(bt.dd_maks, 0) }}</div><div class="text-[11px] text-muted">dari puncak</div></div>
            <div><div class="text-[11px] text-muted">Trade untung</div><div class="font-medium tabular-nums">{{ persen(bt.win_rate, 0, false) }}</div><div class="text-[11px] text-muted"><span class="text-naik">{{ persen(bt.rata_menang, 0) }}</span> / <span class="text-turun">{{ persen(bt.rata_kalah, 0) }}</span></div></div>
          </div>
        </div>
      </Panel>
      <Panel class="h-full" judul="Dividen" ket="Pemburu dividen saham syariah · gagal diuji, uji maju dihentikan">
        <template #aksi><button class="tombol" @click="pindahTab('dividen', 'daftar')">Buka <ArrowRight class="h-3.5 w-3.5" /></button></template>
        <div class="flex flex-wrap gap-2">
          <span class="chip bg-turun-bg text-turun">H17a/c/d gagal</span>
          <span class="chip bg-surface-2 text-muted">uji maju 2027 dihentikan</span>
        </div>
        <p class="m-0 mt-3 text-xs leading-relaxed text-ink-2">Aturan "10 yield tertinggi" gagal di saham syariah dan non-syariah 2014-2026: penghasilan tinggi hanya saat boom batu bara.</p>
        <div class="mt-4 text-xs text-muted">Yield tertinggi saat ini · rutin bayar ≥ 3 tahun · bukan rekomendasi</div>
        <Kerangka v-if="!divSiap" class="mt-2" :n="5" />
        <div class="mt-2 grid grid-cols-1 gap-x-6 sm:grid-flow-col sm:grid-cols-2" :style="{ gridTemplateRows: `repeat(${Math.ceil(divPilihan.length / 2)}, auto)` }">
          <div v-for="(x, i) in divPilihan" :key="x.kode" class="flex items-center gap-3 border-b border-garis py-2 text-[13px]">
            <span class="w-4 text-right text-xs text-muted tabular-nums">{{ i + 1 }}</span>
            <KodeSaham :kode="x.kode" />
            <span v-if="x.yield != null" class="ml-auto font-medium tabular-nums" :class="kelasPersen(x.yield)">{{ persen(x.yield, 1) }}</span>
          </div>
        </div>
        <p v-if="divYield != null" class="m-0 mt-3 text-xs leading-relaxed text-muted">
          Rata-rata yield <span class="font-medium" :class="kelasPersen(divYield)">{{ persen(divYield, 1) }}</span> per tahun (dividen setahun ÷ harga, sebelum pajak 10%).
          Harga sahamnya tetap bisa turun lebih dalam dari dividennya.
        </p>
      </Panel>
    </div>

    <div class="flex items-baseline gap-3 px-1 pt-3"><h2 class="m-0 text-[17px] font-medium">Produk</h2><span class="text-xs text-muted">tempat menaruh uang yang bisa dibeli langsung</span></div>
    <div class="grid gap-5 lg:grid-cols-2">
      <Panel class="h-full" judul="Reksa Dana" :ket="`${rdJumlah} produk syariah · terbaik per jenis menurut skor 1 tahun`" rapat>
        <template #aksi><button class="tombol" @click="pindahTab('reksadana', 'katalog')">Buka <ArrowRight class="h-3.5 w-3.5" /></button></template>
        <Kerangka v-if="!siap" jenis="tabel" :n="4" />
        <table v-else class="tabel">
          <tbody>
            <tr v-for="x in rdTerbaik" :key="x.id" class="cursor-pointer" @click="pindahTab('reksadana', 'katalog')">
              <td><div class="flex items-center gap-3"><Logo jenis="mi" :kunci="kunciMi(x.mi)" :teks="x.mi" :ukuran="32" /><div class="min-w-0"><div class="text-xs text-muted">{{ x.kategori_label }}</div><div class="max-w-[240px] truncate text-[13px]">{{ x.nama }}</div></div></div></td>
              <td class="text-right font-medium tabular-nums" :class="kelasPersen(x.ret_1th)">{{ persen(x.ret_1th) }}</td>
            </tr>
          </tbody>
        </table>
        <p class="m-0 px-6 pt-1 pb-3 text-xs text-muted">Hasil 1 tahun terakhir, bukan jaminan ke depan.</p>
      </Panel>
      <Panel class="h-full" judul="ETF" :ket="`${etfSyariah.idx} ETF syariah IDX · ${etfSyariah.luar} ETF syariah luar negeri`" rapat>
        <template #aksi><button class="tombol" @click="pindahTab('etf', 'daftar')">Buka <ArrowRight class="h-3.5 w-3.5" /></button></template>
        <Kerangka v-if="!siap" jenis="tabel" :n="4" />
        <table v-else class="tabel">
          <tbody>
            <tr v-for="x in etfSyariah.atas" :key="x.kode">
              <td><div class="flex items-center gap-3"><Logo :jenis="x.logo[0]" :kunci="x.logo[1]" :teks="x.logo[2]" :ukuran="32" /><div class="min-w-0"><div class="text-[13px] font-medium">{{ x.kode }} <span class="chip ml-1 !h-5 !px-2 !text-[10px] bg-surface-2 text-muted">{{ x.asal }}</span></div><div class="max-w-[240px] truncate text-xs text-muted">{{ x.nama }}</div></div></div></td>
              <td class="text-right font-medium tabular-nums" :class="kelasPersen(x.ret)">{{ persen(x.ret) }}</td>
            </tr>
          </tbody>
        </table>
        <p class="m-0 px-6 pt-1 pb-3 text-xs text-muted">ETF syariah dengan hasil 1 tahun tertinggi (ETF luar dalam rupiah).</p>
      </Panel>
    </div>

    <div class="flex items-baseline gap-3 px-1 pt-3"><h2 class="m-0 text-[17px] font-medium">Sistem</h2><span class="text-xs text-muted">data, jadwal otomatis, dan cadangan</span></div>
    <div class="grid gap-5 lg:grid-cols-2">
      <Panel class="h-full" judul="Aktivitas terakhir">
        <Kerangka v-if="!status" jenis="tabel" :n="5" />
        <p v-else-if="!aktivitas.length" class="m-0 text-[13px] text-muted">Belum ada aktivitas.</p>
        <ol v-else class="m-0 list-none space-y-4 p-0">
          <li v-for="(a, i) in aktivitas" :key="i" class="flex gap-3">
            <span class="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full border-2" :class="a.warna"></span>
            <div class="min-w-0">
              <div class="text-[13px]">{{ a.teks }} <span class="text-muted">· <TeksWarna :teks="a.ket" /></span></div>
              <div class="text-xs text-muted">{{ waktu(a.waktu) }}</div>
            </div>
          </li>
        </ol>
      </Panel>
      <PanelPerawatan class="h-full" />
    </div>

    <div id="sumber-data" class="scroll-mt-6">
      <PanelSumberData />
    </div>
  </div>
</template>

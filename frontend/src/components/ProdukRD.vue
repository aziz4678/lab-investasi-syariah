<script setup>
import { ref, computed, watch } from "vue";
import { ArrowLeft, FileText, ExternalLink } from "lucide-vue-next";
import { ambil, persen, rupiah, ringkas, kelasPersen } from "../util.js";
import Panel from "./Panel.vue";
import Kerangka from "./Kerangka.vue";
import Stats from "./Stats.vue";
import GrafikRentang from "./GrafikRentang.vue";
import Segmen from "./Segmen.vue";
import KesimpulanProduk from "./KesimpulanProduk.vue";
import Logo, { kunciMi } from "./Logo.vue";

const props = defineProps({ id: Number, tanpaKembali: Boolean });
const emit = defineEmits(["kembali"]);
const p = ref(null);
const galat = ref("");
const modeGrafik = ref("nav");
const rentangRD = ref("ALL");
const NAMA_RENTANG = { "1W": "1 Minggu", "1M": "1 Bulan", "3M": "3 Bulan", YTD: "YTD", "1Y": "1 Tahun", "3Y": "3 Tahun", "5Y": "5 Tahun", ALL: "Sejak Awal" };
function awalRentang(tgl, k) {
  const n = tgl.length;
  if (n < 2 || k === "ALL") return 0;
  const akhir = new Date(tgl[n - 1]);
  const d = new Date(akhir);
  if (k === "YTD") d.setFullYear(akhir.getFullYear() - 1, 11, 31);
  else if (k === "1W") d.setDate(d.getDate() - 7);
  else d.setMonth(d.getMonth() - { "1M": 1, "3M": 3, "1Y": 12, "3Y": 36, "5Y": 60 }[k]);
  const batas = d.toISOString().slice(0, 10);
  let i = n - 1;
  while (i > 0 && tgl[i] > batas) i -= 1;
  return i;
}
const kinerja = computed(() => {
  const g = p.value?.grafik;
  if (!g?.tgl?.length) return null;
  const i = awalRentang(g.tgl, rentangRD.value);
  const nav = g.nav.slice(i);
  if (nav.length < 2) return null;
  const tahun = (new Date(g.tgl.at(-1)) - new Date(g.tgl[i])) / 864e5 / 365.25;
  const ret = (nav.at(-1) / nav[0] - 1) * 100;
  let puncak = nav[0], dd = 0;
  for (const v of nav) {
    puncak = Math.max(puncak, v);
    dd = Math.min(dd, (v / puncak - 1) * 100);
  }
  return { tahun, ret, cagr: tahun >= 1 ? (Math.pow(nav.at(-1) / nav[0], 1 / tahun) - 1) * 100 : null, dd, mulai: g.tgl[i] };
});

watch(() => props.id, async (id) => {
  p.value = null;
  galat.value = "";
  if (!id) return;
  try {
    p.value = await ambil(`rd/produk/${id}`);
  } catch {
    galat.value = "Produk tidak ditemukan.";
  }
}, { immediate: true });

const uang = (v) => (v == null ? "–" : `${p.value?.mata_uang === "USD" ? "US$" : "Rp"}${ringkas(v)}`);

const tglId = (s) => (s ? new Date(s).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }) : "");
const stat = computed(() => {
  const x = p.value;
  if (!x) return [];
  const mk = x.median_kategori || {};
  return [
    { label: "NAV/Unit", nilai: x.nav == null ? "–" : x.nav.toLocaleString("id-ID", { maximumFractionDigits: 4 }), ket: tglId(x.nav_tgl), info: "Net Asset Value per unit penyertaan pada tanggal terakhir yang dipublikasikan." },
    { label: "AUM", nilai: uang(x.aum), ket: [x.aum_tgl ? `Per ${tglId(x.aum_tgl)}` : "", x.aum_ubah != null ? `${persen(x.aum_ubah, 1)} dari bulan sebelumnya` : ""].filter(Boolean).join(" · "), info: "Asset Under Management: total dana kelolaan produk ini." },
    { label: "Total AUM Manajer Investasi", nilai: x.aum_mi == null ? "–" : `Rp${ringkas(x.aum_mi)}`, ket: `${x.aum_mi_produk} reksa dana syariah`, info: `Jumlah AUM seluruh reksa dana syariah yang dikelola ${x.mi} dalam katalog.${x.aum_mi_kurs ? ` Produk berdenominasi USD dikonversi dengan kurs Rp${rupiah(Math.round(x.aum_mi_kurs))}.` : ""}` },
    { label: "Tingkat Risiko", nilai: x.risiko == null ? "–" : `${Math.round(x.risiko)}/9`, ket: x.risiko_label ? `Risiko ${x.risiko_label.toLowerCase()}` : "Tidak tersedia", info: "Klasifikasi risiko skala 1 (terendah) sampai 9 (tertinggi) dari Pasardana berdasarkan prospektus: 1–3 rendah, 4–6 sedang, 7–9 tinggi." },
    { label: "Imbal Hasil 1 Tahun", nilai: persen(x.ret_1th, 2), ket: mk.ret_1th != null ? `Median kategori ${persen(mk.ret_1th, 1)}` : "", info: "Perubahan NAV/Unit selama 12 bulan terakhir, setelah dikurangi biaya." },
    kinerja.value?.cagr != null
      ? { label: `CAGR ${NAMA_RENTANG[rentangRD.value]}`, nilai: persen(kinerja.value.cagr, 2), ket: `Sejak ${tglId(kinerja.value.mulai)} · ${kinerja.value.tahun.toLocaleString("id-ID", { maximumFractionDigits: 1 })} tahun`, info: "Compound Annual Growth Rate: pertumbuhan rata-rata NAV/Unit per tahun pada rentang yang dipilih di grafik." }
      : { label: `Imbal Hasil ${NAMA_RENTANG[rentangRD.value]}`, nilai: persen(kinerja.value?.ret, 2), ket: kinerja.value ? `Sejak ${tglId(kinerja.value.mulai)} · tidak disetahunkan` : "", info: "Perubahan NAV/Unit pada rentang yang dipilih. Rentang di bawah 1 tahun tidak disetahunkan (CAGR hanya untuk rentang minimal 1 tahun)." },
    { label: `Max Drawdown ${NAMA_RENTANG[rentangRD.value]}`, nilai: persen(kinerja.value?.dd, 2), ket: rentangRD.value === "1Y" && mk.dd != null ? `Median kategori ${persen(mk.dd, 1)}` : kinerja.value && new Date(kinerja.value.mulai) < new Date(Date.now() - 400 * 864e5) ? "Sebelum 12 bulan terakhir memakai NAV akhir bulan" : "Berdasarkan NAV harian", info: "Penurunan terbesar NAV/Unit dari titik tertinggi ke titik terendah pada rentang yang dipilih di grafik." },
    { label: "Expense Ratio", nilai: x.biaya == null ? "–" : persen(x.biaya, 2, false), ket: mk.biaya != null ? `Median kategori ${persen(mk.biaya, 2, false)}` : "", info: "Total biaya operasional tahunan yang dibebankan pada dana, dalam persen dari AUM." },
  ];
});

const RET = [["ret_1bln", "1 bulan"], ["ret_3bln", "3 bulan"], ["ret_6bln", "6 bulan"], ["ret_ytd", "Year to date"], ["ret_1th", "1 tahun"], ["vol", "Volatilitas (tahunan)"], ["dd", "Max drawdown"]];
const infoProduk = computed(() => {
  const x = p.value;
  if (!x) return [];
  const r = [["Minimum pembelian awal", x.min_beli], ["Minimum pembelian selanjutnya", x.min_beli_lagi], ["Imbalan jasa manajer investasi", x.biaya_mi],
    ["Tingkat risiko", x.risiko == null ? null : `${Math.round(x.risiko)} dari 9 (${x.risiko_label})`], ["Tanggal peluncuran", x.terbit ? tglId(x.terbit) : null], ["Tolok ukur (benchmark)", x.pembanding], ["Kode ISIN", x.isin]];
  if (x.dividen?.length) r.push(["Pembagian hasil investasi", `${x.dividen.length} kali`]);
  return r.map(([l, v]) => [l, v == null || v === "" ? "–" : v]);
});
const kurva = computed(() => p.value?.grafik || { tgl: [], nav: [] });
const maksAset = computed(() => Math.max(1, ...(p.value?.aset || []).map((a) => a.bobot || 0)));
</script>

<template>
  <div class="space-y-5">
    <button v-if="!tanpaKembali" class="tombol" @click="emit('kembali')"><ArrowLeft class="h-3.5 w-3.5" />Kembali ke katalog</button>
    <div v-if="galat" class="panel px-6 py-4 text-turun">{{ galat }}</div>
    <template v-else-if="!p">
      <Kerangka panel :n="3" />
      <Kerangka panel jenis="grafik" :tinggi="300" />
      <Kerangka panel jenis="stat" :n="8" :judul="false" kolom="grid-cols-2 md:grid-cols-4" />
    </template>
    <template v-else>
      <div class="panel px-6 py-5">
        <div class="flex flex-wrap items-center gap-3">
          <Logo jenis="mi" :kunci="kunciMi(p.mi)" :teks="p.mi" :ukuran="48" />
          <span class="mr-1 text-[19px] font-medium">{{ p.nama }}</span>
          <span class="chip bg-aksen-lembut text-aksen">{{ p.kategori_label }}</span>
          <span class="chip bg-naik-bg text-naik">Syariah</span>
          <span v-if="p.mata_uang === 'USD'" class="chip bg-kuning-bg text-kuning">Dolar AS</span>
          <span v-if="p.etf" class="chip bg-surface-2 text-ink-2">ETF (diperdagangkan di bursa)</span>
          <span v-if="p.skor != null" class="chip bg-surface-2 text-ink-2" title="Skor 0–100 dibandingkan produk sekategori">Skor {{ Math.round(p.skor) }} · peringkat {{ p.peringkat }}/{{ p.jumlah_kategori }}</span>
        </div>
        <p class="m-0 mt-1.5 text-[13px] text-ink-2">Manajer investasi: {{ p.mi }}<template v-if="p.kustodian"> · Bank kustodian: {{ p.kustodian }}</template></p>
        <p v-if="p.deskripsi" class="m-0 mt-3 max-w-[900px] text-[13px] leading-relaxed text-muted">{{ p.deskripsi }}</p>
      </div>

      <div class="grid gap-5 xl:grid-cols-[1.5fr_1fr]">
        <Panel :judul="modeGrafik === 'nav' ? 'Riwayat NAV/Unit' : 'Riwayat AUM'" :ket="modeGrafik === 'aum' ? (kurva.aum?.tgl.length ? `Sejak ${tglId(kurva.aum.tgl[0])} · data akhir bulan dari laporan NAB OJK dan Pasardana` : 'Data AUM belum tersedia') : p.panjang ? `Sejak ${tglId(p.panjang.mulai)} · data akhir bulan dari laporan OJK dan data harian 12 bulan terakhir dari Pasardana` : `${kurva.tgl.length} hari bursa · data harian Pasardana`">
          <GrafikRentang v-if="modeGrafik === 'aum'" key="aum" :tgl="kurva.aum?.tgl || []" :harga="kurva.aum?.nilai || []" nama="AUM" :awal="rentangRD" bulanan @rentang="(k) => (rentangRD = k)"
            :tinggi="260" :format="uang" />
          <GrafikRentang v-else key="nav" :tgl="kurva.tgl" :harga="kurva.nav" :pembanding="kurva.pembanding" :nama="'NAV'" :nama-pembanding="p.pembanding || 'Tolok ukur'" :awal="rentangRD" @rentang="(k) => (rentangRD = k)"
            :tinggi="260" :format="(v) => v.toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 })" />
          <div class="mt-4 flex justify-center"><Segmen v-model="modeGrafik" :pilihan="[['nav', 'NAV/Unit'], ['aum', 'AUM']]" /></div>
        </Panel>
        <Panel judul="Perbandingan dengan Kategori" :ket="`Median ${p.jumlah_kategori_semua} reksa dana ${p.kategori_label.toLowerCase()} syariah berdenominasi ${p.mata_uang === 'USD' ? 'USD' : 'rupiah'}`" rapat>
          <table class="tabel">
            <thead><tr><th>Periode</th><th class="!text-right">Produk</th><th class="!text-right">Median kategori</th></tr></thead>
            <tbody>
              <tr v-for="[k, l] in RET" :key="k">
                <td class="text-ink-2">{{ l }}</td>
                <td class="text-right font-medium" :class="k === 'vol' ? '' : kelasPersen(p[k])">{{ p[k] == null ? "–" : persen(p[k], 2, k !== "vol") }}</td>
                <td class="text-right" :class="k === 'vol' ? 'text-muted' : kelasPersen(p.median_kategori?.[k])">{{ p.median_kategori?.[k] == null ? "–" : persen(p.median_kategori[k], 2, k !== "vol") }}</td>
              </tr>
            </tbody>
          </table>
        </Panel>
      </div>

      <Stats :items="stat" kolom="grid-cols-2 md:grid-cols-4" />

      <Panel v-if="p.panjang && p.panjang.tahun >= 2" judul="Kinerja Jangka Panjang" :ket="`Riwayat ${p.panjang.tahun.toLocaleString('id-ID')} tahun (${tglId(p.panjang.mulai)} s.d. sekarang) · setelah dikurangi biaya`">
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-xs text-muted">CAGR 3 tahun terakhir</div><div class="mt-0.5 text-[17px] font-medium" :class="kelasPersen(p.panjang.cagr_3)">{{ persen(p.panjang.cagr_3, 1) }}</div></div>
          <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-xs text-muted">CAGR 5 tahun terakhir</div><div class="mt-0.5 text-[17px] font-medium" :class="kelasPersen(p.panjang.cagr_5)">{{ persen(p.panjang.cagr_5, 1) }}</div><div v-if="p.panjang.cagr_5 == null" class="text-[11px] text-muted">Riwayat belum mencapai 5 tahun</div></div>
          <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-xs text-muted">CAGR sejak awal data</div><div class="mt-0.5 text-[17px] font-medium" :class="kelasPersen(p.panjang.cagr_semua)">{{ persen(p.panjang.cagr_semua, 1) }}</div></div>
          <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-xs text-muted">Max drawdown (seluruh periode)</div><div class="mt-0.5 text-[17px] font-medium" :class="kelasPersen(p.panjang.dd)">{{ persen(p.panjang.dd, 1) }}</div><div class="text-[11px] text-muted">Berdasarkan NAV akhir bulan</div></div>
        </div>
        <div v-if="p.panjang.per_tahun.length" class="mt-5">
          <div class="mb-2 text-xs text-muted">Imbal hasil per tahun kalender · positif {{ p.panjang.tahun_naik }} dari {{ p.panjang.tahun_dihitung }} tahun<template v-if="p.panjang.per_tahun.at(-1).tahun === new Date().getFullYear()"> ({{ p.panjang.per_tahun.at(-1).tahun }} = year to date)</template></div>
          <div class="flex flex-wrap gap-2">
            <div v-for="t in p.panjang.per_tahun" :key="t.tahun" class="min-w-[76px] rounded-xl px-3 py-2 text-center" :class="t.ret >= 0 ? 'bg-naik-bg' : 'bg-turun-bg'">
              <div class="text-[11px] text-muted">{{ t.tahun }}</div>
              <div class="text-[13px] font-medium tabular-nums" :class="t.ret >= 0 ? 'text-naik' : 'text-turun'">{{ persen(t.ret, 1) }}</div>
            </div>
          </div>
        </div>
      </Panel>

      <div class="grid gap-5 lg:grid-cols-2">
        <Panel judul="Komposisi Portofolio" :ket="p.aset.length || p.alokasi_aset.length ? 'Berdasarkan fund fact sheet terakhir · persentase terhadap AUM' : 'Data portofolio belum tersedia'">
          <div v-if="p.alokasi_aset.length" class="mb-5">
            <div class="mb-2 text-xs text-muted">Alokasi aset</div>
            <div class="flex h-3 overflow-hidden rounded-full bg-surface-2">
              <div v-for="(a, i) in p.alokasi_aset" :key="a.nama" :style="{ width: `${a.bobot || 0}%` }" :class="['bg-s1', 'bg-s2', 'bg-s4', 'bg-s3'][i % 4]" class="border-r-2 border-surface last:border-r-0"></div>
            </div>
            <div class="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-ink-2">
              <span v-for="(a, i) in p.alokasi_aset" :key="a.nama" class="inline-flex items-center gap-1.5"><span class="h-2 w-2 rounded-full" :class="['bg-s1', 'bg-s2', 'bg-s4', 'bg-s3'][i % 4]"></span>{{ a.nama }} {{ persen(a.bobot, 1, false) }}</span>
            </div>
          </div>
          <div v-if="p.aset.length" class="mb-2 text-xs text-muted">Kepemilikan efek terbesar</div>
          <div v-if="p.aset.length" class="space-y-2.5">
            <div v-for="a in p.aset.slice(0, 10)" :key="a.nama">
              <div class="flex justify-between gap-3 text-[13px]"><span class="truncate">{{ a.nama }}</span><span class="shrink-0 tabular-nums">{{ a.bobot != null ? persen(a.bobot, 1, false) : "–" }}</span></div>
              <div class="mt-1 h-1.5 rounded-full bg-surface-2"><div class="h-full rounded-full bg-s1" :style="{ width: `${((a.bobot || 0) / maksAset) * 100}%` }"></div></div>
            </div>
          </div>
        </Panel>
        <Panel judul="Informasi Produk" rapat>
          <dl class="m-0">
            <div v-for="[l, v] in infoProduk" :key="l" class="flex items-start justify-between gap-6 border-t border-garis px-6 py-3 text-[13px]">
              <dt class="shrink-0 text-ink-2">{{ l }}</dt>
              <dd class="m-0 min-w-0 text-right break-words tabular-nums">{{ v }}</dd>
            </div>
          </dl>
          <div class="px-6 pt-2 pb-4">
            <div class="mb-1.5 flex items-center justify-between gap-3 text-xs text-muted">
              <span>Dokumen produk</span>
              <a :href="p.url_sumber" target="_blank" rel="noopener" class="inline-flex items-center gap-1 text-aksen hover:underline">Buka di Pasardana<ExternalLink class="h-3 w-3" /></a>
            </div>
            <a v-for="dk in p.dokumen" :key="dk.id" :href="dk.url" target="_blank" rel="noopener" class="flex items-center gap-2 py-1 text-xs text-ink-2 hover:text-aksen">
              <FileText class="h-3.5 w-3.5 shrink-0 text-muted" />
              <span class="min-w-0 flex-1 truncate" :title="dk.nama">{{ dk.jenis_label }} · {{ tglId(dk.tgl) }}</span>
              <ExternalLink class="h-3 w-3 shrink-0 text-muted" />
            </a>
            <p v-if="!p.dokumen.length" class="m-0 text-xs text-muted">Dokumen belum tersedia.</p>
            <p class="m-0 mt-1.5 text-[11px] text-muted">Unduhan PDF di Pasardana memerlukan verifikasi captcha.</p>
          </div>
        </Panel>
      </div>
      <KesimpulanProduk :k="p.kesimpulan" />
      <p class="m-0 text-xs text-muted">Sumber: Pasardana dan laporan NAB OJK. Skor membandingkan produk dengan kategori yang sama berdasarkan kinerja 12 bulan terakhir dan bukan merupakan proyeksi. Informasi ini bukan nasihat keuangan.</p>
    </template>
  </div>
</template>

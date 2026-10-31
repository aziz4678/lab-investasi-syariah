<script setup>
import { ref, computed, watch, onMounted, onUnmounted, inject } from "vue";
import { ArrowLeft, TriangleAlert, Info as IkonInfo } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { persen, rupiah, ringkas, kelasPersen } from "@/utils/format";
import { pakaiPekerjaan } from "@/composables/pekerjaan";
import Panel from "@/components/common/Panel.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import Segmen from "@/components/common/Segmen.vue";
import HeaderStrategi from "@/components/common/HeaderStrategi.vue";
import PanelPekerjaan from "@/components/sistem/PanelPekerjaan.vue";
import GrafikRentang from "@/components/charts/GrafikRentang.vue";
import ProdukRD from "@/components/produk/ProdukRD.vue";
import Logo, { kunciMi } from "@/components/common/Logo.vue";
import EtfLuarDetail from "@/components/produk/EtfLuarDetail.vue";
import BandingEtf from "@/components/produk/BandingEtf.vue";
import RingkasHariIni from "@/components/produk/RingkasHariIni.vue";

const props = defineProps({ sub: String });
const emit = defineEmits(["sub"]);
const SUB = [["data", "Cara membaca"], ["luar", "ETF luar negeri"], ["daftar", "ETF Indonesia"], ["banding", "Bandingkan"]];
const SEPI = 50_000_000;

const data = ref(null);
const jenis = ref("semua");
const pilih = ref(Number(location.hash.split("/")[2]) || null);
const grafik = ref(null);
const { kerja, galat, sibuk, mulai, lanjutkan } = pakaiPekerjaan();

async function muat() {
  data.value = await ambil("etf/daftar").catch(() => ({ data: [], jenis: {} }));
}
onMounted(async () => {
  await muat();
  await lanjutkan("etf_perbarui", muat);
});

const semua = computed(() => data.value?.data || []);
const pilihanJenis = computed(() => [["semua", `Semua (${semua.value.length})`], ...Object.entries(data.value?.jenis || {}).map(([k, l]) => [k, `${l} (${semua.value.filter((x) => x.jenis === k).length})`])]);
const tampil = computed(() => semua.value.filter((x) => jenis.value === "semua" || x.jenis === jenis.value));
const aktif = computed(() => semua.value.find((x) => x.id === pilih.value));

watch(pilih, async (id) => {
  history.replaceState(null, "", id ? `#etf/daftar/${id}` : `#etf/${props.sub}`);
  grafik.value = null;
  const x = semua.value.find((r) => r.id === id);
  if (x?.kode) grafik.value = await ambil(`etf/grafik/${x.kode}`).catch(() => null);
  window.scrollTo({ top: 0 });
});
const statusApp = inject("status", null);
const intra = ref(null);
const intraSiap = ref(false);
async function muatIntra() {
  const k = aktif.value?.kode;
  if (!k) return;
  const v = await ambil(`pasar/intraday?kode=${k}`).catch(() => null);
  if (aktif.value?.kode !== k) return;
  if (v?.tgl?.length) intra.value = v;
  intraSiap.value = true;
}
watch(() => aktif.value?.kode, (k) => {
  intra.value = null;
  intraSiap.value = false;
  if (k) muatIntra();
}, { immediate: true });
let detak = setInterval(() => statusApp?.value?.bursa_buka && aktif.value?.kode && muatIntra(), 60000);
onUnmounted(() => clearInterval(detak));
watch(semua, () => {
  if (pilih.value && !grafik.value && aktif.value?.kode) ambil(`etf/grafik/${aktif.value.kode}`).then((g) => (grafik.value = g)).catch(() => null);
});

const luar = ref(null);
const saringLuar = ref("syariah");
const pilihLuar = ref(location.hash.startsWith("#etf/luar/") ? decodeURIComponent(location.hash.split("/")[2]) : null);
async function muatLuar() {
  luar.value = await ambil("etf/luar").catch(() => ({ data: [] }));
}
watch(() => props.sub, async (x) => {
  if (x === "luar" && !luar.value) await muatLuar();
  if (x !== "luar") pilihLuar.value = null;
}, { immediate: true });
watch(pilihLuar, (k) => {
  if (props.sub === "luar") history.replaceState(null, "", k ? `#etf/luar/${encodeURIComponent(k)}` : "#etf/luar");
  window.scrollTo({ top: 0 });
});
const wilayah = ref("semua");
const kelasPilih = ref("semua");
const cariLuar = ref("");
const urutLuar = ref({ kolom: "aum", turun: true });
const URUT_WILAYAH = ["AS", "AS dividen", "Dunia", "Negara maju", "Eropa", "Asia", "Asia Tenggara", "Negara berkembang", "Amerika Latin", "Timur Tengah", "Sektor teknologi", "Sektor lain"];
const daftarWilayah = computed(() => [...new Set((luar.value?.data || []).map((x) => x.wilayah))].sort((a, b) => URUT_WILAYAH.indexOf(a) - URUT_WILAYAH.indexOf(b)));
const daftarKelas = computed(() => [...new Set((luar.value?.data || []).map((x) => x.kelas))]);
const tampilLuar = computed(() => {
  const q = cariLuar.value.trim().toLowerCase();
  const x = (luar.value?.data || []).filter((r) => (saringLuar.value === "semua" || (saringLuar.value === "syariah") === r.syariah)
    && (wilayah.value === "semua" || r.wilayah === wilayah.value) && (kelasPilih.value === "semua" || r.kelas === kelasPilih.value)
    && (!q || `${r.kode} ${r.nama} ${r.isi || ""}`.toLowerCase().includes(q)));
  const { kolom, turun } = urutLuar.value;
  return [...x].sort((a, b) => {
    const va = a[kolom], vb = b[kolom];
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;
    const c = typeof va === "string" ? va.localeCompare(vb) : va - vb;
    return turun ? -c : c;
  });
});
function urutkan(k) {
  urutLuar.value = urutLuar.value.kolom === k ? { kolom: k, turun: !urutLuar.value.turun } : { kolom: k, turun: !["biaya", "kode"].includes(k) };
}
const KOLOM_LUAR = [
  ["kode", "ETF", 0, ""],
  ["ret_1th", "Hasil 1 tahun", 1, "Total hasil 12 bulan terakhir (harga + dividen), dalam mata uang ETF"],
  ["cagr_2020", "Per tahun sejak 2020", 1, "Rata-rata hasil per tahun sejak awal 2020, supaya semua ETF dibandingkan di periode yang sama"],
  ["cagr_2020_rp", "Dalam rupiah", 1, "Sama, tapi kalau dihitung dalam rupiah (ikut naik-turun kurs)"],
  ["dd_2020", "Turun terdalam", 1, "Penurunan terbesar dari titik tertinggi sejak 2020"],
  ["dividen_yield12", "Dividen", 1, "Yield 12 bulan terakhir (sebelum pajak) dan seberapa sering dibayar"],
  ["biaya", "Biaya/th", 1, "Biaya pengelolaan per tahun (expense ratio), sudah dipotong dari harga"],
  ["aum", "Dana kelolaan", 1, "Total uang investor di ETF ini. Makin besar biasanya makin ramai dan aman dari penutupan"],
];
const KELAS = { saham: "Saham", sukuk: "Sukuk", properti: "Properti (REIT)", obligasi: "Obligasi", emas: "Emas", komoditas: "Komoditas" };
const SIMBOL = { USD: "US$", GBP: "£", GBp: "£", EUR: "€" };
const usd = (v, mu = "USD") => (v == null ? "–" : `${SIMBOL[mu] || mu + " "}${ringkas(v)}`);
const uang = (v, usd) => (v == null ? "–" : `${usd ? "US$" : "Rp"}${ringkas(v)}`);
const FREK_PENDEK = { Mingguan: "mingguan", Bulanan: "bulanan", "Kuartalan (3 bulanan)": "3 bulanan", "Dua kali setahun": "2× setahun", Tahunan: "tahunan" };
</script>

<template>
  <div class="space-y-5">
    <HeaderStrategi judul="ETF" :sub="sub" :pilihan="SUB" @sub="(s) => { pilih = null; pilihLuar = null; emit('sub', s); }"
      ringkas="ETF adalah reksa dana yang dibeli dan dijual di bursa seperti saham. Satu ETF berisi puluhan sampai ribuan saham/obligasi sekaligus, jadi risiko satu perusahaan jadi kecil. Biayanya umumnya lebih murah dari reksa dana biasa."
      :chip="[{ teks: `${semua.length} ETF syariah Indonesia`, kelas: 'bg-aksen-lembut text-aksen' }, { teks: `${luar?.data?.length || 71} ETF luar negeri`, kelas: 'bg-surface-2 text-ink-2' }, { teks: 'Data: Yahoo, Pasardana', kelas: 'bg-surface-2 text-ink-2' }]" />

    <template v-if="sub === 'daftar' && pilih && aktif">
      <button class="tombol" @click="pilih = null"><ArrowLeft class="h-3.5 w-3.5" />Kembali ke daftar ETF</button>
      <ProdukRD :id="pilih" :kode-bursa="aktif.kode" :isi="aktif.isi" :tanpa-harga-bursa="!aktif.kode" tanpa-kembali>
        <Panel v-if="aktif.kode" :judul="`Harga ${aktif.kode} di bursa`" :ket="`1D: harga per menit hari ini (tertunda ±10 menit) · rentang lain: harga penutupan harian sejak ${aktif.bursa_mulai} · lonjakan sesaat > 20% dari median 5 hari tidak ditampilkan`">
          <GrafikRentang v-if="grafik && intraSiap" :key="aktif.kode" :tgl="grafik.tgl" :harga="grafik.close" :pembanding="grafik.ihsg" :nama="aktif.kode" nama-pembanding="IHSG"
            :intraday="intra" :awal="intra ? '1D' : '1Y'" :format="(v) => v.toLocaleString('id-ID', { maximumFractionDigits: 0 })" />
          <Kerangka v-else jenis="grafik" :tinggi="300" />
          <RingkasHariIni :intra="intra" :format="(v) => v.toLocaleString('id-ID', { maximumFractionDigits: 0 })" :uang="(v) => uang(v)"
            :catatan="intra && intra.nilai_transaksi < SEPI ? 'transaksi sepi, grafik per menit bisa putus-putus' : ''" />
          <div class="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-xs text-muted">Modal minimal (1 lot)</div><div class="mt-0.5 text-[17px] font-medium">Rp{{ rupiah(Math.round(aktif.harga * 100)) }}</div><div class="text-[11px] text-muted">100 unit × harga terakhir</div></div>
            <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-xs text-muted">Pertumbuhan per tahun</div><div class="mt-0.5 text-[17px] font-medium" :class="kelasPersen(aktif.cagr_semua)">{{ aktif.cagr_semua == null ? "–" : persen(aktif.cagr_semua, 1) }}</div><div class="text-[11px] text-muted">sejak terdaftar ({{ aktif.tahun_data }} th)</div></div>
            <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-xs text-muted">Turun terdalam</div><div class="mt-0.5 text-[17px] font-medium" :class="kelasPersen(aktif.dd_semua)">{{ persen(aktif.dd_semua, 1) }}</div><div class="text-[11px] text-muted">harga bursa, sejak terdaftar</div></div>
            <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-xs text-muted">Transaksi per hari</div><div class="mt-0.5 text-[17px] font-medium" :class="aktif.nilai_transaksi < SEPI ? 'text-kuning' : ''">{{ uang(aktif.nilai_transaksi) }}</div><div class="text-[11px] text-muted">rata-rata 20 hari{{ aktif.nilai_transaksi < SEPI ? " · sepi" : "" }}</div></div>
          </div>
          <p v-if="aktif.lonjakan_dibuang" class="m-0 mt-3 flex items-start gap-2 rounded-2xl bg-kuning-bg px-4 py-3 text-xs text-kuning">
            <TriangleAlert class="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>Pernah ada {{ aktif.lonjakan_dibuang }} transaksi di harga yang jauh dari biasanya. ETF yang sepi bisa diperdagangkan jauh di atas/bawah nilai aslinya (NAV): selalu bandingkan harga beli dengan NAV terakhir di bawah.</span>
          </p>
        </Panel>
      </ProdukRD>
    </template>

    <template v-else-if="sub === 'daftar' && !data">
      <Kerangka panel :n="2" :judul="false" />
      <Kerangka panel jenis="tabel" :n="8" logo />
    </template>
    <template v-else-if="sub === 'daftar'">
      <div class="panel flex flex-wrap items-center justify-between gap-3 px-6 py-4">
        <div class="min-w-0">
          <div class="text-[13px] font-medium">ETF syariah yang tercatat di Bursa Efek Indonesia</div>
          <div class="text-xs text-muted">Dibeli lewat aplikasi sekuritas (rekening saham) dalam rupiah, minimal 1 lot = 100 unit.</div>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <Segmen v-model="jenis" kecil :pilihan="pilihanJenis" />
          <button class="tombol" :disabled="sibuk" @click="mulai('aksi/etf_perbarui', {}, muat)">Perbarui</button>
        </div>
      </div>
      <PanelPekerjaan :kerja="kerja" :galat="galat" />
      <Panel judul="Daftar ETF syariah Indonesia" :ket="`${tampil.length} ETF · klik untuk detail · transaksi < Rp${ringkas(SEPI)}/hari ditandai sepi`" rapat>
        <div class="overflow-x-auto">
          <table class="tabel min-w-[820px]">
            <thead>
              <tr>
                <th>ETF</th><th class="!text-right" title="Perubahan NAV 12 bulan terakhir">Hasil 1 tahun</th>
                <th class="!text-right" title="Pertumbuhan harga bursa per tahun sejak terdaftar">Per tahun</th>
                <th class="!text-right" title="Penurunan harga bursa terbesar dari puncak">Turun terdalam</th>
                <th class="!text-right" title="Rata-rata nilai transaksi 20 hari bursa terakhir. Makin kecil, makin susah menjual di harga wajar">Transaksi/hari</th>
                <th class="!text-right" title="Biaya pengelolaan per tahun">Biaya/th</th><th class="!text-right">Dana kelolaan</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="x in tampil" :key="x.id" class="cursor-pointer hover:bg-surface-2/50" @click="pilih = x.id">
                <td class="!h-auto max-w-[340px] !whitespace-normal py-3">
                  <div class="flex items-start gap-3"><Logo jenis="mi" :kunci="kunciMi(x.mi)" :teks="x.mi" :ukuran="32" /><div class="min-w-0">
                    <div class="flex items-center gap-2"><span v-if="x.kode" class="chip !h-5 !px-2 bg-aksen-lembut text-aksen">{{ x.kode }}</span><span class="truncate font-medium">{{ x.nama }}</span></div>
                    <div class="truncate text-[11px] text-muted" :title="x.mi">{{ x.jenis_label }} · {{ x.mi }}</div>
                  </div></div>
                </td>
                <td class="text-right font-medium" :class="kelasPersen(x.ret_1th)">{{ x.ret_1th == null ? "–" : persen(x.ret_1th, 1) }}</td>
                <td class="text-right" :class="kelasPersen(x.cagr_semua)">{{ x.cagr_semua == null ? "–" : persen(x.cagr_semua, 1) }}<span v-if="x.tahun_data >= 1" class="text-[11px] text-muted"> ({{ Math.round(x.tahun_data) }} th)</span></td>
                <td class="text-right" :class="kelasPersen(x.dd_semua)">{{ x.dd_semua == null ? "–" : persen(x.dd_semua, 1) }}</td>
                <td class="text-right tabular-nums"><span :class="x.nilai_transaksi != null && x.nilai_transaksi < SEPI ? 'text-kuning' : ''">{{ uang(x.nilai_transaksi) }}</span><span v-if="x.nilai_transaksi != null && x.nilai_transaksi < SEPI" class="chip ml-1 !h-5 !px-2 bg-kuning-bg text-kuning">sepi</span></td>
                <td class="text-right text-ink-2">{{ x.biaya == null ? "–" : persen(x.biaya, 2, false) }}</td>
                <td class="text-right tabular-nums">{{ uang(x.aum, x.mata_uang === "USD") }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="m-0 px-6 py-3 text-xs text-muted">"–" di kolom bursa = kode bursa belum ditemukan di Yahoo, atau ETF baru terdaftar (kurang dari 1 tahun). Hasil 1 tahun dihitung dari NAV. Semua ETF syariah Indonesia sangat sepi transaksi; baca bagian "Risiko ETF yang sepi" di tab Cara membaca.</p>
      </Panel>
    </template>

    <template v-else-if="sub === 'luar'">
      <EtfLuarDetail v-if="pilihLuar" :kode="pilihLuar" @kembali="pilihLuar = null" />
      <template v-else>
        <div class="panel space-y-3 px-6 py-4">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <Segmen v-model="saringLuar" :pilihan="[['syariah', 'Syariah'], ['bukan', 'Bukan syariah'], ['semua', 'Semua']]" />
            <div class="flex flex-wrap items-center gap-2">
              <select v-model="wilayah" class="!h-9 text-[13px]"><option value="semua">Semua wilayah</option><option v-for="w in daftarWilayah" :key="w" :value="w">{{ w }}</option></select>
              <select v-model="kelasPilih" class="!h-9 text-[13px]"><option value="semua">Semua jenis</option><option v-for="k in daftarKelas" :key="k" :value="k">{{ KELAS[k] || k }}</option></select>
              <input v-model="cariLuar" class="!h-9 w-44 text-[13px]" placeholder="Cari kode / nama" />
              <button class="tombol" :disabled="sibuk" @click="mulai('aksi/etf_perbarui', {}, muatLuar)">Perbarui</button>
            </div>
          </div>
          <p v-if="wilayah !== 'semua' && luar?.wilayah_ket?.[wilayah]" class="m-0 rounded-2xl bg-surface-2 px-4 py-2.5 text-[13px] text-ink-2"><b class="font-medium text-ink">{{ wilayah }}:</b> {{ luar.wilayah_ket[wilayah] }}</p>
          <p v-if="saringLuar !== 'syariah'" class="m-0 rounded-2xl bg-turun-bg px-4 py-2.5 text-xs text-turun">ETF berlabel "bukan syariah" tidak memakai saringan syariah (isinya bisa termasuk bank konvensional, asuransi, alkohol, judi). Ditampilkan sebagai pembanding.</p>
        </div>
        <Panel judul="ETF luar negeri" :ket="`${tampilLuar.length} dari ${luar?.data?.length || 0} ETF · bursa AS & London · termasuk dividen · klik judul kolom untuk mengurutkan, klik baris untuk detail`" rapat>
          <Kerangka v-if="!luar" jenis="tabel" :n="10" logo />
          <div v-else class="overflow-x-auto">
            <table class="tabel min-w-[1040px]">
              <thead>
                <tr>
                  <th v-for="[k, l, kanan, t] in KOLOM_LUAR" :key="k" class="cursor-pointer select-none hover:text-ink" :class="kanan ? '!text-right' : ''" :title="t" @click="urutkan(k)">
                    {{ l }}<span v-if="urutLuar.kolom === k" class="ml-0.5">{{ urutLuar.turun ? "↓" : "↑" }}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="x in tampilLuar" :key="x.kode" class="cursor-pointer hover:bg-surface-2/50" @click="pilihLuar = x.kode">
                  <td class="!h-auto max-w-[440px] !whitespace-normal py-3">
                    <div class="flex items-start gap-3"><Logo jenis="etf" :kunci="x.kode" :teks="x.penerbit || x.kode" :ukuran="32" /><div class="min-w-0">
                      <div class="flex items-center gap-2">
                        <span class="chip !h-5 !px-2 bg-aksen-lembut text-aksen">{{ x.kode }}</span>
                        <span class="truncate font-medium">{{ x.nama }}</span>
                      </div>
                      <div class="mt-0.5 flex items-center gap-1.5 overflow-hidden text-[11px] whitespace-nowrap text-muted">
                        <span class="chip !h-4 !px-1.5 !text-[10px]" :class="x.syariah ? 'bg-naik-bg text-naik' : 'bg-turun-bg text-turun'">{{ x.syariah ? "syariah" : "bukan syariah" }}</span>
                        {{ x.wilayah }} · {{ KELAS[x.kelas] || x.kelas }} · sejak {{ x.mulai?.slice(0, 4) }}<template v-if="x.bursa === 'London'"> · bursa London</template>
                      </div>
                    </div></div>
                  </td>
                  <td class="text-right font-medium" :class="kelasPersen(x.ret_1th)">{{ persen(x.ret_1th, 1) }}</td>
                  <td class="text-right" :class="kelasPersen(x.cagr_2020)">{{ x.cagr_2020 == null ? "–" : persen(x.cagr_2020, 1) }}</td>
                  <td class="text-right" :class="kelasPersen(x.cagr_2020_rp)">{{ x.cagr_2020_rp == null ? "–" : persen(x.cagr_2020_rp, 1) }}</td>
                  <td class="text-right" :class="kelasPersen(x.dd_2020)">{{ x.dd_2020 == null ? "–" : persen(x.dd_2020, 1) }}</td>
                  <td class="text-right">
                    <div class="text-ink-2">{{ x.dividen_n12 ? persen(x.dividen_yield12, 1, false) : "–" }}</div>
                    <div class="text-[11px] text-muted">{{ x.dividen_n12 ? FREK_PENDEK[x.dividen_frek] || x.dividen_frek : "akumulasi" }}</div>
                  </td>
                  <td class="text-right text-ink-2">{{ persen(x.biaya, 2, false) }}</td>
                  <td class="text-right tabular-nums">{{ usd(x.aum, x.mata_uang === "GBp" ? "USD" : x.mata_uang) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="m-0 px-6 py-3 text-xs leading-relaxed text-muted">"–" di kolom sejak 2020 = ETF terdaftar setelah awal 2020, lihat grafiknya. Hasil dihitung dalam mata uang ETF (dolar, atau pound untuk sebagian ETF London); kolom rupiah memakai kurs mata uang itu. "Akumulasi" = dividen tidak dibagikan tapi diinvestasikan ulang. Pajak dividen dan pajak di Indonesia dijelaskan di detail tiap ETF.</p>
        </Panel>
      </template>
    </template>

    <BandingEtf v-else-if="sub === 'banding'" />

    <template v-else>
      <div class="grid gap-5 lg:grid-cols-2">
        <Panel judul="Apa itu ETF">
          <div class="space-y-2 text-[13px] leading-relaxed text-ink-2">
            <p class="m-0">Bayangkan sebuah keranjang berisi banyak saham sekaligus. Dengan membeli satu unit ETF, kamu ikut memiliki sedikit dari semua isi keranjang itu. Contoh: membeli SPUS berarti ikut memiliki sekitar 200 perusahaan besar Amerika yang lolos saringan syariah.</p>
            <p class="m-0">ETF dibeli dan dijual di bursa seperti saham, jadi harganya bergerak sepanjang jam bursa. Kebanyakan ETF hanya <b class="font-medium text-ink">meniru sebuah indeks</b>, sehingga biayanya murah.</p>
          </div>
        </Panel>
        <Panel judul="ETF Indonesia vs ETF luar negeri" rapat>
          <table class="tabel">
            <thead><tr><th></th><th>ETF Indonesia</th><th>ETF luar negeri</th></tr></thead>
            <tbody>
              <tr><td class="text-ink-2">Dibeli lewat</td><td class="!whitespace-normal">Aplikasi sekuritas (rekening saham)</td><td class="!whitespace-normal">Aplikasi yang melayani saham AS/global</td></tr>
              <tr><td class="text-ink-2">Mata uang</td><td>Rupiah</td><td>Dolar AS (sebagian pound)</td></tr>
              <tr><td class="text-ink-2">Ramai transaksi</td><td class="!whitespace-normal">Sangat sepi</td><td class="!whitespace-normal">Umumnya sangat ramai</td></tr>
              <tr><td class="text-ink-2">Pajak</td><td class="!whitespace-normal">0,1% saat jual (final)</td><td class="!whitespace-normal">Pajak dividen di AS + lapor di SPT</td></tr>
            </tbody>
          </table>
        </Panel>
      </div>

      <Panel judul="Arti tiap kolom">
        <div class="grid gap-x-8 gap-y-2.5 text-[13px] leading-relaxed text-ink-2 md:grid-cols-2">
          <p class="m-0"><b class="font-medium text-ink">Hasil 1 tahun</b>: untung/rugi kalau membeli tepat setahun lalu, sudah termasuk dividen.</p>
          <p class="m-0"><b class="font-medium text-ink">Per tahun sejak 2020</b>: rata-rata hasil tiap tahun sejak awal 2020. Dipakai supaya semua ETF dibandingkan di periode yang sama.</p>
          <p class="m-0"><b class="font-medium text-ink">Dalam rupiah</b>: hasil yang benar-benar kamu rasakan sebagai orang Indonesia, karena ikut terpengaruh naik-turun kurs. Kalau rupiah melemah, angka ini lebih besar.</p>
          <p class="m-0"><b class="font-medium text-ink">Turun terdalam</b>: penurunan paling besar dari titik tertinggi. Anggap ini "paling sakit yang pernah terjadi", supaya kamu siap mental.</p>
          <p class="m-0"><b class="font-medium text-ink">Dividen (yield)</b>: dividen setahun dibagi harga. Yield 2% berarti modal Rp10 jt menghasilkan sekitar Rp200 rb setahun sebelum pajak.</p>
          <p class="m-0"><b class="font-medium text-ink">Biaya/th</b>: biaya pengelolaan yang otomatis dipotong dari harga. 0,1% berarti Rp10 rb per Rp10 jt setahun.</p>
          <p class="m-0"><b class="font-medium text-ink">Dana kelolaan</b>: total uang investor. ETF besar lebih ramai dan lebih kecil kemungkinannya ditutup.</p>
          <p class="m-0"><b class="font-medium text-ink">Transaksi/hari</b> (ETF Indonesia): rata-rata nilai jual-beli per hari. Kalau kecil, menjual bisa susah dan harganya bisa meleset.</p>
        </div>
      </Panel>

      <div class="grid gap-5 lg:grid-cols-2">
        <Panel judul="Dividen">
          <ul class="m-0 list-disc space-y-1.5 pl-5 text-[13px] leading-relaxed text-ink-2">
            <li><b class="font-medium text-ink">Frekuensi</b> berbeda-beda: ada yang membayar <b class="font-medium text-ink">bulanan</b> (mis. SPUS, SPSK), <b class="font-medium text-ink">tiap 3 bulan</b> (mis. SPY, QQQ, SCHD), <b class="font-medium text-ink">2× setahun</b> (banyak ETF London), atau <b class="font-medium text-ink">tidak membagi sama sekali</b>.</li>
            <li><b class="font-medium text-ink">Akumulasi (Acc)</b>: dividen tidak dibagikan, langsung diinvestasikan ulang di dalam ETF. Cocok untuk menabung jangka panjang dan lebih sederhana soal pajak.</li>
            <li><b class="font-medium text-ink">Distribusi (Dist)</b>: dividen dibagikan ke rekening. Cocok kalau ingin penghasilan rutin.</li>
            <li>ETF teknologi biasanya yield-nya kecil (di bawah 1%) karena perusahaannya lebih memilih menumbuhkan usaha. ETF dividen, properti, dan sukuk yield-nya lebih besar (3–5%).</li>
          </ul>
        </Panel>
        <Panel judul="Pajak (aturan umum)">
          <ul class="m-0 list-disc space-y-1.5 pl-5 text-[13px] leading-relaxed text-ink-2">
            <li><b class="font-medium text-ink">ETF Indonesia</b>: {{ luar?.pajak?.idx || "0,1% dari nilai jual (final)." }}</li>
            <li><b class="font-medium text-ink">ETF di bursa AS</b>: dividen dipotong 30%, atau 15% kalau mengisi formulir W-8BEN. Untung dari menjual tidak dipajaki AS. Aset di AS di atas US$60.000 bisa kena pajak warisan AS.</li>
            <li><b class="font-medium text-ink">ETF di bursa London (domisili Irlandia)</b>: dividen ke kamu tidak dipotong, dan tidak kena pajak warisan AS. Pajak AS atas saham Amerika di dalamnya sudah dipotong di level dana.</li>
            <li><b class="font-medium text-ink">Di Indonesia</b>: dividen dan untung dari luar negeri dilaporkan di SPT dan kena tarif progresif 5–35%. Pajak yang sudah dipotong di luar negeri bisa dikurangkan (kredit pajak). Dividen luar negeri bisa bebas pajak kalau diinvestasikan kembali di Indonesia sesuai syarat.</li>
            <li class="text-muted">{{ luar?.pajak?.catatan || "Aturan umum, bukan nasihat pajak." }}</li>
          </ul>
        </Panel>
      </div>

      <div class="grid gap-5 lg:grid-cols-2">
        <Panel judul="Saringan syariah">
          <ul class="m-0 list-disc space-y-1.5 pl-5 text-[13px] leading-relaxed text-ink-2">
            <li>Usaha utamanya harus halal: tanpa bank & asuransi konvensional, alkohol, rokok, judi, hiburan dewasa, dan sejenisnya.</li>
            <li>Rasio keuangan dibatasi, umumnya utang berbunga dan kas berbunga masing-masing di bawah ±33% dari nilai perusahaan.</li>
            <li>Pendapatan dari usaha non-halal yang kecil harus "dibersihkan" (purifikasi), biasanya disumbangkan oleh penerbit ETF.</li>
            <li>Karena bank tidak masuk, ETF syariah AS jadi lebih berat ke teknologi dan kesehatan. Ini yang membuat hasilnya bisa berbeda jauh dari S&P 500 biasa.</li>
          </ul>
        </Panel>
        <Panel judul="Risiko yang perlu diingat">
          <ul class="m-0 list-disc space-y-1.5 pl-5 text-[13px] leading-relaxed text-ink-2">
            <li><b class="font-medium text-ink">Pasar</b>: ETF saham bisa turun 30–50% di masa krisis, walaupun isinya menyebar.</li>
            <li><b class="font-medium text-ink">Kurs</b>: ETF luar negeri ikut naik-turun dengan nilai rupiah. Rupiah menguat = hasil dalam rupiah berkurang.</li>
            <li><b class="font-medium text-ink">Terkonsentrasi</b>: ETF sektor (teknologi, energi) atau satu negara lebih bergejolak dari ETF dunia.</li>
            <li><b class="font-medium text-ink">ETF sepi</b> (terutama ETF Indonesia): harga bisa melenceng jauh dari nilai aslinya. Contoh nyata: XSSI pada Agustus 2025 sempat diperdagangkan 3–4× di atas biasanya, dan yang membeli di puncak rugi sekitar 77%.</li>
          </ul>
        </Panel>
      </div>

      <Panel judul="Sumber data">
        <ul class="m-0 list-disc space-y-1.5 pl-5 text-[13px] text-ink-2">
          <li>ETF Indonesia: daftar, NAV, biaya, dan dana kelolaan dari Pasardana; harga bursa dari Yahoo Finance (kode bursa diverifikasi dengan mencocokkan harga terhadap NAV).</li>
          <li>ETF luar negeri: harga, dividen, biaya, dana kelolaan, 10 isi terbesar, dan pembagian sektor dari Yahoo Finance. Kurs dolar dan pound dari Yahoo Finance.</li>
          <li>Diperbarui otomatis tiap hari bursa (jadwal 17:30) atau lewat tombol Perbarui.</li>
        </ul>
      </Panel>
    </template>
  </div>
</template>

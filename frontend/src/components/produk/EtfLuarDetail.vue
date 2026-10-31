<script setup>
import { ref, computed, watch, onUnmounted } from "vue";
import { ArrowLeft, Info as IkonInfo, Landmark, Coins, PieChart } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { persen, rupiah, ringkas, kelasPersen } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import Segmen from "@/components/common/Segmen.vue";
import Logo from "@/components/common/Logo.vue";
import GrafikRentang from "@/components/charts/GrafikRentang.vue";
import KesimpulanProduk from "@/components/produk/KesimpulanProduk.vue";
import RingkasHariIni from "@/components/produk/RingkasHariIni.vue";
import KeyakinanEtf from "@/components/produk/KeyakinanEtf.vue";

const props = defineProps({ kode: String });
const emit = defineEmits(["kembali"]);
const x = ref(null);
const grafik = ref(null);
const banding = ref("SPY");
const uangEtf = (v) => {
  if (v == null) return "–";
  const mu = x.value?.mata_uang || "USD";
  const t = v.toLocaleString("id-ID", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return mu === "GBp" ? `${t}p` : `${{ USD: "US$", GBP: "£", EUR: "€" }[mu] || mu + " "}${t}`;
};
const modal = ref(10_000_000);
const w8ben = ref(true);
const BULAN = ["", "Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
const KELAS = { saham: "Saham", sukuk: "Sukuk", properti: "Properti (REIT)", obligasi: "Obligasi", emas: "Emas", komoditas: "Komoditas" };
const SIMBOL = { USD: "US$", GBP: "£", GBp: "pence " };

watch(() => props.kode, async (k) => {
  x.value = null;
  if (k) x.value = await ambil(`etf/luar/detail/${k}`).catch(() => null);
}, { immediate: true });
watch([() => props.kode, banding], async ([k, b]) => {
  grafik.value = null;
  if (k) grafik.value = await ambil(`etf/luar/grafik/${k}?banding=${b === k ? (k === "SPY" ? "QQQ" : "SPY") : b}`).catch(() => null);
}, { immediate: true });

const intra = ref(null);
const intraSiap = ref(false);
async function muatIntra() {
  const k = props.kode;
  if (!k) return;
  const v = await ambil(`etf/luar/intraday/${k}`).catch(() => null);
  if (props.kode !== k) return;
  if (v?.tgl?.length) intra.value = v;
  intraSiap.value = true;
}
watch(() => props.kode, () => {
  intra.value = null;
  intraSiap.value = false;
  muatIntra();
}, { immediate: true });
const detak = setInterval(() => document.visibilityState === "visible" && muatIntra(), 60000);
onUnmounted(() => clearInterval(detak));
const uangBesar = (v) => {
  const mu = x.value?.mata_uang || "USD";
  return mu === "GBp" ? `£${ringkas(v / 100)}` : `${{ USD: "US$", GBP: "£", EUR: "€" }[mu] || mu + " "}${ringkas(v)}`;
};
const maksTop = computed(() => Math.max(1, ...(x.value?.isi_top || []).map((a) => a.bobot)));
const maksSektor = computed(() => Math.max(1, ...(x.value?.sektor_bobot || []).map((a) => a.bobot)));
const simulasi = computed(() => {
  const v = x.value;
  if (!v) return null;
  const m = Number(modal.value) || 0;
  const kotor = (m * (v.dividen_yield12 || 0)) / 100;
  const potongAs = v.bursa === "London" ? 0 : w8ben.value ? 0.15 : 0.3;
  const bersih = kotor * (1 - potongAs);
  const biaya = (m * (v.biaya || 0)) / 100;
  return { kotor, potongAs, bersih, biaya, perBayar: v.dividen_n12 ? bersih / v.dividen_n12 : 0 };
});
</script>

<template>
  <div class="space-y-5">
    <button class="tombol" @click="emit('kembali')"><ArrowLeft class="h-3.5 w-3.5" />Kembali ke daftar</button>
    <template v-if="!x">
      <Kerangka panel :n="3" />
      <Kerangka panel jenis="grafik" :tinggi="300" />
      <div class="grid gap-5 lg:grid-cols-2">
        <Kerangka panel jenis="tabel" :n="6" logo />
        <Kerangka panel jenis="tabel" :n="6" />
      </div>
    </template>
    <template v-else>
      <div class="panel px-6 py-5">
        <div class="flex flex-wrap items-center gap-3">
          <Logo jenis="etf" :kunci="x.kode" :teks="x.penerbit || x.kode" :ukuran="48" />
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <span class="chip bg-aksen-lembut text-aksen">{{ x.kode }}</span>
              <span class="text-[19px] font-medium">{{ x.nama }}</span>
            </div>
            <div class="mt-1 flex flex-wrap items-center gap-1.5">
              <span class="chip" :class="x.syariah ? 'bg-naik-bg text-naik' : 'bg-turun-bg text-turun'">{{ x.syariah ? "Syariah" : "Bukan syariah" }}</span>
              <span class="chip bg-surface-2 text-ink-2">{{ KELAS[x.kelas] || x.kelas }}</span>
              <span class="chip bg-surface-2 text-ink-2">{{ x.wilayah }}</span>
              <span class="chip bg-surface-2 text-ink-2">Bursa {{ x.bursa }} · {{ x.mata_uang === "USD" ? "dolar AS" : x.mata_uang === "GBp" ? "pound (pence)" : x.mata_uang }}</span>
              <span class="chip bg-surface-2 text-ink-2">Dividen: {{ x.dividen_frek }}</span>
            </div>
          </div>
        </div>
        <div class="mt-4 grid gap-3 md:grid-cols-3">
          <div class="rounded-2xl bg-surface-2 px-4 py-3">
            <div class="mb-1 flex items-center gap-1.5 text-xs font-medium text-ink-2"><IkonInfo class="h-3.5 w-3.5" />Apa isinya</div>
            <p class="m-0 text-[13px] leading-relaxed">{{ x.isi || x.nama }}</p>
          </div>
          <div class="rounded-2xl bg-surface-2 px-4 py-3">
            <div class="mb-1 text-xs font-medium text-ink-2">Cocok untuk</div>
            <p class="m-0 text-[13px] leading-relaxed">{{ x.cocok || "–" }}</p>
          </div>
          <div class="rounded-2xl bg-surface-2 px-4 py-3">
            <div class="mb-1 text-xs font-medium text-ink-2">Tentang wilayahnya</div>
            <p class="m-0 text-[13px] leading-relaxed">{{ x.wilayah_ket || "–" }}</p>
          </div>
        </div>
        <p v-if="!x.syariah" class="m-0 mt-3 rounded-2xl bg-turun-bg px-4 py-2.5 text-xs text-turun">ETF ini tidak memakai saringan syariah: isinya bisa termasuk bank konvensional, asuransi, alkohol, atau usaha lain yang tidak sesuai syariah. Ditampilkan sebagai pembanding.</p>
        <div class="mt-4 grid grid-cols-2 gap-3 md:grid-cols-5">
          <div class="rounded-2xl border border-garis px-4 py-3"><div class="text-xs text-muted">Per tahun sejak 2020</div><div class="mt-0.5 text-[17px] font-medium" :class="kelasPersen(x.cagr_2020)">{{ x.cagr_2020 == null ? "–" : persen(x.cagr_2020, 1) }}</div><div class="text-[11px] text-muted">rupiah {{ x.cagr_2020_rp == null ? "–" : persen(x.cagr_2020_rp, 1) }}</div></div>
          <div class="rounded-2xl border border-garis px-4 py-3"><div class="text-xs text-muted">Hasil 1 tahun</div><div class="mt-0.5 text-[17px] font-medium" :class="kelasPersen(x.ret_1th)">{{ persen(x.ret_1th, 1) }}</div><div class="text-[11px] text-muted">rupiah {{ persen(x.ret_1th_rp, 1) }}</div></div>
          <div class="rounded-2xl border border-garis px-4 py-3"><div class="text-xs text-muted">Turun terdalam</div><div class="mt-0.5 text-[17px] font-medium" :class="kelasPersen(x.dd_2020 ?? x.dd_semua)">{{ persen(x.dd_2020 ?? x.dd_semua, 1) }}</div><div class="text-[11px] text-muted">{{ x.dd_2020 != null ? "sejak 2020" : "sejak terdaftar" }}</div></div>
          <div class="rounded-2xl border border-garis px-4 py-3"><div class="text-xs text-muted">Yield dividen</div><div class="mt-0.5 text-[17px] font-medium">{{ persen(x.dividen_yield12, 2, false) }}</div><div class="text-[11px] text-muted">12 bulan terakhir, sebelum pajak</div></div>
          <div class="rounded-2xl border border-garis px-4 py-3"><div class="text-xs text-muted">Biaya per tahun</div><div class="mt-0.5 text-[17px] font-medium">{{ persen(x.biaya, 2, false) }}</div><div class="text-[11px] text-muted">dana kelolaan {{ x.aum ? `US$${ringkas(x.aum)}` : "–" }}</div></div>
        </div>
      </div>

      <Panel judul="Harga" :ket="`1D: harga per menit sesi terakhir di bursa ${x.bursa === 'London' ? 'London (08.00–16.30 waktu London)' : 'AS (09.30–16.00 waktu New York, 20.30/21.30–03.00/04.00 WIB)'}, tertunda ±10 menit · rentang lain: harga penutupan harian`">
        <template #aksi><Segmen v-model="banding" kecil :pilihan="[['SPY', 'vs S&P 500'], ['QQQ', 'vs Nasdaq-100'], ['SPUS', 'vs SPUS'], ['', 'Tanpa pembanding']]" /></template>
        <GrafikRentang v-if="grafik && intraSiap" :key="x.kode" :tgl="grafik.tgl" :harga="grafik.harga" :total="grafik.nilai" :pembanding="grafik.banding" :nama="x.kode"
          :nama-pembanding="grafik.banding_kode || ''" :intraday="intra" :awal="intra ? '1D' : '1Y'" :format="uangEtf" />
        <Kerangka v-else jenis="grafik" :tinggi="300" />
        <RingkasHariIni :intra="intra" :format="uangEtf" :uang="uangBesar" />
      </Panel>

      <KeyakinanEtf :k="x.keyakinan" :x="x" />

      <div class="grid gap-5 lg:grid-cols-2">
        <Panel judul="10 isi terbesar" :ket="x.isi_top.length ? '% dari dana · data penerbit lewat Yahoo' : 'Data isi belum tersedia untuk ETF ini'">
          <div v-if="x.isi_top.length" class="space-y-2.5">
            <div v-for="a in x.isi_top" :key="a.kode">
              <div class="flex justify-between gap-3 text-[13px]"><span class="truncate"><b class="font-medium">{{ a.kode }}</b> <span class="text-muted">{{ a.nama }}</span></span><span class="shrink-0 tabular-nums">{{ persen(a.bobot, 1, false) }}</span></div>
              <div class="mt-1 h-1.5 rounded-full bg-surface-2"><div class="h-full rounded-full bg-s1" :style="{ width: `${(a.bobot / maksTop) * 100}%` }"></div></div>
            </div>
            <p class="m-0 pt-1 text-xs text-muted">10 terbesar = {{ persen(x.isi_top.reduce((s, a) => s + a.bobot, 0), 0, false) }} dari dana. Makin besar angka ini, makin bergantung pada sedikit perusahaan.</p>
          </div>
        </Panel>
        <Panel judul="Pembagian sektor" :ket="x.sektor_bobot.length ? '% dari bagian saham' : 'Tidak berlaku (bukan ETF saham) atau belum tersedia'">
          <div v-if="x.sektor_bobot.length" class="space-y-2.5">
            <div v-for="a in x.sektor_bobot" :key="a.nama">
              <div class="flex justify-between gap-3 text-[13px]"><span>{{ a.nama }}</span><span class="tabular-nums">{{ persen(a.bobot, 1, false) }}</span></div>
              <div class="mt-1 h-1.5 rounded-full bg-surface-2"><div class="h-full rounded-full bg-s2" :style="{ width: `${(a.bobot / maksSektor) * 100}%` }"></div></div>
            </div>
          </div>
          <div v-if="x.aset_bobot.length" class="mt-4 flex flex-wrap gap-2 text-xs">
            <span class="text-muted">Jenis aset:</span>
            <span v-for="a in x.aset_bobot" :key="a.nama" class="chip bg-surface-2 text-ink-2">{{ a.nama }} {{ persen(a.bobot, 0, false) }}</span>
          </div>
        </Panel>
      </div>

      <div class="grid gap-5 lg:grid-cols-2">
        <Panel judul="Dividen" :ket="`${x.dividen_frek}${x.dividen_n12 ? ` · ${x.dividen_n12} kali dalam 12 bulan terakhir` : ''}`">
          <template v-if="x.dividen_n12">
            <div class="mb-3 grid grid-cols-2 gap-3">
              <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-xs text-muted">Total 12 bulan / lembar</div><div class="mt-0.5 text-[17px] font-medium">{{ SIMBOL[x.mata_uang] || "" }}{{ x.dividen_12bln.toLocaleString("id-ID", { maximumFractionDigits: 3 }) }}</div></div>
              <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-xs text-muted">Yield (dividen ÷ harga)</div><div class="mt-0.5 text-[17px] font-medium">{{ persen(x.dividen_yield12, 2, false) }}</div></div>
            </div>
            <div class="mb-3 flex flex-wrap items-center gap-1.5 text-xs"><span class="text-muted">Biasanya dibayar bulan:</span><span v-for="b in x.dividen_bulan" :key="b" class="chip bg-aksen-lembut text-aksen">{{ BULAN[b] }}</span></div>
            <div class="max-h-[340px] overflow-auto rounded-2xl border border-garis">
              <div v-for="r in x.dividen_riwayat" :key="r.tgl" class="flex justify-between border-t border-garis px-4 py-1.5 text-[13px] first:border-t-0">
                <span class="text-ink-2">{{ r.tgl }}</span><span class="tabular-nums">{{ SIMBOL[x.mata_uang] || "" }}{{ r.nilai.toLocaleString("id-ID", { maximumFractionDigits: 4 }) }}</span>
              </div>
            </div>
          </template>
          <p v-else class="m-0 text-[13px] leading-relaxed text-ink-2">ETF ini <b class="font-medium">tidak membagikan dividen</b>. Dividen dari isinya langsung diinvestasikan ulang (tipe akumulasi, biasanya ditandai "Acc"), jadi hasilnya muncul sebagai kenaikan harga. Cocok kalau tidak butuh penghasilan rutin dan ingin lebih sederhana soal pajak.</p>
        </Panel>

        <Panel judul="Pajak & biaya (perkiraan)" :ket="x.pajak.judul">
          <div class="space-y-2.5 text-[13px] leading-relaxed text-ink-2">
            <p class="m-0 flex gap-2"><Coins class="mt-0.5 h-4 w-4 shrink-0 text-muted" /><span><b class="font-medium text-ink">Dividen:</b> {{ x.pajak.dividen }}</span></p>
            <p class="m-0 flex gap-2"><PieChart class="mt-0.5 h-4 w-4 shrink-0 text-muted" /><span><b class="font-medium text-ink">Menjual:</b> {{ x.pajak.jual }}</span></p>
            <p class="m-0 flex gap-2"><Landmark class="mt-0.5 h-4 w-4 shrink-0 text-muted" /><span><b class="font-medium text-ink">Pajak warisan:</b> {{ x.pajak.warisan }}</span></p>
            <p class="m-0 rounded-2xl bg-surface-2 px-4 py-3 text-xs"><b class="font-medium text-ink">Di Indonesia:</b> {{ x.pajak.indonesia }}</p>
          </div>
          <div v-if="x.dividen_n12" class="mt-4 rounded-2xl border border-garis px-4 py-3">
            <div class="flex flex-wrap items-center gap-2 text-[13px]">
              <span class="font-medium">Simulasi kalau beli</span>
              <span class="inline-flex items-center gap-1">Rp <input v-model.number="modal" type="number" min="0" step="1000000" class="!h-8 w-36 tabular-nums" /></span>
              <label v-if="x.bursa !== 'London'" class="ml-auto flex items-center gap-1.5 text-xs text-ink-2"><input v-model="w8ben" type="checkbox" class="accent-[var(--aksen)]" />sudah isi W-8BEN</label>
            </div>
            <table class="tabel mt-2">
              <tbody>
                <tr><td class="text-ink-2">Dividen setahun (sebelum pajak)</td><td class="text-right tabular-nums">Rp{{ rupiah(Math.round(simulasi.kotor)) }}</td></tr>
                <tr><td class="text-ink-2">Dipotong pajak {{ x.bursa === "London" ? "luar negeri" : "AS" }} ({{ persen(simulasi.potongAs * 100, 0, false) }})</td><td class="text-right tabular-nums text-turun">−Rp{{ rupiah(Math.round(simulasi.kotor - simulasi.bersih)) }}</td></tr>
                <tr><td class="font-medium">Masuk ke rekening setahun</td><td class="text-right font-medium tabular-nums">Rp{{ rupiah(Math.round(simulasi.bersih)) }}</td></tr>
                <tr><td class="text-ink-2">Rata-rata per pembayaran ({{ x.dividen_n12 }}× setahun)</td><td class="text-right tabular-nums">Rp{{ rupiah(Math.round(simulasi.perBayar)) }}</td></tr>
                <tr><td class="text-ink-2">Biaya pengelolaan setahun (sudah termasuk di harga)</td><td class="text-right tabular-nums">Rp{{ rupiah(Math.round(simulasi.biaya)) }}</td></tr>
              </tbody>
            </table>
            <p class="m-0 mt-2 text-[11px] text-muted">Belum termasuk pajak penghasilan di Indonesia (progresif, bisa dikurangi kredit pajak luar negeri), fee broker, dan selisih kurs. {{ x.pajak.catatan }}</p>
          </div>
          <p v-else class="m-0 mt-3 text-[11px] text-muted">{{ x.pajak.catatan }}</p>
        </Panel>
      </div>

      <KesimpulanProduk :k="x.kesimpulan" />
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch } from "vue";
import { ArrowLeft, FileText, ExternalLink, TriangleAlert, GitCompareArrows } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { persen, rupiah, ringkas, kelasPersen } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import GrafikRentang from "@/components/charts/GrafikRentang.vue";
import Segmen from "@/components/common/Segmen.vue";
import KesimpulanProduk from "@/components/produk/KesimpulanProduk.vue";
import KeyakinanRD from "@/components/produk/KeyakinanRD.vue";
import LencanaRD from "@/components/produk/LencanaRD.vue";
import TersediaDi from "@/components/produk/TersediaDi.vue";
import Logo, { kunciMi } from "@/components/common/Logo.vue";

const props = defineProps({ id: Number, tanpaKembali: Boolean, kodeBursa: String, isi: String, tanpaHargaBursa: Boolean });
const emit = defineEmits(["kembali", "banding"]);
const p = ref(null);
const galat = ref("");
const modeGrafik = ref("nav");
const deskripsiRapi = computed(() => {
  const d = (p.value?.deskripsi || "").trim();
  const kata = (w) => (w.length <= 3 || /\d/.test(w) ? w : w[0] + w.slice(1).toLowerCase());
  return d.replace(/^(?:[A-Z0-9&().\-]{2,}\s+){2,}/, (m) => m.split(/(\s+)/).map(kata).join(""));
});
const rentangRD = ref("ALL");

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

const COCOK = {
  pasar_uang: "Dana darurat dan uang yang dipakai kurang dari 1 tahun",
  pendapatan_tetap: "Tabungan untuk 1–3 tahun ke depan",
  campuran: "Uang yang tidak dipakai 3–5 tahun",
  saham: "Uang yang tidak dipakai 5 tahun atau lebih, dan siap melihat nilainya turun separuh",
  indeks: "Uang yang tidak dipakai 5 tahun atau lebih",
  global: "Jangka panjang, siap dengan naik-turun kurs dolar",
  terproteksi: "Uang yang pasti tidak dipakai sampai jatuh tempo",
  etf: "Lihat menu ETF",
  penyertaan_terbatas: "Investor besar/profesional",
};
const uang = (v) => (v == null ? "–" : `${p.value?.mata_uang === "USD" ? "$" : "Rp"}${ringkas(v)}`);
const tglId = (s) => (s ? new Date(s).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }) : "");
const minBeli = (v) => (!v || v === "-" ? "–" : String(v).replace(/^Rp\.?\s*/i, "Rp").replace(/^(USD|US\$)\s*/i, "$").replace(/,-$/, ""));
const sejutaJadi = computed(() => (p.value?.ret_3t != null ? 1e6 * (1 + p.value.ret_3t / 100) : null));
const tglHari = (s) => (s ? new Date(s).toLocaleDateString("id-ID", { weekday: "short", day: "numeric", month: "short", year: "numeric" }) : "");
const kelasRD = computed(() => /\bkelas\b/i.test(p.value?.nama || ""));
const ketAum = computed(() => {
  const x = p.value;
  if (!x) return "";
  const r = [kelasRD.value ? "kelas ini" : "", x.aum_tgl ? `per ${tglId(x.aum_tgl)}` : ""];
  if (x.aum_total && Math.abs(x.aum_total / x.aum - 1) > 0.005) r.push(`semua kelas ${uang(x.aum_total)}`);
  return r.filter(Boolean).join(" · ");
});
const baris = computed(() => (p.value?.jendela || []).map(([k, l]) => ({ k, l, x: p.value.kinerja?.[k] })));
const KUNCI_MEDIAN = { "1b": "ret_1bln", "3b": "ret_3bln", "6b": "ret_6bln", ytd: "ret_ytd", "1t": "ret_1th", "3t": "ret_3t", "5t": "ret_5t" };
const medianSejenis = (k) => p.value?.median_kategori?.[KUNCI_MEDIAN[k]] ?? null;
const adaKira = computed(() => baris.value.some((b) => b.x?.kira));
const adaKurs = computed(() => baris.value.some((b) => b.x?.kurs));
const kurs = computed(() => (p.value?.mata_uang === "USD" ? "$" : "Rp"));
const namaUang = computed(() => (p.value?.mata_uang === "USD" ? "dolar AS" : "rupiah"));
const formatNav = (v) => {
  const d = p.value?.mata_uang === "USD" ? 4 : 2;
  return `${kurs.value}${v.toLocaleString("id-ID", { minimumFractionDigits: d, maximumFractionDigits: d })}`;
};
const formatSumbu = (v) => `${kurs.value}${v.toLocaleString("id-ID", { maximumFractionDigits: 2 })}`;
const NAMA_PERIODE ={ "1b": "1 bulan", "3b": "3 bulan", "6b": "6 bulan", ytd: "Sejak awal tahun", "1t": "1 tahun", "3t": "3 tahun", "5t": "5 tahun", "10t": "10 tahun" };
const sejakAwal = computed(() => {
  const n = p.value?.grafik?.nav || [];
  if (n.length < 2 || p.value?.cagr_semua == null) return null;
  return { total: (n[n.length - 1] / n[0] - 1) * 100, per_tahun: p.value.cagr_semua, mulai: p.value.cagr_mulai };
});
const risiko = computed(() => {
  const x = p.value;
  if (!x) return [];
  const m = x.median_kategori || {};
  return [
    x.tahun_terburuk ? { l: "Tahun terburuk", v: persen(x.tahun_terburuk.ret, 2), c: kelasPersen(x.tahun_terburuk.ret),
      ket: x.tahun_terburuk.ret < 0 ? `Di tahun paling buruk (${x.tahun_terburuk.tahun}), nilainya turun ${persen(Math.abs(x.tahun_terburuk.ret), 2, false)} dalam setahun.` : `Bahkan di tahun paling buruk (${x.tahun_terburuk.tahun}) masih naik.` } : null,
    x.turun_terburuk != null ? { l: "Turun terdalam sepanjang riwayat", v: persen(x.turun_terburuk, 2), c: x.turun_terburuk < -0.05 ? "text-turun" : "",
      ket: `Kalau membeli di titik paling tinggi, nilainya pernah turun sampai ${persen(Math.abs(x.turun_terburuk), 2, false)} sebelum naik lagi.` } : null,
    x.dd != null ? { l: "Turun terdalam 12 bulan terakhir", v: persen(x.dd, 2), c: x.dd < -0.05 ? "text-turun" : "",
      ket: m.dd != null ? `Produk sejenis biasanya ${persen(m.dd, 2)}.` : "" } : null,
    x.vol != null ? { l: "Seberapa sering naik-turun", v: persen(x.vol, 2, false), c: "",
      ket: `Volatilitas per tahun. Makin besar, makin tajam naik-turunnya.${m.vol != null ? ` Produk sejenis biasanya ${persen(m.vol, 2, false)}.` : ""}` } : null,
  ].filter(Boolean);
});
const detailProduk = computed(() => {
  const x = p.value;
  if (!x) return [];
  return [
    { l: "Jenis reksa dana", v: x.kategori_label },
    { l: "Mata uang", v: x.mata_uang === "USD" ? "Dolar AS ($)" : "Rupiah (Rp)", k: x.mata_uang === "USD" ? "beli, jual, dan NAV dalam dolar" : "" },
    { l: "Tingkat risiko", v: x.risiko == null ? null : `${Math.round(x.risiko)} dari 9`, k: x.risiko_label ? `${x.risiko_label} (prospektus)` : "" },
    { l: "Biaya per tahun", v: x.biaya == null ? null : persen(x.biaya, 2, false), k: x.median_kategori?.biaya != null ? `sejenis ${persen(x.median_kategori.biaya, 2, false)}` : "expense ratio" },
    { l: "Diluncurkan", v: x.terbit ? tglId(x.terbit) : null, k: x.tahun_data ? `data ${String(x.tahun_data).replace(".", ",")} th` : "" },
    x.etf ? { l: "Minimal beli", v: "1 lot", k: "100 unit, di bursa" } : { l: "Min. pembelian", v: minBeli(x.min_beli), k: "di aplikasi bisa beda" },
    x.etf ? null : { l: "Min. pembelian berikutnya", v: minBeli(x.min_beli_lagi) },
    x.etf ? null : { l: "Min. penjualan", v: minBeli(x.min_jual) },
    { l: "Imbalan manajer investasi", v: x.biaya_mi },
    { l: "Dana kelolaan (AUM)", v: x.aum == null ? null : uang(x.aum), k: ketAum.value },
    { l: "NAV per unit", v: x.nav == null ? null : formatNav(x.nav), k: x.nav_tgl ? `per ${tglId(x.nav_tgl)}` : "" },
    { l: "Total dana kelolaan MI", v: x.aum_mi ? `Rp${ringkas(x.aum_mi)}` : null, k: x.aum_mi ? `${x.aum_mi_produk} RD syariah, dalam rupiah` : "" },
    { l: "Bank kustodian", v: x.kustodian, penuh: true },
    { l: "Tolok ukur", v: x.pembanding, penuh: true },
    { l: "Kode ISIN", v: x.isin },
    x.dividen?.length ? { l: "Pembagian hasil", v: `${x.dividen.length} kali`, k: "dividen tunai" } : null,
  ].filter((r) => r && r.v != null && r.v !== "" && r.v !== "–");
});
const cocok = computed(() => {
  const x = p.value;
  if (!x) return "–";
  if (x.kategori === "etf") {
    const n = `${x.nama} ${props.isi || ""}`;
    if (/emas|gold/i.test(n)) return "Simpanan jangka panjang dan penyeimbang saat pasar saham turun; harganya ikut harga emas dan kurs";
    if (/sukuk|obligasi|bond|pendapatan tetap/i.test(n)) return "Tabungan 1–3 tahun";
    return "Uang yang tidak dipakai 5 tahun atau lebih";
  }
  return COCOK[x.kategori] || "–";
});
const kurva = computed(() => p.value?.grafik || { tgl: [], nav: [] });
const dokumenUtama = computed(() => {
  const ada = new Map();
  for (const dk of p.value?.dokumen || []) if (!ada.has(dk.jenis_label)) ada.set(dk.jenis_label, dk);
  return [...ada.values()].sort((a, b) => a.jenis_label.localeCompare(b.jenis_label));
});
const maksAset = computed(() => Math.max(1, ...(p.value?.aset || []).map((a) => a.bobot || 0)));
const namaPembanding = computed(() => (/7.?Day|BI|Rate/i.test(p.value?.pembanding || "") ? "BI-Rate (dibungakan)" : p.value?.pembanding || "Tolok ukur"));
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap gap-2">
      <button v-if="!tanpaKembali" class="tombol" @click="emit('kembali')"><ArrowLeft class="h-3.5 w-3.5" />Kembali</button>
      <button v-if="p && !tanpaKembali" class="tombol" @click="emit('banding', id)"><GitCompareArrows class="h-3.5 w-3.5" />Bandingkan dengan produk lain</button>
    </div>
    <div v-if="galat" class="panel px-6 py-4 text-turun">{{ galat }}</div>
    <template v-else-if="!p">
      <Kerangka panel :n="3" />
      <div class="grid gap-5 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <div class="min-w-0 space-y-5">
          <Kerangka panel jenis="grafik" :tinggi="300" />
          <Kerangka panel jenis="stat" :n="8" :judul="false" kolom="grid-cols-2 sm:grid-cols-4" />
        </div>
        <Kerangka panel :n="8" />
      </div>
    </template>
    <template v-else>
      <div class="panel px-6 py-5">
        <div class="flex flex-wrap items-start justify-between gap-x-8 gap-y-4">
          <div class="flex min-w-0 flex-1 basis-[420px] items-start gap-3.5">
            <Logo jenis="mi" :kunci="kunciMi(p.mi)" :teks="p.mi" :ukuran="52" />
            <div class="min-w-0">
              <h2 class="m-0 text-[20px] leading-snug font-medium">{{ p.nama }}</h2>
              <div class="mt-1 text-[13px] text-ink-2">
                {{ p.mi }}<span class="text-muted"> · </span>{{ p.kategori_label }}<span class="text-muted"> · </span><span class="text-naik">Syariah</span><template v-if="p.mata_uang === 'USD'"><span class="text-muted"> · </span><span class="text-kuning">dalam dolar AS</span></template><template v-if="p.etf && p.kategori !== 'etf'"><span class="text-muted"> · </span>ETF</template>
              </div>
              <div v-if="p.lencana?.length || p.urut" class="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2">
                <LencanaRD :lencana="p.lencana" tanpa-peringatan />
                <span v-if="p.urut" class="text-xs text-muted" title="Urutan dari jumlah lencana, lalu peringatan paling sedikit, lalu hasil 3 tahun">Urutan {{ p.urut }} dari {{ p.jumlah_kategori }} {{ p.kategori_label.toLowerCase() }}</span>
              </div>
            </div>
          </div>
          <div v-if="p.etf" class="max-w-[300px] shrink-0">
            <div class="mb-1.5 text-[11px] text-muted">Beli di</div>
            <div class="rounded-2xl bg-surface-2 px-4 py-2.5 text-[13px] text-ink-2">
              <b class="font-medium text-ink">Bursa Efek Indonesia</b><template v-if="kodeBursa">, kode <b class="font-medium text-ink">{{ kodeBursa }}</b></template>
              <div class="mt-0.5 text-xs text-muted">Lewat aplikasi sekuritas mana pun, seperti membeli saham (minimal 1 lot = 100 unit).</div>
              <div v-if="tanpaHargaBursa" class="mt-1 text-xs text-kuning">Riwayat harga bursanya belum tersedia; angka di bawah memakai NAV dari Pasardana.</div>
            </div>
          </div>
          <div v-else class="shrink-0">
            <div class="mb-1.5 text-[11px] text-muted">Tersedia di</div>
            <TersediaDi :platform="p.platform" lengkap />
          </div>
        </div>

        <div v-if="p.deskripsi || isi" class="mt-4 space-y-2 border-t border-garis pt-4 text-[13px] leading-relaxed">
          <p v-if="isi" class="m-0 text-ink-2"><b class="font-medium text-ink">Apa isinya:</b> {{ isi }}</p>
          <p v-if="p.deskripsi" class="m-0 text-muted">{{ deskripsiRapi }}</p>
        </div>
        <div v-if="p.peringatan?.length" class="mt-4 rounded-2xl bg-kuning-bg px-4 py-3">
          <div class="flex items-center gap-2 text-[13px] font-medium text-kuning"><TriangleAlert class="h-4 w-4" />Perlu dicek sebelum membeli</div>
          <ul class="m-0 mt-2 space-y-1.5 pl-6 text-[13px] leading-relaxed text-ink-2">
            <li v-for="w in p.peringatan" :key="w.kode"><span class="font-medium text-ink">{{ w.label }}.</span> {{ w.ket }}</li>
          </ul>
          <p class="m-0 mt-2 text-[11px] text-muted">Peringatan otomatis dari data; bukan vonis produk bermasalah.</p>
        </div>
      </div>

      <slot />

      <div class="grid gap-5 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <div class="min-w-0 space-y-5">
          <Panel :judul="modeGrafik === 'nav' ? 'NAV/Unit' : 'AUM (dana kelolaan)'" :ket="modeGrafik === 'aum' ? (kurva.aum?.tgl.length ? `Sejak ${tglId(kurva.aum.tgl[0])} · akhir bulan dari laporan OJK dan Pasardana` : 'Data AUM belum tersedia') : p.panjang ? `Harga per unit · sejak ${tglId(p.panjang.mulai)} · akhir bulan dari laporan OJK, harian dari Pasardana` : `Harga per unit · ${kurva.tgl.length} hari bursa · harian Pasardana`">
            <GrafikRentang v-if="modeGrafik === 'aum'" key="aum" :tgl="kurva.aum?.tgl || []" :harga="kurva.aum?.nilai || []" nama="AUM" :awal="rentangRD" bulanan @rentang="(k) => (rentangRD = k)"
              :tinggi="260" :format="uang" />
            <GrafikRentang v-else key="nav" :tgl="kurva.tgl" :harga="kurva.nav" :pembanding="kurva.pembanding" nama="NAV" :nama-pembanding="namaPembanding" :awal="rentangRD" @rentang="(k) => (rentangRD = k)"
              :tinggi="260" :format="formatNav" :format-sumbu="formatSumbu" />
            <div class="mt-4 flex flex-col items-center gap-2">
              <Segmen v-model="modeGrafik" kecil :pilihan="[['nav', 'NAV'], ['aum', 'AUM']]" />
              <span v-if="p.nav_tgl" class="text-xs text-muted">NAV terakhir <b class="font-medium text-ink">{{ tglHari(p.nav_tgl) }}</b> · Pasardana</span>
            </div>
          </Panel>

          <Panel v-if="baris.some((b) => b.x)" judul="Performa" :ket="`Naik-turunnya nilai investasi, dalam ${namaUang}, sudah dipotong biaya · NAV ${tglHari(p.nav_tgl)}`" rapat>
            <div class="overflow-x-auto px-3">
              <table class="tabel w-full text-[13px]">
                <thead>
                  <tr>
                    <th>Kalau beli</th>
                    <th class="text-right!">Hasilnya</th>
                    <th class="text-right!" title="Rata-rata per tahun (CAGR)"><span class="sm:hidden">Per tahun</span><span class="hidden sm:inline">Rata-rata per tahun</span></th>
                    <th class="hidden text-right! sm:table-cell" title="Nilai tengah reksa dana sejenis">Produk sejenis</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="b in baris" :key="b.k" :title="b.x ? `Dihitung dari NAV ${tglId(b.x.awal)}${b.x.kira ? ' (akhir bulan terdekat)' : ''} sampai ${tglId(b.x.akhir)}` : ''">
                    <td class="text-ink-2">{{ b.k === "ytd" ? "Awal tahun ini" : `${NAMA_PERIODE[b.k]} lalu` }}</td>
                    <template v-if="b.x">
                      <td class="text-right text-[14px] font-medium tabular-nums" :class="kelasPersen(b.x.total)">{{ persen(b.x.total, 2) }}<sup v-if="b.x.kira" class="ml-0.5 text-[10px] text-muted">≈</sup></td>
                      <td class="text-right tabular-nums" :class="b.x.per_tahun == null ? 'text-muted' : kelasPersen(b.x.per_tahun)">{{ b.x.per_tahun == null || b.k === "1t" ? "" : `${persen(b.x.per_tahun, 2)}/th` }}</td>
                      <td class="hidden text-right tabular-nums text-muted sm:table-cell">{{ medianSejenis(b.k) == null ? "" : persen(medianSejenis(b.k), 2) }}</td>
                    </template>
                    <td v-else colspan="3" class="text-right text-xs text-muted">produk belum setua ini</td>
                  </tr>
                  <tr v-if="sejakAwal">
                    <td class="text-ink-2">Sejak data pertama<div class="text-[11px] text-muted">{{ tglId(sejakAwal.mulai) }}</div></td>
                    <td class="text-right text-[14px] font-medium tabular-nums" :class="kelasPersen(sejakAwal.total)">{{ persen(sejakAwal.total, 2) }}</td>
                    <td class="text-right tabular-nums" :class="kelasPersen(sejakAwal.per_tahun)">{{ persen(sejakAwal.per_tahun, 2) }}/th</td>
                    <td class="hidden sm:table-cell"></td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div class="space-y-2 px-6 pt-3 pb-4">
              <p v-if="sejutaJadi" class="m-0 rounded-2xl bg-surface-2 px-4 py-3 text-[13px] text-ink-2">Contoh: <b class="font-medium text-ink">{{ p.mata_uang === "USD" ? "$1.000" : "Rp1 juta" }}</b> yang dibeli 3 tahun lalu sekarang menjadi sekitar <b class="font-medium" :class="kelasPersen(p.cagr_3)">{{ p.mata_uang === "USD" ? `$${rupiah(Math.round(sejutaJadi / 1000))}` : `Rp${rupiah(Math.round(sejutaJadi / 1000) * 1000)}` }}</b>{{ p.mata_uang === "USD" ? " (dalam dolar, belum termasuk naik-turun kurs rupiah)" : "" }}. Hasil masa lalu, bukan jaminan.</p>
              <details v-if="adaKira" class="text-[11px] leading-snug text-muted">
                <summary class="cursor-pointer select-none">≈ = perkiraan, bisa beda sedikit dari aplikasi. Kenapa?</summary>
                <p class="m-0 mt-1.5">NAV harian dari Pasardana baru tersedia sejak 22 Okt 2025. Untuk periode yang lebih panjang dipakai NAV akhir bulan dari laporan OJK yang paling dekat dengan tanggal awalnya.<template v-if="adaKurs"> Untuk reksa dana dolar, NAV akhir bulan OJK dihitung dari dana kelolaan rupiah ÷ kurs, jadi bisa meleset ±0,2–3% lagi.</template> Arahkan kursor ke baris untuk melihat tanggal yang dipakai.</p>
              </details>
            </div>
          </Panel>

          <Panel v-if="risiko.length" judul="Risiko" ket="Seberapa dalam nilainya pernah turun" rapat>
            <dl class="m-0">
              <div v-for="x in risiko" :key="x.l" class="flex items-start justify-between gap-6 border-t border-garis px-6 py-3.5">
                <div class="min-w-0">
                  <dt class="text-[13px] font-medium">{{ x.l }}</dt>
                  <dd v-if="x.ket" class="m-0 mt-0.5 text-xs leading-snug text-muted">{{ x.ket }}</dd>
                </div>
                <dd class="m-0 shrink-0 text-[15px] font-medium tabular-nums" :class="x.c">{{ x.v }}</dd>
              </div>
            </dl>
          </Panel>

        </div>

        <div class="min-w-0 space-y-5">
          <Panel judul="Detail produk">
            <div class="flex items-center gap-3 border-b border-garis pb-4">
              <Logo jenis="mi" :kunci="kunciMi(p.mi)" :teks="p.mi" :ukuran="36" />
              <div class="min-w-0">
                <div class="text-[11px] text-muted">Nama produk</div>
                <div class="text-[13px] leading-snug font-medium">{{ p.nama }}</div>
              </div>
            </div>
            <div class="border-b border-garis py-4">
              <div class="text-[11px] text-muted">Cocok untuk</div>
              <div class="mt-0.5 text-[13px] font-medium">{{ cocok }}</div>
            </div>
            <dl class="m-0 grid grid-cols-2 gap-x-5 gap-y-4 pt-4">
              <div v-for="x in detailProduk" :key="x.l" class="min-w-0" :class="x.penuh ? 'col-span-2' : ''">
                <dt class="text-[11px] text-muted">{{ x.l }}</dt>
                <dd class="m-0 mt-0.5 text-[13px] font-medium wrap-break-word tabular-nums">{{ x.v }}</dd>
                <dd v-if="x.k" class="m-0 text-[11px] text-muted">{{ x.k }}</dd>
              </div>
            </dl>
            <div v-if="dokumenUtama.length" class="mt-5 grid grid-cols-2 gap-2.5">
              <a v-for="dk in dokumenUtama" :key="dk.jenis_label" :href="dk.url" target="_blank" rel="noopener" class="flex items-center justify-center gap-2 rounded-xl border border-garis px-3 py-2.5 text-[13px] font-medium hover:border-aksen hover:text-aksen" :title="`${dk.nama || dk.jenis_label} · ${tglId(dk.tgl)}`">
                <FileText class="h-4 w-4 shrink-0 text-aksen" />{{ dk.jenis_label }}
              </a>
            </div>
            <div class="mt-3 flex flex-wrap items-center justify-between gap-2 text-[11px] text-muted">
              <span>{{ dokumenUtama.length ? `Dokumen terakhir ${tglId(dokumenUtama[0].tgl)} · unduhan PDF perlu captcha` : "Dokumen belum tersedia" }}</span>
              <a :href="p.url_sumber" target="_blank" rel="noopener" class="inline-flex items-center gap-1 text-aksen hover:underline">Buka di Pasardana<ExternalLink class="h-3 w-3" /></a>
            </div>
          </Panel>

          <Panel judul="Isi reksa dana ini" :ket="p.aset.length || p.alokasi_aset.length ? 'Dari fund fact sheet terakhir · persen dari dana kelolaan' : 'Data isi portofolio belum tersedia'">
            <div v-if="p.alokasi_aset.length" class="mb-5">
              <div class="mb-2 text-xs text-muted">Jenis aset</div>
              <div class="flex h-3 overflow-hidden rounded-full bg-surface-2">
                <div v-for="(a, i) in p.alokasi_aset" :key="a.nama" :style="{ width: `${a.bobot || 0}%` }" :class="['bg-s1', 'bg-s2', 'bg-s4', 'bg-s3'][i % 4]" class="border-r-2 border-surface last:border-r-0"></div>
              </div>
              <div class="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-ink-2">
                <span v-for="(a, i) in p.alokasi_aset" :key="a.nama" class="inline-flex items-center gap-1.5"><span class="h-2 w-2 rounded-full" :class="['bg-s1', 'bg-s2', 'bg-s4', 'bg-s3'][i % 4]"></span>{{ a.nama }} {{ persen(a.bobot, 1, false) }}</span>
              </div>
            </div>
            <div v-if="p.aset.length" class="mb-2 text-xs text-muted">10 isi terbesar</div>
            <div v-if="p.aset.length" class="space-y-2.5">
              <div v-for="a in p.aset.slice(0, 10)" :key="a.nama">
                <div class="flex justify-between gap-3 text-[13px]"><span class="truncate">{{ a.nama }}</span><span class="shrink-0 tabular-nums">{{ a.bobot != null ? persen(a.bobot, 1, false) : "–" }}</span></div>
                <div class="mt-1 h-1.5 rounded-full bg-surface-2"><div class="h-full rounded-full bg-s1" :style="{ width: `${((a.bobot || 0) / maksAset) * 100}%` }"></div></div>
              </div>
            </div>
          </Panel>
        </div>
      </div>
      <KeyakinanRD :k="p.keyakinan" :p="p" />

      <KesimpulanProduk :k="p.kesimpulan" />
      <p class="m-0 text-xs text-muted">Sumber: Pasardana, laporan NAB OJK, katalog publik Bibit/Ajaib/Makmur. Lencana dan urutan dihitung otomatis dari data masa lalu, bukan ramalan. Bukan nasihat keuangan.</p>
    </template>
  </div>
</template>

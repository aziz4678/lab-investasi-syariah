<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { Search, ChevronRight, RefreshCw, Trophy } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { persen, rupiah, ringkas, kelasPersen } from "@/utils/format";
import { pakaiPekerjaan } from "@/composables/pekerjaan";
import Panel from "@/components/common/Panel.vue";
import Segmen from "@/components/common/Segmen.vue";
import HeaderStrategi from "@/components/common/HeaderStrategi.vue";
import PanelPekerjaan from "@/components/sistem/PanelPekerjaan.vue";
import ProdukRD from "@/components/produk/ProdukRD.vue";
import Logo, { kunciMi } from "@/components/common/Logo.vue";
import SukukDetail from "@/components/produk/SukukDetail.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import Pemutar from "@/components/common/Pemutar.vue";

const props = defineProps({ sub: String });
const emit = defineEmits(["sub"]);
const SUB = [["katalog", "Reksa dana"], ["sukuk", "Sukuk & SBN"], ["banding", "Perbandingan"], ["alokasi", "Alokasi"], ["data", "Metodologi"]];

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

const KET_KAT = {
  pasar_uang: ["Risiko paling rendah. Berinvestasi pada deposito dan sukuk berjangka pendek.", "Dana darurat atau pengganti tabungan dengan horizon kurang dari 1 tahun"],
  pendapatan_tetap: ["Mayoritas berinvestasi pada sukuk. Fluktuasi relatif kecil dan dipengaruhi perubahan suku bunga.", "Horizon investasi 1–3 tahun dengan pendapatan stabil"],
  campuran: ["Berinvestasi pada saham dan sukuk dengan porsi yang ditentukan manajer investasi.", "Horizon investasi 3–5 tahun"],
  saham: ["Mayoritas berinvestasi pada saham syariah. Fluktuasi nilai dapat besar.", "Horizon investasi minimal 5 tahun dengan toleransi penurunan modal"],
  indeks: ["Mengikuti indeks saham syariah (JII/ISSI), umumnya dengan biaya lebih rendah.", "Horizon investasi minimal 5 tahun"],
  etf: ["ETF tersedia pada menu ETF Syariah.", "Lihat menu ETF Syariah"],
  global: ["Reksa dana konvensional (melalui agen penjual atau bank) yang berinvestasi pada efek luar negeri, umumnya berdenominasi USD.", "Diversifikasi global dengan toleransi risiko nilai tukar"],
  terproteksi: ["Pokok investasi diproteksi hingga jatuh tempo; tidak dapat dicairkan sewaktu-waktu.", "Dana yang tidak dibutuhkan hingga jatuh tempo"],
  penyertaan_terbatas: ["Khusus investor profesional dengan minimum investasi umumnya miliaran rupiah.", "Investor institusi"],
  dire: ["Investasi pada properti atau infrastruktur.", "Horizon investasi jangka panjang"],
};
const KET_SUKUK = {
  SR: "Sukuk Ritel: SBSN yang ditawarkan kepada investor individu pada masa penawaran melalui mitra distribusi, dengan imbalan tetap setiap bulan yang dijamin negara. Dapat diperdagangkan di pasar sekunder setelah masa minimum kepemilikan.",
  PBS: "Project Based Sukuk: SBSN yang diperdagangkan di pasar sekunder melalui perantara pedagang efek atau bank. Harga berfluktuasi mengikuti perubahan suku bunga.",
  SPNS: "Surat Perbendaharaan Negara Syariah: SBSN berjangka pendek (maksimal 1 tahun).",
  Korporasi: "Sukuk yang diterbitkan korporasi. Imbal hasil lebih tinggi disertai risiko gagal bayar; perhatikan peringkat (rating) penerbit.",
  "Negara lain": "Seri SBSN lainnya (misalnya seri global/valuta asing atau pembiayaan proyek).",
};

const daftar = ref(null);
const kategori = ref([]);
const sukukData = ref(null);
const pilihSukuk = ref(location.hash.startsWith("#reksadana/sukuk/") ? decodeURIComponent(location.hash.split("/")[2]) : null);
const sukukDipilih = computed(() => (sukukData.value?.data || []).find((x) => x.kode === pilihSukuk.value));
watch(pilihSukuk, (k) => {
  if (props.sub === "sukuk") history.replaceState(null, "", k ? `#reksadana/sukuk/${encodeURIComponent(k)}` : "#reksadana/sukuk");
  window.scrollTo({ top: 0 });
});
watch(sukukDipilih, (x) => { if (x && x.jenis !== jenisSukuk.value) jenisSukuk.value = x.jenis; });
const bandingData = ref(null);
const makro = ref(null);
const alok = ref(null);
const memuatAlok = ref(false);
const awalId = Number(location.hash.split("/")[2]) || null;
const pilih = ref(awalId);
const filterKat = ref(baca("rd_kategori", "pasar_uang"));
const cari = ref("");
const urut = ref({ kolom: "skor", turun: true });
const semua = ref(false);
const jenisSukuk = ref("SR");
const profil = ref(baca("rd_profil", "moderat"));
const modal = ref(baca("rd_modal", 100000000));
const deposito = ref(baca("rd_deposito", 4));
const { kerja, galat, sibuk, mulai, lanjutkan } = pakaiPekerjaan();

async function muat() {
  [daftar.value, kategori.value] = await Promise.all([ambil("rd/daftar").catch(() => null), ambil("rd/kategori").catch(() => [])]);
}
async function muatAlokasi() {
  memuatAlok.value = true;
  alok.value = await ambil(`rd/alokasi?profil=${profil.value}&modal=${Number(modal.value) || 100000000}`).catch(() => null);
  memuatAlok.value = false;
}
onMounted(async () => {
  await muat();
  await lanjutkan("rd_perbarui", muat);
});
watch(() => props.sub, async (s) => {
  if (s === "sukuk" && !sukukData.value) sukukData.value = await ambil("rd/sukuk").catch(() => ({ data: [], ringkas: [] }));
  if (s === "banding" && !makro.value) ambil("makro").then((m) => (makro.value = m)).catch(() => (makro.value = {}));
  if (s === "banding" && !bandingData.value) bandingData.value = await ambil("rd/banding").catch(() => ({ data: [] }));
  if (s === "alokasi") muatAlokasi();
}, { immediate: true });
watch(filterKat, (v) => {
  simpan("rd_kategori", v);
  semua.value = false;
});
watch(pilih, (id) => history.replaceState(null, "", id ? `#reksadana/katalog/${id}` : `#reksadana/${props.sub}`));
watch([profil, modal], () => {
  simpan("rd_profil", profil.value);
  simpan("rd_modal", Number(modal.value) || 0);
  if (props.sub === "alokasi") muatAlokasi();
});
watch(deposito, (v) => simpan("rd_deposito", Number(v) || 0));

const info = computed(() => daftar.value?.info);
const data = computed(() => daftar.value?.data || []);
const pilihanKat = computed(() => kategori.value.map((k) => [k.kategori, k.label]));
const katAktif = computed(() => kategori.value.find((k) => k.kategori === filterKat.value));
const tersaring = computed(() => {
  const q = cari.value.trim().toLowerCase();
  let x = data.value.filter((r) => (q ? `${r.nama} ${r.mi}`.toLowerCase().includes(q) : r.kategori === filterKat.value));
  const { kolom, turun } = urut.value;
  x = [...x].sort((a, b) => {
    const va = a[kolom], vb = b[kolom];
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;
    const c = typeof va === "string" ? va.localeCompare(vb) : va - vb;
    return turun ? -c : c;
  });
  return x;
});
const tampil = computed(() => (semua.value ? tersaring.value : tersaring.value.slice(0, 15)));
const terbaik = computed(() => data.value.filter((r) => r.kategori === filterKat.value && r.skor != null).sort((a, b) => b.skor - a.skor).slice(0, 3));
function ganti(k) {
  urut.value = urut.value.kolom === k ? { kolom: k, turun: !urut.value.turun } : { kolom: k, turun: !["biaya", "nama"].includes(k) };
}
function buka(id) {
  pilih.value = id;
  if (props.sub !== "katalog") emit("sub", "katalog");
  window.scrollTo({ top: 0 });
}
const KOLOM = [
  ["nama", "Reksa dana", 0, ""],
  ["nav", "NAV/Unit", 1, "Net Asset Value per unit pada tanggal terakhir"],
  ["ret_1th", "Imbal hasil 1 th", 1, "Perubahan NAV/Unit 12 bulan terakhir, setelah dikurangi biaya"],
  ["cagr_semua", "CAGR", 1, "Compound Annual Growth Rate sejak awal data tersedia (laporan OJK mulai 2013, disambung data Pasardana). Tanda '–' berarti riwayat kurang dari 1 tahun"],
  ["dd", "Max drawdown 1 th", 1, "Penurunan terbesar dari titik tertinggi dalam 12 bulan terakhir. Semakin mendekati 0 semakin stabil"],
  ["biaya", "Expense ratio", 1, "Total biaya tahunan yang dibebankan pada dana. Semakin kecil semakin baik"],
  ["aum", "AUM", 1, "Asset Under Management: total dana kelolaan produk"],
  ["risiko", "Risiko", 1, "Tingkat risiko skala 1–9 berdasarkan prospektus (Pasardana)"],
  ["skor", "Skor", 1, "Skor 0–100 dibandingkan produk sejenis. Lihat tab Metodologi"],
];
const navRD = (r) => (r.nav == null ? "–" : r.nav.toLocaleString("id-ID", { maximumFractionDigits: r.nav >= 100 ? 2 : 4 }));
const labelRisiko = (v) => (v == null ? "" : v <= 3 ? "Rendah" : v <= 6 ? "Sedang" : "Tinggi");
const uangRD = (r) => (r.aum == null ? "–" : `${r.mata_uang === "USD" ? "US$" : "Rp"}${ringkas(r.aum)}`);
const waktuData = computed(() => (info.value?.diperbarui ? new Date(info.value.diperbarui).toLocaleString("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "–"));

const JENIS_SUKUK = [["SR", "Sukuk ritel (SR)"], ["PBS", "Sukuk negara (PBS)"], ["SPNS", "SPN syariah"], ["Korporasi", "Korporasi"], ["Negara lain", "Lainnya"]];
const sukukTampil = computed(() => (sukukData.value?.data || []).filter((x) => x.jenis === jenisSukuk.value).sort((a, b) => (a.jatuh_tempo || "").localeCompare(b.jatuh_tempo || "")));
const ringkasSukuk = computed(() => Object.fromEntries((sukukData.value?.ringkas || []).map((x) => [x.jenis, x])));
const sukukAktif = computed(() => ringkasSukuk.value[jenisSukuk.value]);

const opsiBanding = computed(() => {
  const o = [...(bandingData.value?.data || [])];
  const dep = Number(deposito.value) || 0;
  if (dep > 0) o.push({ nama: "Deposito syariah (input pengguna)", jenis: "Bank", hasil: dep * 0.8, risiko: 1, pajak: "Bagi hasil dikenakan pajak final 20% (angka setelah pajak)", catatan: "Dijamin LPS hingga batas tertentu; pencairan sebelum jatuh tempo dapat dikenakan penalti", dasar: `${dep}% sebelum pajak` });
  return o.sort((a, b) => (a.risiko - b.risiko) || ((b.hasil ?? 0) - (a.hasil ?? 0)));
});
const inflasi = computed(() => makro.value?.inflasi?.nilai ?? null);
const maksHasil = computed(() => Math.max(1, inflasi.value ?? 0, ...opsiBanding.value.map((x) => Math.abs(x.hasil ?? 0))));
const bulanTahun = (t) => (t ? new Date(t).toLocaleDateString("id-ID", { month: "short", year: "numeric" }) : "");
const kotakMakro = computed(() => {
  const m = makro.value;
  if (!m?.bi_rate || !m?.inflasi) return [];
  const ubah = (x) => (x.setahun_lalu == null ? "" : ` · setahun lalu ${persen(x.setahun_lalu, 2, false)}`);
  return [
    { l: "BI-Rate", v: persen(m.bi_rate.nilai, 2, false), k: `per ${new Date(m.bi_rate.tgl).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" })}${ubah(m.bi_rate)}`, t: "Suku bunga acuan Bank Indonesia; patokan bunga deposito dan imbal hasil sukuk" },
    { l: "Inflasi tahunan", v: persen(m.inflasi.nilai, 2, false), k: `${bulanTahun(m.inflasi.tgl)}${ubah(m.inflasi)}`, t: "Kenaikan harga barang setahun terakhir (BPS via BI). Imbal hasil di bawah angka ini berarti daya beli turun" },
    { l: "Bunga riil", v: persen(m.bunga_riil, 2), k: "BI-Rate dikurangi inflasi", t: "Positif = menabung/sukuk mengalahkan inflasi" },
  ];
});
const RISIKO = ["", "Sangat rendah", "Rendah", "Sedang", "Tinggi", "Sangat tinggi"];
const WARNA_PORSI = ["bg-s1", "bg-s2", "bg-s4"];
const tglPendek = (t) => (t ? new Date(t).toLocaleDateString("id-ID", { month: "short", year: "numeric" }) : "–");
</script>

<template>
  <div class="space-y-5">
    <HeaderStrategi judul="Reksa Dana & Sukuk" :sub="sub" :pilihan="SUB" @sub="(s) => { pilih = null; emit('sub', s); }"
      ringkas="Evaluasi reksa dana dan sukuk syariah berdasarkan imbal hasil, CAGR, max drawdown, expense ratio, AUM, dan tingkat risiko dibandingkan produk sejenis."
      :chip="[{ teks: `${info?.produk ?? '…'} reksa dana syariah`, kelas: 'bg-aksen-lembut text-aksen' }, { teks: `${info?.sukuk ?? '…'} sukuk`, kelas: 'bg-surface-2 text-ink-2' }, { teks: info?.ojk ? `Riwayat NAV sejak ${info.ojk.dari.slice(0, 4)} (OJK)` : 'Data NAV baru ±1 tahun', kelas: info?.ojk ? 'bg-surface-2 text-ink-2' : 'bg-kuning-bg text-kuning' }]" />

    <ProdukRD v-if="pilih" :id="pilih" @kembali="pilih = null" />

    <template v-else-if="sub === 'katalog' && !daftar">
      <Kerangka panel jenis="kartu" :n="3" kolom="md:grid-cols-3" />
      <Kerangka panel jenis="tabel" :n="8" logo />
    </template>
    <template v-else-if="sub === 'katalog'">
      <div class="panel px-6 py-5">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div class="text-[15px] font-medium">Kategori reksa dana</div>
          <div class="relative w-full sm:w-72">
            <Search class="pointer-events-none absolute top-1/2 left-3.5 h-4 w-4 -translate-y-1/2 text-muted" />
            <input v-model="cari" class="!h-9 w-full !border !border-garis !bg-surface !pl-9 text-[13px]" placeholder="Cari produk atau manajer investasi" />
          </div>
        </div>
        <Segmen v-model="filterKat" :pilihan="pilihanKat" @update:model-value="cari = ''" />
        <div v-if="katAktif && !cari" class="mt-4 grid gap-4 rounded-2xl bg-surface-2 px-5 py-4 md:grid-cols-[1.4fr_1fr]">
          <div>
            <div class="text-[13px] font-medium">{{ katAktif.label }} <span class="font-normal text-muted">· {{ katAktif.jumlah }} produk · total AUM Rp{{ ringkas(katAktif.aum) }}</span></div>
            <p class="m-0 mt-1 text-[13px] text-ink-2">{{ KET_KAT[katAktif.kategori]?.[0] }}</p>
            <p class="m-0 mt-1 text-xs text-muted">Sesuai untuk: {{ KET_KAT[katAktif.kategori]?.[1] }}</p>
          </div>
          <div class="grid grid-cols-3 gap-3 text-center">
            <div><div class="text-xs text-muted">Imbal hasil 1 th</div><div class="mt-0.5 text-[17px] font-medium" :class="kelasPersen(katAktif.ret_1th)">{{ persen(katAktif.ret_1th, 1) }}</div><div class="text-[11px] text-muted">median</div></div>
            <div><div class="text-xs text-muted">Max drawdown 1 th</div><div class="mt-0.5 text-[17px] font-medium" :class="kelasPersen(katAktif.dd)">{{ persen(katAktif.dd, 1) }}</div><div class="text-[11px] text-muted">median</div></div>
            <div><div class="text-xs text-muted">Expense ratio</div><div class="mt-0.5 text-[17px] font-medium">{{ katAktif.biaya == null ? "–" : persen(katAktif.biaya, 2, false) }}</div><div class="text-[11px] text-muted">median</div></div>
          </div>
        </div>
      </div>

      <div v-if="!cari && terbaik.length">
        <div class="mb-3 flex items-center gap-2 text-[15px] font-medium"><Trophy class="h-4 w-4 text-kuning" />Tiga skor tertinggi kategori {{ katAktif?.label.toLowerCase() }}</div>
        <div class="grid gap-4 md:grid-cols-3">
          <button v-for="(r, i) in terbaik" :key="r.id" type="button" class="panel flex flex-col gap-4 p-4 text-left transition hover:bg-surface-2/60" @click="buka(r.id)">
            <div class="flex min-h-[48px] items-center gap-3">
              <div class="relative shrink-0">
                <Logo jenis="mi" :kunci="kunciMi(r.mi)" :teks="r.mi" :ukuran="44" />
                <span class="absolute -top-1.5 -left-1.5 grid h-5 w-5 place-items-center rounded-full bg-aksen text-[11px] font-semibold text-aksen-teks ring-2 ring-surface">{{ i + 1 }}</span>
              </div>
              <div class="min-w-0 flex-1">
                <div class="line-clamp-2 text-[14px] font-medium leading-snug" :title="r.nama">{{ r.nama }}</div>
                <div class="mt-0.5 truncate text-[11px] text-muted" :title="r.mi">{{ r.mi }}</div>
              </div>
              <div class="shrink-0 text-right">
                <div class="text-[22px] leading-none font-semibold tabular-nums text-naik">{{ Math.round(r.skor) }}</div>
                <div class="mt-1 text-[10px] tracking-wide text-muted uppercase">skor</div>
              </div>
            </div>
            <div class="mt-auto grid grid-cols-3 divide-x divide-garis rounded-2xl bg-surface-2 py-2.5">
              <div class="min-w-0 px-3"><div class="truncate text-[11px] text-muted">Imbal hasil 1 th</div><div class="mt-0.5 text-[14px] font-medium tabular-nums" :class="kelasPersen(r.ret_1th)">{{ persen(r.ret_1th, 1) }}</div></div>
              <div class="min-w-0 px-3"><div class="truncate text-[11px] text-muted">Drawdown 1 th</div><div class="mt-0.5 text-[14px] font-medium tabular-nums" :class="kelasPersen(r.dd)">{{ persen(r.dd, 1) }}</div></div>
              <div class="min-w-0 px-3"><div class="truncate text-[11px] text-muted">Expense ratio</div><div class="mt-0.5 text-[14px] font-medium tabular-nums">{{ r.biaya == null ? "–" : persen(r.biaya, 2, false) }}</div></div>
            </div>
          </button>
        </div>
      </div>

      <Panel :judul="cari ? `Hasil pencarian “${cari}”` : `Semua ${katAktif?.label.toLowerCase() || 'reksa dana'}`"
        :ket="`${tersaring.length} produk · pilih baris untuk melihat detail · data per ${waktuData}`" rapat>
        <template #aksi>
          <button class="tombol" :disabled="sibuk" @click="mulai('aksi/rd_perbarui', {}, muat)"><RefreshCw class="h-3.5 w-3.5" :class="sibuk ? 'animate-spin' : ''" />Perbarui</button>
        </template>
        <PanelPekerjaan class="mx-6 mb-3" :kerja="kerja" :galat="galat" />
        <div class="overflow-x-auto">
          <table class="tabel min-w-[1080px]">
            <thead>
              <tr>
                <th v-for="[k, l, kanan, t] in KOLOM" :key="k" class="cursor-pointer select-none hover:text-ink" :class="kanan ? '!text-right' : ''" :title="t" @click="ganti(k)">
                  {{ l }}<span v-if="urut.kolom === k" class="ml-0.5">{{ urut.turun ? "↓" : "↑" }}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in tampil" :key="r.id" class="cursor-pointer hover:bg-surface-2/50" @click="buka(r.id)">
                <td class="!h-auto max-w-[280px] py-2.5">
                  <div class="flex items-center gap-3">
                  <Logo jenis="mi" :kunci="kunciMi(r.mi)" :teks="r.mi" :ukuran="32" />
                  <div class="min-w-0">
                  <div class="truncate font-medium">{{ r.nama }}</div>
                  <div class="truncate text-[11px] text-muted">
                    {{ r.mi }}<template v-if="cari"> · {{ r.kategori_label }}</template><template v-if="r.mata_uang === 'USD'"> · USD</template>
                    <span v-if="r.nav_lama" class="text-kuning" :title="`NAV terakhir ${r.nav_tgl}`"> · NAV belum diperbarui</span>
                    <span v-if="r.nav_beku" class="text-kuning" title="NAV hampir tidak pernah berubah"> · NAV tidak bergerak</span>
                  </div>
                  </div>
                  </div>
                </td>
                <td class="text-right tabular-nums text-ink-2">{{ navRD(r) }}</td>
                <td class="text-right font-medium" :class="kelasPersen(r.ret_1th)">{{ r.ret_1th == null ? "–" : persen(r.ret_1th, 2) }}</td>
                <td class="text-right"><div :class="kelasPersen(r.cagr_semua)">{{ r.cagr_semua == null ? "–" : persen(r.cagr_semua, 1) }}</div><div v-if="r.cagr_semua != null" class="text-[11px] text-muted">{{ String(r.tahun_data).replace(".", ",") }} th</div></td>
                <td class="text-right" :class="kelasPersen(r.dd)">{{ r.dd == null ? "–" : persen(r.dd, 1) }}</td>
                <td class="text-right text-ink-2">{{ r.biaya == null ? "–" : persen(r.biaya, 2, false) }}</td>
                <td class="text-right tabular-nums">{{ uangRD(r) }}</td>
                <td class="text-right text-ink-2" :title="labelRisiko(r.risiko)">{{ r.risiko == null ? "–" : `${Math.round(r.risiko)}/9` }}</td>
                <td class="text-right">
                  <span v-if="r.skor != null" class="chip" :class="r.skor >= 70 ? 'bg-naik-bg text-naik' : r.skor < 40 ? 'bg-turun-bg text-turun' : 'bg-surface-2 text-ink-2'">{{ Math.round(r.skor) }}</span>
                  <span v-else class="text-xs text-muted" :title="r.nav_beku ? 'NAV tidak bergerak' : 'Riwayat NAV kurang dari 200 hari bursa'">{{ r.nav_beku ? "–" : "baru" }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <button v-if="tersaring.length > 15" class="mx-6 my-3 text-xs text-muted hover:underline" @click="semua = !semua">{{ semua ? "Tampilkan 15 teratas" : `Tampilkan seluruh ${tersaring.length} produk` }}</button>
      </Panel>
    </template>

    <SukukDetail v-else-if="sub === 'sukuk' && sukukDipilih" :x="sukukDipilih" :ket="KET_SUKUK[sukukDipilih.jenis]" @kembali="pilihSukuk = null" />

    <template v-else-if="sub === 'sukuk'">
      <div class="panel px-6 py-5">
        <div class="mb-4 text-[15px] font-medium">Jenis sukuk</div>
        <Segmen v-model="jenisSukuk" :pilihan="JENIS_SUKUK" />
        <div class="mt-4 grid gap-4 rounded-2xl bg-surface-2 px-5 py-4 md:grid-cols-[1.4fr_1fr]">
          <p class="m-0 text-[13px] leading-relaxed text-ink-2">{{ KET_SUKUK[jenisSukuk] }}</p>
          <div class="grid grid-cols-3 gap-3 text-center">
            <div><div class="text-xs text-muted">Seri aktif</div><div class="mt-0.5 text-[17px] font-medium">{{ sukukAktif?.jumlah ?? 0 }}</div></div>
            <div><div class="text-xs text-muted">Kupon per tahun</div><div class="mt-0.5 text-[17px] font-medium">{{ sukukAktif?.kupon_median != null ? persen(sukukAktif.kupon_median, 2, false) : "–" }}</div><div class="text-[11px] text-muted">median</div></div>
            <div><div class="text-xs text-muted">Yield</div><div class="mt-0.5 text-[17px] font-medium">{{ sukukAktif?.ytm_median != null ? persen(sukukAktif.ytm_median, 2, false) : "–" }}</div><div class="text-[11px] text-muted">median</div></div>
          </div>
        </div>
        <p class="m-0 mt-3 text-xs text-muted">Sukuk Tabungan (ST) tidak diperdagangkan di pasar sekunder sehingga tidak tercantum dalam daftar ini.</p>
      </div>
      <Panel :judul="JENIS_SUKUK.find((j) => j[0] === jenisSukuk)?.[1]" :ket="`${sukukTampil.length} seri · diurutkan berdasarkan jatuh tempo terdekat · pilih baris untuk melihat detail dan grafik harga`" rapat>
        <Kerangka v-if="!sukukData" jenis="tabel" :n="8" logo />
        <div v-else class="overflow-x-auto">
          <table class="tabel min-w-[820px]">
            <thead><tr><th>Seri</th><th class="!text-right">Kupon</th><th>Jatuh tempo</th><th class="!text-right" title="Harga dalam persen dari nilai pokok; 100 = nilai nominal">Harga</th><th class="!text-right" title="Yield to maturity: estimasi imbal hasil tahunan apabila dibeli pada harga terakhir dan dimiliki hingga jatuh tempo">YTM</th><th>Penerbit / peringkat</th></tr></thead>
            <tbody>
              <tr v-for="x in sukukTampil" :key="x.kode" class="cursor-pointer hover:bg-surface-2/50" @click="pilihSukuk = x.kode">
                <td class="!h-auto max-w-[340px] py-2.5"><div class="flex items-center gap-3"><Logo :jenis="['SR', 'PBS', 'SPNS', 'Negara lain'].includes(x.jenis) ? 'negara' : 'emiten'" :kunci="['SR', 'PBS', 'SPNS', 'Negara lain'].includes(x.jenis) ? 'kemenkeu' : x.penerbit" :teks="x.penerbit" :ukuran="30" /><div class="min-w-0"><div class="font-medium">{{ x.kode }}</div><div class="truncate text-[11px] text-muted" :title="x.nama">{{ x.nama }}</div></div></div></td>
                <td class="text-right">{{ x.kupon == null ? "–" : persen(x.kupon * 100, 2, false) }}</td>
                <td class="tabular-nums">{{ tglPendek(x.jatuh_tempo) }} <span class="text-xs text-muted">· {{ x.sisa_tahun == null ? "–" : `sisa ${x.sisa_tahun.toLocaleString("id-ID", { maximumFractionDigits: 1 })} tahun` }}</span></td>
                <td class="text-right">{{ x.harga == null ? "–" : x.harga.toLocaleString("id-ID", { maximumFractionDigits: 2 }) }}</td>
                <td class="text-right font-medium">{{ x.ytm == null ? "–" : persen(x.ytm * 100, 2, false) }}</td>
                <td class="text-xs text-ink-2">{{ x.penerbit }}<template v-if="x.rating"> · {{ x.rating }}</template><template v-else-if="['SR', 'PBS', 'SPNS'].includes(x.jenis)"> · dijamin negara</template></td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="m-0 px-6 py-3 text-xs text-muted">Harga 100 setara dengan nilai nominal. Harga di bawah 100 (diskon) menghasilkan yield lebih tinggi dari kupon. Imbalan dan keuntungan modal dikenakan pajak final 10%.</p>
      </Panel>
    </template>

    <template v-else-if="sub === 'banding'">
      <Panel judul="Perbandingan Instrumen" ket="Diurutkan dari risiko terendah · reksa dana: median imbal hasil 12 bulan terakhir · sukuk: kupon atau YTM saat ini · saham: dividend yield atau hasil backtest" rapat>
        <template #aksi>
          <label class="flex items-center gap-2 text-xs text-ink-2">Bagi hasil deposito <input v-model.number="deposito" type="number" min="0" max="15" step="0.25" class="!h-8 w-20 text-right tabular-nums" />%</label>
        </template>
        <div v-if="kotakMakro.length" class="grid grid-cols-1 gap-3 px-6 pb-4 sm:grid-cols-3">
          <div v-for="k in kotakMakro" :key="k.l" class="rounded-2xl bg-surface-2 px-4 py-3" :title="k.t">
            <div class="text-xs text-muted">{{ k.l }}</div>
            <div class="mt-0.5 text-[17px] font-medium tabular-nums" :class="k.l === 'Bunga riil' ? kelasPersen(makro.bunga_riil) : ''">{{ k.v }}</div>
            <div class="text-[11px] text-muted">{{ k.k }}</div>
          </div>
        </div>
        <Kerangka v-if="!bandingData" jenis="tabel" :n="8" />
        <div v-else class="overflow-x-auto">
          <table class="tabel min-w-[760px]">
            <thead><tr><th class="w-[46%]">Instrumen</th><th>Tingkat risiko</th><th>Imbal hasil per tahun</th></tr></thead>
            <tbody>
              <tr v-for="o in opsiBanding" :key="o.nama">
                <td class="!h-auto !whitespace-normal py-3"><div class="font-medium">{{ o.nama }}</div><div class="text-[11px] text-muted">{{ o.jenis }} · {{ o.dasar }}</div><div class="mt-1 text-xs leading-relaxed text-ink-2">{{ o.catatan }}</div></td>
                <td class="!h-auto py-3 align-top"><div class="mt-1 flex items-center gap-1" :title="RISIKO[o.risiko]"><span v-for="i in 5" :key="i" class="h-2 w-2 rounded-full" :class="i <= o.risiko ? (o.risiko >= 4 ? 'bg-turun' : o.risiko >= 3 ? 'bg-kuning' : 'bg-naik') : 'bg-surface-3'"></span></div><div class="mt-1 text-[11px] text-muted">{{ RISIKO[o.risiko] }}</div></td>
                <td class="!h-auto !whitespace-normal py-3 align-top">
                  <div class="mt-1 flex items-center gap-2">
                    <div class="relative h-2 flex-1 rounded-full bg-surface-2">
                      <div class="h-full rounded-full" :class="(o.hasil ?? 0) < 0 ? 'bg-turun' : 'bg-s1'" :style="{ width: `${(Math.abs(o.hasil ?? 0) / maksHasil) * 100}%` }"></div>
                      <div v-if="inflasi != null" class="absolute -top-1 h-4 w-0.5 rounded bg-kuning" :style="{ left: `${(inflasi / maksHasil) * 100}%` }" :title="`Inflasi ${persen(inflasi, 2, false)}`"></div>
                    </div>
                    <span class="w-16 text-right font-medium tabular-nums" :class="kelasPersen(o.hasil)">{{ o.hasil == null ? "–" : persen(o.hasil, 1) }}</span>
                  </div>
                  <div class="mt-1 text-[11px] text-muted"><template v-if="inflasi != null && o.hasil != null"><span :class="o.hasil >= inflasi ? 'text-naik' : 'text-kuning'">{{ o.hasil >= inflasi ? "di atas" : "di bawah" }} inflasi</span> · </template><template v-if="o.hasil_atas != null">Kuartil atas ≥ {{ persen(o.hasil_atas, 1, false) }} · </template>{{ o.pajak }}</div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="inflasi != null" class="m-0 px-6 pt-3 text-xs text-muted">Garis kuning pada bar = inflasi tahunan {{ persen(inflasi, 2, false) }}. Sumber BI-Rate dan inflasi: Bank Indonesia.</p>
        <p class="m-0 px-6 py-3 text-xs text-muted">IHSG mengalami penurunan dalam 12 bulan terakhir sehingga kinerja reksa dana saham tampak rendah. Kesimpulan sebaiknya tidak diambil dari data satu tahun saja.</p>
      </Panel>
    </template>

    <template v-else-if="sub === 'alokasi'">
      <div class="panel px-6 py-5">
        <div class="flex flex-wrap items-end justify-between gap-4">
          <div>
            <div class="mb-2 text-xs text-muted">Profil risiko</div>
            <Segmen v-model="profil" :pilihan="[['konservatif', 'Konservatif'], ['moderat', 'Moderat'], ['agresif', 'Agresif']]" />
          </div>
          <label class="block">
            <span class="mb-2 block text-xs text-muted">Modal</span>
            <span class="flex items-center gap-2 text-[13px] text-ink-2">Rp <input v-model.number="modal" type="number" min="0" step="1000000" class="!h-9 w-44 tabular-nums" /></span>
          </label>
        </div>
        <div v-if="memuatAlok && alok" class="mt-4"><Pemutar teks="Menghitung ulang alokasi..." /></div>
        <Kerangka v-if="!alok && memuatAlok" class="mt-5" :n="3" />
        <template v-if="alok">
          <div class="mt-5 text-[13px] text-ink-2"><b class="font-medium text-ink">{{ alok.label }}:</b> {{ alok.ket }}.</div>
          <div class="mt-3 flex h-3 overflow-hidden rounded-full">
            <div v-for="(x, i) in alok.porsi" :key="x.kategori" :style="{ width: `${x.persen}%` }" :class="WARNA_PORSI[i]" class="border-r-2 border-surface last:border-r-0"></div>
          </div>
          <div class="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-[13px]">
            <span v-for="(x, i) in alok.porsi" :key="x.kategori" class="inline-flex items-center gap-2"><span class="h-2.5 w-2.5 rounded-full" :class="WARNA_PORSI[i]"></span>{{ x.label }} {{ x.persen }}% · Rp{{ ringkas(x.nilai) }}</span>
          </div>
          <p class="m-0 mt-4 rounded-2xl bg-surface-2 px-4 py-3 text-xs leading-relaxed text-ink-2">Apabila kinerja 12 bulan terakhir terulang: imbal hasil <b class="font-medium" :class="kelasPersen(alok.ret_1th)">{{ persen(alok.ret_1th, 1) }}</b> (Rp{{ ringkas(alok.modal * alok.ret_1th / 100) }}) dengan rata-rata max drawdown <span :class="kelasPersen(alok.dd)">{{ persen(alok.dd, 1) }}</span>. Ilustrasi ini berdasarkan data satu tahun ketika IHSG menurun; hasil pada periode lain dapat berbeda signifikan.</p>
        </template>
      </div>
      <div v-if="!alok && memuatAlok" class="grid gap-5 lg:grid-cols-3">
        <Kerangka v-for="i in 3" :key="i" panel jenis="tabel" :n="3" logo />
      </div>
      <div v-if="alok" class="grid gap-5 transition-opacity lg:grid-cols-3" :class="memuatAlok ? 'opacity-50' : ''">
        <Panel v-for="x in alok.porsi" :key="x.kategori" :judul="`${x.label} · ${x.persen}%`" :ket="`Rp${rupiah(Math.round(x.nilai))} · tiga skor tertinggi`" rapat>
          <p v-if="!x.pilihan.length" class="m-0 px-6 pb-4 text-muted">Belum ada produk dengan data yang memadai.</p>
          <button v-for="pp in x.pilihan" :key="pp.id" type="button" class="flex w-full items-center gap-3 border-t border-garis px-6 py-3 text-left first:border-t-0 hover:bg-surface-2/50" @click="buka(pp.id)">
            <Logo jenis="mi" :kunci="kunciMi(pp.mi)" :teks="pp.mi || pp.nama" :ukuran="30" />
            <div class="min-w-0 flex-1">
              <div class="truncate text-[13px] font-medium">{{ pp.nama }}</div>
              <div class="text-[11px] text-muted">Imbal hasil 1 th <span :class="kelasPersen(pp.ret_1th)">{{ persen(pp.ret_1th, 1) }}</span> · max drawdown <span :class="kelasPersen(pp.dd)">{{ persen(pp.dd, 1) }}</span> · expense ratio {{ pp.biaya == null ? "–" : persen(pp.biaya, 2, false) }}</div>
            </div>
            <span class="chip bg-naik-bg text-naik">{{ Math.round(pp.skor) }}</span>
            <ChevronRight class="h-4 w-4 text-muted" />
          </button>
        </Panel>
      </div>
      <p class="m-0 text-xs text-muted">Porsi setiap profil mengikuti alokasi umum robo-advisor dan bukan hasil pengujian. Disarankan menyebar dana ke 2–3 produk per kategori agar tidak bergantung pada satu manajer investasi. Informasi ini bukan nasihat keuangan.</p>
    </template>

    <template v-else>
      <Panel judul="Definisi Indikator">
        <ul class="m-0 list-disc space-y-1.5 pl-5 text-[13px] text-ink-2">
          <li><b class="font-medium">NAV/Unit</b> (Net Asset Value per unit): nilai aktiva bersih per unit penyertaan pada tanggal terakhir yang dipublikasikan.</li>
          <li><b class="font-medium">AUM</b> (Asset Under Management): total dana kelolaan suatu produk. Produk dengan AUM kecil memiliki risiko pembubaran yang lebih tinggi.</li>
          <li><b class="font-medium">Total AUM</b>: jumlah AUM seluruh produk dalam satu kategori atau seluruh reksa dana syariah yang dikelola satu manajer investasi.</li>
          <li><b class="font-medium">Imbal hasil 1 tahun</b>: perubahan NAV/Unit selama 12 bulan terakhir setelah dikurangi biaya. Keuntungan reksa dana bukan objek pajak bagi pemegang unit.</li>
          <li><b class="font-medium">CAGR</b> (Compound Annual Growth Rate): pertumbuhan rata-rata NAV/Unit per tahun sejak awal data tersedia. Periode tiap produk berbeda, sehingga perbandingan antarproduk perlu memperhatikan lama periodenya.</li>
          <li><b class="font-medium">Max drawdown 1 tahun</b>: penurunan terbesar NAV/Unit dari titik tertinggi ke titik terendah dalam 12 bulan terakhir.</li>
          <li><b class="font-medium">Expense ratio</b>: total biaya tahunan yang dibebankan pada dana, dalam persen dari AUM.</li>
          <li><b class="font-medium">Tingkat risiko</b>: klasifikasi risiko skala 1 (terendah) sampai 9 (tertinggi) berdasarkan prospektus, bersumber dari Pasardana: 1–3 rendah, 4–6 sedang, 7–9 tinggi.</li>
        </ul>
      </Panel>
      <Panel judul="Metode Perhitungan Skor">
        <ul class="m-0 list-disc space-y-1.5 pl-5 text-[13px] text-ink-2">
          <li>Skor 0–100 hanya membandingkan produk dengan <b class="font-medium">kategori dan mata uang yang sama</b> menggunakan peringkat persentil.</li>
          <li>Pasar uang: imbal hasil 1 tahun 60%, expense ratio 20%, AUM 20%.</li>
          <li>Kategori lain: imbal hasil 1 tahun 40%, max drawdown 25%, volatilitas harian 15%, expense ratio 10%, AUM 10%.</li>
          <li>Produk dengan riwayat NAV kurang dari {{ daftar?.min_titik ?? 200 }} hari bursa ditandai "baru"; produk dengan NAV yang tidak bergerak tidak dinilai.</li>
        </ul>
      </Panel>
      <Panel judul="Keterbatasan Data">
        <ul class="m-0 list-disc space-y-1.5 pl-5 text-[13px] text-ink-2">
          <li>Skor menggunakan data 12 bulan (aturan dikunci). CAGR menggunakan NAV akhir bulan dari laporan OJK (sejak 2013) yang disambung dengan NAV harian Pasardana; NAV berdenominasi USD dari OJK dikonversi dengan kurs akhir bulan. IHSG menurun dalam 12 bulan terakhir sehingga imbal hasil 1 tahun tampak rendah.</li>
          <li>Belum terbukti bahwa produk dengan skor tinggi tahun ini akan tetap unggul pada tahun berikutnya; hal ini akan diuji setelah data mencapai minimal 3 tahun.</li>
          <li>Reksa dana yang telah dibubarkan tidak tercakup dalam data (survivorship bias), sehingga median kategori cenderung sedikit lebih tinggi dari kondisi sebenarnya.</li>
          <li>Sumber: Pasardana (data publik) diperbarui setiap hari bursa; riwayat NAV jangka panjang dari laporan NAB OJK.</li>
        </ul>
      </Panel>
    </template>
  </div>
</template>

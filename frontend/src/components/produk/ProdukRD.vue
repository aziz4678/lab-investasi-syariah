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
const uang = (v) => (v == null ? "–" : `${p.value?.mata_uang === "USD" ? "US$" : "Rp"}${ringkas(v)}`);
const tglId = (s) => (s ? new Date(s).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }) : "");
const minBeli = (v) => (!v || v === "-" ? "–" : String(v).replace(/^Rp\.?\s*/i, "Rp").replace(/,-$/, ""));
const sejutaJadi = computed(() => (p.value?.cagr_3 != null ? 1e6 * Math.pow(1 + p.value.cagr_3 / 100, 3) : null));
const ringkasan = computed(() => {
  const x = p.value;
  if (!x) return [];
  return [
    x.cagr_3 != null
      ? { l: "Rata-rata per tahun", v: persen(x.cagr_3, 1), k: "3 tahun terakhir, setelah biaya", c: kelasPersen(x.cagr_3) }
      : { l: "Hasil 12 bulan", v: persen(x.ret_1th, 1), k: "riwayat belum 3 tahun", c: kelasPersen(x.ret_1th) },
    { l: "Tahun terburuk", v: x.tahun_terburuk ? persen(x.tahun_terburuk.ret, 1) : "–", k: x.tahun_terburuk ? `tahun ${x.tahun_terburuk.tahun}` : "belum ada tahun penuh", c: x.tahun_terburuk ? kelasPersen(x.tahun_terburuk.ret) : "" },
    { l: "Turun terburuk", v: x.turun_terburuk == null ? "–" : persen(x.turun_terburuk, 1), k: "dari titik tertinggi, sepanjang riwayat", c: x.turun_terburuk < -0.05 ? "text-turun" : "" },
    { l: "Biaya per tahun", v: x.biaya == null ? "–" : persen(x.biaya, 2, false), k: x.median_kategori?.biaya != null ? `nilai tengah sejenis ${persen(x.median_kategori.biaya, 2, false)}` : "", c: "" },
    x.etf ? { l: "Minimal beli", v: "1 lot", k: "100 unit, dibeli di bursa", c: "" } : { l: "Minimal beli", v: minBeli(x.min_beli), k: "menurut manajer investasi; di aplikasi bisa beda", c: "" },
    { l: "Dana kelolaan", v: uang(x.aum), k: x.aum_tgl ? `per ${tglId(x.aum_tgl)}` : "", c: "" },
  ].filter((r) => r.v !== "–" && r.v != null);
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
const PERIODE = [["ret_1bln", "1 bln"], ["ret_3bln", "3 bln"], ["ret_6bln", "6 bln"], ["ret_ytd", "Sejak Jan"], ["ret_1th", "1 th"]];
const infoProduk = computed(() => {
  const x = p.value;
  if (!x) return [];
  const r = [["Minimal pembelian awal", minBeli(x.min_beli)], ["Minimal pembelian berikutnya", minBeli(x.min_beli_lagi)], ["Imbalan manajer investasi", x.biaya_mi],
    ["Tingkat risiko (prospektus)", x.risiko == null ? null : `${Math.round(x.risiko)} dari 9 (${x.risiko_label})`], ["Diluncurkan", x.terbit ? tglId(x.terbit) : null],
    ["Bank kustodian (penyimpan aset)", x.kustodian], ["Tolok ukur", x.pembanding], ["Total dana kelolaan MI ini", x.aum_mi ? `Rp${ringkas(x.aum_mi)} · ${x.aum_mi_produk} RD syariah` : null], ["Kode ISIN", x.isin]];
  if (x.dividen?.length) r.push(["Pembagian hasil (dividen)", `${x.dividen.length} kali`]);
  return r.map(([l, v]) => [l, v == null || v === "" ? "–" : v]);
});
const kurva = computed(() => p.value?.grafik || { tgl: [], nav: [] });
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
      <Kerangka panel jenis="stat" :n="6" :judul="false" kolom="grid-cols-2 md:grid-cols-3" />
      <Kerangka panel jenis="grafik" :tinggi="300" />
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

      <Panel judul="Ringkasan 30 detik" :ket="`Cocok untuk: ${cocok}`">
        <p v-if="ringkasan.length < 3" class="m-0 mb-3 text-[13px] text-ink-2">Produk ini masih sangat baru (data {{ String(p.tahun_data ?? 0).replace(".", ",") }} tahun), jadi sebagian besar angka belum bisa dihitung.</p>
        <div class="grid grid-cols-2 gap-3 md:grid-cols-3">
          <div v-for="x in ringkasan" :key="x.l" class="rounded-2xl bg-surface-2 px-4 py-3">
            <div class="text-xs text-muted">{{ x.l }}</div>
            <div class="mt-0.5 truncate text-[17px] font-medium tabular-nums" :class="x.c">{{ x.v }}</div>
            <div class="text-[11px] text-muted">{{ x.k }}</div>
          </div>
        </div>
        <p v-if="sejutaJadi" class="m-0 mt-4 text-[13px] text-ink-2">Contoh: <b class="font-medium text-ink">Rp1 juta</b> yang dibeli 3 tahun lalu sekarang menjadi sekitar <b class="font-medium" :class="kelasPersen(p.cagr_3)">Rp{{ rupiah(Math.round(sejutaJadi / 1000) * 1000) }}</b>{{ p.mata_uang === "USD" ? " (dalam dolar, belum termasuk kurs)" : "" }}. Hasil masa lalu, bukan jaminan.</p>
      </Panel>

      <Panel :judul="modeGrafik === 'nav' ? 'NAV/Unit' : 'AUM (dana kelolaan)'" :ket="modeGrafik === 'aum' ? (kurva.aum?.tgl.length ? `Sejak ${tglId(kurva.aum.tgl[0])} · akhir bulan dari laporan OJK dan Pasardana` : 'Data AUM belum tersedia') : p.panjang ? `Harga per unit · sejak ${tglId(p.panjang.mulai)} · akhir bulan dari laporan OJK, harian 12 bulan terakhir dari Pasardana` : `Harga per unit · ${kurva.tgl.length} hari bursa · harian Pasardana`">
        <GrafikRentang v-if="modeGrafik === 'aum'" key="aum" :tgl="kurva.aum?.tgl || []" :harga="kurva.aum?.nilai || []" nama="AUM" :awal="rentangRD" bulanan @rentang="(k) => (rentangRD = k)"
          :tinggi="260" :format="uang" />
        <GrafikRentang v-else key="nav" :tgl="kurva.tgl" :harga="kurva.nav" :pembanding="kurva.pembanding" nama="NAV" :nama-pembanding="namaPembanding" :awal="rentangRD" @rentang="(k) => (rentangRD = k)"
          :tinggi="260" :format="(v) => v.toLocaleString('id-ID', { minimumFractionDigits: 2, maximumFractionDigits: 2 })" />
        <div class="mt-4 flex flex-wrap items-center justify-between gap-3">
          <Segmen v-model="modeGrafik" kecil :pilihan="[['nav', 'NAV'], ['aum', 'AUM']]" />
          <div class="flex flex-wrap gap-1.5 text-xs">
            <span v-for="[k, l] in PERIODE" :key="k" class="chip bg-surface-2 text-ink-2" :title="p.median_kategori?.[k] != null ? `Nilai tengah RD sejenis ${persen(p.median_kategori[k], 2)}` : ''">{{ l }} <b class="font-medium" :class="kelasPersen(p[k])">{{ p[k] == null ? "–" : persen(p[k], 1) }}</b></span>
          </div>
        </div>
      </Panel>

      <div class="grid gap-5 lg:grid-cols-2 [&>*]:min-w-0">
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
        <Panel judul="Informasi produk" rapat>
          <dl class="m-0">
            <div v-for="[l, v] in infoProduk" :key="l" class="flex items-start justify-between gap-6 border-t border-garis px-6 py-3 text-[13px]">
              <dt class="shrink-0 text-ink-2">{{ l }}</dt>
              <dd class="m-0 min-w-0 text-right break-words tabular-nums">{{ v }}</dd>
            </div>
          </dl>
          <div class="px-6 pt-2 pb-4">
            <div class="mb-1.5 flex items-center justify-between gap-3 text-xs text-muted">
              <span>Dokumen (prospektus & fund fact sheet)</span>
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
      <KeyakinanRD :k="p.keyakinan" :p="p" />

      <KesimpulanProduk :k="p.kesimpulan" />
      <p class="m-0 text-xs text-muted">Sumber: Pasardana, laporan NAB OJK, katalog publik Bibit/Ajaib/Makmur. Lencana dan urutan dihitung otomatis dari data masa lalu, bukan ramalan. Bukan nasihat keuangan.</p>
    </template>
  </div>
</template>

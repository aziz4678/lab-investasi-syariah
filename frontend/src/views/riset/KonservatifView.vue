<script setup>
import { ref, computed, watch, onMounted, inject } from "vue";
import { RefreshCw, Lock, Unlock, ExternalLink } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { pakaiPekerjaan } from "@/composables/pekerjaan";
import { persen, rupiahRingkas } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import Segmen from "@/components/common/Segmen.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import PanelPekerjaan from "@/components/sistem/PanelPekerjaan.vue";
import GrafikJalurModal from "@/components/charts/GrafikJalurModal.vue";

const data = ref(null);
const siap = ref(false);
const kerja = pakaiPekerjaan();
const pindahTab = inject("pindahTab");
const bukaProduk = (id) => {
  pindahTab("reksadana", "katalog");
  history.replaceState(null, "", `#reksadana/katalog/${id}`);
};
const porsiKartu = ref("sbn50");
const opsi = ref("sbn50");
const modal = ref(1000000000);
const pengeluaran = ref(10000000);
const bulanDarurat = ref(6);
const tarikGrafik = ref(null);

const PILIHAN_SBN = [["sbn30", "SBN 30%"], ["sbn50", "SBN 50%"], ["sbn70", "SBN 70%"]];
const PILIHAN_OPSI = [["tanpa_sbn", "Tanpa SBN"], ...PILIHAN_SBN];
const NAMA_OPSI = { tanpa_sbn: "Tanpa SBN", sbn30: "Dengan SBN 30%", sbn50: "Dengan SBN 50%", sbn70: "Dengan SBN 70%", jii_pu: "Pembanding: 54% JII / 46% RD pasar uang" };
const WARNA_WADAH = { darurat: "bg-s4", pu: "bg-s2", pt: "bg-s1", sbn: "bg-s3" };

const muat = async () => {
  data.value = await ambil("konservatif").catch(() => null);
  siap.value = true;
};
onMounted(async () => {
  await muat();
  await kerja.lanjutkan("penarikan_hitung", muat);
});
const hitungUlang = () => kerja.mulai("aksi/penarikan_hitung", {}, muat);

const bulanTeks = (s) => {
  if (!s) return "–";
  const [t, b] = String(s).slice(0, 7).split("-").map(Number);
  return new Date(t, b - 1, 1).toLocaleDateString("id-ID", { month: "short", year: "numeric" });
};
const tglTeks = (s) => (s ? new Date(s).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }) : "–");
const pr = (v, d = 1) => (v == null ? "–" : persen(v * 100, d, false));
const prTanda = (v, d = 1) => (v == null ? "–" : persen(v * 100, d, true));
const modalRiil = (v) => (v == null ? "–" : `${(v * 100).toLocaleString("id-ID", { maximumFractionDigits: 1 })}%`);

const ada = computed(() => data.value?.ada);
const patokan = computed(() => data.value?.patokan);
const terbaru = computed(() => data.value?.terbaru);
const pat = (kode) => patokan.value?.portofolio?.find((p) => p.kode === kode);
const baru = (kode) => terbaru.value?.portofolio?.find((p) => p.kode === kode);
const geser = (kode) => data.value?.geser?.[kode];
const porsiSbn = (kode) => pat(kode)?.porsi_sbn ?? 0;

const kartu = computed(() => [
  { kode: "tanpa_sbn", judul: "Tanpa SBN", ikon: Unlock, ket: "RD pendapatan tetap syariah / RD pasar uang syariah 50/50, rebalance tahunan.", sifat: "Bisa dicairkan kapan saja · 0% terkunci" },
  { kode: porsiKartu.value, judul: "Dengan SBN", ikon: Lock, pilih: true,
    ket: "Sebagian di Sukuk Ritel / Sukuk Tabungan (SR/ST) yang dipegang sampai jatuh tempo, sisanya RD pendapatan tetap / pasar uang 50/50.",
    sifat: `Porsi terkunci rata-rata ${pr(pat(porsiKartu.value)?.kunci_rata, 0)} · SBN tidak bisa dijual sebelum jatuh tempo` },
]);

const angka = (s) => Number(String(s).replace(/\D/g, "")) || 0;
const tampilRp = (v) => (v ? v.toLocaleString("id-ID") : "");

const sebaran = computed(() => {
  const darurat = Math.min(pengeluaran.value * bulanDarurat.value, modal.value);
  const sisa = Math.max(modal.value - darurat, 0);
  const w = porsiSbn(opsi.value);
  const sbn = sisa * w;
  const rd = sisa - sbn;
  const wadah = [
    { kode: "darurat", nama: "Dana darurat · RD pasar uang syariah", ket: `${bulanDarurat.value} bulan pengeluaran, dipisah dari modal investasi`, nilai: darurat },
    { kode: "pt", nama: "RD pendapatan tetap syariah", ket: "bagian RD 50%", nilai: rd / 2 },
    { kode: "pu", nama: "RD pasar uang syariah", ket: "bagian RD 50% · sumber penarikan bulanan", nilai: rd / 2 },
  ];
  if (w > 0) wadah.push({ kode: "sbn", nama: "SBN ritel syariah (SR/ST)", ket: "dipegang sampai jatuh tempo", nilai: sbn });
  const aman = pat(opsi.value)?.aman_5;
  return { darurat, sisa, sbn, wadah, total: modal.value, aman, kurang: pengeluaran.value * bulanDarurat.value > modal.value,
    penghasilan: aman ? (sisa * aman) / 12 : null };
});

const penawaranPakai = computed(() => {
  const p = data.value?.penawaran;
  if (!p) return null;
  if (p.dibuka) return { status: "dibuka", seri: p.dibuka.seri, jenis: p.dibuka.jenis, ket: `masa penawaran ${tglTeks(p.dibuka.mulai)} – ${tglTeks(p.dibuka.tutup)}`,
    varian: p.dibuka.varian.map((v) => ({ seri: v.seri, tenor: v.tenor, jatuh: bulanTeks(v.jatuh_tempo), kupon: v.kupon, jenis_kupon: v.jenis_kupon })) };
  const x = [...(p.perkiraan ?? [])].filter((x) => x.bulan).sort((a, b) => a.bulan.localeCompare(b.bulan))[0];
  if (!x) return null;
  return { status: "perkiraan", seri: x.seri, jenis: x.jenis, ket: `perkiraan sekitar ${bulanTeks(x.bulan)}`,
    varian: x.tenor.map((t) => ({ seri: `${x.seri}T${t}`, tenor: t, jatuh: "perkiraan", kupon: null })) };
});
const tangga = computed(() => {
  const p = penawaranPakai.value;
  if (!p || !sebaran.value.sbn) return [];
  return p.varian.map((v) => ({ ...v, nilai: sebaran.value.sbn / p.varian.length }));
});

const jalurOpsi = computed(() => baru(opsi.value)?.jalur ?? []);
const pilihanTarik = computed(() => jalurOpsi.value.map((j) => [String(j.tarik), `${pr(j.tarik)}${j.tarik === baru(opsi.value)?.aman_5 ? " (aman)" : ""}`]));
watch([opsi, () => data.value], () => {
  const a = baru(opsi.value)?.aman_5;
  tarikGrafik.value = String(a ?? jalurOpsi.value[0]?.tarik ?? "");
}, { immediate: true });
const jalurPilih = computed(() => jalurOpsi.value.find((j) => String(j.tarik) === tarikGrafik.value));

const produk = computed(() => data.value?.produk ?? {});
const kolomTabel = computed(() => patokan.value?.portofolio?.[0]?.tabel?.map((x) => x.tarik) ?? []);
const kelasUtuh = (v) => (v == null ? "text-muted" : v >= 0.8 ? "font-medium text-naik" : v >= 0.5 ? "text-ink" : "text-muted");
const lebarPersen = (v, total) => `${total ? Math.max((v / total) * 100, 0) : 0}%`;
</script>

<template>
  <div class="space-y-5">
    <Panel judul="Portofolio Konservatif" ket="Berapa yang aman ditarik rutin tanpa daya beli modal berkurang">
      <template #aksi>
        <span v-if="ada" class="chip" :class="data.basi ? 'bg-kuning-bg text-kuning' : 'bg-surface-2 text-ink-2'">
          Dihitung {{ tglTeks(terbaru.dihitung) }} · data s/d {{ bulanTeks(terbaru.periode.akhir) }}<template v-if="data.basi"> · data basi</template>
        </span>
        <button class="tombol" :disabled="kerja.sibuk.value" @click="hitungUlang"><RefreshCw class="h-3.5 w-3.5" :class="kerja.sibuk.value ? 'animate-spin' : ''" />Hitung ulang</button>
      </template>
      <PanelPekerjaan class="mb-4" :kerja="kerja.kerja.value" :galat="kerja.galat.value" />
      <Kerangka v-if="!siap" jenis="kartu" :n="2" kolom="grid-cols-1 md:grid-cols-2" />
      <p v-else-if="!ada" class="m-0 text-[13px] text-ink-2">Belum ada hasil hitungan. Tekan "Hitung ulang" (±5 menit).</p>
      <div v-else class="grid gap-4 md:grid-cols-2">
        <div v-for="k in kartu" :key="k.judul" class="flex flex-col rounded-2xl border border-garis px-5 py-4">
          <div class="flex items-center gap-2"><component :is="k.ikon" class="h-4 w-4 text-aksen" /><div class="text-[15px] font-medium">{{ k.judul }}</div></div>
          <p class="m-0 mt-1 text-[13px] text-ink-2">{{ k.ket }}</p>
          <Segmen v-if="k.pilih" v-model="porsiKartu" :pilihan="PILIHAN_SBN" kecil class="mt-3 self-start" />
          <div class="mt-4">
            <div class="text-xs text-muted">Tingkat aman per tahun · patokan {{ data.patokan_tahun }}</div>
            <div class="mt-0.5 text-[28px] leading-tight font-semibold">
              <template v-if="pat(k.kode)?.aman_5 != null">{{ pr(pat(k.kode).aman_5) }}</template>
              <span v-else class="text-[17px] font-medium text-muted">belum ada tingkat yang aman (≤ 3%)</span>
            </div>
            <div class="text-[11px] text-muted">
              <template v-if="geser(k.kode)">patokan {{ pr(geser(k.kode).patokan) }} → terbaru <span class="font-medium text-kuning">{{ pr(geser(k.kode).terbaru) }}</span></template>
              <template v-else>terbaru {{ pr(baru(k.kode)?.aman_5) }} (data s/d {{ bulanTeks(terbaru.periode.akhir) }})</template>
              · horizon 3 th: {{ pr(pat(k.kode)?.aman_3) }}
            </div>
          </div>
          <div class="mt-4 grid grid-cols-3 gap-3 border-t border-garis pt-3 text-center">
            <div><div class="text-[11px] text-muted">Rata-rata riil/th</div><div class="mt-0.5 text-[15px] font-medium">{{ prTanda(pat(k.kode)?.cagr_riil, 2) }}</div><div class="text-[10px] text-muted">tanpa penarikan</div></div>
            <div><div class="text-[11px] text-muted">Modal riil 5 th</div><div class="mt-0.5 text-[15px] font-medium">{{ modalRiil(pat(k.kode)?.di_aman_5?.median) }}</div><div class="text-[10px] text-muted">biasanya</div></div>
            <div><div class="text-[11px] text-muted">Modal riil 5 th</div><div class="mt-0.5 text-[15px] font-medium">{{ modalRiil(pat(k.kode)?.di_aman_5?.terburuk) }}</div><div class="text-[10px] text-muted">paling sial</div></div>
          </div>
          <p class="m-0 mt-3 text-[11px] text-muted">{{ k.sifat }}</p>
        </div>
      </div>
    </Panel>

    <Panel v-if="ada" judul="Penyebaran dana" ket="Dana darurat dipisah dulu, sisanya dibagi sesuai opsi. Penghasilan dihitung dari sisa modal × tingkat aman.">
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div class="min-w-0">
          <label class="text-xs text-muted">Modal</label>
          <div class="mt-1 flex items-center rounded-full bg-surface-2 px-4"><span class="text-[13px] text-muted">Rp</span>
            <input :value="tampilRp(modal)" @input="(e) => (modal = angka(e.target.value))" inputmode="numeric" class="h-10 w-full min-w-0 bg-transparent px-2 text-[15px] outline-none" /></div>
          <div class="mt-1 text-[11px] text-muted">{{ rupiahRingkas(modal) }}</div>
        </div>
        <div class="min-w-0">
          <label class="text-xs text-muted">Pengeluaran per bulan</label>
          <div class="mt-1 flex items-center rounded-full bg-surface-2 px-4"><span class="text-[13px] text-muted">Rp</span>
            <input :value="tampilRp(pengeluaran)" @input="(e) => (pengeluaran = angka(e.target.value))" inputmode="numeric" class="h-10 w-full min-w-0 bg-transparent px-2 text-[15px] outline-none" /></div>
          <div class="mt-1 text-[11px] text-muted">{{ rupiahRingkas(pengeluaran) }}</div>
        </div>
        <div class="min-w-0">
          <label class="text-xs text-muted">Dana darurat (bulan)</label>
          <div class="mt-1 flex items-center rounded-full bg-surface-2 px-4">
            <input v-model.number="bulanDarurat" type="number" min="0" max="36" class="h-10 w-full min-w-0 bg-transparent text-[15px] outline-none" /><span class="text-[13px] text-muted">bulan</span></div>
        </div>
        <div class="min-w-0">
          <div class="text-xs text-muted">Opsi</div>
          <Segmen v-model="opsi" :pilihan="PILIHAN_OPSI" kecil class="mt-1.5" />
        </div>
      </div>
      <p v-if="sebaran.kurang" class="m-0 mt-3 text-xs text-kuning">Dana darurat lebih besar dari modal; seluruh modal dipakai sebagai dana darurat.</p>

      <div class="mt-5 flex h-4 w-full overflow-hidden rounded-full bg-surface-2">
        <div v-for="w in sebaran.wadah" :key="w.kode" :class="WARNA_WADAH[w.kode]" :style="{ width: lebarPersen(w.nilai, sebaran.total) }" :title="w.nama"></div>
      </div>
      <div class="mt-4 overflow-x-auto">
        <table class="tabel min-w-[520px]">
          <thead><tr><th>Wadah</th><th class="!text-right">Rupiah</th><th class="!text-right">% modal</th></tr></thead>
          <tbody>
            <tr v-for="w in sebaran.wadah" :key="w.kode">
              <td><div class="flex items-center gap-2"><span class="h-2.5 w-2.5 shrink-0 rounded-full" :class="WARNA_WADAH[w.kode]"></span><div><div class="text-[13px]">{{ w.nama }}</div><div class="text-[11px] text-muted">{{ w.ket }}</div></div></div></td>
              <td class="text-right font-medium tabular-nums">{{ rupiahRingkas(w.nilai) }}</td>
              <td class="text-right tabular-nums text-ink-2">{{ pr(sebaran.total ? w.nilai / sebaran.total : null) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="tangga.length" class="mt-4 rounded-2xl bg-surface-2 px-4 py-3">
        <div class="text-[13px] font-medium">Bagian SBN: {{ penawaranPakai.seri }} ({{ penawaranPakai.jenis === "ST" ? "Sukuk Tabungan" : "Sukuk Ritel" }}) · {{ penawaranPakai.ket }}</div>
        <div class="mt-2 grid gap-2 sm:grid-cols-2">
          <div v-for="v in tangga" :key="v.seri" class="flex items-baseline justify-between gap-3 rounded-xl bg-surface px-3 py-2 text-[13px]">
            <span>{{ v.seri }} <span class="text-[11px] text-muted">tenor {{ v.tenor }} th · jatuh tempo {{ v.jatuh }}<template v-if="v.kupon"> · kupon awal {{ pr(v.kupon, 2) }}</template></span></span>
            <span class="font-medium tabular-nums">{{ rupiahRingkas(v.nilai) }}</span>
          </div>
        </div>
        <p class="m-0 mt-2 text-[11px] text-muted">Mengikuti aturan simulasi: seluruh porsi SBN masuk penawaran berikutnya, dibagi rata antar seri. Sampai tanggal terbit, uangnya parkir di RD pasar uang.</p>
      </div>

      <div class="mt-4 flex flex-wrap items-baseline justify-between gap-3 border-t border-garis pt-4">
        <div>
          <div class="text-xs text-muted">Penghasilan per bulan dari sisa modal {{ rupiahRingkas(sebaran.sisa) }} · tingkat aman {{ pr(sebaran.aman) }}</div>
          <div class="text-[24px] font-semibold">{{ sebaran.penghasilan != null ? `${rupiahRingkas(sebaran.penghasilan)}/bulan` : "tidak ada tingkat aman" }}</div>
        </div>
        <div class="text-[11px] text-muted">naik mengikuti inflasi tiap tahun · pengeluaran Anda {{ rupiahRingkas(pengeluaran) }}/bulan</div>
      </div>
    </Panel>

    <Panel v-if="ada" judul="Cara menjalankannya">
      <ol class="m-0 list-decimal space-y-1.5 pl-5 text-[13px] text-ink-2">
        <li>Penghasilan bulanan diambil dari kupon SBN dulu; kekurangannya dari menjual RD pasar uang.</li>
        <li>Tiap Desember, kembalikan RD pendapatan tetap dan pasar uang ke 50/50.</li>
        <li>Tiap masa penawaran SBN ritel, isi porsi SBN yang kosong (dari seri yang jatuh tempo) ke seri baru. Tangga jatuh tempo terbentuk sendiri seiring waktu: tiap seri jatuh tempo, uangnya diputar ke penawaran berikutnya.</li>
        <li>Dana darurat tidak ikut ditarik dan tidak dimasukkan ke SBN.</li>
      </ol>
      <div class="mt-5 grid gap-5 lg:grid-cols-[1fr_1.4fr]">
        <div class="min-w-0 rounded-2xl border border-garis px-4 py-3">
          <div class="text-[13px] font-medium">Penawaran SBN ritel syariah</div>
          <div v-if="data.penawaran?.dibuka" class="mt-2 text-[13px]">
            <span class="chip bg-naik-bg text-naik">sedang dibuka</span>
            <div class="mt-1.5">{{ data.penawaran.dibuka.seri }}: {{ tglTeks(data.penawaran.dibuka.mulai) }} – {{ tglTeks(data.penawaran.dibuka.tutup) }}</div>
            <div v-for="v in data.penawaran.dibuka.varian" :key="v.seri" class="text-[12px] text-ink-2">{{ v.seri }} · {{ v.tenor }} th · kupon awal {{ pr(v.kupon, 2) }}<template v-if="v.spread"> (BI-Rate + {{ pr(v.spread, 2) }}, floating with floor)</template></div>
            <a :href="data.penawaran.dibuka.sumber" target="_blank" rel="noopener" class="mt-1 inline-flex items-center gap-1 text-[11px] text-aksen">siaran pers DJPPR <ExternalLink class="h-3 w-3" /></a>
          </div>
          <div v-for="x in data.penawaran?.perkiraan ?? []" :key="x.jenis" class="mt-3 text-[13px]">
            <span class="chip bg-surface-2 text-ink-2">perkiraan</span>
            <div class="mt-1.5">{{ x.jenis === "SR" ? "Sukuk Ritel" : "Sukuk Tabungan" }} berikutnya ({{ x.seri }}) sekitar <b class="font-medium">{{ bulanTeks(x.bulan) }}</b></div>
            <div class="text-[11px] text-muted">dari pola {{ x.dasar_pola }} (bulan {{ x.pola_bulan.join(", ") }}); bukan jadwal resmi</div>
          </div>
        </div>
        <div class="min-w-0">
          <div class="mb-2 text-[13px] font-medium">Sukuk Ritel (SR) yang beredar di pasar sekunder</div>
          <div class="overflow-x-auto">
            <table class="tabel min-w-[520px]">
              <thead><tr><th>Seri</th><th class="!text-right">Kupon</th><th>Jatuh tempo</th><th class="!text-right">Harga</th><th class="!text-right">Hasil kalau ditahan, bersih</th></tr></thead>
              <tbody>
                <tr v-for="s in data.sr" :key="s.kode">
                  <td class="font-medium">{{ s.kode }}</td>
                  <td class="text-right tabular-nums">{{ pr(s.kupon, 2) }}</td>
                  <td class="tabular-nums">{{ bulanTeks(s.jatuh_tempo) }}</td>
                  <td class="text-right tabular-nums">{{ s.harga?.toLocaleString("id-ID", { maximumFractionDigits: 2 }) ?? "–" }}<div class="text-[10px] text-muted">{{ tglTeks(s.tgl_harga) }}</div></td>
                  <td class="text-right font-medium tabular-nums">{{ pr(s.ytm_bersih, 2) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="m-0 mt-2 text-[11px] text-muted">Bersih = setelah pajak kupon 10%. Harga = transaksi terakhir di Pasardana; seri yang jarang ditransaksikan bisa memakai harga basi. Dalam simulasi, SBN dibeli di pasar perdana, bukan sekunder.</p>
        </div>
      </div>
    </Panel>

    <Panel v-if="ada" judul="Contoh produk per wadah" ket="Contoh yang memenuhi kriteria, bukan rekomendasi. Memilih dari return masa lalu belum terbukti (H18 belum diuji).">
      <div class="grid gap-5 lg:grid-cols-2">
        <div v-for="(w, kat) in produk" :key="kat" class="min-w-0">
          <div class="text-[13px] font-medium">{{ w.label }}</div>
          <div class="text-[11px] text-muted">{{ w.jumlah_lolos }} lolos saringan · {{ w.jumlah_aum_besar }} dengan dana kelolaan ≥ median ({{ rupiahRingkas(w.batas_aum) }}) · diurutkan dari biaya termurah</div>
          <div class="mt-2 space-y-1.5">
            <a v-for="p in w.produk" :key="p.id" :href="`#reksadana/katalog/${p.id}`" @click.prevent="bukaProduk(p.id)" class="flex items-center justify-between gap-3 rounded-xl border border-garis px-3 py-2 transition hover:bg-surface-2">
              <div class="min-w-0"><div class="truncate text-[13px] font-medium">{{ p.nama }}</div><div class="truncate text-[11px] text-muted">{{ p.mi }} · riwayat {{ p.tahun_data?.toLocaleString("id-ID", { maximumFractionDigits: 1 }) }} th</div></div>
              <div class="shrink-0 text-right text-[12px]"><div>biaya {{ persen(p.biaya, 2, false) }}/th</div><div class="text-[11px] text-muted">AUM {{ rupiahRingkas(p.aum) }}</div></div>
            </a>
          </div>
        </div>
      </div>
      <p class="m-0 mt-3 text-[11px] text-muted">Saringan: syariah, rupiah, masih aktif (NAV ≤ {{ data.kriteria_produk.aktif_hari }} hari), riwayat ≥ {{ data.kriteria_produk.min_tahun }} th, bukan RD bagi hasil tunai (tanda Pasardana atau NAV tumbuh &lt; {{ pr(data.kriteria_produk.nav_datar, 0) }}/th), biaya diketahui. Return tidak dipakai untuk mengurutkan.</p>
    </Panel>

    <Panel v-if="ada && jalurPilih" judul="Perjalanan modal riil" :ket="`${NAMA_OPSI[opsi]} · tarik ${pr(jalurPilih.tarik)}/th dari modal awal, naik mengikuti inflasi · ${terbaru.n_mulai_5} tanggal mulai · hasil hitung terbaru (${bulanTeks(terbaru.periode.akhir)})`">
      <div class="mb-3 flex flex-wrap items-center gap-2"><span class="text-xs text-muted">Tarik per tahun</span><Segmen v-model="tarikGrafik" :pilihan="pilihanTarik" kecil /></div>
      <GrafikJalurModal :tahun="jalurPilih.tahun" />
      <div class="mt-4 grid grid-cols-2 gap-3 text-center sm:grid-cols-4">
        <div class="rounded-2xl bg-surface-2 px-3 py-2"><div class="text-[11px] text-muted">Modal riil th 5, biasanya</div><div class="text-[15px] font-medium">{{ modalRiil(jalurPilih.tahun.at(-1)?.median) }}</div></div>
        <div class="rounded-2xl bg-surface-2 px-3 py-2"><div class="text-[11px] text-muted">Modal riil th 5, paling sial</div><div class="text-[15px] font-medium">{{ modalRiil(jalurPilih.tahun.at(-1)?.terburuk) }}</div></div>
        <div class="rounded-2xl bg-surface-2 px-3 py-2"><div class="text-[11px] text-muted">Penurunan terdalam</div><div class="text-[15px] font-medium text-turun">{{ prTanda(jalurPilih.dd_terdalam) }}</div></div>
        <div class="rounded-2xl bg-surface-2 px-3 py-2"><div class="text-[11px] text-muted">Penurunan biasanya</div><div class="text-[15px] font-medium">{{ prTanda(jalurPilih.dd_median) }}</div></div>
      </div>
      <p class="m-0 mt-3 text-[11px] text-muted">Penurunan = dari titik tertinggi modal riil dalam 5 tahun, sudah termasuk efek penarikan; SBN dinilai 100 karena dipegang sampai jatuh tempo.</p>
    </Panel>

    <section v-if="ada" class="panel">
      <details>
        <summary class="cursor-pointer list-none px-6 py-4 text-[15px] font-medium">Detail & keterbatasan <span class="text-xs font-normal text-muted">· % tanggal mulai yang modal riilnya utuh setelah 5 tahun</span></summary>
        <div class="overflow-x-auto pb-4">
          <table class="tabel min-w-[640px]">
            <thead><tr><th>Portofolio</th><th v-for="t in kolomTabel" :key="t" class="!text-right">Tarik {{ pr(t) }}/th</th><th class="!text-right">Rata-rata riil/th</th></tr></thead>
            <tbody>
              <tr v-for="p in patokan.portofolio" :key="p.kode">
                <td class="text-[13px]">{{ NAMA_OPSI[p.kode] ?? p.nama }}</td>
                <td v-for="x in p.tabel" :key="x.tarik" class="text-right tabular-nums" :class="kelasUtuh(x.riil5?.utuh)">{{ x.riil5 ? `${Math.round(x.riil5.utuh * 100)}%` : "–" }}</td>
                <td class="text-right tabular-nums">{{ prTanda(p.cagr_riil, 2) }}</td>
              </tr>
            </tbody>
          </table>
          <p class="m-0 px-6 pt-3 text-[11px] text-muted">Lolos = modal riil ≥ 100% di ≥ 80% tanggal mulai ({{ patokan.n_mulai_5 }} tanggal mulai, horizon 5 th) dan tidak pernah kehabisan dana cair. Pembanding JII memakai asumsi dividen {{ pr(patokan.dividen_jii) }}/th.</p>
        </div>
      </details>
    </section>

    <div v-if="ada" class="rounded-2xl bg-surface-2 px-5 py-4 text-[12px] leading-relaxed text-ink-2">
      <div>• Data {{ bulanTeks(patokan.periode.awal) }} – {{ bulanTeks(patokan.periode.akhir) }}: indikatif, bukan jaminan.</div>
      <div>• "Aman" = daya beli modal tidak turun (sudah memperhitungkan inflasi), bukan sekadar nominal tetap.</div>
      <div>• Kupon SBN di masa lalu lebih tinggi dari kupon sekarang, jadi opsi Dengan SBN bisa terlalu optimis.</div>
      <div>• Dana darurat dipisah, 100% di RD pasar uang syariah (tidak di SBN).</div>
    </div>
  </div>
</template>

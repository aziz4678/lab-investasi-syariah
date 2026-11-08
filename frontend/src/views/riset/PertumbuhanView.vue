<script setup>
import { ref, computed, watch, onMounted, inject } from "vue";
import { RefreshCw, Sprout, CalendarClock, Repeat, Scale, AlertTriangle, ChevronRight, ChevronDown, Globe, MapPin, Info } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { pakaiPekerjaan } from "@/composables/pekerjaan";
import { persen, rupiahRingkas } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import Segmen from "@/components/common/Segmen.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import Pemutar from "@/components/common/Pemutar.vue";
import Logo, { kunciMi } from "@/components/common/Logo.vue";
import PanelPekerjaan from "@/components/sistem/PanelPekerjaan.vue";
import TersediaDi from "@/components/produk/TersediaDi.vue";
import BatangSeri from "@/components/charts/BatangSeri.vue";

const dasar = ref(null);
const rencana = ref(null);
const siap = ref(false);
const memuat = ref(false);
const kerja = pakaiPekerjaan();
const pindahTab = inject("pindahTab");

const setoran = ref(1000000);
const modalAwal = ref(0);
const aplikasi = ref("semua");
const tahunHasil = ref("10");

const PILIHAN_APLIKASI = [["semua", "Semua"], ["bibit", "Bibit"], ["makmur", "Makmur"], ["ajaib", "Ajaib"]];
const PILIHAN_TAHUN = [["5", "5 tahun"], ["10", "10 tahun"]];
const KELAS_RISIKO = { Rendah: "bg-naik-bg text-naik", Sedang: "bg-kuning-bg text-kuning", Tinggi: "bg-turun-bg text-turun" };
const NAMA_PORTO = { "100% IDX": "100% Indonesia", "70/30": "70% Indonesia / 30% global", "50/50": "50/50 (halaman ini)", "100% global": "100% global" };
const NAMA_SUMBER_PENDEK = { indeks: "indeks", kategori: "rata-rata RD sejenis", keranjang: "keranjang produk" };

const muatDasar = async () => {
  dasar.value = await ambil("pertumbuhan").catch(() => null);
};
const muatRencana = async () => {
  memuat.value = true;
  const q = new URLSearchParams({ setoran: setoran.value || 0, modal_awal: modalAwal.value || 0, aplikasi: aplikasi.value });
  rencana.value = await ambil(`pertumbuhan/rencana?${q}`).catch(() => null);
  memuat.value = false;
  siap.value = true;
};
const muatSemua = async () => {
  await Promise.all([muatDasar(), muatRencana()]);
};
let jeda = null;
watch([setoran, modalAwal, aplikasi], () => {
  clearTimeout(jeda);
  jeda = setTimeout(muatRencana, 300);
});
onMounted(async () => {
  await muatSemua();
  await kerja.lanjutkan("pertumbuhan_hitung", muatSemua);
});
const hitungUlang = () => kerja.mulai("aksi/pertumbuhan_hitung", {}, muatSemua);

const bukaProduk = (id) => {
  pindahTab("reksadana", "katalog");
  history.replaceState(null, "", `#reksadana/katalog/${id}`);
};
const angka = (s) => Number(String(s).replace(/\D/g, "")) || 0;
const tampilRp = (v) => (v ? v.toLocaleString("id-ID") : "");
const bulanTeks = (s) => {
  if (!s) return "–";
  const [t, b] = String(s).slice(0, 7).split("-").map(Number);
  return new Date(t, b - 1, 1).toLocaleDateString("id-ID", { month: "long", year: "numeric" });
};
const bulanPendek = (s) => {
  if (!s) return "–";
  const [t, b] = String(s).slice(0, 7).split("-").map(Number);
  return new Date(t, b - 1, 1).toLocaleDateString("id-ID", { month: "short", year: "numeric" });
};
const tglTeks = (s) => (s ? new Date(s).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }) : "–");
const pr = (v, d = 1) => (v == null ? "–" : persen(v * 100, d, false));
const prTanda = (v, d = 1) => (v == null ? "–" : persen(v * 100, d, true));
const dariSeratus = (v) => (v == null ? "–" : Math.round(v * 100));

const ada = computed(() => rencana.value?.ada && dasar.value?.ada);
const r = computed(() => rencana.value);
const d = computed(() => dasar.value);
const hasil = computed(() => r.value?.rentang?.[tahunHasil.value] ?? null);
const teksSumber = (x) => (x ? `${x.sumber_teks}; ${x.n_mulai} tanggal mulai (${bulanPendek(x.mulai_awal)} – ${bulanPendek(x.mulai_akhir)})` : "");
const kalimatHasil = (x) => {
  if (!x) return "";
  const setorTeks = r.value.masukan.modal_awal > 0
    ? `modal awal ${rupiahRingkas(r.value.masukan.modal_awal)} lalu setor ${rupiahRingkas(r.value.masukan.setoran)} per bulan`
    : `setor ${rupiahRingkas(r.value.masukan.setoran)} per bulan`;
  return `Kalau dulu ${setorTeks} selama ${x.tahun} tahun (total ${rupiahRingkas(x.total)}), biasanya jadi ${rupiahRingkas(x.median)}; kondisi terburuk ${rupiahRingkas(x.terburuk)}; ${dariSeratus(x.untung)} dari 100 periode untung.`;
};
const kelasHasil = (nilai, total) => (nilai >= total ? "text-naik" : "text-turun");

const peringatan = computed(() => r.value?.peringatan ?? []);
const isiLokal = computed(() => r.value?.isi?.lokal ?? []);
const isiGlobal = computed(() => r.value?.isi?.global ?? []);
const beliMap = computed(() => Object.fromEntries((r.value?.beli ?? []).map((b) => [b.id, b.nilai])));
const nilaiBulanIni = (p) => beliMap.value[p.id] ?? 0;
const teksCakupan = computed(() => {
  const c = r.value?.cakupan;
  if (!c || !c.aplikasi.length) return null;
  return c.jenis === "satu" ? `Semua produk bisa dibeli di: ${c.aplikasi.join(", ")}` : `Butuh ${c.aplikasi.length} aplikasi: ${c.aplikasi.join(" + ")}`;
});
const minBeliTeks = (p) => {
  if (p.min_beli_nilai == null) return p.min_beli_mi || "tidak tercatat";
  if (p.min_beli_nilai === 0) return "tanpa batas";
  return p.min_beli_uang === "USD" ? `US$${p.min_beli_nilai.toLocaleString("id-ID")}` : rupiahRingkas(p.min_beli_nilai);
};

const jadwal = computed(() => {
  if (!r.value) return [];
  const daftar = [];
  const lk = isiLokal.value.length;
  const gl = isiGlobal.value.length;
  if (r.value.cara_setor === "rata") {
    const isi = [`${rupiahRingkas(r.value.bagian.lokal)} dibagi rata ke ${lk} RD saham Indonesia (${rupiahRingkas(lk ? r.value.bagian.lokal / lk : 0)} per produk).`];
    isi.push(gl ? `${rupiahRingkas(r.value.bagian.global)} ke ${isiGlobal.value[0].nama}.` : `${rupiahRingkas(r.value.bagian.global)} untuk porsi global belum ada produknya di aplikasi ini.`);
    isi.push("Paling praktis: pasang beli rutin otomatis (auto-debit) di aplikasinya, tanggal yang sama tiap bulan.");
    daftar.push({ ikon: Repeat, kapan: "Tiap bulan", judul: `Setor ${rupiahRingkas(r.value.masukan.setoran)}, dibagi rata`, isi });
  } else {
    const j = r.value.jadwal_setor ?? [];
    daftar.push({ ikon: Repeat, kapan: "Tiap bulan", judul: `Setor ${rupiahRingkas(r.value.masukan.setoran)} ke satu produk, bergiliran`, isi: [
      `Setoran per produk kalau dibagi rata kurang dari ${rupiahRingkas(r.value.setor_rata_min)}, jadi lebih praktis bergiliran. Produk global kebagian tiap 2 bulan supaya tetap separuh.`,
      ...j.slice(0, 6).map((x) => `${bulanTeks(x.bulan)}: ${x.nama}`)] });
  }
  const s = r.value.desember;
  if (s) {
    daftar.push({ ikon: Scale, kapan: "Tiap Desember", judul: "Kembalikan ke separuh-separuh", isi: [
      `Contoh dengan hasil ${s.tahun} (${s.sumber}): setelah setor ${rupiahRingkas(s.setoran_total)} setahun, bagian Indonesia ±${rupiahRingkas(s.lokal)} dan global ±${rupiahRingkas(s.global)}.`,
      `Jual ±${rupiahRingkas(s.pindah)} dari bagian ${s.dari === "lokal" ? "Indonesia" : "global"}, belikan ke bagian ${s.ke === "lokal" ? "Indonesia" : "global"}, supaya masing-masing ±${rupiahRingkas(s.target)}.`,
      "Atau lebih sederhana: tidak menjual, tapi setoran bulan-bulan berikutnya diarahkan ke bagian yang tertinggal sampai seimbang lagi."] });
  }
  daftar.push({ ikon: CalendarClock, kapan: "Tiap Januari", judul: "Cek isi keranjang", isi: ["Daftar produk dibentuk ulang otomatis di halaman ini (biaya, dana kelolaan, ketersediaan di aplikasi).", "Kalau ada yang berubah, setoran baru ikuti daftar belanja yang baru; produk lama tidak perlu dijual kecuali bubar."] });
  return daftar;
});

const DEKADE_LABEL = { "Jun 2001-2009": "2001–2009", "2010-2019": "2010–2019", "2020-Okt 2026": "2020–2026" };
const dekade = computed(() => {
  const i = d.value?.indeks;
  if (!i) return null;
  const kunci = Object.keys(i["50/50"].dekade);
  const bulat = (v) => Math.round(v * 1000) / 10;
  return {
    label: kunci.map((k) => DEKADE_LABEL[k] ?? k),
    seri: [
      { nama: "Indonesia", data: kunci.map((k) => bulat(i["100% IDX"].dekade[k])), warna: "--series-2" },
      { nama: "Global", data: kunci.map((k) => bulat(i["100% global"].dekade[k])), warna: "--series-4" },
      { nama: "Campuran 50/50", data: kunci.map((k) => bulat(i["50/50"].dekade[k])), warna: "--series-1" },
    ],
    baris: kunci.map((k) => ({ k: DEKADE_LABEL[k] ?? k, lk: i["100% IDX"].dekade[k], gl: i["100% global"].dekade[k], c: i["50/50"].dekade[k] })),
  };
});
const formatPersenTahun = (v) => `${v.toLocaleString("id-ID")}%`;
const turunCampuran = computed(() => d.value?.indeks?.["50/50"]?.dd);
const turunLokal = computed(() => d.value?.indeks?.["100% IDX"]?.dd);

const detailBuka = ref(false);
const KRITERIA_TEKS = { K1: "10 tahun terburuk 50/50 lebih baik dari 100% Indonesia", K2: "Hasil per risiko (CAGR ÷ |turun terdalam|) ≥ 100% Indonesia", K3: "CAGR tidak lebih rendah dari 100% Indonesia − 2 poin/th" };
const nilaiKriteria = (k, v) => (k === "K2" ? `${v[1].toFixed(2)} vs ${v[2].toFixed(2)}`.replaceAll(".", ",") : `${prTanda(v[1])} vs ${prTanda(v[2])}`);
const tabelSip = computed(() => {
  const s = d.value?.sip ?? {};
  const baris = [["keranjang", "Keranjang produk (50/50)"], ["kategori", "Rata-rata RD sejenis (50/50)"], ["kategori_lokal", "Rata-rata RD sejenis, 100% Indonesia"], ["kategori_global", "Rata-rata RD sejenis, 100% global"],
    ["indeks", "Indeks (50/50)"], ["indeks_lokal", "Indeks, 100% Indonesia"], ["indeks_global", "Indeks, 100% global"]];
  return baris.filter(([k]) => s[k]).map(([k, nama]) => ({ k, nama, lima: s[k]["5"], sepuluh: s[k]["10"] }));
});
const gugurGrup = computed(() => {
  const g = d.value?.keranjang?.gugur ?? [];
  return [["LK", "Indonesia"], ["GL", "Global"]].map(([w, nama]) => ({ w, nama, isi: g.filter((x) => x.wadah === w) }));
});
const isianPakai = computed(() => d.value?.isian?.[aplikasi.value] ?? d.value?.isian?.semua);
const perAplikasi = computed(() => d.value?.keranjang?.per_aplikasi ?? {});
const sumberPakai = (t) => NAMA_SUMBER_PENDEK[d.value?.pakai?.[aplikasi.value]?.[t]] ?? "–";
const lamaPulih = (x) => (x.pulih != null ? `${x.pulih} bln` : `belum (${x.sejak_puncak} bln)`);
</script>

<template>
  <div class="space-y-5">
    <Panel judul="Portofolio Pertumbuhan Syariah" ket="Separuh saham syariah Indonesia, separuh saham syariah global, dalam rupiah. Setor tiap bulan, seimbangkan tiap Desember.">
      <template #aksi>
        <span class="chip bg-kuning-bg text-kuning">Lolos uji setelah data diketahui · bukan jaminan</span>
        <span v-if="d?.ada" class="chip bg-surface-2 text-ink-2">Dihitung {{ tglTeks(d.dihitung) }} · data s/d {{ bulanTeks(d.periode.kategori[1]) }}</span>
        <button class="tombol" :disabled="kerja.sibuk.value" @click="hitungUlang"><RefreshCw class="h-3.5 w-3.5" :class="kerja.sibuk.value ? 'animate-spin' : ''" />Hitung ulang</button>
      </template>
      <PanelPekerjaan class="mb-4" :kerja="kerja.kerja.value" :galat="kerja.galat.value" />
      <div class="mb-6 rounded-2xl bg-aksen-lembut px-5 py-4">
        <div class="flex items-center gap-2 text-[15px] font-medium"><Sprout class="h-4 w-4 text-aksen" />Untuk siapa?</div>
        <ul class="m-0 mt-2 space-y-1.5 pl-4 text-[13px] leading-relaxed text-ink-2">
          <li><b class="font-medium text-ink">Tujuannya</b> uang tumbuh dalam jangka panjang dengan cara menabung rutin, bukan jual-beli cepat.</li>
          <li><b class="font-medium text-ink">Isinya</b> reksa dana saham syariah Indonesia dan reksa dana saham syariah global, masing-masing separuh.</li>
          <li><b class="font-medium text-ink">Syaratnya</b> uangnya tidak dipakai minimal 5 tahun dan siap melihat nilainya turun dalam di tengah jalan. Uang untuk kebutuhan dekat ada di <a href="#konservatif" class="text-aksen" @click.prevent="pindahTab('konservatif')">Portofolio Konservatif</a>.</li>
        </ul>
      </div>
      <div class="text-[13px] font-medium">1 · Isi data</div>
      <div class="mt-3 grid gap-4 sm:grid-cols-3">
        <div class="min-w-0">
          <label class="text-xs text-muted">Setoran per bulan</label>
          <div class="mt-1 flex items-center rounded-full bg-surface-2 px-4"><span class="text-[13px] text-muted">Rp</span>
            <input :value="tampilRp(setoran)" @input="(e) => (setoran = angka(e.target.value))" inputmode="numeric" class="h-10 w-full min-w-0 bg-transparent px-2 text-[15px] outline-none" /></div>
          <div class="mt-1 text-[11px] text-muted">{{ rupiahRingkas(setoran) }}</div>
        </div>
        <div class="min-w-0">
          <label class="text-xs text-muted">Modal awal <span class="text-muted">(opsional)</span></label>
          <div class="mt-1 flex items-center rounded-full bg-surface-2 px-4"><span class="text-[13px] text-muted">Rp</span>
            <input :value="tampilRp(modalAwal)" @input="(e) => (modalAwal = angka(e.target.value))" inputmode="numeric" placeholder="0" class="h-10 w-full min-w-0 bg-transparent px-2 text-[15px] outline-none" /></div>
          <div class="mt-1 text-[11px] text-muted">{{ modalAwal ? `${rupiahRingkas(modalAwal)}, dibeli sekali di awal` : "kosongkan kalau hanya setor bulanan" }}</div>
        </div>
        <div class="min-w-0">
          <div class="text-xs text-muted">Aplikasi yang aku pakai <span class="text-muted">(opsional)</span></div>
          <Segmen v-model="aplikasi" :pilihan="PILIHAN_APLIKASI" kecil class="mt-1.5" />
          <div class="mt-1 text-[11px] text-muted">{{ aplikasi === "semua" ? "produk dari semua tempat beli" : "hanya produk yang ditemukan di aplikasi ini" }}</div>
        </div>
      </div>
    </Panel>

    <Kerangka v-if="!siap" jenis="kartu" :n="2" kolom="grid-cols-1 md:grid-cols-2" />
    <Panel v-else-if="!ada" judul="Belum ada hasil hitungan"><p class="m-0 text-[13px] text-ink-2">Tekan "Hitung ulang" (±1 menit).</p></Panel>
    <template v-else>
      <section class="panel relative px-4 py-5 sm:px-6">
        <Pemutar v-if="memuat" class="absolute top-4 right-4" />
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="text-[13px] font-medium">2 · Hasilnya kalau dulu</div>
          <Segmen v-model="tahunHasil" :pilihan="PILIHAN_TAHUN" kecil />
        </div>
        <template v-if="hasil">
          <p class="m-0 mt-3 text-[16px] leading-relaxed font-medium">{{ kalimatHasil(hasil) }}</p>
          <div class="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-[11px] text-muted">Total disetor</div><div class="text-[18px] font-semibold tabular-nums">{{ rupiahRingkas(hasil.total) }}</div></div>
            <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-[11px] text-muted">Biasanya jadi</div><div class="text-[18px] font-semibold tabular-nums" :class="kelasHasil(hasil.median, hasil.total)">{{ rupiahRingkas(hasil.median) }}</div></div>
            <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-[11px] text-muted">Kondisi terburuk</div><div class="text-[18px] font-semibold tabular-nums" :class="kelasHasil(hasil.terburuk, hasil.total)">{{ rupiahRingkas(hasil.terburuk) }}</div><div class="text-[11px] text-muted">mulai {{ bulanPendek(hasil.mulai_terburuk) }}</div></div>
            <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-[11px] text-muted">Kondisi terbaik</div><div class="text-[18px] font-semibold tabular-nums" :class="kelasHasil(hasil.terbaik, hasil.total)">{{ rupiahRingkas(hasil.terbaik) }}</div><div class="text-[11px] text-muted">mulai {{ bulanPendek(hasil.mulai_terbaik) }}</div></div>
          </div>
          <p class="m-0 mt-3 text-[11px] leading-relaxed text-muted">Dari {{ teksSumber(hasil) }}. Angka yang ditampilkan memakai sumber yang hasilnya paling rendah, supaya tidak terlalu optimis. Hasil masa lalu, bukan janji.</p>
          <p v-if="tahunHasil === '10' && hasil.n_mulai < 12" class="m-0 mt-1 text-[11px] text-kuning">Data reksa dana global baru ada sejak 2016, jadi periode 10 tahun yang bisa dihitung masih sangat sedikit.</p>
        </template>
      </section>

      <section class="panel overflow-hidden px-4 py-5 sm:px-6">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="text-[13px] font-medium">3 · Daftar belanja bulan ini</div>
          <span v-if="teksCakupan" class="chip bg-surface-2 text-ink-2">{{ teksCakupan }}</span>
        </div>
        <div v-for="(w, i) in peringatan" :key="i" class="mt-3 flex items-start gap-2 rounded-2xl bg-kuning-bg px-4 py-3 text-[13px] text-kuning">
          <AlertTriangle class="mt-0.5 h-4 w-4 shrink-0" />
          <div class="min-w-0">
            <div class="font-medium">{{ w.teks }}</div>
            <div v-if="w.saran?.length" class="mt-0.5 text-[12px]">Aplikasi yang lengkap (Indonesia + global): {{ w.saran.join(", ") }}.</div>
            <ul v-if="w.calon?.length" class="m-0 mt-1 pl-4 text-[12px]"><li v-for="c in w.calon" :key="c.id">{{ c.nama }} · {{ c.alasan.join(", ") }}</li></ul>
          </div>
        </div>
        <div v-if="r.awal" class="mt-3 rounded-2xl bg-surface-2 px-4 py-3 text-[13px] text-ink-2">
          Modal awal {{ rupiahRingkas(r.awal.total) }}: {{ rupiahRingkas(r.awal.lokal_per_produk) }} ke tiap RD Indonesia<template v-if="isiGlobal.length"> dan {{ rupiahRingkas(r.awal.global_per_produk) }} ke RD global</template><template v-else>; porsi global {{ rupiahRingkas(r.awal.global_tanpa_produk) }} belum ada produknya di aplikasi ini</template>.
        </div>
        <div v-for="g in [{ k: 'lokal', judul: 'Saham syariah Indonesia', ikon: MapPin, isi: isiLokal, total: r.bagian.lokal }, { k: 'global', judul: 'Saham syariah global', ikon: Globe, isi: isiGlobal, total: r.bagian.global }]" :key="g.k" class="mt-4">
          <div class="flex items-center justify-between gap-3">
            <div class="flex items-center gap-2 text-[14px] font-medium"><component :is="g.ikon" class="h-4 w-4 text-muted" />{{ g.judul }} · separuh</div>
            <div class="shrink-0 text-[15px] font-semibold whitespace-nowrap tabular-nums">{{ rupiahRingkas(g.total) }}<span class="text-[11px] font-normal text-muted">/bulan</span></div>
          </div>
          <div class="mt-2 grid gap-3 md:grid-cols-3">
            <div v-for="p in g.isi" :key="p.id" class="flex flex-col rounded-2xl border border-garis p-4">
              <div class="flex items-start gap-3">
                <Logo jenis="mi" :kunci="kunciMi(p.mi)" :teks="p.mi" :ukuran="34" />
                <div class="min-w-0 flex-1">
                  <a :href="`#reksadana/katalog/${p.id}`" class="text-[13px] leading-snug font-medium text-ink hover:text-aksen" @click.prevent="bukaProduk(p.id)">{{ p.nama }}</a>
                  <div class="mt-0.5 text-[11px] text-muted">{{ g.k === "lokal" ? "Indonesia" : "Global" }} · {{ p.mata_uang === "USD" ? "Dolar AS" : "Rupiah" }}</div>
                </div>
              </div>
              <div class="mt-2 flex flex-wrap items-center gap-1.5">
                <span class="chip" :class="KELAS_RISIKO[p.risiko]" :title="p.risiko_sumber === 'resmi' ? `Tingkat risiko ${p.risiko_skala} dari skala 1–9 (detail produk)` : 'Data resmi tidak ada'">Risiko {{ p.risiko.toLowerCase() }}</span>
                <TersediaDi :platform="p.platform" kecil />
              </div>
              <div class="mt-2 text-[11px] text-muted">Minimal beli versi MI: {{ minBeliTeks(p) }}<span v-if="p.cek_aplikasi" class="chip ml-1 bg-kuning-bg text-kuning">cek di aplikasi</span></div>
              <p v-if="p.catatan" class="m-0 mt-2 flex items-start gap-1.5 text-[11px] leading-relaxed text-ink-2"><Info class="mt-0.5 h-3 w-3 shrink-0 text-aksen" />{{ p.catatan }}</p>
              <div class="mt-auto flex items-end justify-between pt-3">
                <div><div class="text-[11px] text-muted">Bulan ini</div><div class="text-[17px] font-semibold tabular-nums" :class="nilaiBulanIni(p) ? '' : 'text-muted'">{{ rupiahRingkas(nilaiBulanIni(p)) }}</div></div>
                <a :href="`#reksadana/katalog/${p.id}`" class="inline-flex items-center text-[11px] text-aksen" @click.prevent="bukaProduk(p.id)">Detail<ChevronRight class="h-3 w-3" /></a>
              </div>
            </div>
            <div v-if="!g.isi.length" class="rounded-2xl border border-dashed border-garis p-4 text-[12px] text-muted">Belum ada produk {{ g.k === "global" ? "global" : "Indonesia" }} yang lolos di aplikasi ini. Porsi {{ rupiahRingkas(g.total) }} jangan diisi produk lain diam-diam; lihat peringatan di atas.</div>
          </div>
        </div>
      </section>

      <section class="panel px-4 py-5 sm:px-6">
        <div class="text-[13px] font-medium">4 · Jadwal rutin</div>
        <ol class="m-0 mt-3 list-none space-y-3 p-0">
          <li v-for="j in jadwal" :key="j.kapan" class="flex items-start gap-3 rounded-2xl bg-surface-2 px-4 py-3">
            <span class="hidden h-9 w-9 shrink-0 place-items-center rounded-full bg-aksen-lembut text-aksen sm:grid"><component :is="j.ikon" class="h-4 w-4" /></span>
            <div class="min-w-0">
              <div class="text-[11px] text-muted">{{ j.kapan }}</div>
              <div class="text-[14px] font-medium">{{ j.judul }}</div>
              <ul class="m-0 mt-1 space-y-0.5 pl-4 text-[12px] leading-relaxed text-ink-2"><li v-for="(x, i) in j.isi" :key="i">{{ x }}</li></ul>
            </div>
          </li>
        </ol>
      </section>

      <section v-if="dekade" class="panel px-4 py-5 sm:px-6">
        <div class="text-[13px] font-medium">5 · Kenapa dicampur</div>
        <p class="m-0 mt-2 text-[14px] leading-relaxed">{{ d.dekade.teks }}</p>
        <p class="m-0 mt-1 text-[11px] text-muted">Sumber: {{ d.dekade.sumber }}. Rata-rata per tahun tiap dekade.</p>
        <div class="mt-4 grid gap-4 lg:grid-cols-[1fr_280px]">
          <BatangSeri :label="dekade.label" :seri="dekade.seri" legenda :format="formatPersenTahun" :tinggi="230" />
          <table class="w-full text-[12px]">
            <thead><tr class="text-left text-muted"><th class="pb-1 font-normal">Dekade</th><th class="pb-1 text-right font-normal">Indonesia</th><th class="pb-1 text-right font-normal">Global</th><th class="pb-1 text-right font-normal">50/50</th></tr></thead>
            <tbody>
              <tr v-for="b in dekade.baris" :key="b.k" class="border-t border-garis">
                <td class="py-1.5">{{ b.k }}</td>
                <td class="py-1.5 text-right tabular-nums" :class="b.lk < 0 ? 'text-turun' : 'text-naik'">{{ prTanda(b.lk) }}</td>
                <td class="py-1.5 text-right tabular-nums" :class="b.gl < 0 ? 'text-turun' : 'text-naik'">{{ prTanda(b.gl) }}</td>
                <td class="py-1.5 text-right font-medium tabular-nums" :class="b.c < 0 ? 'text-turun' : 'text-naik'">{{ prTanda(b.c) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="panel px-4 py-5 sm:px-6">
        <div class="text-[13px] font-medium">6 · Risiko</div>
        <ul class="m-0 mt-2 space-y-1.5 pl-4 text-[13px] leading-relaxed text-ink-2">
          <li><b class="font-medium text-ink">Bisa turun dalam.</b> Di data indeks, campuran 50/50 pernah turun {{ pr(Math.abs(turunCampuran ?? 0), 0) }} dari puncak (100% Indonesia {{ pr(Math.abs(turunLokal ?? 0), 0) }}). Semua produknya berisiko Tinggi.</li>
          <li><b class="font-medium text-ink">Banyak saham teknologi AS.</b> Bagian global didominasi segelintir perusahaan teknologi besar Amerika.</li>
          <li><b class="font-medium text-ink">Kurs bisa naik atau turun.</b> Rupiah yang melemah selama ini ikut menambah hasil global; kalau rupiah menguat, hasilnya berkurang.</li>
          <li><b class="font-medium text-ink">Biaya RD global lebih mahal</b>, sekitar 2% per tahun, ditambah selisih kurs saat beli dan jual.</li>
          <li><b class="font-medium text-ink">Bukan jaminan.</b> Cara ini lolos uji yang disusun setelah gambaran data masa lalu sudah diketahui, jadi masih harus dibuktikan ke depan (pemantauan mulai Januari 2027).</li>
          <li><b class="font-medium text-ink">Uang yang dipakai kurang dari 5 tahun lagi jangan di sini.</b> Taruh di <a href="#konservatif" class="text-aksen" @click.prevent="pindahTab('konservatif')">Portofolio Konservatif</a>.</li>
        </ul>
      </section>

      <section class="panel overflow-hidden">
        <button class="flex w-full items-center justify-between gap-3 px-4 py-4 text-left sm:px-6" @click="detailBuka = !detailBuka">
          <span class="text-[13px] font-medium">Detail untuk yang penasaran</span>
          <ChevronDown class="h-4 w-4 text-muted transition" :class="detailBuka ? 'rotate-180' : ''" />
        </button>
        <div v-if="detailBuka" class="space-y-6 border-t border-garis px-4 py-5 text-[12px] sm:px-6">
          <div>
            <div class="text-[13px] font-medium">Hasil uji H35 (indeks, Jun 2001 – Okt 2026, rupiah)</div>
            <div class="mt-2 overflow-x-auto">
              <table class="w-full min-w-[560px]">
                <thead><tr class="text-left text-muted"><th class="pb-1 font-normal">Portofolio</th><th class="pb-1 text-right font-normal">CAGR</th><th class="pb-1 text-right font-normal">Turun terdalam</th><th class="pb-1 text-right font-normal">Pulih</th><th class="pb-1 text-right font-normal">MAR</th><th class="pb-1 text-right font-normal">10 th terburuk</th><th class="pb-1 text-right font-normal">10 th terbaik</th><th class="pb-1 text-right font-normal">% 10 th &gt; IDX</th></tr></thead>
                <tbody>
                  <tr v-for="(x, k) in d.indeks" :key="k" class="border-t border-garis" :class="k === '50/50' ? 'font-medium' : ''">
                    <td class="py-1.5">{{ NAMA_PORTO[k] ?? k }}</td><td class="py-1.5 text-right tabular-nums">{{ prTanda(x.cagr) }}</td><td class="py-1.5 text-right tabular-nums text-turun">{{ prTanda(x.dd) }}</td>
                    <td class="py-1.5 text-right">{{ lamaPulih(x) }}</td><td class="py-1.5 text-right tabular-nums">{{ x.mar?.toFixed(2).replace(".", ",") }}</td>
                    <td class="py-1.5 text-right tabular-nums">{{ prTanda(x.j_buruk) }}</td><td class="py-1.5 text-right tabular-nums">{{ prTanda(x.j_baik) }}</td><td class="py-1.5 text-right">{{ k === "100% IDX" ? "–" : `${Math.round(x.j_menang * 100)}%` }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <ul class="m-0 mt-3 space-y-1 pl-4 text-ink-2">
              <li v-for="(v, k) in d.kriteria" :key="k">{{ k }} · {{ KRITERIA_TEKS[k] }}: {{ nilaiKriteria(k, v) }} <b :class="v[0] ? 'text-naik' : 'text-turun'">{{ v[0] ? "lulus" : "gagal" }}</b></li>
              <li>K4 · K1–K3 tetap lulus dengan asumsi pesimis (dividen JII 0%, global 1%, DJIM US sebelum 2008): <b :class="d.k4 ? 'text-naik' : 'text-turun'">{{ d.k4 ? "lulus" : "gagal" }}</b></li>
              <li>Pecahan hasil global seluruh periode: {{ prTanda(d.pecah.Penuh.usd) }}/th dalam dolar + {{ prTanda(d.pecah.Penuh.kurs) }}/th dari kurs = {{ prTanda(d.pecah.Penuh.rupiah) }}/th dalam rupiah.</li>
              <li>Status: lolos pasca hasil (arah umum data sudah diketahui sebelum uji). Wajib uji maju mulai Jan 2027 sebelum dipakai untuk porsi besar. <a href="#hipotesis/H35" class="text-aksen" @click.prevent="pindahTab('hipotesis', 'H35')">Buka H35</a></li>
            </ul>
          </div>
          <div>
            <div class="text-[13px] font-medium">Setor {{ rupiahRingkas(d.setoran_contoh) }}/bulan per sumber (median · terburuk · % periode untung)</div>
            <div class="mt-2 overflow-x-auto">
              <table class="w-full min-w-[560px]">
                <thead><tr class="text-left text-muted"><th class="pb-1 font-normal">Sumber</th><th class="pb-1 text-right font-normal">5 tahun</th><th class="pb-1 text-right font-normal">10 tahun</th></tr></thead>
                <tbody>
                  <tr v-for="b in tabelSip" :key="b.k" class="border-t border-garis">
                    <td class="py-1.5">{{ b.nama }}</td>
                    <td class="py-1.5 text-right tabular-nums">{{ b.lima ? `${rupiahRingkas(b.lima.median)} · ${rupiahRingkas(b.lima.terburuk)} · ${Math.round(b.lima.untung * 100)}% (${b.lima.n_mulai})` : "–" }}</td>
                    <td class="py-1.5 text-right tabular-nums">{{ b.sepuluh ? `${rupiahRingkas(b.sepuluh.median)} · ${rupiahRingkas(b.sepuluh.terburuk)} · ${Math.round(b.sepuluh.untung * 100)}% (${b.sepuluh.n_mulai})` : "–" }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p class="m-0 mt-2 text-muted">Angka dalam kurung = jumlah tanggal mulai. Yang dipakai di atas (paling rendah): 5 tahun = {{ sumberPakai("5") }}, 10 tahun = {{ sumberPakai("10") }}. Total setor 5 th {{ rupiahRingkas(d.setoran_contoh * 60) }}, 10 th {{ rupiahRingkas(d.setoran_contoh * 120) }}.</p>
            <p v-if="isianPakai" class="m-0 mt-1 text-muted">Bulan sebelum produk ada diisi rata-rata RD sejenis: Indonesia {{ pr(isianPakai.LK.isian) }}, global {{ pr(isianPakai.GL.isian) }} dari bulan sejak Jul 2016.</p>
          </div>
          <div>
            <div class="text-[13px] font-medium">Produk yang lolos per aplikasi (Indonesia / global)</div>
            <div class="mt-2 flex flex-wrap gap-2">
              <span v-for="(v, k) in perAplikasi" :key="k" class="chip bg-surface-2 text-ink-2">{{ k === "semua" ? "Semua" : k[0].toUpperCase() + k.slice(1) }}: {{ v.LK }} / {{ v.GL_disetujui }}</span>
            </div>
          </div>
          <div>
            <div class="text-[13px] font-medium">Produk yang tidak dipakai & alasannya</div>
            <div class="mt-2 grid gap-4 lg:grid-cols-2">
              <div v-for="g in gugurGrup" :key="g.w">
                <div class="text-muted">{{ g.nama }} ({{ g.isi.length }})</div>
                <ul class="m-0 mt-1 max-h-[260px] list-none space-y-1 overflow-y-auto p-0">
                  <li v-for="x in g.isi" :key="x.id" class="rounded-lg bg-surface-2 px-3 py-1.5"><span class="text-ink">{{ x.nama }}</span> <span class="text-muted">· {{ x.alasan.join(", ") }}</span></li>
                </ul>
              </div>
            </div>
          </div>
          <div>
            <div class="text-[13px] font-medium">Keterbatasan</div>
            <ul class="m-0 mt-1 space-y-1 pl-4 text-ink-2">
              <li>Data reksa dana global baru ada sejak 2016 (periode yang menguntungkan global); angka 10 tahun dari produk hanya beberapa tanggal mulai.</li>
              <li>Jalur indeks memakai asumsi dividen (JII 2,5%/th, global 1,8%/th sebelum 2008) dan biaya indeks, bukan biaya RD nyata.</li>
              <li>Minimal beli diambil dari data manajer investasi; di aplikasi bisa jauh lebih kecil. Ketersediaan di aplikasi dari katalog publiknya dan bisa berubah.</li>
              <li>Hanya dari NAV bulanan OJK (rupiah = NAB ÷ unit, kurs OJK). Biaya RD sudah di NAV; biaya kurs bank saat beli/jual RD dolar tidak dihitung.</li>
            </ul>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

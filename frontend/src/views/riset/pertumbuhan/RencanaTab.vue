<script setup>
import { computed, inject } from "vue";
import { CalendarClock, Repeat, Scale, AlertTriangle, ChevronRight, Globe, MapPin, Info, ShieldAlert } from "lucide-vue-next";
import { rupiahRingkas } from "@/utils/format";
import Segmen from "@/components/common/Segmen.vue";
import Pemutar from "@/components/common/Pemutar.vue";
import Logo, { kunciMi } from "@/components/common/Logo.vue";
import TersediaDi from "@/components/produk/TersediaDi.vue";
import { pr, prAngka, kelasTanda, dariSeratus, bulanTeks, bulanPendek, KELAS_RISIKO, NAMA_SUMBER } from "@/views/riset/pertumbuhan/bantu";

const props = defineProps({ r: Object, d: Object, memuat: Boolean });
const emit = defineEmits(["sub"]);
const setoran = defineModel("setoran", { type: Number });
const modalAwal = defineModel("modalAwal", { type: Number });
const aplikasi = defineModel("aplikasi", { type: String });
const pindahTab = inject("pindahTab");

const PILIHAN_APLIKASI = [["semua", "Semua"], ["bibit", "Bibit"], ["makmur", "Makmur"], ["ajaib", "Ajaib"]];
const angka = (s) => Number(String(s).replace(/\D/g, "")) || 0;
const tampilRp = (v) => (v ? v.toLocaleString("id-ID") : "");
const bukaProduk = (id) => {
  pindahTab("reksadana", "katalog");
  history.replaceState(null, "", `#reksadana/katalog/${id}`);
};

const hasil = computed(() => ["5", "10"].map((t) => props.r?.rentang?.[t]).filter(Boolean));
const kalimat = (x) => {
  const m = props.r.masukan;
  const setor = m.modal_awal > 0 ? `modal awal ${rupiahRingkas(m.modal_awal)} lalu setor ${rupiahRingkas(m.setoran)}/bulan` : `setor ${rupiahRingkas(m.setoran)}/bulan`;
  return `Kalau dulu ${setor} selama ${x.tahun} tahun, biasanya jadi ${rupiahRingkas(x.median)}.`;
};
const kelasHasil = (nilai, total) => (nilai >= total ? "text-naik" : "text-turun");

const peringatan = computed(() => props.r?.peringatan ?? []);
const isiLokal = computed(() => props.r?.isi?.lokal ?? []);
const isiGlobal = computed(() => props.r?.isi?.global ?? []);
const beliMap = computed(() => Object.fromEntries((props.r?.beli ?? []).map((b) => [b.id, b.nilai])));
const nilaiBulanIni = (p) => beliMap.value[p.id] ?? 0;
const grup = computed(() => [
  { k: "lokal", judul: "Saham syariah Indonesia", ikon: MapPin, isi: isiLokal.value, total: props.r.bagian.lokal },
  { k: "global", judul: "Saham syariah global", ikon: Globe, isi: isiGlobal.value, total: props.r.bagian.global },
]);
const teksCakupan = computed(() => {
  const c = props.r?.cakupan;
  if (!c || !c.aplikasi.length) return null;
  return c.jenis === "satu" ? `Semua produk bisa dibeli di: ${c.aplikasi.join(", ")}` : `Butuh ${c.aplikasi.length} aplikasi: ${c.aplikasi.join(" + ")}`;
});
const minBeliTeks = (p) => {
  if (p.min_beli_nilai == null) return p.min_beli_mi || "tidak tercatat";
  if (p.min_beli_nilai === 0) return "tanpa batas";
  return p.min_beli_uang === "USD" ? `US$${p.min_beli_nilai.toLocaleString("id-ID")}` : rupiahRingkas(p.min_beli_nilai);
};

const jadwal = computed(() => {
  const r = props.r;
  const daftar = [];
  const lk = isiLokal.value.length;
  if (r.cara_setor === "rata") {
    daftar.push({ ikon: Repeat, kapan: "Tiap bulan", judul: `Setor ${rupiahRingkas(r.masukan.setoran)}, dibagi rata`, isi: [
      `${rupiahRingkas(r.bagian.lokal)} dibagi rata ke ${lk} RD saham Indonesia (${rupiahRingkas(lk ? r.bagian.lokal / lk : 0)} per produk).`,
      isiGlobal.value.length ? `${rupiahRingkas(r.bagian.global)} ke ${isiGlobal.value[0].nama}.` : `${rupiahRingkas(r.bagian.global)} untuk porsi global: belum ada produknya di aplikasi ini (lihat peringatan).`,
      "Paling praktis: pasang beli rutin otomatis (auto-debit) di aplikasinya, tanggal yang sama tiap bulan."] });
  } else {
    daftar.push({ ikon: Repeat, kapan: "Tiap bulan", judul: `Setor ${rupiahRingkas(r.masukan.setoran)} ke satu produk, bergiliran`, isi: [
      `Kalau dibagi rata, tiap produk dapat kurang dari ${rupiahRingkas(r.setor_rata_min)}, jadi lebih praktis bergiliran. Produk global kebagian tiap 2 bulan supaya tetap separuh.`,
      ...(r.jadwal_setor ?? []).map((x) => `${bulanTeks(x.bulan)}: ${x.nama}`)] });
  }
  const s = r.desember;
  if (s) {
    daftar.push({ ikon: Scale, kapan: "Tiap Desember", judul: "Kembalikan ke separuh-separuh", isi: [
      `Contoh dengan hasil ${s.tahun} (${s.sumber}): setelah setor ${rupiahRingkas(s.setoran_total)} setahun, bagian Indonesia ±${rupiahRingkas(s.lokal)} dan global ±${rupiahRingkas(s.global)}.`,
      `Jual ±${rupiahRingkas(s.pindah)} dari bagian ${s.dari === "lokal" ? "Indonesia" : "global"}, belikan ke bagian ${s.ke === "lokal" ? "Indonesia" : "global"}, supaya masing-masing ±${rupiahRingkas(s.target)}.`,
      "Cara lain tanpa menjual: setoran bulan-bulan berikutnya diarahkan ke bagian yang tertinggal sampai seimbang lagi."] });
  }
  daftar.push({ ikon: CalendarClock, kapan: "Tiap Januari", judul: "Cek isi keranjang", isi: ["Daftar produk dibentuk ulang otomatis di halaman ini (biaya, dana kelolaan, ketersediaan di aplikasi).", "Kalau ada yang berubah, setoran baru ikuti daftar belanja yang baru; produk lama tidak perlu dijual kecuali bubar."] });
  return daftar;
});
const ddCampuran = computed(() => props.d?.indeks?.["50/50"]?.dd);
const ddLokal = computed(() => props.d?.indeks?.["100% IDX"]?.dd);
</script>

<template>
  <div class="space-y-5">
    <section class="panel px-4 py-5 sm:px-6">
      <div class="text-[14px] font-medium">1 · Isi data</div>
      <p class="m-0 mt-1 text-[12px] text-muted">Semua angka di halaman ini menyesuaikan isian ini.</p>
      <div class="mt-3 grid gap-4 sm:grid-cols-3">
        <div class="min-w-0">
          <label class="text-xs text-muted">Setoran per bulan</label>
          <div class="mt-1 flex items-center rounded-full bg-surface-2 px-4"><span class="text-[13px] text-muted">Rp</span>
            <input :value="tampilRp(setoran)" @input="(e) => (setoran = angka(e.target.value))" inputmode="numeric" class="h-10 w-full min-w-0 bg-transparent px-2 text-[15px] outline-none" /></div>
          <div class="mt-1 text-[11px] text-muted">{{ rupiahRingkas(setoran) }} per bulan</div>
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
    </section>

    <section class="panel relative px-4 py-5 sm:px-6">
      <Pemutar v-if="memuat" class="absolute top-4 right-4" />
      <div class="text-[14px] font-medium">2 · Hasilnya kalau dulu dilakukan</div>
      <p class="m-0 mt-1 text-[12px] text-muted">Dihitung untuk setiap bulan mulai yang mungkin di masa lalu, lalu diringkas. Angka yang dipakai selalu dari sumber yang hasilnya paling rendah, supaya tidak terlalu optimis.</p>
      <div class="mt-4 grid gap-4 lg:grid-cols-2">
        <div v-for="x in hasil" :key="x.tahun" class="rounded-2xl border border-garis p-4">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div class="text-[15px] font-semibold">{{ x.tahun }} tahun</div>
            <span class="chip bg-surface-2 text-ink-2">{{ dariSeratus(x.untung) }} dari 100 periode untung</span>
          </div>
          <p class="m-0 mt-2 text-[14px] leading-relaxed">{{ kalimat(x) }}</p>
          <div class="mt-3 grid grid-cols-2 gap-2">
            <div class="rounded-xl bg-surface-2 px-3 py-2"><div class="text-[11px] text-muted">Total disetor</div><div class="text-[17px] font-semibold tabular-nums">{{ rupiahRingkas(x.total) }}</div></div>
            <div class="rounded-xl bg-surface-2 px-3 py-2"><div class="text-[11px] text-muted">Biasanya jadi</div><div class="text-[17px] font-semibold tabular-nums" :class="kelasHasil(x.median, x.total)">{{ rupiahRingkas(x.median) }}</div></div>
            <div class="rounded-xl bg-surface-2 px-3 py-2"><div class="text-[11px] text-muted">Paling sial</div><div class="text-[17px] font-semibold tabular-nums" :class="kelasHasil(x.terburuk, x.total)">{{ rupiahRingkas(x.terburuk) }}</div><div class="text-[11px] text-muted">kalau mulai {{ bulanPendek(x.mulai_terburuk) }}</div></div>
            <div class="rounded-xl bg-surface-2 px-3 py-2"><div class="text-[11px] text-muted">Paling beruntung</div><div class="text-[17px] font-semibold tabular-nums" :class="kelasHasil(x.terbaik, x.total)">{{ rupiahRingkas(x.terbaik) }}</div><div class="text-[11px] text-muted">kalau mulai {{ bulanPendek(x.mulai_terbaik) }}</div></div>
          </div>
          <p class="m-0 mt-3 text-[11px] leading-relaxed text-muted">Sumber: {{ NAMA_SUMBER[x.sumber] }} · {{ x.n_mulai }} bulan mulai ({{ bulanPendek(x.mulai_awal) }} – {{ bulanPendek(x.mulai_akhir) }}).</p>
          <p v-if="x.n_mulai < 12" class="m-0 mt-1 text-[11px] text-kuning">Data reksa dana global baru ada sejak 2016, jadi periode {{ x.tahun }} tahun yang bisa dihitung masih sangat sedikit.</p>
        </div>
      </div>
      <button class="mt-3 inline-flex items-center text-[12px] text-aksen" @click="emit('sub', 'historis')">Lihat grafik & data historis lengkap<ChevronRight class="h-3.5 w-3.5" /></button>
    </section>

    <section class="panel overflow-hidden px-4 py-5 sm:px-6">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="text-[14px] font-medium">3 · Daftar belanja bulan ini</div>
        <span v-if="teksCakupan" class="chip bg-aksen-lembut text-aksen">{{ teksCakupan }}</span>
      </div>
      <p class="m-0 mt-1 text-[12px] text-muted">Produk dipilih dengan aturan tetap (biaya termurah di antara yang cukup besar dan tersedia di aplikasi), bukan dari hasil terbaik.</p>
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
      <div v-for="g in grup" :key="g.k" class="mt-5">
        <div class="flex items-center justify-between gap-3">
          <div class="flex min-w-0 items-center gap-2 text-[14px] font-medium"><component :is="g.ikon" class="h-4 w-4 shrink-0 text-muted" />{{ g.judul }} · separuh</div>
          <div class="shrink-0 text-[15px] font-semibold whitespace-nowrap tabular-nums">{{ rupiahRingkas(g.total) }}<span class="text-[11px] font-normal text-muted">/bulan</span></div>
        </div>
        <div class="mt-2 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          <div v-for="p in g.isi" :key="p.id" class="flex flex-col rounded-2xl border border-garis p-4">
            <div class="flex items-start gap-3">
              <Logo jenis="mi" :kunci="kunciMi(p.mi)" :teks="p.mi" :ukuran="34" />
              <div class="min-w-0 flex-1">
                <a :href="`#reksadana/katalog/${p.id}`" class="text-[13px] leading-snug font-medium text-ink hover:text-aksen" @click.prevent="bukaProduk(p.id)">{{ p.nama }}</a>
                <div class="mt-0.5 text-[11px] text-muted">{{ p.mi }} · {{ g.k === "lokal" ? "Indonesia" : "Global" }} · {{ p.mata_uang === "USD" ? "Dolar AS" : "Rupiah" }}</div>
              </div>
            </div>
            <div class="mt-2 flex flex-wrap items-center gap-1.5">
              <span class="chip" :class="KELAS_RISIKO[p.risiko]" :title="p.risiko_sumber === 'resmi' ? `Tingkat risiko ${p.risiko_skala} dari skala 1–9 (detail produk)` : 'Data resmi tidak ada'">Risiko {{ p.risiko.toLowerCase() }}</span>
              <TersediaDi :platform="p.platform" kecil />
            </div>
            <div v-if="p.kinerja" class="mt-3 grid grid-cols-3 gap-1.5 text-center">
              <div class="rounded-lg bg-surface-2 px-1 py-1.5"><div class="text-[10px] text-muted">1 tahun</div><div class="text-[12px] font-medium tabular-nums" :class="kelasTanda(p.kinerja.ret_1th)">{{ prAngka(p.kinerja.ret_1th) }}</div></div>
              <div class="rounded-lg bg-surface-2 px-1 py-1.5"><div class="text-[10px] text-muted">5 th, per tahun</div><div class="text-[12px] font-medium tabular-nums" :class="kelasTanda(p.kinerja.cagr_5)">{{ prAngka(p.kinerja.cagr_5) }}</div></div>
              <div class="rounded-lg bg-surface-2 px-1 py-1.5"><div class="text-[10px] text-muted">Turun terburuk</div><div class="text-[12px] font-medium tabular-nums text-turun">{{ prAngka(p.kinerja.turun_terburuk) }}</div></div>
            </div>
            <div class="mt-2 text-[11px] text-muted">Biaya ±{{ p.biaya?.toLocaleString("id-ID", { maximumFractionDigits: 2 }) }}%/th · riwayat {{ Math.floor(p.tahun_data ?? 0) }} th · dalam rupiah</div>
            <div class="mt-1 text-[11px] text-muted">Minimal beli versi MI: {{ minBeliTeks(p) }}<span v-if="p.cek_aplikasi" class="chip ml-1 bg-kuning-bg text-kuning">cek di aplikasi</span></div>
            <p v-if="p.catatan" class="m-0 mt-2 flex items-start gap-1.5 text-[11px] leading-relaxed text-ink-2"><Info class="mt-0.5 h-3 w-3 shrink-0 text-aksen" />{{ p.catatan }}</p>
            <div class="mt-auto flex items-end justify-between pt-3">
              <div><div class="text-[11px] text-muted">Beli bulan ini</div><div class="text-[17px] font-semibold tabular-nums" :class="nilaiBulanIni(p) ? '' : 'text-muted'">{{ rupiahRingkas(nilaiBulanIni(p)) }}</div></div>
              <a :href="`#reksadana/katalog/${p.id}`" class="inline-flex items-center text-[11px] text-aksen" @click.prevent="bukaProduk(p.id)">Detail produk<ChevronRight class="h-3 w-3" /></a>
            </div>
          </div>
          <div v-if="!g.isi.length" class="rounded-2xl border border-dashed border-garis p-4 text-[12px] text-muted">Belum ada produk {{ g.k === "global" ? "global" : "Indonesia" }} yang lolos di aplikasi ini. Porsi {{ rupiahRingkas(g.total) }} jangan diisi produk lain diam-diam; lihat peringatan di atas.</div>
        </div>
      </div>
      <p class="m-0 mt-3 text-[11px] text-muted">Angka kinerja = hasil masa lalu tiap produk dalam rupiah (sumber data reksa dana), hanya untuk gambaran, bukan alasan memilih.</p>
    </section>

    <section class="panel px-4 py-5 sm:px-6">
      <div class="text-[14px] font-medium">4 · Jadwal rutin</div>
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

    <section class="panel px-4 py-5 sm:px-6">
      <div class="flex items-center gap-2 text-[14px] font-medium"><ShieldAlert class="h-4 w-4 text-turun" />5 · Risiko yang perlu diterima</div>
      <ul class="m-0 mt-2 space-y-1.5 pl-4 text-[13px] leading-relaxed text-ink-2">
        <li><b class="font-medium text-ink">Bisa turun dalam.</b> Di data indeks, campuran 50/50 pernah turun {{ pr(Math.abs(ddCampuran ?? 0), 0) }} dari puncak (100% Indonesia {{ pr(Math.abs(ddLokal ?? 0), 0) }}). Semua produknya berisiko tinggi.</li>
        <li><b class="font-medium text-ink">Banyak saham teknologi AS.</b> Bagian global didominasi segelintir perusahaan teknologi besar Amerika.</li>
        <li><b class="font-medium text-ink">Kurs bisa naik atau turun.</b> Rupiah yang melemah selama ini ikut menambah hasil global; kalau rupiah menguat, hasilnya berkurang.</li>
        <li><b class="font-medium text-ink">Biaya RD global lebih mahal</b>, sekitar 2% per tahun, ditambah selisih kurs saat beli dan jual.</li>
        <li><b class="font-medium text-ink">Bukan jaminan.</b> Cara ini lolos uji yang disusun setelah gambaran data masa lalu sudah diketahui, jadi masih harus dibuktikan ke depan (pemantauan mulai Januari 2027).</li>
        <li><b class="font-medium text-ink">Uang yang dipakai kurang dari 5 tahun lagi jangan di sini.</b> Taruh di <a href="#konservatif" class="text-aksen" @click.prevent="pindahTab('konservatif')">Portofolio Konservatif</a>.</li>
      </ul>
    </section>
  </div>
</template>

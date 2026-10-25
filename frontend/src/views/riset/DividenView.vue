<script setup>
import { ref, computed, onMounted } from "vue";
import { Search, ArrowUpDown } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { persen, rupiah, kelasPersen } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import Stats from "@/components/common/Stats.vue";
import Segmen from "@/components/common/Segmen.vue";
import KodeSaham from "@/components/common/KodeSaham.vue";
import KalkulatorDividen from "@/components/dividen/KalkulatorDividen.vue";
import HeaderStrategi from "@/components/common/HeaderStrategi.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import Pemutar from "@/components/common/Pemutar.vue";

const props = defineProps({ sub: String });
const emit = defineEmits(["sub"]);
const SUB = [["daftar", "Daftar & kalender"], ["kalkulator", "Kalkulator"], ["uji", "Hasil uji"], ["trap", "Dividend trap"], ["aturan", "Aturan"]];
const BULAN = ["", "Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];

const daftar = ref(null);
const ringkas = ref(null);
const jadwal = ref(null);
const semuaJadwal = ref(false);
const filter = ref("konsisten");
const sektor = ref("");
const cari = ref("");
const urut = ref({ kolom: "yield", turun: true });
const semua = ref(false);

onMounted(async () => {
  ambil("dividen/jadwal").then((x) => (jadwal.value = x)).catch(() => (jadwal.value = {}));
  ambil("dividen/ringkasan").then((x) => (ringkas.value = x)).catch(() => (ringkas.value = {}));
  daftar.value = await ambil("dividen/daftar").catch(() => ({ data: [] }));
});

const data = computed(() => daftar.value?.data || []);
const tandaKet = computed(() => daftar.value?.tanda || {});
const daftarSektor = computed(() => [...new Set(data.value.map((x) => x.sektor).filter(Boolean))].sort());
const FILTER = [["semua", "Semua"], ["konsisten", "Bayar ≥ 3 th berturut"], ["aman", "Tanpa tanda bahaya"], ["tinggi", "Yield ≥ 6%"]];

const stat = computed(() => {
  const x = data.value.filter((s) => s.dps12 > 0);
  const med = (a) => (a.length ? [...a].sort((p, q) => p - q)[Math.floor(a.length / 2)] : null);
  return [
    { label: "Saham bayar dividen", nilai: String(x.length), ket: "12 bulan terakhir · syariah likuid" },
    { label: "Yield median", nilai: persen(med(x.map((s) => s.yield)), 1, false), ket: "sebelum pajak 10%" },
    { label: "Konsisten ≥ 5 tahun", nilai: String(data.value.filter((s) => s.beruntun >= 5).length), ket: "bayar tiap tahun" },
    { label: "Yield ≥ 6%", nilai: String(x.filter((s) => s.yield >= 6).length), ket: "rawan trap 65% historis" },
    { label: "Tanpa tanda bahaya", nilai: String(x.filter((s) => !s.tanda.length).length), ket: "lolos semua cek trap" },
  ];
});

const nilaiUrut = (s, k) => (k === "tanda" ? s.tanda.length : k === "trap" ? s.trap?.trap ?? -1 : s[k] ?? (typeof s[k] === "string" ? "" : -Infinity));
const tersaring = computed(() => {
  const q = cari.value.trim().toUpperCase();
  let x = data.value.filter((s) => s.dps12 > 0
    && (filter.value === "semua" || (filter.value === "konsisten" && s.beruntun >= 3) || (filter.value === "aman" && !s.tanda.length) || (filter.value === "tinggi" && s.yield >= 6))
    && (!sektor.value || s.sektor === sektor.value) && (!q || s.kode.includes(q) || (s.nama || "").toUpperCase().includes(q)));
  const { kolom, turun } = urut.value;
  x = [...x].sort((a, b) => {
    const va = nilaiUrut(a, kolom), vb = nilaiUrut(b, kolom);
    const c = typeof va === "string" ? va.localeCompare(vb) : va - vb;
    return turun ? -c : c;
  });
  return x;
});
const tampil = computed(() => (semua.value ? tersaring.value : tersaring.value.slice(0, 50)));
function ganti(k) {
  urut.value = urut.value.kolom === k ? { kolom: k, turun: !urut.value.turun } : { kolom: k, turun: k !== "kode" };
}

const kalender = computed(() => {
  const per = Array.from({ length: 13 }, () => []);
  for (const s of data.value.filter((x) => x.beruntun >= 3)) for (const b of s.bulan) per[b].push(s);
  const maks = Math.max(1, ...per.map((x) => x.length));
  return per.slice(1).map((x, i) => ({ bulan: BULAN[i + 1], n: x.length, persen: (x.length / maks) * 100, contoh: [...x].sort((a, b) => b.yield - a.yield).slice(0, 4).map((s) => s.kode) }));
});

function batang(s) {
  const e = Object.entries(s.dps_tahun);
  return e.map(([t, v], i) => {
    const lalu = i ? e[i - 1][1] : null;
    const berjalan = i === e.length - 1;
    const turun = lalu != null && v < lalu;
    const kelas = v <= 0 ? "bg-surface-3" : berjalan && turun ? "bg-muted" : turun ? "bg-turun" : "bg-naik";
    const ket = lalu > 0 ? ` (${v >= lalu ? "+" : ""}${Math.round((v / lalu - 1) * 100)}%)` : "";
    return { t, v, kelas, berjalan, judul: `${t}${berjalan ? " (berjalan)" : ""}: Rp${rupiah(v)}${ket}` };
  });
}

function maxDps(s) {
  return Math.max(1, ...Object.values(s.dps_tahun));
}

const UJI = computed(() => [
  ["H17a 2014–2019 (data latihan)", ringkas.value?.h17a_dev, "Gagal 2/4: penghasilan tinggi & stabil, total return kalah dari semua saham dan 2015 rugi −39%."],
  ["H17a 2021–2026 (dihitung sebagai pembanding H17b)", ringkas.value?.h17a_2021, "Tidak dihitung sebagai bukti: H17a sudah gagal di data latihan. Periode ini bertepatan dengan boom batu bara."],
  ["H17b dividen + saringan anti-trap 2021–2026", ringkas.value?.h17b, "Tidak diadopsi: saringan membuang saham batu bara yang justru menang besar."],
  ["H17c aturan uji maju di saham non-syariah 2014–2026", ringkas.value?.h17c, "Gagal 1/4 (25 Okt 2026): bukti utama. Penghasilan hanya 2,4%/th dan return di bawah IHSG; aturan tidak terbukti umum. Saham non-syariah, hanya untuk menguji pola."],
  ["H17d aturan uji maju di saham syariah 2014–2026", ringkas.value?.h17d, "Gagal 2/4 (25 Okt 2026), pasca hasil: return di atas IHSG, tapi penghasilan 2015–2017 di bawah 3% dan 2015 rugi −32,9%. Penghasilan tinggi hanya saat boom batu bara."],
]);
function cagr(rows) {
  if (!rows?.length) return null;
  const f = rows.reduce((a, r) => a * (1 + r.total / 100), 1);
  const fb = rows.reduce((a, r) => a * (1 + r.pembanding_total / 100), 1);
  const n = rows.length - (rows.at(-1).parsial ? 0.2 : 0);
  return { s: (f ** (1 / n) - 1) * 100, b: (fb ** (1 / n) - 1) * 100, inc: rows.filter((r) => !r.parsial).reduce((a, r) => a + r.penghasilan, 0) / rows.filter((r) => !r.parsial).length };
}

const trap = computed(() => ringkas.value?.trap);
const ex = computed(() => ringkas.value?.exdate);
const jenisTrap = ref("exdate");
const HARI_EX = [[1, "Hari ex"], [5, "5 hari"], [10, "10 hari"], [20, "20 hari"], [60, "60 hari"]];
const TAHAP = { "menunggu cum": ["Masih bisa beli", "bg-naik-bg text-naik"], "menunggu bayar": ["Tunggu cair", "bg-surface-2 text-ink-2"], selesai: ["Selesai", "bg-surface-2 text-muted"] };
const jadwalSyariah = computed(() => (jadwal.value?.data || []).filter((x) => x.syariah && x.tahap !== "selesai"));
const jadwalTampil = computed(() => (semuaJadwal.value ? jadwalSyariah.value : jadwalSyariah.value.slice(0, 12)));
const cekIdx = computed(() => jadwal.value?.info?.cek);
const tglId = (t) => (t ? new Date(t).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }) : "–");
</script>

<template>
  <div class="space-y-5">
    <HeaderStrategi judul="Pemburu Dividen" :sub="sub" :pilihan="SUB" @sub="emit('sub', $event)"
      ringkas="Mencari penghasilan rutin dari dividen (bagi hasil laba perusahaan) saham syariah, bukan dari naik-turun harga."
      :langkah="[{ judul: 'Pilih', teks: 'Tiap awal tahun dipilih 10 saham syariah yang dividennya paling tinggi dan rutin dibayar 3 tahun berturut-turut.' }, { judul: 'Tahan', teks: 'Saham ditahan setahun penuh, tidak dijual meski harga turun.' }, { judul: 'Terima', teks: 'Dividen masuk ke kas setelah dipotong pajak 10%.' }, { judul: 'Ganti', teks: 'Awal tahun berikutnya pilihan diperbarui dengan cara yang sama.' }]"
      harapan="Penghasilan dividennya tinggi dan cukup stabil (4–10% per tahun), tapi harga sahamnya ikut naik-turun bersama harga batu bara dan komoditas. Di backtest 2014-2019 total hasilnya kalah dari pasar. Aturan uji maju juga gagal saat diuji di saham non-syariah dan syariah 2014-2026, jadi uji maju 2027 dihentikan (25 Okt 2026). Halaman ini tetap berguna sebagai daftar, kalender, dan kalkulator dividen."
      :chip="[{ teks: 'H17', kelas: 'bg-surface-2 text-muted' }, { teks: 'Gagal diuji', kelas: 'bg-turun-bg text-turun' }, { teks: 'Uji maju dihentikan', kelas: 'bg-surface-2 text-muted' }, { teks: 'Saham syariah IDX', kelas: 'bg-surface-2 text-ink-2' }]" />

    <template v-if="sub === 'daftar'">
      <Kerangka v-if="!daftar" panel jenis="stat" :n="5" :judul="false" kolom="grid-cols-2 md:grid-cols-3 xl:grid-cols-5" />
      <Stats v-else :items="stat" kolom="grid-cols-2 md:grid-cols-3 xl:grid-cols-5" />

      <Panel judul="Jadwal dividen terdekat" :ket="!jadwal ? 'Memuat jadwal...' : jadwal?.info ? `Saham syariah · dari kalender resmi IDX (impor ${tglId(jadwal.info.diimpor)}) · beli paling lambat di tanggal cum` : 'Jadwal resmi IDX belum diimpor'" rapat>
        <Kerangka v-if="!jadwal" jenis="tabel" :n="5" logo />
        <p v-else-if="!jadwal?.info" class="m-0 px-6 pb-5 text-[13px] text-ink-2">Impor dulu lewat Beranda → Sumber data → "Jadwal dividen resmi". Setelah itu tampil di sini: tanggal cum, ex, cair, dan nilai dividen yang sudah diumumkan.</p>
        <p v-else-if="!jadwalSyariah.length" class="m-0 px-6 pb-5 text-[13px] text-ink-2">Tidak ada jadwal dividen saham syariah yang sedang berjalan. Musim dividen biasanya April–Juli; impor ulang tiap bulan supaya pengumuman baru masuk.</p>
        <template v-else>
          <div class="overflow-x-auto">
            <table class="tabel min-w-[760px]">
              <thead><tr><th>Saham</th><th>Status</th><th>Cum</th><th>Ex</th><th>Cair</th><th class="!text-right">Dividen/lembar</th><th class="!text-right">Yield</th></tr></thead>
              <tbody>
                <tr v-for="x in jadwalTampil" :key="x.kode + x.ex">
                  <td class="!h-auto py-2.5"><KodeSaham :kode="x.kode" /><div class="max-w-[200px] truncate text-[11px] text-muted">{{ x.nama || "" }}</div></td>
                  <td><span class="chip" :class="TAHAP[x.tahap][1]">{{ TAHAP[x.tahap][0] }}</span></td>
                  <td class="tabular-nums">{{ tglId(x.cum) }}</td>
                  <td class="tabular-nums">{{ tglId(x.ex) }}</td>
                  <td class="tabular-nums">{{ tglId(x.bayar) }}</td>
                  <td class="text-right tabular-nums" :title="x.asal ? `sumber: ${x.asal}` : 'belum diumumkan / belum ada'">{{ x.per_lembar ? `Rp${rupiah(x.per_lembar)}` : "–" }}</td>
                  <td class="text-right">{{ x.yield != null ? persen(x.yield, 1, false) : "–" }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="flex flex-wrap items-center justify-between gap-2 px-6 py-3 text-xs text-muted">
            <span>Nilai per lembar dari profil IDX, atau dari Yahoo kalau ex-date sudah lewat. "–" = nilainya belum ada di kedua sumber (lihat pengumuman emiten).</span>
            <button v-if="jadwalSyariah.length > 12" class="tombol !bg-surface" @click="semuaJadwal = !semuaJadwal">{{ semuaJadwal ? "Ringkas" : `Semua (${jadwalSyariah.length})` }}</button>
          </div>
        </template>
      </Panel>

      <Panel judul="Kalender dividen" ket="Bulan ex-date yang biasa (3 tahun terakhir) untuk saham yang bayar ≥ 3 tahun berturut-turut · dividen cair biasanya 2–4 minggu setelah ex-date">
        <Kerangka v-if="!daftar" jenis="kartu" :n="12" kolom="grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 xl:grid-cols-12" />
        <div v-else class="grid grid-cols-3 gap-2 sm:grid-cols-4 lg:grid-cols-6 xl:grid-cols-12">
          <div v-for="k in kalender" :key="k.bulan" class="rounded-2xl bg-surface-2 px-3 py-3">
            <div class="text-xs text-muted">{{ k.bulan }}</div>
            <div class="mt-0.5 text-[18px] font-medium tabular-nums">{{ k.n }}</div>
            <div class="mt-1.5 h-1.5 rounded-full bg-surface-3"><div class="h-full rounded-full bg-s1" :style="{ width: `${k.persen}%` }"></div></div>
            <div class="mt-1.5 truncate text-[11px] text-muted" :title="k.contoh.join(', ')">{{ k.contoh.join(" ") || "–" }}</div>
          </div>
        </div>
      </Panel>

      <Panel judul="Daftar dividen saham syariah" :ket="`${tersaring.length} saham · klik kode untuk detail · batang dividen: hijau = naik/sama dari tahun lalu, merah = turun, pudar = tahun berjalan (belum lengkap)`" rapat>
        <div class="flex flex-wrap items-center gap-2 px-6 pb-3">
          <Segmen v-model="filter" :pilihan="FILTER" kecil />
          <select v-model="sektor" class="!h-8 !text-xs">
            <option value="">Semua sektor</option>
            <option v-for="s in daftarSektor" :key="s" :value="s">{{ s }}</option>
          </select>
          <div class="relative">
            <Search class="pointer-events-none absolute top-1/2 left-3 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
            <input v-model="cari" class="!h-8 w-44 !pl-8 !text-xs" placeholder="Cari kode / nama" />
          </div>
        </div>
        <template v-if="!daftar">
          <div class="px-6 pb-2"><Pemutar teks="Menghitung daftar dividen (±10 detik)..." /></div>
          <Kerangka jenis="tabel" :n="8" logo />
        </template>
        <div v-else class="overflow-x-auto">
          <table class="tabel min-w-[1100px]">
            <thead>
              <tr>
                <th v-for="[k, l, kanan] in [['kode', 'Saham'], ['harga', 'Harga', 1], ['dps12', 'Dividen 12 bln', 1], ['yield', 'Yield', 1], ['beruntun', 'Berturut', 1], ['bulan', 'Ex-date biasa'], ['dps_tahun', 'Dividen 6 tahun'], ['payout', 'Payout', 1], ['tanda', 'Tanda bahaya'], ['trap', 'Trap historis', 1]]"
                  :key="k" class="cursor-pointer select-none hover:text-ink" :class="kanan ? '!text-right' : ''" @click="!['bulan', 'dps_tahun'].includes(k) && ganti(k)">
                  <span class="inline-flex items-center gap-1">{{ l }}<ArrowUpDown v-if="urut.kolom === k" class="h-3 w-3 text-aksen" /></span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in tampil" :key="s.kode">
                <td class="!h-auto py-2.5"><KodeSaham :kode="s.kode" /><div class="max-w-[200px] truncate text-[11px] text-muted" :title="s.nama">{{ s.nama || s.sektor || "" }}</div></td>
                <td class="text-right tabular-nums">{{ rupiah(s.harga) }}</td>
                <td class="text-right tabular-nums">Rp{{ rupiah(s.dps12) }}</td>
                <td class="text-right font-medium" :class="s.yield >= 12 ? 'text-turun' : s.yield >= 6 ? 'text-kuning' : ''">{{ persen(s.yield, 1, false) }}</td>
                <td class="text-right" :class="s.beruntun >= 5 ? 'text-naik' : ''">{{ s.beruntun }} th</td>
                <td class="text-xs text-ink-2">{{ s.bulan.map((b) => BULAN[b]).join(", ") }}</td>
                <td>
                  <div class="flex h-7 items-end gap-0.5" >
                    <div v-for="b in batang(s)" :key="b.t" :title="b.judul" class="w-2.5 rounded-sm hover:outline hover:outline-2 hover:outline-offset-1 hover:outline-ink" :class="b.kelas" :style="{ height: `${Math.max(b.v > 0 ? 8 : 2, (b.v / maxDps(s)) * 100)}%`, opacity: b.berjalan ? 0.55 : 1 }"></div>
                  </div>
                </td>
                <td class="text-right" :class="s.payout > 100 ? 'text-turun' : ''">{{ s.payout != null ? `${s.payout}%` : "–" }}</td>
                <td>
                  <span v-if="!s.tanda.length" class="chip bg-naik-bg text-naik">aman</span>
                  <span v-else class="chip bg-kuning-bg text-kuning" :title="s.tanda.map((t) => '• ' + tandaKet[t]).join('\n')">{{ s.tanda.length }} tanda</span>
                </td>
                <td class="text-right text-xs" :class="s.trap?.trap >= 65 ? 'text-turun' : ''">{{ s.trap && s.yield >= 6 ? `${s.trap.trap}%` : "–" }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="flex flex-wrap items-center justify-between gap-2 px-6 py-3 text-xs text-muted">
          <span>Arahkan kursor ke "tanda" untuk detail. Trap historis hanya untuk yield ≥ 6% (asal data analisis). Yield sebelum pajak dividen 10%.</span>
          <button v-if="tersaring.length > 50" class="hover:text-ink" @click="semua = !semua">{{ semua ? "Tampilkan 50 teratas" : `Tampilkan semua ${tersaring.length}` }}</button>
        </div>
      </Panel>
    </template>

    <KalkulatorDividen v-else-if="sub === 'kalkulator'" :daftar="data" :tanda-ket="tandaKet" />

    <template v-else-if="(sub === 'uji' || sub === 'trap') && !ringkas">
      <Kerangka panel jenis="stat" :n="4" kolom="grid-cols-2 sm:grid-cols-4" />
      <div class="grid gap-5 xl:grid-cols-2">
        <Kerangka panel jenis="tabel" :n="6" />
        <Kerangka panel jenis="tabel" :n="6" />
      </div>
    </template>
    <template v-else-if="sub === 'uji'">
      <Panel v-for="[judul, rows, ket] in UJI" :key="judul" :judul="judul" :ket="ket" rapat>
        <div v-if="rows?.length" class="flex flex-wrap gap-2 px-6 pb-3">
          <span class="chip bg-surface-2 text-ink-2">Return per tahun {{ persen(cagr(rows).s, 1) }}</span>
          <span class="chip bg-surface-2 text-ink-2">Semua saham {{ persen(cagr(rows).b, 1) }}</span>
          <span class="chip bg-surface-2 text-ink-2">Penghasilan dividen rata-rata {{ persen(cagr(rows).inc, 1, false) }}/th</span>
        </div>
        <div class="overflow-x-auto">
          <table class="tabel min-w-[900px]">
            <thead><tr><th>Tahun</th><th class="!text-right">Penghasilan dividen</th><th class="!text-right">Harga</th><th class="!text-right">Total</th><th class="!text-right">Semua saham</th><th class="!text-right">IHSG</th><th>Isi portofolio</th></tr></thead>
            <tbody>
              <tr v-for="r in rows || []" :key="r.tahun" class="align-top">
                <td class="!h-auto py-2.5">{{ r.tahun }}<span v-if="r.parsial" class="text-muted">* berjalan</span></td>
                <td class="!h-auto py-2.5 text-right font-medium">{{ persen(r.penghasilan, 1, false) }}</td>
                <td class="!h-auto py-2.5 text-right" :class="r.harga >= 0 ? 'text-naik' : 'text-turun'">{{ persen(r.harga, 1) }}</td>
                <td class="!h-auto py-2.5 text-right font-medium" :class="r.total >= 0 ? 'text-naik' : 'text-turun'">{{ persen(r.total, 1) }}</td>
                <td class="!h-auto py-2.5 text-right" :class="r.pembanding_total >= 0 ? 'text-naik' : 'text-turun'">{{ persen(r.pembanding_total, 1) }}</td>
                <td class="!h-auto py-2.5 text-right" :class="r.ihsg >= 0 ? 'text-naik' : 'text-turun'">{{ persen(r.ihsg, 1) }}</td>
                <td class="!h-auto !whitespace-normal py-2.5 text-xs text-ink-2"><span v-for="k in String(r.saham || '').split(' ')" :key="k" class="mr-1.5 inline-block"><KodeSaham :kode="k" /></span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </Panel>
    </template>

    <template v-else-if="sub === 'trap'">
      <Segmen v-model="jenisTrap" :pilihan="[['exdate', 'Turun setelah ex-date'], ['yield', 'Yield tinggi palsu']]" />

      <template v-if="jenisTrap === 'exdate'">
        <Panel judul="Trap ex-date: dapat dividen, rugi di harga" :ket="ex ? `${ex.semua.n} dividen saham syariah likuid (nilai transaksi ≥ Rp1 M) sejak ${ex.mulai.slice(0, 4)} · beli di close tanggal cum` : 'Belum dihitung'">
          <p class="m-0 text-[13px] leading-relaxed text-ink-2">Beli paling lambat di tanggal cum supaya tercatat dapat dividen. Besoknya (ex-date) harga dibuka turun karena dividen sudah "keluar" dari saham, dan sering lanjut turun beberapa hari. Kalau turunnya lebih dalam dari dividen bersih yang diterima, hasil akhirnya rugi. Hitungan di bawah sudah memasukkan dividen bersih pajak {{ ex ? ex.pajak * 100 : 10 }}% dan biaya beli+jual ±{{ ex?.biaya ?? 0.6 }}%.</p>
          <div v-if="ex" class="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
            <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-xs text-muted">Yield median</div><div class="text-[20px] font-medium">{{ persen(ex.semua.yield_median, 1, false) }}</div></div>
            <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-xs text-muted">Harga 20 hari setelah ex</div><div class="text-[20px] font-medium text-turun">{{ persen(ex.semua.harga_h20, 1) }}</div><div class="text-[11px] text-muted">lebih dalam dari dividennya</div></div>
            <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-xs text-muted">Rugi setelah dividen (20 hari)</div><div class="text-[20px] font-medium text-turun">{{ Math.round(ex.semua.rugi_h20) }}%</div><div class="text-[11px] text-muted">dari semua kasus</div></div>
            <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-xs text-muted">Balik ke harga cum ≤ 20 hari</div><div class="text-[20px] font-medium">{{ Math.round(ex.semua.pulih_20) }}%</div><div class="text-[11px] text-muted">≤ 60 hari {{ Math.round(ex.semua.pulih_60) }}%</div></div>
          </div>
        </Panel>

        <div v-if="ex" class="grid gap-5 xl:grid-cols-2">
          <Panel judul="Kalau dijual setelah …" ket="Median semua kasus · total = harga + dividen bersih − biaya" rapat>
            <table class="tabel">
              <thead><tr><th>Jual di</th><th class="!text-right">Harga</th><th class="!text-right">Total</th><th class="!text-right">Rugi</th><th class="!text-right">vs IHSG</th></tr></thead>
              <tbody>
                <tr v-for="[k, l] in HARI_EX" :key="k">
                  <td>{{ l }}</td>
                  <td class="text-right" :class="kelasPersen(ex.semua[`harga_h${k}`])">{{ persen(ex.semua[`harga_h${k}`], 1) }}</td>
                  <td class="text-right font-medium" :class="kelasPersen(ex.semua[`total_h${k}`])">{{ persen(ex.semua[`total_h${k}`], 2) }}</td>
                  <td class="text-right">{{ Math.round(ex.semua[`rugi_h${k}`]) }}%</td>
                  <td class="text-right text-xs" :class="kelasPersen(ex.semua[`lebih_ihsg_h${k}`])">{{ persen(ex.semua[`lebih_ihsg_h${k}`], 2) }}</td>
                </tr>
              </tbody>
            </table>
            <p class="m-0 px-6 py-3 text-xs text-muted">"vs IHSG" = total dikurangi perubahan IHSG di hari yang sama (apakah lebih buruk dari pasar).</p>
          </Panel>
          <Panel judul="Makin besar dividen, makin sering rugi" ket="Total 20 hari setelah ex, per tingkat yield saat cum" rapat>
            <table class="tabel">
              <thead><tr><th>Yield</th><th class="!text-right">Kasus</th><th class="!text-right">Total 20 hari</th><th class="!text-right">Rugi</th><th class="!text-right">Balik ≤ 60 hari</th></tr></thead>
              <tbody>
                <tr v-for="g in ex.per_yield" :key="g.label">
                  <td>{{ g.label }}</td>
                  <td class="text-right text-muted">{{ g.n }}</td>
                  <td class="text-right font-medium" :class="kelasPersen(g.total_h20)">{{ persen(g.total_h20, 2) }}</td>
                  <td class="text-right" :class="g.rugi_h20 >= 60 ? 'text-turun' : ''">{{ Math.round(g.rugi_h20) }}%</td>
                  <td class="text-right">{{ Math.round(g.pulih_60) }}%</td>
                </tr>
              </tbody>
            </table>
          </Panel>
        </div>

        <Panel v-if="ex" judul="Per tahun" ket="Total 20 hari setelah ex (median)" rapat>
          <div class="overflow-x-auto">
            <table class="tabel min-w-[520px]">
              <thead><tr><th>Tahun</th><th class="!text-right">Kasus</th><th class="!text-right">Total 20 hari</th><th class="!text-right">Rugi</th><th class="!text-right">vs IHSG</th></tr></thead>
              <tbody>
                <tr v-for="t in ex.per_tahun" :key="t.tahun">
                  <td>{{ t.tahun }}</td><td class="text-right text-muted">{{ t.n }}</td>
                  <td class="text-right font-medium" :class="kelasPersen(t.total_h20)">{{ persen(t.total_h20, 2) }}</td>
                  <td class="text-right">{{ Math.round(t.rugi_h20) }}%</td>
                  <td class="text-right text-xs" :class="kelasPersen(t.lebih_ihsg_h20)">{{ persen(t.lebih_ihsg_h20, 2) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel v-if="ex" judul="Contoh terburuk (yield ≥ 4%)" rapat>
          <div class="overflow-x-auto">
            <table class="tabel min-w-[560px]">
              <thead><tr><th>Saham</th><th>Ex-date</th><th class="!text-right">Yield</th><th class="!text-right">Hari ex</th><th class="!text-right">20 hari</th><th class="!text-right">Total</th><th class="!text-right">Balik ke harga cum</th></tr></thead>
              <tbody>
                <tr v-for="x in ex.terburuk" :key="x.kode + x.ex">
                  <td><KodeSaham :kode="x.kode" /></td><td class="tabular-nums">{{ x.ex }}</td>
                  <td class="text-right">{{ persen(x.yield, 1, false) }}</td><td class="text-right" :class="kelasPersen(x.h1)">{{ persen(x.h1, 1) }}</td>
                  <td class="text-right" :class="kelasPersen(x.h20)">{{ persen(x.h20, 1) }}</td><td class="text-right font-medium" :class="kelasPersen(x.total20)">{{ persen(x.total20, 1) }}</td>
                  <td class="text-right text-xs">{{ x.hari_pulih ? `${x.hari_pulih} hari` : "belum" }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </Panel>
        <p class="m-0 text-xs text-muted">Kesimpulan: membeli saham hanya untuk mengejar dividen lalu cepat menjual rata-rata rugi setelah pajak dan biaya, dan makin besar dividennya makin sering rugi. Strategi tahan setahun (H17a/c/d) pun gagal diuji, lihat tab Hasil uji. Ini analisis deskriptif, bukan uji strategi; sejalan dengan uji H2 (beli ex−5, jual cum) yang gagal.</p>
      </template>

      <template v-else>
      <Panel judul="Dividend trap versi yield" ket="Saham yang yield-nya terlihat tinggi tapi ujungnya merugikan dalam 12 bulan">

        <p class="m-0 text-[13px] text-ink-2">Dalam analisis ini, sebuah saham dianggap <b class="font-medium">trap</b> kalau dalam 12 bulan setelah dibeli: total return (harga + dividen) negatif, <b class="font-medium">atau</b> dividen berikutnya dipotong ≥ 30%. Data: saham syariah likuid dengan yield ≥ 6% di akhir tahun 2012–2024.</p>
        <div v-if="trap" class="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
          <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-xs text-muted">Kasus</div><div class="text-[20px] font-medium">{{ trap.n }}</div></div>
          <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-xs text-muted">Kena trap</div><div class="text-[20px] font-medium text-turun">{{ Math.round(trap.trap) }}%</div></div>
          <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-xs text-muted">Dividen dipotong ≥ 30%</div><div class="text-[20px] font-medium">{{ Math.round(trap.dipotong) }}%</div></div>
          <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-xs text-muted">Total return 12 bln (median)</div><div class="text-[20px] font-medium" :class="trap.total_median >= 0 ? 'text-naik' : 'text-turun'">{{ persen(trap.total_median, 1) }}</div></div>
        </div>
      </Panel>
      <Panel v-if="trap" judul="Tanda bahaya" ket="Peluang trap kalau tanda ADA vs TIDAK ada · sampel kecil, anggap petunjuk" rapat>
        <table class="tabel">
          <thead><tr><th>Tanda saat dibeli</th><th class="!text-right">Trap kalau ada</th><th class="!text-right">Trap kalau tidak</th><th class="!text-right">Median total (ada / tidak)</th></tr></thead>
          <tbody>
            <tr v-for="(f, k) in trap.fitur" :key="k">
              <td class="!h-auto !whitespace-normal py-2.5">{{ f.nama }}</td>
              <td class="text-right font-medium" :class="f.ya - f.tidak >= 10 ? 'text-turun' : ''">{{ Math.round(f.ya) }}% <span class="text-xs font-normal text-muted">n={{ f.n_ya }}</span></td>
              <td class="text-right">{{ Math.round(f.tidak) }}% <span class="text-xs text-muted">n={{ f.n_tidak }}</span></td>
              <td class="text-right text-xs">{{ persen(f.median_ya, 1) }} / {{ persen(f.median_tidak, 1) }}</td>
            </tr>
          </tbody>
        </table>
      </Panel>
      <div v-if="trap" class="grid gap-5 lg:grid-cols-2">
        <Panel judul="Per tingkat yield" rapat>
          <table class="tabel"><tbody>
            <tr v-for="(g, k) in trap.yield" :key="k"><td>Yield {{ k }}</td><td class="text-right font-medium" :class="g.trap >= 70 ? 'text-turun' : ''">trap {{ Math.round(g.trap) }}%</td><td class="text-right text-xs text-muted">n={{ g.n }} · median {{ persen(g.median, 1) }}</td></tr>
          </tbody></table>
        </Panel>
        <Panel judul="Jumlah tanda (spesial, harga turun, di bawah MA200, komoditas)" rapat>
          <table class="tabel"><tbody>
            <tr v-for="(g, k) in trap.tanda" :key="k"><td>{{ k }} tanda</td><td class="text-right font-medium" :class="g.trap >= 70 ? 'text-turun' : ''">trap {{ Math.round(g.trap) }}%</td><td class="text-right text-xs text-muted">n={{ g.n }} · median {{ persen(g.median, 1) }}</td></tr>
          </tbody></table>
        </Panel>
      </div>
      <p class="m-0 text-xs text-muted">Contoh trap terburuk 2012–2024: LPPF 2019 (−70%, dividen hilang), LPIN 2021 (−66%), HRUM 2014 (−59%), ITMG 2014 (−54%), MPPA 2014 (−39%). Saringan anti-trap sederhana (H17b) tidak memperbaiki hasil portofolio.</p>
      </template>
    </template>

    <template v-else>
      <Panel judul="Aturan yang diuji">
        <ul class="m-0 list-disc space-y-1.5 pl-5 text-[13px] text-ink-2">
          <li><b class="font-medium">H17a</b>: tiap akhir Desember pilih 10 saham syariah likuid (nilai transaksi ≥ Rp5 M/hari) yang membayar dividen di masing-masing 3 tahun terakhir, dengan yield 12 bulan tertinggi. Beli open hari bursa pertama Januari, tahan setahun, sama bobot.</li>
          <li><b class="font-medium">H17b</b>: H17a + payout ≤ 100%, laba tidak turun > 30%, dividen tidak dipotong > 30%, DER ≤ 2 (bukan bank), arus kas operasi ≥ dividen.</li>
          <li><b class="font-medium">H17c / H17d</b> (aturan uji maju dividen_v1): seperti H17a + maksimal 3 saham per sektor, dihitung harian dengan lot dan tanggal cair dividen. H17c di saham non-syariah, H17d di saham syariah, 2014 s/d Okt 2026. Syarat lulus: penghasilan rata-rata ≥ 4% dan ≥ 3% di ≥ 80% tahun, return ≥ IHSG dan ≥ semua saham, penurunan tidak lebih buruk dari IHSG − 10 poin, tahun terburuk tidak jauh lebih buruk dari pembanding. Keduanya gagal; uji maju 2027 dihentikan.</li>
          <li>Dividen tunai dipotong pajak 10%. Biaya fee 0,15%/0,25% + 1 tick per sisi untuk saham yang berganti. Pembanding: semua saham syariah likuid sama bobot.</li>
          <li>Syarat lulus: return per tahun ≥ pembanding, penghasilan dividen rata-rata ≥ 4%, penghasilan ≥ 3% di ≥ 80% tahun, tahun terburuk tidak jauh lebih buruk dari pembanding.</li>
        </ul>
      </Panel>
      <Panel judul="Data">
        <ul class="m-0 list-disc space-y-1.5 pl-5 text-[13px] text-ink-2">
          <li>Dividen dari Yahoo Finance (tanggal = ex-date, sudah disesuaikan stock split). Ikut terbarui otomatis bersama harga harian (Perbarui / jadwal 17:30).</li>
          <li>Tanda bahaya fundamental (payout, laba, arus kas, DER) dari laporan keuangan IDX; cara memperbarui ada di Beranda → Sumber data.</li>
          <li>Tanggal cum, ex, dan cair resmi dari kalender IDX (lewat browser, tombol di Sumber data). Pembayaran yang tidak ada di kalender IDX memakai ex-date + jeda bayar biasa saham itu. Dividen spesial (sekali bayar) ikut terhitung di yield 12 bulan.</li>
          <li v-if="cekIdx">Cek silang Yahoo vs IDX sejak {{ cekIdx.awal }}: {{ cekIdx.persen_yahoo_di_idx }}% dividen Yahoo ada di kalender IDX, {{ cekIdx.persen_idx_di_yahoo }}% dividen IDX ada di Yahoo<template v-if="cekIdx.nilai_dibandingkan">, nilai per lembar cocok (selisih ≤ 5%) {{ cekIdx.nilai_cocok_5persen }}/{{ cekIdx.nilai_dibandingkan }}</template>. Jeda ex-date ke cair median {{ cekIdx.jeda_bayar_median }} hari.</li>
        </ul>
      </Panel>
    </template>

    <p class="m-0 text-xs text-muted">Bukan nasihat keuangan. Yield masa lalu tidak menjamin dividen berikutnya.</p>
  </div>
</template>

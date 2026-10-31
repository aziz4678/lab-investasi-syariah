<script setup>
import { ref, computed } from "vue";
import { Award, TriangleAlert, ShieldCheck, ExternalLink, Search, ChevronRight, UserRound, Smartphone, Briefcase, Landmark, LineChart, Wallet } from "lucide-vue-next";
import { persen } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import { pakaiPlatform } from "@/composables/platformRD";

const props = defineProps({ daftar: Object, m: Object });
const { info } = pakaiPlatform();
const cari = ref("");
const pto = computed(() => {
  const q = cari.value.trim().toLowerCase();
  return (info.value?.pto || []).filter((x) => !q || `${x.nama} ${x.pemilik}`.toLowerCase().includes(q));
});
const tgl = (s) => (s ? new Date(s).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }) : "–");
const kat = (k) => props.m?.kategori?.find((x) => x.kategori === k);
const nol = (v) => (v == null ? "–" : Math.abs(v) < 0.05 ? "0,0%" : persen(v, 1));

const BAGIAN = [["dasar", "Cara kerja"], ["jenis", "Jenis"], ["beli", "Cara membeli"], ["biaya", "Biaya & pajak"], ["aman", "Seberapa aman"], ["istilah", "Istilah"], ["baca", "Membaca halaman ini"], ["platform", "Tempat beli"], ["data", "Sumber data"]];
const lompat = (id) => document.getElementById(`ck-${id}`)?.scrollIntoView({ behavior: "smooth", block: "start" });

const ALUR = [
  { ikon: UserRound, judul: "Kamu", isi: "Menyetor uang lewat aplikasi atau bank." },
  { ikon: Smartphone, judul: "Agen penjual", isi: "Aplikasi berizin OJK (APERD) meneruskan uangmu." },
  { ikon: Briefcase, judul: "Manajer investasi", isi: "Mengelola uang banyak orang: membeli deposito, sukuk, atau saham syariah." },
  { ikon: Landmark, judul: "Bank kustodian", isi: "Menyimpan semua aset dan menghitung NAV tiap hari, terpisah dari manajer investasi." },
  { ikon: LineChart, judul: "NAV harian", isi: "Nilai unitmu naik-turun mengikuti isi reksa dana." },
  { ikon: Wallet, judul: "Jual kapan saja", isi: "Unit dijual di NAV hari itu, uang kembali ke rekeningmu." },
];
const JENIS = [
  ["pasar_uang", "Pasar uang", "Deposito & sukuk < 1 tahun", "Sangat rendah", "< 1 tahun", "Dana darurat, pengganti tabungan"],
  ["pendapatan_tetap", "Pendapatan tetap", "Sukuk negara & perusahaan", "Rendah–sedang", "1–3 tahun", "Tabungan jangka menengah"],
  ["campuran", "Campuran", "Saham + sukuk", "Sedang", "3–5 tahun", "Seimbang tumbuh dan stabil"],
  ["saham", "Saham", "Saham syariah", "Tinggi", "5 tahun +", "Pertumbuhan jangka panjang"],
  ["indeks", "Indeks", "Mengikuti indeks (mis. JII)", "Tinggi", "5 tahun +", "Saham dengan biaya lebih rendah"],
  ["global", "Global", "Saham luar negeri, biasanya USD", "Tinggi + kurs", "5 tahun +", "Menyebar ke luar Indonesia"],
  ["terproteksi", "Terproteksi", "Sukuk sampai jatuh tempo", "Rendah", "Sampai jatuh tempo", "Uang yang pasti tidak dipakai"],
];
const LANGKAH = [
  ["Pilih aplikasi berizin OJK", "Cek di daftar Portal Transaksi Online OJK di bawah. Bibit, Ajaib, Makmur, Bareksa, bank besar, dan sekuritas besar terdaftar."],
  ["Daftar dan verifikasi", "Isi data diri, foto KTP dan swafoto (e-KYC), lalu isi profil risiko. Biasanya selesai dalam 1 hari kerja."],
  ["Pilih produk", "Sesuaikan dengan kapan uangnya dipakai (tab Mulai di sini). Lihat lencana, peringatan, dan fund fact sheet."],
  ["Bayar", "Transfer atau virtual account. Pembayaran sebelum pukul 13.00 WIB hari bursa memakai NAV hari itu; setelahnya NAV hari bursa berikutnya."],
  ["Unit masuk", "Jumlah unit = uang ÷ NAV. Contoh: Rp1.000.000 ÷ NAV 1.250 = 800 unit. Nilai investasimu = unit × NAV terbaru."],
  ["Jual (pencairan)", "Bisa kapan saja di hari bursa. Uang masuk paling lama 7 hari bursa (aturan OJK); pasar uang biasanya 1–2 hari kerja."],
];
const BIAYA = [
  ["Biaya pengelolaan (expense ratio)", "Dipotong otomatis dari NAV setiap hari; angka hasil di aplikasi sudah setelah biaya ini.", "Lihat kolom Biaya/th"],
  ["Biaya beli", "Banyak aplikasi menggratiskan; sebagian produk/bank memungut sampai ±2%.", "Cek di aplikasinya"],
  ["Biaya jual", "Umumnya 0%, kadang dikenakan kalau dijual terlalu cepat.", "Cek di aplikasinya"],
  ["Biaya pindah (switching)", "Pindah ke RD lain di manajer investasi yang sama; bisa ±0–2%.", "Cek di aplikasinya"],
  ["Pajak keuntungan RD", "Bukan objek pajak bagi pemegang unit; pajak sudah diurus di dalam dana.", "0%"],
  ["Pembanding: kupon sukuk negara", "Kena pajak final atas kupon.", "10%"],
  ["Pembanding: bunga deposito", "Kena pajak final atas bunga/bagi hasil.", "20%"],
];
const AMAN = [
  ["Diawasi OJK", "Manajer investasi, produk, dan agen penjual harus berizin dan melapor ke OJK.", true],
  ["Aset dipisah", "Uang dan efek disimpan di bank kustodian atas nama reksa dana, bukan di rekening manajer investasi. Kalau MI bangkrut, aset tetap milik investor.", true],
  ["Syariah diawasi", "Isinya hanya efek di Daftar Efek Syariah OJK, diawasi Dewan Pengawas Syariah tiap manajer investasi.", true],
  ["Tidak dijamin LPS", "Beda dengan deposito: nilai reksa dana bisa turun dan tidak ada penjaminan pemerintah.", false],
  ["Risiko turun harga", "Sukuk turun saat suku bunga naik; saham bisa turun lebih dari separuh.", false],
  ["Risiko penerbit", "Sukuk perusahaan bisa gagal bayar. Perhatikan peringatan \"1 efek > 15%\".", false],
  ["Risiko pembubaran", "Dana kelolaan di bawah Rp10 miliar selama 120 hari bursa wajib dibubarkan; uang dikembalikan sesuai NAV saat itu.", false],
];
const ISTILAH = [
  ["NAV/Unit (harga per unit)", "Net Asset Value per unit", "Harga satu unit reksa dana hari itu. Untung/rugi kamu = perubahan NAV. Biaya pengelolaan sudah dipotong di sini."],
  ["AUM (dana kelolaan)", "Asset Under Management", "Total uang semua investor di produk ini. Di bawah Rp10 miliar terlalu lama, produk wajib dibubarkan."],
  ["Rata-rata per tahun", "CAGR", "Kalau hasilnya dibagi rata tiap tahun, berapa persen per tahun. \"3 th\" = dihitung dari 3 tahun terakhir."],
  ["Turun terburuk", "Max drawdown", "Penurunan paling dalam dari titik tertinggi ke titik terendah. Gambaran \"paling sakit\" yang pernah dialami pemegangnya."],
  ["Biaya per tahun", "Expense ratio", "Total biaya pengelolaan setahun, dalam persen dana."],
  ["Manajer investasi", "MI", "Perusahaan yang mengelola uang dan memilih isi reksa dana."],
  ["Bank kustodian", "Custodian bank", "Bank yang menyimpan aset reksa dana dan menghitung NAV."],
  ["Agen penjual / aplikasi", "APERD", "Pihak yang menjual reksa dana ke kamu. Harus berizin OJK."],
  ["Fund fact sheet", "FFS", "Laporan bulanan 1–2 halaman: isi portofolio, hasil, biaya."],
  ["Prospektus", "", "Dokumen resmi lengkap: tujuan, kebijakan investasi, biaya, risiko."],
  ["Unit penyertaan", "UP", "\"Saham\" kamu di reksa dana. Jumlahnya tetap; nilainya ikut NAV."],
  ["Tolok ukur", "Benchmark", "Pembanding resmi produk (mis. bunga deposito, indeks JII)."],
  ["Hasil kalau ditahan (sukuk)", "YTM", "Perkiraan hasil per tahun sukuk kalau dibeli di harga sekarang dan dipegang sampai jatuh tempo."],
];
const LENCANA = [
  ["Konsisten", "Dalam ≥ 60% periode 12 bulan, hasilnya di atas nilai tengah RD sejenis. Butuh data ≥ 3 tahun."],
  ["Kalahkan inflasi", "Hasil di atas inflasi pada ≥ 80% tahun penuh (minimal 3 tahun)."],
  ["Tahan banting", "Turun terburuk sepanjang riwayat lebih ringan dari nilai tengah RD sejenis (data ≥ 3 tahun). Tidak diberikan kalau NAV terlalu mulus."],
  ["Biaya murah", "Biaya per tahun termasuk 25% termurah di jenisnya."],
];
const PERINGATAN = [
  ["Data pendek", "Riwayat kurang dari 3 tahun; belum pernah diuji di masa sulit."],
  ["NAV terlalu mulus", "Naik-turunnya jauh lebih kecil dari RD sejenis dan tidak pernah turun dalam 24 bulan. Bisa berarti isinya jarang diperdagangkan, risikonya baru terlihat saat ada masalah."],
  ["1 efek > 15%", "Satu surat berharga (bukan milik negara/deposito) lebih dari 15% isi dana. Kalau penerbitnya bermasalah, dampaknya besar."],
  ["AUM naik/turun ×3", "Dalam 6 bulan uang investor naik/turun lebih dari 3 kali lipat."],
  ["AUM hampir habis", "Dana kelolaan menyusut sampai mendekati batas pembubaran."],
  ["Biaya tidak diketahui", "Biaya tahunan tidak tercantum di data; cek di prospektus/fund fact sheet."],
];
const SUMBER = [
  ["NAV harian, biaya, isi portofolio, AUM", "Pasardana (data publik)", "Tiap hari bursa 17.30"],
  ["Riwayat NAV sejak 2013", "Laporan NAB bulanan OJK", "Bulanan (data terbit ±tanggal 8)"],
  ["Daftar produk di Bibit", "Halaman publik bibit.id (tanpa login)", "Tiap 30 hari"],
  ["Daftar produk di Ajaib & Makmur", "Sitemap publik situsnya", "Tiap 7 hari"],
  ["Daftar aplikasi berizin", "Portal reksa dana OJK", "Tiap 90 hari"],
  ["Inflasi, BI-Rate, bunga antarbank", "Bank Indonesia / FRED", "Bulanan"],
  ["Sukuk negara & korporasi", "Pasardana", "Tiap hari bursa"],
];
</script>

<template>
  <div class="space-y-5">
    <div class="panel flex flex-wrap gap-1.5 px-4 py-3">
      <button v-for="[id, l] in BAGIAN" :key="id" class="chip bg-surface-2 text-ink-2 hover:bg-aksen-lembut hover:text-aksen" @click="lompat(id)">{{ l }}</button>
    </div>

    <Panel id="ck-dasar" class="scroll-mt-4" judul="Reksa dana dalam 1 menit" ket="Uang banyak orang dikumpulkan, dikelola profesional, disimpan terpisah, diawasi OJK">
      <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <div v-for="(a, i) in ALUR" :key="a.judul" class="relative rounded-2xl bg-surface-2 px-4 py-3">
          <div class="flex items-center gap-2">
            <span class="grid h-8 w-8 place-items-center rounded-full bg-aksen-lembut text-aksen"><component :is="a.ikon" class="h-4 w-4" /></span>
            <span class="text-[13px] font-medium">{{ a.judul }}</span>
          </div>
          <p class="m-0 mt-2 text-xs leading-relaxed text-ink-2">{{ a.isi }}</p>
          <ChevronRight v-if="i < ALUR.length - 1" class="absolute top-1/2 -right-3 hidden h-4 w-4 -translate-y-1/2 text-muted xl:block" />
        </div>
      </div>
      <div class="mt-4 rounded-2xl border border-garis px-4 py-3 text-[13px] leading-relaxed text-ink-2">
        <b class="font-medium text-ink">Untung dan rugi datang dari perubahan NAV.</b> Contoh: beli Rp1.000.000 saat NAV 1.000 → dapat 1.000 unit. Setahun kemudian NAV 1.050 → nilainya Rp1.050.000 (untung 5%). Kalau NAV turun ke 980 → nilainya Rp980.000 (rugi 2%). NAV naik dari bunga deposito, kupon sukuk, dividen, dan kenaikan harga isinya, lalu dikurangi biaya.
      </div>
    </Panel>

    <Panel id="ck-jenis" class="scroll-mt-4" judul="Jenis reksa dana syariah" ket="Angka hasil & turun terburuk = nilai tengah produk di katalog, rupiah, dari laporan OJK" rapat>
      <div class="overflow-x-auto">
        <table class="tabel min-w-[860px]">
          <thead><tr><th>Jenis</th><th>Isinya</th><th>Risiko</th><th>Simpan minimal</th><th class="!text-right">Hasil/th (3 th)</th><th class="!text-right">Turun terburuk</th><th>Cocok untuk</th></tr></thead>
          <tbody>
            <tr v-for="[k, nama, isi, risiko, lama, cocok] in JENIS" :key="k">
              <td class="font-medium">{{ nama }}</td>
              <td class="!whitespace-normal text-[13px] text-ink-2">{{ isi }}</td>
              <td class="text-[13px] text-ink-2">{{ risiko }}</td>
              <td class="text-[13px] text-ink-2">{{ lama }}</td>
              <td class="text-right tabular-nums">{{ kat(k)?.cagr_3 == null ? "–" : persen(kat(k).cagr_3, 1) }}</td>
              <td class="text-right tabular-nums" :class="kat(k)?.turun_terburuk < -1 ? 'text-turun' : ''">{{ nol(kat(k)?.turun_terburuk) }}</td>
              <td class="!whitespace-normal text-[13px] text-ink-2">{{ cocok }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="m-0 px-6 py-3 text-xs text-muted">Risiko lebih tinggi bukan jaminan hasil lebih tinggi. 3 tahun terakhir RD saham syariah justru kalah dari pasar uang; lihat penjelasan di tab Mulai di sini.</p>
    </Panel>

    <Panel id="ck-beli" class="scroll-mt-4" judul="Cara membeli dan menjual" ket="Alur umum di aplikasi mana pun">
      <ol class="m-0 grid gap-3 pl-0 md:grid-cols-2 xl:grid-cols-3">
        <li v-for="([j, isi], i) in LANGKAH" :key="j" class="flex gap-3 rounded-2xl bg-surface-2 px-4 py-3">
          <span class="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-aksen text-xs font-semibold text-aksen-teks">{{ i + 1 }}</span>
          <span class="text-[13px] leading-relaxed text-ink-2"><b class="block font-medium text-ink">{{ j }}</b>{{ isi }}</span>
        </li>
      </ol>
    </Panel>

    <div class="grid gap-5 lg:grid-cols-2 [&>*]:min-w-0">
      <Panel id="ck-biaya" class="scroll-mt-4" judul="Biaya dan pajak" rapat>
        <table class="tabel">
          <tbody>
            <tr v-for="[a, b, c] in BIAYA" :key="a">
              <td class="!h-auto !whitespace-normal py-2.5"><div class="text-[13px] font-medium">{{ a }}</div><div class="text-xs text-ink-2">{{ b }}</div></td>
              <td class="!h-auto py-2.5 text-right text-[13px] whitespace-nowrap text-ink-2">{{ c }}</td>
            </tr>
          </tbody>
        </table>
      </Panel>
      <Panel id="ck-aman" class="scroll-mt-4" judul="Seberapa aman?">
        <ul class="m-0 space-y-2.5 pl-0 text-[13px] text-ink-2">
          <li v-for="[a, b, baik] in AMAN" :key="a" class="flex gap-2">
            <ShieldCheck v-if="baik" class="mt-0.5 h-4 w-4 shrink-0 text-naik" />
            <TriangleAlert v-else class="mt-0.5 h-4 w-4 shrink-0 text-kuning" />
            <span><b class="font-medium text-ink">{{ a }}.</b> {{ b }}</span>
          </li>
        </ul>
      </Panel>
    </div>

    <Panel id="ck-istilah" class="scroll-mt-4" judul="Istilah" ket="Nama yang dipakai di halaman ini, istilah resminya, dan artinya" rapat>
      <div class="overflow-x-auto">
        <table class="tabel min-w-[640px]">
          <thead><tr><th>Istilah</th><th>Nama resmi</th><th>Artinya</th></tr></thead>
          <tbody>
            <tr v-for="[a, b, c] in ISTILAH" :key="a">
              <td class="!h-auto py-2.5 font-medium">{{ a }}</td>
              <td class="!h-auto py-2.5 text-ink-2">{{ b || "–" }}</td>
              <td class="!h-auto !whitespace-normal py-2.5 text-[13px] text-ink-2">{{ c }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </Panel>

    <div id="ck-baca" class="grid scroll-mt-4 gap-5 lg:grid-cols-2 [&>*]:min-w-0">
      <Panel judul="Lencana" ket="Diberikan otomatis dari riwayat NAV (laporan OJK sejak 2013 + Pasardana)">
        <ul class="m-0 space-y-2.5 pl-0 text-[13px] text-ink-2">
          <li v-for="[a, b] in LENCANA" :key="a" class="flex gap-2"><Award class="mt-0.5 h-4 w-4 shrink-0 text-naik" /><span><b class="font-medium text-ink">{{ a }}.</b> {{ b }}</span></li>
        </ul>
        <p class="m-0 mt-3 text-xs leading-relaxed text-muted">Urutan produk: jumlah lencana terbanyak, lalu peringatan paling sedikit, lalu hasil 3 tahun. Lencana menggambarkan masa lalu; <b class="font-medium">belum terbukti</b> produk yang bagus kemarin akan tetap bagus besok.</p>
      </Panel>
      <Panel judul="Peringatan" ket="Bukan vonis produk bermasalah, tanda untuk dicek dulu">
        <ul class="m-0 space-y-2.5 pl-0 text-[13px] text-ink-2">
          <li v-for="[a, b] in PERINGATAN" :key="a" class="flex gap-2"><TriangleAlert class="mt-0.5 h-4 w-4 shrink-0 text-kuning" /><span><b class="font-medium text-ink">{{ a }}.</b> {{ b }}</span></li>
        </ul>
      </Panel>
    </div>

    <Panel id="ck-platform" class="scroll-mt-4" judul="Tempat beli" :ket="`${info?.total_rd ?? '…'} dari ${daftar?.data?.length ?? '…'} RD syariah ditemukan di minimal satu platform`">
      <div class="grid gap-3 md:grid-cols-3">
        <div v-for="p in info?.platform || []" :key="p.kode" class="rounded-2xl bg-surface-2 px-4 py-3">
          <div class="flex items-center justify-between gap-2">
            <a :href="p.situs" target="_blank" rel="noopener" class="inline-flex h-8 items-center rounded-full border border-garis bg-white px-3 hover:border-aksen"><img :src="`/api/logo/merek/${p.kode}`" :alt="p.nama" class="w-auto object-contain" :style="{ height: p.kode === 'ajaib' ? '21px' : '15px' }" /></a>
            <span v-if="p.izin_ojk.length" class="chip bg-naik-bg text-naik" :title="p.izin_ojk.map((x) => `${x.nama} (${x.pemilik})`).join('; ')"><ShieldCheck class="h-3 w-3" />Berizin OJK</span>
          </div>
          <div class="mt-2 text-[13px] text-ink-2">{{ p.cocok ?? "–" }} RD syariah</div>
          <div class="text-[11px] text-muted">dari {{ p.sumber }} · {{ tgl(p.diambil) }}</div>
        </div>
      </div>
      <ul class="m-0 mt-4 space-y-1 pl-5 text-xs leading-relaxed text-muted">
        <li>Nama produk dicocokkan dengan katalog (nama dan kelas harus sama). Daftar platform bisa memuat produk yang sudah tidak dijual; selalu cek di aplikasinya.</li>
        <li>Bareksa dan aplikasi lain belum dicek karena tidak punya daftar produk publik. OJK tidak menerbitkan "produk X dijual di mana"; yang diterbitkan OJK adalah daftar aplikasi berizin (di bawah).</li>
      </ul>
    </Panel>

    <Panel judul="Aplikasi jual-beli reksa dana berizin OJK" :ket="`${info?.pto?.length ?? '…'} Portal Transaksi Online terdaftar · sumber: portal reksa dana OJK`" rapat>
      <template #aksi>
        <div class="relative w-56">
          <Search class="pointer-events-none absolute top-1/2 left-3 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
          <input v-model="cari" class="!h-8 w-full !pl-8 text-[13px]" placeholder="Cari aplikasi…" />
        </div>
      </template>
      <div class="max-h-[420px] overflow-auto">
        <table class="tabel min-w-[560px]">
          <thead><tr><th>Aplikasi / sistem</th><th>Perusahaan pemilik</th></tr></thead>
          <tbody>
            <tr v-for="x in pto" :key="x.no">
              <td class="!h-auto w-1/2 !whitespace-normal py-2"><span class="font-medium">{{ x.nama }}</span><div class="max-w-[420px] truncate text-[11px] text-muted" :title="x.url">{{ x.url }}</div></td>
              <td class="!h-auto !whitespace-normal py-2 text-[13px] text-ink-2">{{ x.pemilik }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="m-0 px-6 py-3 text-xs text-muted">Kalau aplikasi yang menawarkan reksa dana tidak ada di daftar ini, jangan transfer uang. Cek langsung di <a :href="info?.pto_sumber" target="_blank" rel="noopener" class="inline-flex items-center gap-0.5 text-aksen hover:underline">reksadana.ojk.go.id<ExternalLink class="h-3 w-3" /></a>.</p>
    </Panel>

    <div id="ck-data" class="grid scroll-mt-4 gap-5 lg:grid-cols-2 [&>*]:min-w-0">
      <Panel judul="Sumber data" rapat>
        <div class="overflow-x-auto">
        <table class="tabel">
          <thead><tr><th>Data</th><th>Sumber</th><th>Diperbarui</th></tr></thead>
          <tbody>
            <tr v-for="[a, b, c] in SUMBER" :key="a">
              <td class="!h-auto !whitespace-normal py-2.5 text-[13px]">{{ a }}</td>
              <td class="!h-auto !whitespace-normal py-2.5 text-[13px] text-ink-2">{{ b }}</td>
              <td class="!h-auto !whitespace-normal py-2.5 text-[13px] text-ink-2">{{ c }}</td>
            </tr>
          </tbody>
        </table>
        </div>
      </Panel>
      <Panel judul="Keterbatasan data">
        <ul class="m-0 list-disc space-y-1.5 pl-5 text-[13px] text-ink-2">
          <li>Hasil dihitung dari NAV saja. RD yang membagi dividen tunai terlihat lebih kecil dari hasil sebenarnya.</li>
          <li>Riwayat jangka panjang memakai NAV akhir bulan dari laporan OJK (sejak 2013), disambung NAV harian Pasardana 12 bulan terakhir.</li>
          <li>RD yang sudah bubar tidak tercakup, sehingga nilai tengah kategori cenderung sedikit lebih bagus dari kenyataan.</li>
          <li>Deposito di pembanding = perkiraan dari bunga antarbank dipotong pajak 20%; bunga bank tertentu bisa berbeda.</li>
          <li>Lencana dan peringatan dihitung otomatis dengan aturan tetap di atas; bukan rekomendasi dan bukan nasihat keuangan.</li>
        </ul>
      </Panel>
    </div>
  </div>
</template>

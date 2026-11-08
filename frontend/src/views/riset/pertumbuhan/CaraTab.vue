<script setup>
import { computed, inject } from "vue";
import { RefreshCw, Sprout, Scale, ListChecks, BookOpen, Database, AlertTriangle } from "lucide-vue-next";
import PanelPekerjaan from "@/components/sistem/PanelPekerjaan.vue";
import TersediaDi from "@/components/produk/TersediaDi.vue";
import { tglTeks, bulanTeks } from "@/views/riset/pertumbuhan/bantu";

const props = defineProps({ d: Object, kerja: Object });
const emit = defineEmits(["hitung"]);
const pindahTab = inject("pindahTab");

const BEDA = [
  { judul: "Portofolio Konservatif", teks: "Untuk penghasilan rutin dan uang yang mungkin dipakai dalam waktu dekat. Isinya RD pendapatan tetap, pasar uang, dan sukuk negara. Turunnya kecil.", tab: "konservatif" },
  { judul: "Portofolio Pertumbuhan (halaman ini)", teks: "Untuk uang yang tidak dipakai minimal 5 tahun. Isinya RD saham syariah Indonesia dan global. Tumbuh lebih besar, tapi bisa turun dalam.", tab: null },
  { judul: "Follow Tren & Momentum Blend", teks: "Strategi jual-beli saham satu per satu (trading) yang masih diuji dengan uang virtual. Bukan cara investasi rutin.", tab: "tren52" },
];
const ISTILAH = [
  ["Setor rutin", "Menabung jumlah yang sama tiap bulan, tanpa menebak kapan harga murah. Kadang dapat harga mahal, kadang murah, rata-ratanya ikut pasar."],
  ["Seimbangkan (rebalance)", "Tiap Desember, bagian yang naik lebih banyak dijual sebagian dan dibelikan bagian yang tertinggal, supaya kembali 50/50. Otomatis 'jual yang mahal, beli yang murah'."],
  ["Reksa dana saham syariah", "Uang banyak orang dikumpulkan dan dibelikan saham yang lolos saringan syariah oleh manajer investasi. Uangnya disimpan di bank kustodian, bukan di manajer investasi."],
  ["Global", "Saham perusahaan di banyak negara (sebagian besar Amerika Serikat). Harganya dalam dolar, jadi nilainya dalam rupiah ikut naik-turun dengan kurs."],
  ["Turun dari puncak", "Seberapa jauh nilai turun dari titik tertingginya sebelum naik lagi. Ini yang paling terasa saat dijalani."],
  ["Periode 10 tahun terburuk", "Dari semua kemungkinan bulan mulai, 10 tahun dengan hasil paling jelek. Menunjukkan seberapa sial nasib terburuknya."],
  ["Angka paling hati-hati", "Hasil dihitung dari beberapa sumber (indeks panjang, rata-rata RD sejenis, produk di keranjang). Yang ditampilkan di depan selalu yang paling rendah."],
  ["Lolos setelah data diketahui", "Uji ditulis sebelum dihitung, tapi gambaran umum sejarah sudah diketahui. Jadi belum boleh dianggap bukti; perlu dipantau maju."],
];

const kriteria = computed(() => props.d?.keranjang?.kriteria);
const perAplikasi = computed(() => Object.entries(props.d?.keranjang?.per_aplikasi ?? {}).map(([k, v]) => ({ k, nama: k === "semua" ? "Semua aplikasi" : k[0].toUpperCase() + k.slice(1), lk: v.LK, gl: v.GL_disetujui })));
const gugur = computed(() => {
  const g = props.d?.keranjang?.gugur ?? [];
  return [["LK", "RD saham syariah Indonesia"], ["GL", "RD saham syariah global (dolar)"]].map(([w, nama]) => ({ w, nama, isi: g.filter((x) => x.wadah === w) }));
});
const pengganti = computed(() => props.d?.keranjang?.pengganti_global ?? []);
const infoKat = computed(() => props.d?.info_kategori);
</script>

<template>
  <div class="space-y-5">
    <section class="panel px-4 py-5 sm:px-6">
      <div class="flex items-center gap-2 text-[14px] font-medium"><Sprout class="h-4 w-4 text-aksen" />Apa ini?</div>
      <p class="m-0 mt-2 text-[13px] leading-relaxed text-ink-2">
        Halaman ini menunjukkan satu cara investasi jangka panjang yang sederhana: setiap bulan menabung jumlah yang sama ke reksa dana saham syariah, separuh di Indonesia dan separuh di luar negeri (global).
        Sekali setahun, di bulan Desember, porsinya dikembalikan ke separuh-separuh. Tidak ada jual-beli harian dan tidak perlu menebak arah pasar.
      </p>
      <p class="m-0 mt-2 text-[13px] leading-relaxed text-ink-2">
        Idenya diuji di riset H35: dalam 25 tahun terakhir, masa buruk saham Indonesia dan saham global jatuh di dekade yang berbeda. Memegang keduanya membuat nasib uang tidak bergantung ke satu negara saja.
      </p>
      <div class="mt-4 grid gap-3 md:grid-cols-3">
        <div v-for="b in BEDA" :key="b.judul" class="rounded-2xl px-4 py-3" :class="b.tab ? 'bg-surface-2' : 'bg-aksen-lembut ring-1 ring-aksen'">
          <div class="text-[13px] font-medium">{{ b.judul }}</div>
          <p class="m-0 mt-1 text-[12px] leading-relaxed text-ink-2">{{ b.teks }}</p>
          <a v-if="b.tab" :href="`#${b.tab}`" class="mt-1 inline-block text-[12px] text-aksen" @click.prevent="pindahTab(b.tab)">Buka</a>
        </div>
      </div>
    </section>

    <section class="panel px-4 py-5 sm:px-6">
      <div class="flex items-center gap-2 text-[14px] font-medium"><Scale class="h-4 w-4 text-aksen" />Cara kerjanya, langkah demi langkah</div>
      <ol class="m-0 mt-3 space-y-2 pl-5 text-[13px] leading-relaxed text-ink-2">
        <li><b class="font-medium text-ink">Pilih produk sekali.</b> Halaman ini sudah memilihkan 3 RD saham syariah Indonesia dan 1 RD saham syariah global dengan aturan tetap (bawah). Pilih aplikasi yang kamu pakai di tab Rencana.</li>
        <li><b class="font-medium text-ink">Pasang beli rutin.</b> Setoran dibagi: separuh rata ke 3 RD Indonesia, separuh ke RD global. Kalau setoran kecil, beli bergiliran satu produk per bulan.</li>
        <li><b class="font-medium text-ink">Biarkan.</b> Jangan dijual saat turun; penurunan 20–40% pernah terjadi dan termasuk normal untuk saham.</li>
        <li><b class="font-medium text-ink">Desember: seimbangkan.</b> Lihat nilai kedua bagian. Pindahkan selisihnya supaya kembali 50/50, atau arahkan setoran berikutnya ke bagian yang tertinggal.</li>
        <li><b class="font-medium text-ink">Januari: cek daftar.</b> Kalau ada produk yang bubar, mahal, atau hilang dari aplikasi, halaman ini menampilkan penggantinya. Produk global tidak pernah diganti otomatis.</li>
      </ol>
    </section>

    <section class="panel px-4 py-5 sm:px-6">
      <div class="flex items-center gap-2 text-[14px] font-medium"><BookOpen class="h-4 w-4 text-aksen" />Istilah</div>
      <dl class="m-0 mt-3 grid gap-3 md:grid-cols-2">
        <div v-for="[k, v] in ISTILAH" :key="k" class="rounded-2xl bg-surface-2 px-4 py-3">
          <dt class="text-[13px] font-medium">{{ k }}</dt>
          <dd class="m-0 mt-0.5 text-[12px] leading-relaxed text-ink-2">{{ v }}</dd>
        </div>
      </dl>
    </section>

    <section v-if="d" class="panel px-4 py-5 sm:px-6">
      <div class="flex items-center gap-2 text-[14px] font-medium"><ListChecks class="h-4 w-4 text-aksen" />Aturan memilih produk</div>
      <ul class="m-0 mt-3 space-y-1.5 pl-4 text-[13px] leading-relaxed text-ink-2">
        <li>Hanya reksa dana <b class="font-medium text-ink">syariah</b> yang masih aktif (harga terbit dalam {{ kriteria?.aktif_hari }} hari) dan punya riwayat minimal {{ kriteria?.min_tahun }} tahun.</li>
        <li>Biaya tahunan diketahui, tidak membagi hasil tunai, dan dana kelolaan minimal setara median produk sejenis yang lolos.</li>
        <li><b class="font-medium text-ink">Wajib tersedia di Bibit, Makmur, atau Ajaib.</b> Produk tanpa data aplikasi tidak dipakai.</li>
        <li>Diurutkan dari biaya termurah. Hasil masa lalu <b class="font-medium text-ink">tidak</b> dipakai untuk memilih.</li>
        <li>Bagian global hanya RD yang membeli saham di banyak negara. RD satu kawasan (Asia, China, ASEAN, India, pasar berkembang, AS saja) dan RD satu sektor (mis. teknologi) ditolak.</li>
        <li>Minimal beli dari data manajer investasi hanya ditampilkan, tidak menyaring, karena di aplikasi sering jauh lebih kecil. Kalau di atas Rp1 jt / US$100 diberi tanda "cek di aplikasi".</li>
        <li>Dibentuk ulang tiap Januari. Di tengah tahun, RD Indonesia yang bubar / makin mahal / dana kelolaannya mengecil diganti calon termurah berikutnya. RD global yang gagal tidak diganti otomatis: bagian global dikosongkan dan calon penggantinya ditampilkan.</li>
      </ul>
      <div class="mt-4 text-[13px] font-medium">Produk yang lolos per aplikasi</div>
      <div class="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <div v-for="a in perAplikasi" :key="a.k" class="rounded-xl bg-surface-2 px-3 py-2">
          <div class="text-[12px] font-medium">{{ a.nama }}</div>
          <div class="text-[11px] text-muted">Indonesia {{ a.lk }} · global {{ a.gl }}</div>
          <div v-if="!a.gl" class="text-[11px] text-kuning">bagian global tidak tersedia</div>
        </div>
      </div>
      <div v-if="pengganti.length" class="mt-4">
        <div class="text-[13px] font-medium">Calon pengganti RD global (tidak dipakai sekarang)</div>
        <ul class="m-0 mt-1 space-y-1 pl-4 text-[12px] text-ink-2"><li v-for="c in pengganti" :key="c.id">{{ c.nama }} · <span class="text-muted">{{ c.alasan.join(", ") }}</span></li></ul>
      </div>
      <div class="mt-4 text-[13px] font-medium">Produk yang tidak dipakai & alasannya</div>
      <div class="mt-2 grid gap-4 lg:grid-cols-2">
        <div v-for="g in gugur" :key="g.w">
          <div class="text-[12px] text-muted">{{ g.nama }} ({{ g.isi.length }})</div>
          <ul class="m-0 mt-1 max-h-[320px] list-none space-y-1 overflow-y-auto p-0 text-[12px]">
            <li v-for="x in g.isi" :key="x.id" class="rounded-lg bg-surface-2 px-3 py-1.5">
              <div class="flex flex-wrap items-center justify-between gap-2"><span class="text-ink">{{ x.nama }}</span><TersediaDi v-if="x.platform?.length" :platform="x.platform" kecil /></div>
              <div class="text-muted">{{ x.alasan.join(", ") }}</div>
            </li>
          </ul>
        </div>
      </div>
    </section>

    <section class="panel px-4 py-5 sm:px-6">
      <div class="flex items-center gap-2 text-[14px] font-medium"><Database class="h-4 w-4 text-aksen" />Data & perhitungan</div>
      <ul class="m-0 mt-3 space-y-1.5 pl-4 text-[13px] leading-relaxed text-ink-2">
        <li><b class="font-medium text-ink">Indeks (2001–2026):</b> JII + perkiraan dividen 2,5%/th untuk Indonesia; indeks saham syariah global (DJIM Titans 100 sampai Jan 2008 + dividen 1,8%/th, lalu MSCI World Islamic) dalam rupiah, kurs akhir bulan. Biaya indeks diasumsikan 0,5–0,6%/th.</li>
        <li><b class="font-medium text-ink">Reksa dana (2016–2026):</b> harga bulanan resmi OJK (nilai aktiva bersih ÷ unit, sudah dikurangi biaya RD), termasuk RD yang sudah bubar.</li>
        <li v-if="infoKat"><b class="font-medium text-ink">Rata-rata RD sejenis, sisi global:</b> {{ infoKat.label_global }}.</li>
        <li><b class="font-medium text-ink">Setor rutin:</b> dihitung untuk setiap bulan mulai yang mungkin; setoran masuk awal bulan, dibagi 50/50, diseimbangkan tiap Desember.</li>
        <li><b class="font-medium text-ink">Angka paling hati-hati:</b> 5 tahun = yang lebih rendah antara produk di keranjang dan rata-rata RD sejenis; 10 tahun = yang terendah dari indeks, rata-rata RD sejenis, dan produk.</li>
      </ul>
      <div class="mt-4 flex items-start gap-2 rounded-2xl bg-kuning-bg px-4 py-3 text-[12px] leading-relaxed text-kuning">
        <AlertTriangle class="mt-0.5 h-4 w-4 shrink-0" />
        <div><b class="font-medium">Perubahan 8 Nov 2026:</b> pembanding global "rata-rata RD sejenis" diganti SETELAH melihat hasil. Versi lama mencampur RD Asia/China/ASEAN/India dan RD satu sektor yang justru dikeluarkan dari keranjang. Sekarang hanya RD global luas; karena jumlahnya kurang dari 5 per bulan, dipakai pengganti indeks MSCI World Islamic dikurangi biaya 2%/th. Angka versi lama tetap ditampilkan di tab Data historis.</div>
      </div>
      <div class="mt-4 text-[13px] font-medium">Keterbatasan</div>
      <ul class="m-0 mt-1 space-y-1 pl-4 text-[12px] leading-relaxed text-ink-2">
        <li>Data reksa dana global baru ada sejak 2016 (periode yang menguntungkan global); hasil 10 tahun dari produk hanya beberapa bulan mulai.</li>
        <li>Jalur indeks memakai perkiraan dividen dan biaya indeks, bukan biaya reksa dana nyata.</li>
        <li>Saringan syariah Indonesia (DES OJK) berbeda dengan standar indeks global (AAOIFI/DJIM/MSCI), meskipun keduanya syariah.</li>
        <li>Minimal beli dan ketersediaan di aplikasi berasal dari data publik dan bisa berubah. Biaya kurs bank saat beli/jual RD dolar tidak dihitung.</li>
      </ul>
      <div class="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-garis pt-4">
        <span class="text-[12px] text-muted">
          <template v-if="d">Dihitung {{ tglTeks(d.dihitung) }} · data s/d {{ bulanTeks(d.periode.kategori[1]) }} · keranjang dibentuk {{ tglTeks(d.keranjang?.dibentuk) }} ({{ d.keranjang?.alasan }}).</template>
          Diperbarui otomatis tiap hari kerja kalau ada data baru.
        </span>
        <button class="tombol" :disabled="kerja.sibuk.value" @click="emit('hitung')"><RefreshCw class="h-3.5 w-3.5" :class="kerja.sibuk.value ? 'animate-spin' : ''" />Hitung ulang</button>
      </div>
      <PanelPekerjaan class="mt-3" :kerja="kerja.kerja.value" :galat="kerja.galat.value" />
    </section>
  </div>
</template>

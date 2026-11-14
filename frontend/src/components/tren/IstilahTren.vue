<script setup>
import { ref, computed } from "vue";
import { Search } from "lucide-vue-next";
import Panel from "@/components/common/Panel.vue";

const props = defineProps({ tambahan: Array, nama: { type: String, default: "Follow Tren" } });
const cari = ref("");
const semua = ref(false);
const DASAR = [
  ["Close (harga penutupan)", "Harga terakhir di akhir hari bursa. Semua keputusan beli/jual memakai close final, dicek setelah pukul 17.00."],
  ["Open (harga pembukaan)", "Harga pertama saat bursa buka pagi hari. Beli dan jual Follow Tren dilakukan di harga ini."],
  ["Cut loss (CL)", "Menjual saham dalam keadaan rugi supaya ruginya tidak membesar. Di Follow Tren: batas jual tersentuh saat masih di bawah harga beli."],
  ["Take profit (TP)", "Menjual saham dalam keadaan untung. Di Follow Tren tidak ada target angka; TP terjadi saat batas jual yang sudah di atas harga beli tersentuh."],
  ["Hold", "Memegang saham yang sudah dibeli sambil menunggu sinyal jual."],
  ["Batas jual (stop)", "Harga patokan: kalau close jatuh di bawahnya, saham dijual besok pagi."],
  ["Trailing stop", "Batas jual yang ikut naik saat harga naik dan tidak pernah turun. Awalnya membatasi rugi, lalu mengunci untung."],
  ["ATR14 (Average True Range)", "Rata-rata jarak gerak harga per hari selama 14 hari terakhir, termasuk lompatan dari close kemarin. Saham Rp1.000 dengan ATR Rp30 biasanya bergerak ±3% sehari."],
  ["3×ATR", "Tiga kali gerak harian biasa. Dipakai sebagai jarak batas jual supaya saham tidak terjual hanya karena goyangan normal."],
  ["Titik impas (break even)", "Posisi ketika batas jual sudah sama dengan harga beli, jadi kalau dijual hasilnya kira-kira nol (sebelum biaya)."],
  ["Breakout 52 minggu", "Close hari ini menyamai atau melewati close tertinggi 250 hari bursa sebelumnya, alias rekor tertinggi setahun."],
  ["Sinyal", "Tanda bahwa saham memenuhi syarat beli (atau jual) hari ini. Tindakannya dilakukan besok pagi."],
  ["Hari bursa", "Hari bursa buka (Senin-Jumat, kecuali libur). 250 hari bursa ≈ 1 tahun, 20 hari bursa ≈ 1 bulan."],
  ["Gap", "Lompatan harga antara close kemarin dan open hari ini, misalnya karena berita semalam. Bisa membuat rugi lebih besar dari batas jual."],
  ["ARA / ARB", "Auto Rejection Atas / Bawah: batas naik / turun maksimal sehari dari bursa. 'Terkunci' = harga mentok di batas itu sepanjang hari, jadi hampir tidak bisa beli (ARA) atau jual (ARB)."],
  ["Tick", "Kenaikan harga terkecil yang diizinkan bursa: Rp1 (harga < 200), Rp2 (200-499), Rp5 (500-1.999), Rp10 (2.000-4.999), Rp25 (≥ 5.000). Model biaya menghitung beli 1 tick lebih mahal dan jual 1 tick lebih murah."],
  ["Fee", "Biaya broker + pajak: beli 0,15%, jual 0,25%. Ditambah selisih 1 tick per sisi, totalnya ±1,2% pulang-pergi (model konservatif; biaya realistis saham likuid ±0,9%, lihat Standar seragam f)."],
  ["Lot", "Satuan beli saham di BEI = 100 lembar."],
  ["Ekuitas", "Total nilai akun: kas + nilai semua saham yang sedang dipegang dengan harga close terakhir."],
  ["Posisi / slot", "Satu saham yang sedang dipegang = satu posisi. Follow Tren punya 10 slot; kalau penuh, sinyal baru dilewati."],
  ["Likuid / nilai transaksi", "Seberapa ramai saham diperdagangkan, diukur dari rata-rata nilai rupiah transaksi per hari."],
  ["Universe", "Kumpulan saham yang boleh dibeli hari itu (syariah + likuid + harga ≥ minimum + gerak wajar + aktif)."],
  ["DES OJK", "Daftar Efek Syariah dari OJK, diperbarui tiap Juni dan Desember. Hanya saham yang masuk DES pada hari sinyal yang boleh dibeli."],
  ["Seed acak", "Angka awal pengacak. Dengan seed yang sama (di sini tanggal), pilihan 'acak' bisa diulang persis."],
  ["Ex-date dividen", "Tanggal mulai saham diperdagangkan tanpa hak dividen. Posisi yang dipegang sebelum tanggal itu mendapat dividen."],
  ["Saham gocap", "Saham di harga terendah bursa (Rp50), biasanya sepi dan sulit dijual."],
  ["Win rate", "Persentase trade yang untung. Follow Tren hanya ±30-40%, tapi untung per trade jauh lebih besar dari ruginya."],
  ["Drawdown (turun terdalam)", "Seberapa jauh nilai modal turun dari titik tertingginya sebelum naik lagi."],
  ["CAGR", "Rata-rata pertumbuhan modal per tahun, seperti bunga majemuk."],
  ["Simulasi Monte Carlo", "Backtest diulang 100 kali dengan pilihan acak berbeda saat sinyal lebih banyak dari slot. Yang dilaporkan median dan rentangnya."],
  ["Backtest", "Menjalankan aturan pada data harga masa lalu untuk melihat hasilnya seandainya dulu dipakai."],
  ["Paper trade", "Menjalankan aturan setiap hari ke depan dengan uang pura-pura, untuk menguji tanpa risiko."],
];
const ISTILAH = computed(() => [...(props.tambahan || []), ...DASAR]);
const tampil = computed(() => {
  const q = cari.value.trim().toLowerCase();
  const a = q ? ISTILAH.value.filter(([k, v]) => k.toLowerCase().includes(q) || v.toLowerCase().includes(q)) : ISTILAH.value;
  return q || semua.value ? a : a.slice(0, 9);
});
</script>

<template>
  <Panel judul="Istilah" :ket="`Arti istilah yang dipakai di halaman ${nama}`">
    <template #aksi>
      <label class="flex h-8 items-center gap-2 rounded-full bg-surface-2 px-3 text-xs">
        <Search class="h-3.5 w-3.5 text-muted" /><input v-model="cari" class="w-40 bg-transparent outline-none" placeholder="Cari istilah…" />
      </label>
    </template>
    <dl class="m-0 grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3">
      <div v-for="i in tampil" :key="i[0]" class="rounded-2xl bg-surface-2 px-4 py-3">
        <dt class="text-[13px] font-medium">{{ i[0] }}</dt>
        <dd class="m-0 mt-1 text-xs leading-relaxed text-ink-2">{{ i[1] }}</dd>
      </div>
    </dl>
    <p v-if="!tampil.length" class="m-0 text-xs text-muted">Tidak ada istilah yang cocok.</p>
    <button v-if="!cari" class="mt-3 text-xs text-aksen hover:underline" @click="semua = !semua">{{ semua ? "Tampilkan lebih sedikit" : `Tampilkan semua ${ISTILAH.length} istilah` }}</button>
  </Panel>
</template>

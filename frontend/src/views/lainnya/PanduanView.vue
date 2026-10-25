<script setup>
import { ref, inject } from "vue";
import { ChevronDown } from "lucide-vue-next";
import Panel from "@/components/common/Panel.vue";

const pindahTab = inject("pindahTab");

const STRUKTUR = [
  ["Beranda", "Kondisi pasar hari ini (IHSG per menit, perputaran uang, saham paling naik/turun, sektor, pasar dunia), ringkasan semua menu, aktivitas, perawatan, dan sumber data.", "beranda"],
  ["Follow Tren", "Strategi saham syariah yang sedang diuji dengan uang pura-pura. Isinya Paper trade (dengan pantauan harga hari ini), Backtest (dengan simulasi modal), Aturan & variabel, dan Riset (semua ide yang pernah diuji).", "tren52"],
  ["Dividen", "Pemburu dividen saham syariah: daftar & kalender dividen, uji maju mulai 2027, kalkulator penghasilan, hasil uji, dan dividend trap.", "dividen"],
  ["Emiten", "Riset satu saham: profil, harga (per menit untuk hari ini), valuasi, dividen, fundamental, kepemilikan, dan riwayat sinyal Follow Tren.", "emiten"],
  ["Reksa Dana", "Katalog reksa dana syariah dengan skor, riwayat NAV sejak 2013, sukuk & SBN, pembanding semua pilihan, dan contoh alokasi.", "reksadana"],
  ["ETF", "ETF syariah Indonesia dan ETF luar negeri (yang bukan syariah diberi label), pembanding antar ETF, dan aturan pajak.", "etf"],
  ["Rencana", "Ide section yang belum dibangun beserta statusnya.", "rencana"],
];

const RUTIN = [
  ["Nyalakan Perbarui otomatis", "Di panel Perawatan, Beranda. Tiap hari bursa jam 17:30 semua data diperbarui, paper dicek ulang, dan database dibackup. Komputer harus menyala; kalau mati, jalan saat komputer hidup lagi."],
  ["Kalau manual: setelah jam 17:00 WIB", "Tekan \"Perbarui hari ini\" di Follow Tren → Paper trade. Harga penutupan baru final setelah bursa tutup."],
  ["Selama bursa buka", "Beranda, Emiten, dan Paper trade menampilkan harga per menit (tertunda ±10 menit). Ini hanya pantauan; transaksi paper tetap memakai harga penutupan final."],
  ["Kalau ada data yang perlu diperbarui", "Lihat Sumber data di bawah Beranda. Data yang tidak punya API (laporan keuangan, jadwal dividen, profil, NAV OJK) diambil lewat script di browser, lalu diimpor dengan tombol."],
  ["Seminggu sekali", "Lihat Zona normal di Paper trade. Normal = lanjut, Waspada = tetap jalankan aturan, Gagal = strategi dihentikan."],
  ["Jangan intervensi", "Pembelian dan penjualan dicatat otomatis sesuai aturan. Jangan memilih atau melewatkan sinyal."],
];

const ISTILAH = [
  ["ATR (Average True Range)", "Rata-rata gerak harga harian saham selama 14 hari. Saham liar punya ATR besar. Jarak stop Follow Tren = 3×ATR."],
  ["Trailing stop", "Batas jual yang ikut naik mengikuti harga tertinggi dan tidak pernah turun. Awalnya membatasi rugi, lalu mengunci untung."],
  ["Harga tertinggi 52 minggu", "Harga penutupan tertinggi dalam ±250 hari bursa terakhir. Menembusnya tanda tren naik yang kuat."],
  ["Open / Close", "Harga pembukaan dan penutupan bursa. Sinyal dihitung dari close, transaksi dilakukan di open hari berikutnya."],
  ["Intraday / per menit", "Harga selama bursa buka, diambil tiap menit dari Yahoo dan tertunda ±10 menit. Sesi 1 dan 2 dipisah istirahat siang (Jumat lebih panjang)."],
  ["ARA / ARB", "Batas naik/turun harian IDX. Kalau terkunci di batas itu, tidak bisa beli (ARA) atau tidak bisa jual (ARB)."],
  ["DES", "Daftar Efek Syariah dari OJK, diperbarui tiap 1 Juni dan 1 Desember. Semua saham di aplikasi ini disaring dengan DES."],
  ["KSEI", "Kustodian Sentral Efek Indonesia. Menerbitkan data kepemilikan saham bulanan per tipe investor."],
  ["Perputaran uang", "Total nilai transaksi saham dalam sehari. Ramai saat naik = minat beli kuat; ramai saat turun = tekanan jual."],
  ["Yield dividen", "Dividen setahun dibagi harga saham. Yield 10% = dividen Rp100 untuk harga Rp1.000."],
  ["Cum date / ex date", "Cum date = hari terakhir membeli untuk dapat dividen. Ex date = hari setelahnya; harga biasanya turun kira-kira sebesar dividen."],
  ["Dividend trap", "Dividen terlihat besar, tapi harga turun lebih dalam dari dividennya, jadi totalnya rugi."],
  ["Nilai wajar & margin of safety", "Perkiraan harga wajar dari laporan keuangan. Margin of safety = seberapa jauh harga sekarang di bawah nilai wajar."],
  ["PER / PBV", "Harga dibanding laba per saham (PER) dan dibanding nilai buku (PBV). Makin kecil makin murah, tapi bisa murah karena memang bermasalah."],
  ["NAV", "Nilai aktiva bersih per unit reksa dana. Naik-turunnya NAV = hasil reksa dana."],
  ["Reksa dana / sukuk / ETF", "Reksa dana = dana kelolaan manajer investasi. Sukuk = obligasi syariah (negara atau perusahaan). ETF = reksa dana yang diperdagangkan di bursa seperti saham."],
  ["CAGR", "Rata-rata pertumbuhan modal per tahun (majemuk)."],
  ["Drawdown / turun terdalam", "Seberapa jauh modal turun dari titik tertingginya sebelum pulih."],
  ["MAR", "Return per tahun dibagi drawdown terdalam. Makin besar makin baik."],
  ["Win rate", "Persentase trade yang untung."],
  ["Backtest", "Simulasi aturan di data masa lalu."],
  ["Holdout", "Data yang disimpan dan hanya dipakai sekali untuk menguji aturan yang sudah dikunci. Mencegah hasil bagus karena kebetulan."],
  ["Paper trade / uji maju", "Menjalankan aturan ke depan dengan uang pura-pura. Datanya belum terjadi saat aturan dikunci, jadi hasilnya paling jujur."],
  ["Zona normal", "Rentang hasil wajar paper trade dari ribuan simulasi ulang backtest. Dikunci sebelum paper berjalan."],
  ["Beli-tahan", "Pembanding: beli semua saham syariah likuid lalu didiamkan."],
  ["Biaya transaksi", "Fee beli 0,15% + jual 0,25% + selisih harga 1 tick per sisi. Rata-rata ±1,2% pulang-pergi."],
  ["Lot", "Satuan transaksi IDX = 100 lembar saham."],
];
const buka = ref(new Set());
function alih(i) {
  const s = new Set(buka.value);
  if (s.has(i)) s.delete(i);
  else s.add(i);
  buka.value = s;
}
</script>

<template>
  <div class="space-y-5">
    <p class="m-0 text-muted">Cara memakai aplikasi ini. Aturan tiap strategi ada di menunya masing-masing (mis. Follow Tren → Aturan & variabel). Klik baris di Struktur aplikasi untuk membuka menunya.</p>

    <Panel judul="Struktur aplikasi" rapat>
      <table class="tabel">
        <tbody>
          <tr v-for="s in STRUKTUR" :key="s[0]" class="cursor-pointer" @click="pindahTab(s[2])">
            <td class="!h-auto w-36 py-3 align-top font-medium">{{ s[0] }}</td>
            <td class="!h-auto !whitespace-normal py-3 text-ink-2">{{ s[1] }}</td>
          </tr>
        </tbody>
      </table>
    </Panel>

    <Panel judul="Rutinitas" rapat>
      <table class="tabel">
        <tbody>
          <tr v-for="(r, i) in RUTIN" :key="r[0]">
            <td class="w-8 text-muted">{{ i + 1 }}</td>
            <td class="!h-auto !whitespace-normal py-2.5"><div class="font-medium">{{ r[0] }}</div><div class="text-xs text-muted">{{ r[1] }}</div></td>
          </tr>
        </tbody>
      </table>
    </Panel>

    <Panel judul="Istilah" rapat>
      <div v-for="(x, i) in ISTILAH" :key="x[0]" class="border-t border-garis">
        <button class="flex h-12 w-full items-center justify-between gap-3 px-6 text-left font-medium transition-colors hover:bg-surface-2/60" @click="alih(i)">
          {{ x[0] }}<ChevronDown class="h-4 w-4 shrink-0 text-muted transition-transform" :class="buka.has(i) ? 'rotate-180' : ''" />
        </button>
        <p v-if="buka.has(i)" class="m-0 px-6 pb-4 text-ink-2">{{ x[1] }}</p>
      </div>
    </Panel>

    <p class="m-0 text-xs text-muted">Bukan nasihat keuangan. Semua angka dari backtest dan simulasi; hasil masa lalu tidak menjamin hasil ke depan.</p>
  </div>
</template>

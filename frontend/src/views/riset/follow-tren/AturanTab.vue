<script setup>
import { RotateCcw } from "lucide-vue-next";
import Panel from "@/components/common/Panel.vue";
import Kerangka from "@/components/common/Kerangka.vue";

defineProps({ s: Object });

const LANGKAH = [
  { judul: "Cari sinyal", isi: "Setiap sore, cari saham syariah likuid yang harga penutupannya menembus titik tertinggi 250 hari bursa terakhir (±1 tahun)." },
  { judul: "Beli di open besok", isi: "Beli di harga pembukaan hari berikutnya. Maksimal 10 saham, masing-masing ±10% modal. Kalau sinyal lebih banyak dari slot kosong, dipilih acak." },
  { judul: "Jual saat tren patah", isi: "Stop = close tertinggi sejak beli − 3×ATR. Stop ikut naik, tidak pernah turun. Kalau close di bawah stop, jual di open besok. Tidak ada target untung." },
];

const CONTOH = [
  ["Hari 1", "1.000", "1.000", "910", "Rugi maks -9%", ""],
  ["Hari 10", "1.150", "1.150", "1.060", "Untung +6% terkunci", "naik"],
  ["Hari 20", "1.400", "1.400", "1.310", "Untung +31% terkunci", "naik"],
  ["Hari 25", "1.350", "1.400", "1.310 (tetap)", "–", ""],
  ["Hari 30", "1.290", "1.400", "1.310, tembus", "Jual di open besok", "turun"],
  ["Hari 31", "Open 1.285", "", "", "Hasil ±28%", "naik"],
];

const RISIKO = [
  "Win rate cuma 30-40%. Rugi beruntun 10-16 kali pernah terjadi.",
  "Penurunan modal 30-40% dari puncak pernah terjadi, dan modal pernah hampir 3 tahun di bawah puncaknya (2021-2024).",
  "Untung datang dari sedikit trade yang naik puluhan sampai ratusan persen. Kalau trade besar itu terlewat, hasil setahun bisa negatif.",
  "Rugi per trade bisa -15% sampai -25% di saham volatil, terutama kalau jatuh tajam semalam atau kena ARB.",
  "Dihitung seperti paper, backtest 2020-2026 memberi 23% per tahun (konservatif 17%) dan 2010-2019 hanya 9% (sama dengan IHSG). Harapan realistis lebih rendah dari angka 2020-2026.",
  "Jangan ubah aturan di tengah jalan: melonggarkan stop, memasang target untung, atau memilih saham sendiri.",
];
</script>

<template>
  <div class="space-y-5">
    <div class="grid gap-5 md:grid-cols-3">
      <div v-for="(l, i) in LANGKAH" :key="l.judul" class="panel p-6">
        <div class="flex items-center gap-3">
          <span class="grid h-8 w-8 place-items-center rounded-full bg-aksen text-[13px] font-medium text-aksen-teks">{{ i + 1 }}</span>
          <span class="font-medium">{{ l.judul }}</span>
        </div>
        <p class="m-0 mt-2 text-ink-2">{{ l.isi }}</p>
      </div>
    </div>

    <template v-if="!s">
      <Kerangka v-for="i in 3" :key="i" panel jenis="tabel" :n="4" />
    </template>
    <Panel v-for="g in s?.variabel || []" :key="g.grup" :judul="g.grup" rapat>
      <div class="overflow-x-auto">
        <table class="tabel min-w-[860px]">
          <thead><tr><th class="w-44">Variabel</th><th class="w-[30%]">Nilai</th><th>Keterangan</th><th class="w-[24%]">Pembaruan</th></tr></thead>
          <tbody>
            <tr v-for="v in g.isi" :key="v.nama" class="align-top">
              <td class="!h-auto py-3 font-medium">{{ v.nama }}</td>
              <td class="!h-auto !whitespace-normal py-3">{{ v.nilai }}</td>
              <td class="!h-auto !whitespace-normal py-3 text-xs text-muted">{{ v.ket }}</td>
              <td class="!h-auto !whitespace-normal py-3 text-xs" :class="v.pembaruan?.startsWith('Tetap') ? 'text-muted' : 'text-ink-2'">{{ v.pembaruan }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </Panel>

    <Panel judul="Contoh trailing stop" ket="Beli di Rp1.000, ATR Rp30, jadi jarak stop 3 × 30 = Rp90 dari close tertinggi" rapat>
      <div class="overflow-x-auto">
        <table class="tabel min-w-[620px]">
          <thead><tr><th>Waktu</th><th class="!text-right">Close</th><th class="!text-right">Close tertinggi</th><th class="!text-right">Stop</th><th>Kalau kena stop</th></tr></thead>
          <tbody>
            <tr v-for="b in CONTOH" :key="b[0]">
              <td class="text-ink-2">{{ b[0] }}</td><td class="text-right">{{ b[1] }}</td><td class="text-right">{{ b[2] }}</td><td class="text-right">{{ b[3] }}</td>
              <td :class="b[5] === 'naik' ? 'text-naik' : b[5] === 'turun' ? 'font-medium text-turun' : 'text-muted'">{{ b[4] }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="m-0 px-6 pt-2 pb-3 text-xs text-muted">Selama harga naik, posisi dipegang tanpa batas atas. Penjualan terjadi sedikit di bawah puncak; itu ongkos supaya tidak keluar karena goyangan biasa.</p>
    </Panel>

    <div class="grid gap-5 lg:grid-cols-2">
      <Panel judul="Sengaja tidak dipakai" ket="Sudah diuji dan tidak memperbaiki hasil" rapat>
        <table class="tabel">
          <Kerangka v-if="!s" jenis="tabel" :n="4" />
          <tbody>
            <tr v-for="t in s?.tidak_dipakai || []" :key="t.nama" class="align-top">
              <td class="!h-auto !whitespace-normal py-3"><div class="font-medium">{{ t.nama }}</div><div class="text-xs text-muted">{{ t.hasil }}</div></td>
              <td class="!h-auto w-16 py-3 text-right"><span class="chip bg-turun-bg text-turun">{{ t.uji }}</span></td>
            </tr>
          </tbody>
        </table>
      </Panel>
      <Panel judul="Reset paper trade" ket="Cara kerja tombol Reset di halaman Paper trade">
        <template #aksi><RotateCcw class="h-4 w-4 text-muted" /></template>
        <ol class="m-0 list-decimal space-y-2 pl-5 text-ink-2">
          <li v-for="r in s?.reset || []" :key="r">{{ r }}</li>
        </ol>
      </Panel>
    </div>

    <Panel judul="Yang harus diterima">
      <ul class="m-0 list-disc space-y-1.5 pl-5 text-ink-2">
        <li v-for="x in RISIKO" :key="x">{{ x }}</li>
      </ul>
    </Panel>
  </div>
</template>

<script setup>
import { inject } from "vue";
import { ArrowRight } from "lucide-vue-next";
import Panel from "@/components/common/Panel.vue";

const pindahTab = inject("pindahTab");

const PERJALANAN = [
  { waktu: "Okt 2026", judul: "Uji data lama 2010-2019", isi: "Gagal tipis 6 dari 7 kriteria (tahun positif 67% < 70%), tapi CAGR 12,1% vs beli-tahan 8,1%.", status: "selesai" },
  { waktu: "Okt 2026", judul: "Uji data baru 2020-2026", isi: "Dibuka sekali sebagai pengecualian, aturan sama persis. Lulus 7 dari 7 kriteria.", status: "selesai" },
  { waktu: "21 Okt 2026", judul: "Paper trade dimulai", isi: "Uang pura-pura Rp100 jt, aturan dikunci, dijalankan tiap hari bursa.", status: "jalan" },
  { waktu: "Jan 2027", judul: "Cek eksekusi", isi: "Hari ke-63: batas GAGAL mulai berlaku.", status: "nanti" },
  { waktu: "Apr 2027", judul: "Cek tengah", isi: "Bandingkan dengan zona wajar backtest.", status: "nanti" },
  { waktu: "Okt 2027", judul: "Keputusan utama", isi: "Tidak pernah WASPADA/GAGAL → uang nyata kecil 10-20%.", status: "nanti" },
];
</script>

<template>
  <Panel judul="Hipotesis H11a: Follow Tren" ket="Apa yang diuji di backtest ini, dan sampai mana sekarang">
    <template #aksi><button class="tombol" @click="pindahTab('hipotesis', 'H11a')">Kriteria lengkap <ArrowRight class="h-3.5 w-3.5" /></button></template>
    <blockquote class="m-0 rounded-2xl border-l-4 border-aksen bg-surface-2 px-5 py-4 text-[14px] leading-relaxed">
      Saham syariah likuid yang harganya mencetak <b class="font-medium">rekor tertinggi setahun</b> cenderung melanjutkan kenaikan. Dengan
      <b class="font-medium">memotong rugi cepat</b> dan <b class="font-medium">membiarkan untung berjalan</b> lewat batas jual yang ikut naik,
      hasil totalnya mengalahkan memegang semua saham syariah secara rata, walau lebih sering rugi daripada untung.
    </blockquote>
    <div class="mt-5 label">Perjalanan uji</div>
    <ol class="m-0 mt-3 grid list-none gap-0 p-0 md:grid-cols-6">
      <li v-for="(j, i) in PERJALANAN" :key="j.judul" class="relative flex gap-3 pb-4 md:block md:pr-3 md:pb-0">
        <div class="flex flex-col items-center md:flex-row">
          <span class="z-10 grid h-6 w-6 shrink-0 place-items-center rounded-full text-[11px] font-medium"
            :class="j.status === 'selesai' ? 'bg-aksen text-aksen-teks' : j.status === 'jalan' ? 'bg-aksen-lembut text-aksen ring-2 ring-aksen' : 'bg-surface-2 text-muted'">{{ i + 1 }}</span>
          <span v-if="i < PERJALANAN.length - 1" class="w-0.5 flex-1 md:h-0.5 md:w-auto" :class="j.status === 'selesai' ? 'bg-aksen' : 'bg-garis'" />
        </div>
        <div class="min-w-0 md:mt-2">
          <div class="text-[11px] text-muted">{{ j.waktu }}<span v-if="j.status === 'jalan'" class="ml-1.5 chip bg-aksen-lembut text-aksen">sekarang</span></div>
          <div class="text-[13px] font-medium">{{ j.judul }}</div>
          <div class="mt-0.5 text-xs leading-relaxed text-ink-2">{{ j.isi }}</div>
        </div>
      </li>
    </ol>
  </Panel>
</template>

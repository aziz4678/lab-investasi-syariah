<script setup>
import { GitCompareArrows } from "lucide-vue-next";
import { persen, kelasPersen } from "@/utils/format";
import Logo, { kunciMi } from "@/components/common/Logo.vue";
import LencanaRD from "@/components/produk/LencanaRD.vue";
import TersediaDi from "@/components/produk/TersediaDi.vue";

defineProps({ r: Object, nomor: Number });
const emit = defineEmits(["buka", "banding"]);
const minBeli = (v) => (!v || v === "-" ? "–" : String(v).replace(/^Rp\.?\s*/i, "Rp").replace(/,-$/, ""));
const nol = (v) => (Math.abs(v) < 0.05 ? "0,0%" : persen(v, 1));
const usd = (r) => r.mata_uang === "USD";
const hasil3 = (r) => (usd(r) ? r.cagr_3_rp : r.cagr_3);
const turun = (r) => (usd(r) ? r.turun_terburuk_rp ?? r.turun_terburuk : r.turun_terburuk);
</script>

<template>
  <div class="panel row-span-4 grid min-w-0 grid-rows-subgrid gap-y-3 p-4">
    <button type="button" class="group flex min-w-0 items-start gap-3 text-left" @click="emit('buka', r.id)">
      <div class="relative shrink-0">
        <Logo jenis="mi" :kunci="kunciMi(r.mi)" :teks="r.mi" :ukuran="40" />
        <span v-if="nomor" class="absolute -top-1.5 -left-1.5 grid h-5 w-5 place-items-center rounded-full bg-aksen text-[11px] font-semibold text-aksen-teks ring-2 ring-surface">{{ nomor }}</span>
      </div>
      <div class="min-w-0 flex-1">
        <div class="line-clamp-2 text-[14px] leading-snug font-medium group-hover:text-aksen" :title="r.nama">{{ r.nama }}</div>
        <div class="mt-0.5 truncate text-[11px] text-muted">{{ r.mi }}<template v-if="r.mata_uang === 'USD'"> · dalam dolar AS</template></div>
      </div>
    </button>

    <div class="content-start">
      <LencanaRD :lencana="r.lencana" :peringatan="r.peringatan" kecil />
    </div>

    <div class="grid min-w-0 grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-x-4 gap-y-3 self-start rounded-2xl bg-surface-2 px-4 py-3">
      <div>
        <div class="text-[11px] text-muted" :title="usd(r) ? 'Rata-rata hasil per tahun 3 tahun terakhir, dalam rupiah (termasuk kurs), setelah biaya' : 'Rata-rata hasil per tahun selama 3 tahun terakhir, setelah biaya'">Rata-rata/th (3 th){{ usd(r) ? " · Rp" : "" }}</div>
        <div v-if="hasil3(r) != null" class="mt-0.5 text-[15px] font-medium tabular-nums" :class="kelasPersen(hasil3(r))">{{ persen(hasil3(r), 1) }}</div>
        <div v-else class="mt-0.5 text-[13px] text-muted" :title="r.ret_1th != null ? `Hasil 12 bulan terakhir ${persen(r.ret_1th, 1)}` : ''">data &lt; 3 th</div>
      </div>
      <div>
        <div class="text-[11px] text-muted" title="Penurunan terdalam dari titik tertinggi sepanjang riwayat (per akhir bulan)">Turun terburuk</div>
        <div class="mt-0.5 text-[15px] font-medium tabular-nums" :class="turun(r) < -0.05 ? 'text-turun' : ''">{{ turun(r) == null ? "–" : nol(turun(r)) }}</div>
      </div>
      <div>
        <div class="text-[11px] text-muted" title="Biaya pengelolaan per tahun (sudah dipotong dari NAV)">Biaya/th</div>
        <div class="mt-0.5 text-[15px] font-medium tabular-nums">{{ r.biaya == null ? "–" : persen(r.biaya, 2, false) }}</div>
      </div>
      <div class="min-w-0">
        <div class="text-[11px] text-muted" title="Minimal pembelian menurut data manajer investasi; di aplikasi bisa berbeda">Min. beli</div>
        <div class="mt-0.5 truncate text-[15px] font-medium tabular-nums">{{ minBeli(r.min_beli) }}</div>
      </div>
    </div>

    <div class="flex min-w-0 items-end justify-between gap-3 self-end border-t border-garis pt-3">
      <div class="min-w-0">
        <div class="mb-1.5 text-[11px] text-muted">Tersedia di</div>
        <TersediaDi :platform="r.platform" kecil />
      </div>
      <button class="inline-flex h-6 shrink-0 items-center gap-1 text-xs text-muted hover:text-aksen" @click="emit('banding', r.id)"><GitCompareArrows class="h-3.5 w-3.5" />Bandingkan</button>
    </div>
  </div>
</template>

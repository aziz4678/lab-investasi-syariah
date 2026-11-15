<script setup>
import { AlertTriangle } from "lucide-vue-next";

const props = defineProps({ kenapa: { type: Object, required: true } });

const KELAS_BADGE = { merah: "bg-turun-bg text-turun", hijau: "bg-naik-bg text-naik", abu: "bg-surface-2 text-muted" };
const pc = (v) => (v == null ? "tidak ada data" : `${v >= 0 ? "+" : ""}${v.toLocaleString("id-ID", { maximumFractionDigits: 1 })}%`);
const jenisSumber = () => (props.kenapa.harapan_jenis === "produk" ? "produk asli" : "pengganti (proksi)");
</script>

<template>
  <div class="mt-2 rounded-xl border border-garis px-3 py-2 text-[12px] leading-relaxed text-ink-2">
    <div class="flex flex-wrap items-center gap-1.5">
      <span class="chip" :class="KELAS_BADGE[kenapa.kondisi.warna]">{{ kenapa.kondisi.teks }}</span>
      <span class="text-[11px] text-muted">Kenapa beli ini</span>
    </div>
    <p class="m-0 mt-1 flex items-start gap-1.5" :class="kenapa.peringatan ? 'text-kuning' : ''">
      <AlertTriangle v-if="kenapa.peringatan" class="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span>{{ kenapa.kalimat }}</span>
    </p>
    <details class="mt-1.5">
      <summary class="cursor-pointer text-[11px] text-aksen">Selengkapnya</summary>
      <dl class="m-0 mt-1.5 space-y-1.5">
        <div>
          <dt class="text-[11px] font-medium text-ink">Perannya</dt>
          <dd class="m-0">{{ kenapa.peran }}</dd>
        </div>
        <div>
          <dt class="sr-only">Rekam jejak</dt>
          <dd class="m-0">{{ kenapa.harapan }}</dd>
          <dd v-if="kenapa.harapan_sumber" class="m-0 text-muted">Sumber angka: {{ jenisSumber() }}, {{ kenapa.harapan_sumber }}. Hasil masa lalu bukan janji.</dd>
        </div>
        <div>
          <dt class="text-[11px] font-medium text-ink">Setahun terakhir</dt>
          <dd class="m-0">Produk ini {{ pc(kenapa.ret_1th) }}<template v-if="kenapa.ret_dari_proksi"> (angka harga emas dunia dalam rupiah, ETF-nya belum setahun)</template>; {{ kenapa.nama_tolok }} {{ pc(kenapa.tolok_1th) }}.</dd>
          <dd v-if="kenapa.ket_tolok" class="m-0 text-muted">{{ kenapa.ket_tolok }}</dd>
          <dd v-if="kenapa.porsi != null || kenapa.biaya != null" class="m-0 text-muted">
            <template v-if="kenapa.porsi != null">Porsi {{ (kenapa.porsi * 100).toLocaleString("id-ID", { maximumFractionDigits: 0 }) }}% dari setoran.</template>
            <template v-if="kenapa.biaya != null"> Biaya {{ kenapa.biaya.toLocaleString("id-ID", { maximumFractionDigits: 2 }) }}% per tahun.</template>
          </dd>
        </div>
      </dl>
    </details>
  </div>
</template>

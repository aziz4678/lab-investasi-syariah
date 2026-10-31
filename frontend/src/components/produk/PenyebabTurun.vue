<script setup>
import { computed } from "vue";
import { TrendingDown, ArrowDownRight, TriangleAlert } from "lucide-vue-next";
import { persen } from "@/utils/format";

const props = defineProps({ p: Object, satuan: { type: String, default: "" } });
const catatan = computed(() => [...(props.p?.catatan || [])].sort((a, b) => b.tahun - a.tahun));
const LABEL = { rugi: "Rugi", melambat: "Melambat" };
</script>

<template>
  <div v-if="catatan.length || p?.tren" class="mt-5">
    <div class="mb-2 flex items-center gap-2 text-[13px] font-medium"><TrendingDown class="h-4 w-4 text-turun" />Kenapa turun?</div>
    <p v-if="p.tren" class="m-0 mb-3 flex gap-2 rounded-2xl bg-kuning-bg px-4 py-2.5 text-[13px] text-ink-2">
      <TriangleAlert class="mt-0.5 h-4 w-4 shrink-0 text-kuning" />
      <span>Hasil tahunan menurun <b class="font-medium text-ink">{{ p.tren.jumlah }} tahun berturut-turut</b> ({{ p.tren.tahun[0] }}–{{ p.tren.tahun.at(-1) }}).</span>
    </p>
    <div class="space-y-2">
      <details v-for="(c, i) in catatan" :key="c.tahun" class="group rounded-2xl border border-garis px-4 py-2.5" :open="i < 2">
        <summary class="flex cursor-pointer list-none flex-wrap items-center gap-x-3 gap-y-1 text-[13px]">
          <span class="font-medium">{{ c.tahun }}<span v-if="c.berjalan" class="text-[11px] font-normal text-muted"> (berjalan)</span></span>
          <span class="chip" :class="c.jenis === 'rugi' ? 'bg-turun-bg text-turun' : 'bg-kuning-bg text-kuning'">
            <ArrowDownRight class="h-3 w-3" />{{ LABEL[c.jenis] }}
          </span>
          <span class="tabular-nums" :class="c.ret < 0 ? 'text-turun' : 'text-ink-2'">{{ persen(c.ret, 1) }}{{ satuan }}</span>
          <span v-if="c.jenis === 'melambat' && c.sebelum != null" class="text-xs text-muted">dari {{ persen(c.sebelum, 1) }} tahun sebelumnya</span>
          <span class="ml-auto text-xs text-muted group-open:hidden">lihat penyebab</span>
        </summary>
        <ul class="m-0 mt-2 space-y-1 pl-5 text-[13px] leading-relaxed text-ink-2">
          <li v-for="a in c.alasan" :key="a.teks">{{ a.teks }}</li>
        </ul>
      </details>
    </div>
    <p class="m-0 mt-2 text-[11px] text-muted">Penyebab dirangkum dari peristiwa besar tahun itu, data pasar (suku bunga, JII, S&P 500, emas, kurs), dan perbandingan dengan produk sejenis. Penyebab persis tiap produk ada di fund fact sheet bulan-bulan tersebut.</p>
  </div>
</template>

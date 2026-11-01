<script setup>
import Panel from "@/components/common/Panel.vue";
import { persen, kelasPersen } from "@/utils/format";

defineProps({ b: Object });
const nilai = (label, v) => (label === "Sharpe" ? v.toFixed(2).replace(".", ",") : persen(v, 1));
const kelas = (label, v) => (label === "Sharpe" ? "" : kelasPersen(v));
</script>

<template>
  <Panel :judul="b?.judul" :ket="b?.ket" rapat>
    <div class="space-y-5 px-6 pb-5">
      <div class="flex flex-wrap items-center gap-2 rounded-2xl bg-kuning-bg px-4 py-2.5 text-xs text-ink-2">
        <span class="chip bg-surface text-ink">dibuat setelah lihat hasil</span>
        <span>Semua angka di bawah dihitung setelah data periode itu terlihat. Bukan bukti; bukti hanya dari paper trade.</span>
      </div>
      <div v-for="p in b?.periode || []" :key="p.judul" class="overflow-x-auto">
        <div class="mb-1 flex flex-wrap items-baseline gap-x-3"><span class="text-[13px] font-medium">{{ p.judul }}</span><span class="text-xs text-muted">{{ p.ket }}</span></div>
        <table class="tabel min-w-[640px]">
          <thead>
            <tr><th class="w-44"></th><th v-for="(k, i) in b.kolom" :key="k" class="!text-right" :class="i === 0 ? 'text-ink' : ''">{{ k }}</th></tr>
          </thead>
          <tbody>
            <tr v-for="r in p.baris" :key="r[0]">
              <td class="text-ink-2">{{ r[0] }}</td>
              <td v-for="(v, i) in r.slice(1)" :key="i" class="text-right tabular-nums" :class="[kelas(r[0], v), i === 0 ? 'font-medium' : '']">{{ nilai(r[0], v) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <ul class="m-0 list-disc space-y-1 pl-5 text-xs leading-relaxed text-ink-2">
        <li v-for="c in b?.catatan || []" :key="c">{{ c }}</li>
      </ul>
    </div>
  </Panel>
</template>

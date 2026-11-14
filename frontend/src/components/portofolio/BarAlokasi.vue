<script setup>
import { rupiahRingkas } from "@/utils/format";

defineProps({ alokasi: { type: Object, required: true } });

const WARNA = { lokal: "bg-s2", global: "bg-s4", emas: "bg-kuning", lainnya: "bg-garis" };
const persenTeks = (v) => (v == null ? "–" : `${(v * 100).toLocaleString("id-ID", { maximumFractionDigits: 1 })}%`);
const tandaTeks = (v) => (v == null ? "" : `${v >= 0 ? "+" : ""}${(v * 100).toLocaleString("id-ID", { maximumFractionDigits: 1 })} poin`);
</script>

<template>
  <div>
    <div v-if="alokasi.total > 0" class="space-y-3">
      <div v-for="k in alokasi.kaki" :key="k.kaki">
        <div class="flex items-center justify-between gap-3 text-[13px]">
          <span class="font-medium">{{ k.nama }}</span>
          <span class="tabular-nums text-ink-2">{{ rupiahRingkas(k.nilai) }} · {{ persenTeks(k.porsi) }}<template v-if="k.target != null"> · target {{ persenTeks(k.target) }}</template></span>
        </div>
        <div class="relative mt-1 h-3 rounded-full bg-surface-2">
          <div class="h-3 rounded-full" :class="WARNA[k.kaki] ?? 'bg-garis'" :style="{ width: `${Math.min((k.porsi ?? 0) * 100, 100)}%` }" />
          <div v-if="k.target != null" class="absolute -top-0.5 h-4 w-0.5 bg-ink" :style="{ left: `${k.target * 100}%` }" :title="`target ${persenTeks(k.target)}`" />
        </div>
        <div v-if="k.selisih_porsi != null" class="mt-0.5 text-[11px]" :class="Math.abs(k.selisih_porsi) < 0.02 ? 'text-muted' : 'text-kuning'">{{ tandaTeks(k.selisih_porsi) }} dari target</div>
      </div>
      <div v-if="alokasi.seimbang" class="rounded-2xl bg-naik-bg px-4 py-3 text-[13px] text-naik">Sudah dekat target. Tidak perlu menyeimbangkan.</div>
      <div v-else-if="alokasi.saran.length" class="rounded-2xl px-4 py-3 text-[13px] leading-relaxed" :class="alokasi.desember ? 'bg-kuning-bg text-kuning' : 'bg-surface-2 text-ink-2'">
        <div class="font-medium" :class="alokasi.desember ? '' : 'text-ink'">{{ alokasi.desember ? "Waktunya menyeimbangkan (Desember)" : "Selisih dari target (cukup info; seimbangkan tiap Desember)" }}</div>
        <ul class="m-0 mt-1 list-none space-y-0.5 p-0">
          <li v-for="s in alokasi.saran" :key="s.kaki">{{ s.aksi === "beli" ? "Tambah" : "Kurangi" }} {{ s.nama }} ±{{ rupiahRingkas(s.nominal) }}</li>
        </ul>
        <p v-if="!alokasi.desember" class="m-0 mt-1 text-[12px] text-muted">Tanpa menjual juga boleh: arahkan setoran berikutnya ke bagian yang tertinggal.</p>
      </div>
    </div>
    <p v-else class="m-0 text-[13px] text-muted">Belum ada nilai untuk dibandingkan dengan target.</p>
  </div>
</template>

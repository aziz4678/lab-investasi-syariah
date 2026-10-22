<script setup>
import Info from "./Info.vue";
import TeksWarna from "./TeksWarna.vue";
import { pecahAngka } from "../util.js";
defineProps({ items: Array, kolom: { type: String, default: "grid-cols-2 md:grid-cols-3 xl:grid-cols-6" }, polos: Boolean });
const WARNA = { naik: "text-naik", turun: "text-turun" };
const BERTANDA = /[+-]\d[\d.,]*%/g;

function jumlahTanda(s) {
  return (String(s ?? "").match(BERTANDA) || []).length;
}

function nada(s) {
  if (s.nada) return WARNA[s.nada];
  if (jumlahTanda(s.nilai) !== 1) return "";
  const v = String(s.nilai).trim();
  if (v.startsWith("+")) return "text-naik";
  return v.startsWith("-") && /[1-9]/.test(v) ? "text-turun" : "";
}
</script>

<template>
  <div :class="polos ? 'rounded-2xl bg-surface-2 px-1 py-1' : 'panel px-2 py-2'">
    <div class="grid" :class="kolom">
      <div v-for="s in items" :key="s.label" class="min-w-0 rounded-[18px] px-4 py-4 transition-colors hover:bg-surface-2/60">
        <div class="label flex items-center gap-1">{{ s.label }}<Info v-if="s.info" :teks="s.info" /></div>
        <div class="mt-1.5 truncate text-[clamp(17px,1.35vw,24px)] leading-8 font-medium tracking-tight tabular-nums" :class="nada(s)">
          <TeksWarna v-if="!s.nada && jumlahTanda(s.nilai) > 1" :teks="s.nilai" />
          <template v-else>{{ pecahAngka(s.nilai)[0] }}<span class="font-light opacity-50">{{ pecahAngka(s.nilai)[1] }}</span></template>
        </div>
        <div v-if="s.ket" class="mt-0.5 line-clamp-2 text-xs leading-snug text-muted" :title="s.ket"><TeksWarna :teks="s.ket" /></div>
      </div>
    </div>
  </div>
</template>

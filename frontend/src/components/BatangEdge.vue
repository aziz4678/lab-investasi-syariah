<script setup>
import { computed } from "vue";
import { persen } from "../util.js";

const props = defineProps({ grup: Array, judul: { type: String, default: "Dari return kotor ke bersih, per trade" } });

const baris = computed(() =>
  props.grup.map((a) => ({
    periode: a.periode,
    isi: [
      { l: "Kotor", v: a.kotor, k: "kotor" },
      ...(a.pemb != null ? [{ l: "Acak (pembanding)", v: a.pemb, k: "acak" }] : []),
      { l: "Biaya", v: -(a.kotor - a.net), k: "biaya" },
      { l: "Bersih", v: a.net, k: "bersih" },
    ],
  })),
);

const maks = computed(() => Math.max(0.5, ...baris.value.flatMap((b) => b.isi.map((x) => Math.abs(x.v)))));
const adaNeg = computed(() => baris.value.some((b) => b.isi.some((x) => x.v < 0)));
const adaPos = computed(() => baris.value.some((b) => b.isi.some((x) => x.v > 0)));
const nol = computed(() => (adaNeg.value && adaPos.value ? 50 : adaNeg.value ? 100 : 0));
const skala = computed(() => (adaNeg.value && adaPos.value ? 50 : 100) / maks.value);

function gaya(x) {
  const w = Math.abs(x.v) * skala.value;
  return x.v >= 0 ? { left: `${nol.value}%`, width: `${w}%` } : { left: `${nol.value - w}%`, width: `${w}%` };
}

const WARNA = { kotor: "bg-s2", acak: "bg-muted/50", biaya: "bg-turun/70" };
const kelas = (x) => WARNA[x.k] || (x.v >= 0 ? "bg-naik" : "bg-turun");
</script>

<template>
  <figure class="m-0">
    <figcaption class="mb-3 text-[13px] font-medium">{{ judul }}</figcaption>
    <div class="space-y-4">
      <div v-for="b in baris" :key="b.periode">
        <div v-if="baris.length > 1" class="mb-1.5 text-xs text-muted">{{ b.periode }}</div>
        <div class="space-y-1.5">
          <div v-for="x in b.isi" :key="x.l" class="grid grid-cols-[96px_1fr_64px] items-center gap-2 text-xs sm:grid-cols-[124px_1fr_68px]" :title="`${x.l}: ${persen(x.v, 2)}`">
            <span :class="x.k === 'bersih' ? 'font-medium text-ink' : 'text-ink-2'">{{ x.l }}</span>
            <span class="relative h-5 rounded-md bg-surface-2/70">
              <span class="absolute top-0 bottom-0 w-px bg-garis" :style="{ left: `${nol}%` }"></span>
              <span class="absolute top-0.5 bottom-0.5 rounded" :class="kelas(x)" :style="gaya(x)"></span>
            </span>
            <span class="text-right font-medium tabular-nums" :class="x.v > 0 ? 'text-naik' : x.v < 0 ? 'text-turun' : 'text-muted'">{{ persen(x.v, 2) }}</span>
          </div>
        </div>
      </div>
    </div>
    <p class="m-0 mt-2.5 text-xs text-muted">Biaya = kotor − bersih (fee + selisih 1 tick per sisi).</p>
  </figure>
</template>

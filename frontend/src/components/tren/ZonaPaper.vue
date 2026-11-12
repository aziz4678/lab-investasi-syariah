<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { ChevronDown } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { persen } from "@/utils/format";
import TeksWarna from "@/components/common/TeksWarna.vue";
import GrafikZona from "@/components/tren/GrafikZona.vue";

const props = defineProps({ muatUlang: Number });
const z = ref(null);
const buka = ref(false);
const bukaAturan = ref(false);

const muat = async () => {
  z.value = await ambil("paper/zona").catch(() => ({ ada: false }));
};
onMounted(muat);
watch(() => props.muatUlang, muat);

const ZONA = {
  normal: { l: "Normal", k: "bg-naik-bg text-naik", t: "Hasil paper masih dalam rentang wajar backtest." },
  waspada: { l: "Waspada", k: "bg-kuning-bg text-kuning", t: "Hasil paper di luar 95% rentang backtest. Tetap jalankan aturan, jangan diubah." },
  gagal: { l: "Gagal", k: "bg-turun-bg text-turun", t: "Aturan lama menyatakan gagal. Status resmi sejak 7 Nov 2026 memakai batas gagal v2 (kartu di atas)." },
  belum: { l: "Belum dinilai", k: "bg-surface-2 text-muted", t: "Penilaian mulai setelah ada hari bursa yang diproses." },
};

const hari = computed(() => z.value?.paper?.hari ?? 0);

const baris = computed(() => {
  const p = z.value?.paper;
  const b = z.value?.batas;
  if (!p || !b) return [];
  return [
    { l: "Return", v: persen(p.return.at(-1), 2), w: `wajar ≥ ${persen(b.ret_p5)} · gagal < ${persen(b.ret_p1)}`, k: p.hari >= 21 ? "" : "dinilai mulai hari ke-21" },
    { l: "Turun terdalam", v: persen(Math.min(...p.dd), 2), w: `wajar ≥ ${persen(b.dd_p5)} · gagal < ${persen(b.dd_p1)}` },
    { l: "Rugi beruntun", v: `${p.beruntun}x`, w: b.beruntun_p95 == null ? "belum ada trade selesai" : `wajar ≤ ${b.beruntun_p95}x · gagal > ${b.beruntun_p99}x` },
  ];
});
</script>

<template>
  <div v-if="z?.ada" class="panel px-6 py-4">
    <button class="flex w-full flex-wrap items-center gap-x-3 gap-y-1 text-left" @click="buka = !buka">
      <span class="text-[15px] font-medium">Pembanding: aturan lama h11a_v1</span>
      <span class="chip !h-6 !px-2.5 !text-xs" :class="ZONA[z.zona].k">{{ ZONA[z.zona].l }}</span>
      <span class="min-w-0 flex-1 text-xs text-muted">{{ ZONA[z.zona].t }}</span>
      <ChevronDown class="h-4 w-4 shrink-0 text-muted transition-transform" :class="buka ? 'rotate-180' : ''" />
    </button>
    <div v-if="buka" class="mt-4">
      <p class="m-0 mb-4 text-xs leading-relaxed text-muted">
        Rentang hasil wajar dari backtest, dikunci {{ z.dibuat.slice(0, 10) }} sebelum paper berjalan. Dihitung dari 5.000 simulasi ulang kurva harian backtest 2020-2026 (versi konservatif ARA/ARB) dengan cara paper.
        Sejak 7 Nov 2026 status resmi memakai aturan v2.
      </p>
      <ul v-if="z.alasan.length" class="m-0 mb-4 list-disc space-y-1 pl-5 text-[13px]" :class="z.zona === 'gagal' ? 'text-turun' : 'text-kuning'">
        <li v-for="a in z.alasan" :key="a">{{ a }}</li>
      </ul>
      <div class="mb-4 grid gap-2 sm:grid-cols-3">
        <div v-for="b in baris" :key="b.l" class="rounded-2xl bg-surface-2 px-4 py-3">
          <div class="text-xs text-muted">{{ b.l }} · hari ke-{{ hari }}</div>
          <div class="mt-0.5 text-[17px] font-medium tabular-nums"><TeksWarna :teks="b.v" /></div>
          <div class="text-[11px] text-muted"><TeksWarna :teks="b.w" /><span v-if="b.k"> · {{ b.k }}</span></div>
        </div>
      </div>
      <GrafikZona lama :muat-ulang="muatUlang" />
      <button class="mt-2 inline-flex items-center gap-1 text-xs text-muted hover:text-ink" @click="bukaAturan = !bukaAturan">
        Aturan yang dikunci<ChevronDown class="h-3.5 w-3.5 transition-transform" :class="bukaAturan ? 'rotate-180' : ''" />
      </button>
      <ol v-if="bukaAturan" class="m-0 mt-2 list-decimal space-y-1 pl-5 text-xs text-ink-2">
        <li v-for="a in z.aturan" :key="a">{{ a }}</li>
      </ol>
    </div>
  </div>
</template>

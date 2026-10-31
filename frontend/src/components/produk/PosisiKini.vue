<script setup>
import { computed } from "vue";
import { MapPin } from "lucide-vue-next";
import { persen, kelasPersen } from "@/utils/format";

const props = defineProps({ p: Object, rupiah: Boolean });
const bulan = (t) => (t ? new Date(t).toLocaleDateString("id-ID", { month: "long", year: "numeric" }) : "–");
const lama = (v) => (v == null ? "–" : v < 1 ? "kurang dari 1 bulan" : v < 12 ? `${Math.round(v)} bulan` : `${(v / 12).toFixed(1).replace(".", ",")} tahun`);
const ringkas = computed(() => {
  const p = props.p;
  if (!p || p.dekat_puncak || !p.n) return null;
  const t = [];
  t.push(`Sebelumnya produk ini pernah turun sedalam ini (atau lebih) ${p.n} kali.`);
  const biasa = p.n > 1 ? "biasanya " : "";
  if (p.median_pulih != null) t.push(`Dari titik penurunan yang sama, ${biasa}butuh ${lama(p.median_pulih)} untuk kembali ke puncak.`);
  if (p.n_12) t.push(p.n_12 > 1 ? `Kalau dibeli saat itu dan ditahan 1 tahun, ${p.naik_12} dari ${p.n_12} kali untung (biasanya ${persen(p.median_ret_12, 1)}).` : `Kalau dibeli saat itu dan ditahan 1 tahun, hasilnya ${persen(p.median_ret_12, 1)}.`);
  return t;
});
</script>

<template>
  <div v-if="p" class="mb-5 rounded-2xl border border-garis px-4 py-3">
    <div class="flex flex-wrap items-center gap-2">
      <MapPin class="h-4 w-4 text-aksen" />
      <span class="text-[13px] font-medium">Posisi sekarang</span>
      <span class="chip bg-surface-2 text-muted">insight · bukan ramalan</span>
    </div>
    <p v-if="p.dekat_puncak" class="m-0 mt-2 text-[13px] leading-relaxed text-ink-2">
      Sekarang <b class="font-medium text-ink">dekat titik tertingginya</b> ({{ Math.abs(p.turun_kini) < 0.05 ? "tepat di puncak" : `${persen(p.turun_kini, 1)} dari puncak` }} {{ bulan(p.puncak) }}{{ rupiah ? ", dalam rupiah" : "" }}). Tidak sedang dalam penurunan besar.
    </p>
    <template v-else>
      <p class="m-0 mt-2 text-[13px] leading-relaxed text-ink-2">
        Sekarang <b class="font-medium text-turun">{{ persen(-p.turun_kini, 1, false) }} di bawah puncaknya</b> ({{ bulan(p.puncak) }}{{ rupiah ? ", dalam rupiah" : "" }}), sudah turun selama {{ lama(p.bulan_sejak) }}.
      </p>
      <ul v-if="ringkas" class="m-0 mt-1.5 space-y-0.5 pl-5 text-[13px] leading-relaxed text-ink-2">
        <li v-for="t in ringkas" :key="t">{{ t }}</li>
      </ul>
      <p v-else class="m-0 mt-1.5 text-[13px] text-ink-2">Ini <b class="font-medium text-ink">penurunan terdalam</b> sejak data produk ini ada, jadi belum ada contoh dari masa lalu tentang berapa lama pulihnya.</p>
      <div v-if="p.kejadian?.length" class="mt-2 flex flex-wrap gap-1.5 text-xs">
        <span v-for="k in p.kejadian" :key="k.tanggal" class="chip bg-surface-2 text-ink-2" :title="`Mulai sedalam sekarang: ${k.tanggal}`">
          {{ k.tahun }}: terdalam {{ persen(k.terdalam, 1) }} · pulih {{ lama(k.bulan_pulih) }}<template v-if="k.ret_12 != null"> · 1 th kemudian <span :class="kelasPersen(k.ret_12)">{{ persen(k.ret_12, 1) }}</span></template>
        </span>
      </div>
      <p class="m-0 mt-2 text-[11px] text-muted"><template v-if="p.n">Hanya catatan masa lalu dari {{ p.n }} kejadian; penurunan kali ini bisa lebih dalam atau lebih lama. </template>Beli rutin tiap bulan lebih aman daripada menebak titik terendah.</p>
    </template>
  </div>
</template>

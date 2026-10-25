<script setup>
import { computed } from "vue";
import { pakaiTema } from "@/composables/tema";
import { warnaDivergen } from "@/utils/chart";
import { persen } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";

const props = defineProps({ ekuitas: Array, perTahun: Object });
const tema = pakaiTema();
const BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];

const baris = computed(() => {
  tema.value;
  const peta = {};
  for (const e of props.ekuitas || []) {
    const [th, bl] = e.bulan.split("-");
    (peta[th] ||= Array(12).fill(null))[Number(bl) - 1] = e.return;
  }
  return Object.keys(peta).sort().map((th) => ({
    tahun: th,
    sel: peta[th].map((v, i) => (v === null ? null : { v, bulan: BULAN[i], ...warnaDivergen(v, 15) })),
    total: props.perTahun ? props.perTahun[th] : null,
  }));
});
</script>

<template>
  <Panel judul="Return per bulan" ket="Hijau = untung, merah = rugi · warna penuh di ±15% · ekuitas harga pasar akhir bulan" rapat>
    <div class="overflow-x-auto px-6 pb-4">
      <table class="w-full min-w-[780px] border-separate border-spacing-1 text-xs tabular-nums">
        <thead>
          <tr class="text-muted">
            <th class="w-12"></th>
            <th v-for="b in BULAN" :key="b" class="pb-1 font-normal">{{ b }}</th>
            <th class="pb-1 font-normal">Tahun</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in baris" :key="r.tahun">
            <th class="pr-2 text-left font-normal text-muted">{{ r.tahun }}</th>
            <td v-for="(s, i) in r.sel" :key="i" class="h-9 min-w-[54px] rounded-xl text-center transition-transform hover:scale-105"
              :style="s ? { background: s.bg, color: s.fg } : {}" :title="s ? `${s.bulan} ${r.tahun}: ${persen(s.v)}` : ''">
              {{ s ? persen(s.v, 1) : "" }}
            </td>
            <td class="text-center font-medium" :class="r.total >= 0 ? 'text-naik' : 'text-turun'">{{ persen(r.total, 0) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </Panel>
</template>

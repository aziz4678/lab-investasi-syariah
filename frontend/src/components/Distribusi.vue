<script setup>
import { computed } from "vue";
import { Bar } from "vue-chartjs";
import { opsiDasar, warna, pakaiTema } from "../util.js";
import Panel from "./Panel.vue";

const props = defineProps({ distribusi: Array });
const tema = pakaiTema();

const data = computed(() => {
  tema.value;
  const d = props.distribusi || [];
  const puncak = Math.max(1, ...d.map((x) => x.jumlah));
  return {
    labels: d.map((x) => x.rentang + "%"),
    datasets: [
      {
        label: "Jumlah trade",
        data: d.map((x) => x.jumlah),
        order: 1,
        grouped: false,
        backgroundColor: d.map((x) =>
          warna(
            x.rentang.startsWith("-") || x.rentang.startsWith("<")
              ? "--turun"
              : "--naik",
          ),
        ),
        borderRadius: 999,
        borderSkipped: false,
        barPercentage: 0.55,
        categoryPercentage: 0.9,
      },
      {
        label: "lintasan",
        data: d.map(() => puncak * 1.08),
        order: 2,
        grouped: false,
        backgroundColor: warna("--surface-2"),
        borderRadius: 999,
        borderSkipped: false,
        barPercentage: 0.55,
        categoryPercentage: 0.9,
      },
    ],
  };
});

const opsi = computed(() => {
  tema.value;
  const o = opsiDasar();
  o.interaction = { mode: "index", intersect: false };
  o.scales.x.grid = { display: false };
  o.plugins.tooltip.filter = (c) => c.datasetIndex === 0;
  o.plugins.tooltip.callbacks = {
    title: (c) => `Hasil ${c[0].label}`,
    label: (c) => ` ${c.parsed.y} trade`,
  };
  return o;
});
</script>

<template>
  <Panel
    judul="Sebaran hasil trade"
    ket="Jumlah trade per rentang hasil"
    info="Banyak trade berakhir rugi kecil (merah); untung datang dari sedikit trade besar di kanan (hijau). Itu sebabnya tidak ada target untung dan stop tidak dilonggarkan."
  >
    <template #aksi>
      <span class="inline-flex items-center gap-1.5 text-xs text-muted"
        ><i class="h-2 w-2 rounded-full bg-turun"></i>Rugi</span
      >
      <span class="inline-flex items-center gap-1.5 text-xs text-muted"
        ><i class="h-2 w-2 rounded-full bg-naik"></i>Untung</span
      >
    </template>
    <div class="h-[250px]"><Bar :data="data" :options="opsi" /></div>
  </Panel>
</template>

<script setup>
import { ref, computed } from "vue";
import { Line } from "vue-chartjs";
import { opsiDasar, warna, pakaiTema, persen } from "../util.js";
import Panel from "./Panel.vue";
import Segmen from "./Segmen.vue";

const props = defineProps({ data: Array });
const tema = pakaiTema();
const rentang = ref("5t");
const RENTANG = [["1t", "1 thn"], ["3t", "3 thn"], ["5t", "5 thn"], ["semua", "Semua"]];
const BULAN = { "1t": 12, "3t": 36, "5t": 60 };

const SERI = [
  { k: "ritel", l: "Ritel lokal", v: "--series-4", ket: "Individu dalam negeri" },
  { k: "institusi", l: "Institusi lokal", v: "--series-2", ket: "Reksa dana, dana pensiun, asuransi, bank" },
  { k: "asing", l: "Asing", v: "--series-1", ket: "Semua investor luar negeri" },
  { k: "korporasi", l: "Korporasi lokal", v: "--series-3", ket: "Perusahaan dalam negeri", putus: true },
];

const potong = computed(() => {
  const d = props.data || [];
  return rentang.value === "semua" ? d : d.slice(-BULAN[rentang.value] - 1);
});

const grafik = computed(() => {
  tema.value;
  const d = potong.value;
  return {
    labels: d.map((x) => x.tgl.slice(0, 7)),
    datasets: SERI.map((s) => ({
      label: s.l, data: d.map((x) => x[s.k]), borderColor: warna(s.v), backgroundColor: warna(s.v), pointBackgroundColor: warna(s.v),
      pointHoverBorderColor: warna("--surface-1"), borderWidth: s.putus ? 1.5 : 2, borderDash: s.putus ? [5, 4] : undefined, pointRadius: 0, tension: 0.25,
    })),
  };
});

const opsi = computed(() => {
  tema.value;
  const o = opsiDasar();
  o.animation = false;
  o.scales.x.ticks.maxTicksLimit = 8;
  o.scales.y.ticks.callback = (v) => `${v}%`;
  o.plugins.tooltip.callbacks = { label: (c) => ` ${c.dataset.label}  ${persen(c.parsed.y, 1, false)}` };
  return o;
});

function ubah(k, n) {
  const d = props.data || [];
  if (d.length <= n) return null;
  return d.at(-1)[k] - d.at(-1 - n)[k];
}

const tabel = computed(() => {
  const d = props.data || [];
  if (!d.length) return [];
  const akhir = d.at(-1);
  return [
    ...SERI.map((s) => ({ ...s, nilai: akhir[s.k], b3: ubah(s.k, 3), b12: ubah(s.k, 12) })),
    { k: "lainnya", l: "Lainnya lokal", ket: "Sekuritas, yayasan, lain-lain", nilai: akhir.lainnya, b3: ubah("lainnya", 3), b12: ubah("lainnya", 12) },
    { k: "di_luar", l: "Di luar data KSEI", ket: "Biasanya saham pengendali / belum di penitipan kolektif", nilai: akhir.di_luar, b3: ubah("di_luar", 3), b12: ubah("di_luar", 12) },
  ];
});

const akhir = computed(() => (props.data || []).at(-1));
</script>

<template>
  <Panel judul="Kepemilikan saham" :ket="akhir ? `Data bulanan KSEI · persen dari jumlah saham · terakhir ${akhir.tgl}` : 'Data bulanan KSEI'"
    info="Informasi saja. Uji H15 menunjukkan perubahan kepemilikan institusi atau ritel tidak memprediksi harga setelah biaya.">
    <template #aksi><Segmen v-model="rentang" :pilihan="RENTANG" kecil /></template>
    <p v-if="!data?.length" class="m-0 text-muted">Belum ada data KSEI untuk saham ini.</p>
    <template v-else>
      <div class="mb-3 flex flex-wrap gap-2 text-xs text-ink-2">
        <span v-for="s in SERI" :key="s.k" class="inline-flex items-center gap-2 rounded-full bg-surface-2 px-3 py-1">
          <span v-if="s.putus" class="w-4 border-t-2 border-dashed" :style="{ borderColor: `var(${s.v})` }"></span>
          <span v-else class="h-0.5 w-4 rounded" :style="{ background: `var(${s.v})` }"></span>
          {{ s.l }} <b class="font-medium text-ink tabular-nums">{{ persen(akhir[s.k], 1, false) }}</b>
        </span>
      </div>
      <div class="h-[260px]"><Line :data="grafik" :options="opsi" /></div>
      <div class="-mx-6 mt-4 overflow-x-auto">
        <table class="tabel min-w-[520px]">
          <thead><tr><th>Pemegang</th><th class="!text-right">Porsi</th><th class="!text-right">Ubah 3 bulan</th><th class="!text-right">Ubah 1 tahun</th></tr></thead>
          <tbody>
            <tr v-for="r in tabel" :key="r.k">
              <td class="!h-auto !whitespace-normal py-2.5"><div class="font-medium">{{ r.l }}</div><div class="text-xs text-muted">{{ r.ket }}</div></td>
              <td class="text-right font-medium">{{ persen(r.nilai, 1, false) }}</td>
              <td class="text-right" :class="r.b3 > 0.05 ? 'text-naik' : r.b3 < -0.05 ? 'text-turun' : 'text-muted'">{{ r.b3 == null ? "–" : persen(r.b3, 2) }} poin</td>
              <td class="text-right" :class="r.b12 > 0.05 ? 'text-naik' : r.b12 < -0.05 ? 'text-turun' : 'text-muted'">{{ r.b12 == null ? "–" : persen(r.b12, 2) }} poin</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </Panel>
</template>

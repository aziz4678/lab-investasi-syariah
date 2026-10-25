<script setup>
import { ref, computed, onMounted } from "vue";
import { Line } from "vue-chartjs";
import { ambil } from "@/api/client";
import { persen, kelasPersen } from "@/utils/format";
import { pakaiTema } from "@/composables/tema";
import { opsiDasar, warna, gradien } from "@/utils/chart";
import Panel from "@/components/common/Panel.vue";
import Segmen from "@/components/common/Segmen.vue";
import Kerangka from "@/components/common/Kerangka.vue";

const tema = pakaiTema();
const data = ref(null);
const siap = ref(false);
const periode = ref("2020");
const porsi = ref(40);

onMounted(async () => {
  data.value = await ambil("rd/lapisan").catch(() => null);
  siap.value = true;
});

const p = computed(() => data.value?.periode?.[periode.value] || null);
const pilihan = computed(() => p.value?.baris.find((b) => b.porsi === porsi.value) || null);
const pilihanPeriode = computed(() => Object.entries(data.value?.periode || {}).map(([k, v]) => [k, v.label]));
const PILIH_PORSI = Array.from({ length: 11 }, (_, i) => [String(i * 10), `${i * 10}%`]);
const lulusInti = (b) => p.value?.patokan_inti != null && b.cagr >= p.value.patokan_inti;

const SERI = computed(() => [
  { label: `Campuran ${porsi.value}% Follow Tren`, data: p.value?.kurva[porsi.value], var: "--series-1", lebar: 2.5, putus: [], isi: true },
  { label: "100% inti", data: p.value?.kurva[0], var: "--series-2", lebar: 2, putus: [], isi: false },
  { label: "100% Follow Tren", data: p.value?.kurva[100], var: "--series-3", lebar: 1.5, putus: [], isi: false },
  { label: "Beli-tahan JII", data: p.value?.jii.kurva, var: "--series-4", lebar: 1.5, putus: [5, 4], isi: false },
]);

const dataGrafik = computed(() => {
  tema.value;
  if (!p.value) return { labels: [], datasets: [] };
  return {
    labels: p.value.bulan,
    datasets: SERI.value.map((s) => ({
      label: s.label, data: s.data, borderColor: warna(s.var), pointBackgroundColor: warna(s.var), pointHoverBorderColor: warna("--surface-1"),
      backgroundColor: s.isi ? gradien(s.var, 0.2) : "transparent", fill: s.isi ? "origin" : false, borderWidth: s.lebar, borderDash: s.putus,
      pointRadius: 0, tension: 0.3, cubicInterpolationMode: "monotone",
    })),
  };
});

const opsiGrafik = computed(() => {
  tema.value;
  const o = opsiDasar();
  o.scales.y.ticks.callback = (v) => `${(v / 100).toFixed(1)}x`;
  o.plugins.tooltip.callbacks = { label: (c) => ` ${c.dataset.label}  ${(c.parsed.y / 100).toFixed(2)}x` };
  return o;
});
</script>

<template>
  <Panel judul="Campuran lapisan: Follow Tren + inti" ket="Analisis, bukan uji · membantu menentukan porsi tiap lapisan · tidak mengubah status hipotesis apa pun">
    <template #aksi>
      <Segmen v-if="pilihanPeriode.length" v-model="periode" :pilihan="pilihanPeriode" kecil />
    </template>
    <Kerangka v-if="!siap" :n="4" />
    <p v-else-if="!p" class="m-0 text-muted">Data backtest Follow Tren belum tersedia. Tekan 'Hitung ulang backtest' di Perawatan.</p>
    <template v-else>
      <div class="rounded-2xl bg-surface-2 px-5 py-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="min-w-0">
            <div class="mb-2 text-xs text-muted">Porsi Follow Tren · sisanya inti {{ 100 - porsi }}% · diseimbangkan tiap Januari</div>
            <Segmen :model-value="String(porsi)" @update:model-value="porsi = Number($event)" :pilihan="PILIH_PORSI" kecil />
          </div>
        </div>
        <div v-if="pilihan" class="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div>
            <div class="text-xs text-muted">CAGR</div>
            <div class="text-xl font-medium tabular-nums" :class="kelasPersen(pilihan.cagr)">{{ persen(pilihan.cagr, 1) }}</div>
            <div class="text-[11px] text-muted">patokan inti {{ persen(p.patokan_inti, 1, false) }}</div>
          </div>
          <div>
            <div class="text-xs text-muted">Penurunan maks (bulanan)</div>
            <div class="text-xl font-medium tabular-nums" :class="kelasPersen(pilihan.dd)">{{ persen(pilihan.dd, 1) }}</div>
            <div class="text-[11px] text-muted">harian lebih dalam</div>
          </div>
          <div>
            <div class="text-xs text-muted">Tahun terburuk</div>
            <div class="text-xl font-medium tabular-nums" :class="kelasPersen(pilihan.terburuk)">{{ persen(pilihan.terburuk, 1) }}</div>
            <div class="text-[11px] text-muted">{{ pilihan.th_terburuk }}</div>
          </div>
          <div>
            <div class="text-xs text-muted">Tahun negatif</div>
            <div class="text-xl font-medium tabular-nums">{{ pilihan.th_negatif }} <span class="text-sm text-muted">dari {{ pilihan.th_lengkap }}</span></div>
            <div class="text-[11px] text-muted">tahun kalender penuh</div>
          </div>
        </div>
      </div>

      <div class="mt-5 flex flex-wrap gap-2">
        <span v-for="s in SERI" :key="s.label" class="inline-flex items-center gap-2 rounded-full bg-surface-2 py-1.5 pr-3 pl-2.5 text-xs text-ink-2">
          <i class="h-2 w-2 rounded-full" :style="{ background: `var(${s.var})` }"></i>{{ s.label }}
        </span>
      </div>
      <div class="mt-3 h-64"><Line :data="dataGrafik" :options="opsiGrafik" /></div>

      <div class="mt-5 overflow-x-auto">
        <table class="w-full text-[13px] tabular-nums">
          <thead>
            <tr class="text-left text-xs text-muted">
              <th class="py-2 pr-3 font-normal">Follow Tren / inti</th>
              <th class="py-2 pr-3 text-right font-normal">CAGR</th>
              <th class="py-2 pr-3 text-right font-normal">Penurunan maks</th>
              <th class="py-2 pr-3 text-right font-normal">Tahun terburuk</th>
              <th class="py-2 pr-3 text-right font-normal">Tahun negatif</th>
              <th class="py-2 text-right font-normal">≥ patokan inti</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="b in p.baris" :key="b.porsi" class="cursor-pointer border-t border-garis transition hover:bg-surface-2/60"
              :class="b.porsi === porsi ? 'bg-aksen-lembut' : ''" @click="porsi = b.porsi">
              <td class="py-2 pr-3">{{ b.porsi }}% / {{ 100 - b.porsi }}%</td>
              <td class="py-2 pr-3 text-right" :class="kelasPersen(b.cagr)">{{ persen(b.cagr, 1) }}</td>
              <td class="py-2 pr-3 text-right" :class="kelasPersen(b.dd)">{{ persen(b.dd, 1) }}</td>
              <td class="py-2 pr-3 text-right"><span :class="kelasPersen(b.terburuk)">{{ persen(b.terburuk, 1) }}</span> <span class="text-xs text-muted">{{ b.th_terburuk }}</span></td>
              <td class="py-2 pr-3 text-right">{{ b.th_negatif }} / {{ b.th_lengkap }}</td>
              <td class="py-2 text-right">{{ lulusInti(b) ? "ya" : "tidak" }}</td>
            </tr>
            <tr class="border-t border-garis text-muted">
              <td class="py-2 pr-3">Beli-tahan JII (pembanding)</td>
              <td class="py-2 pr-3 text-right" :class="kelasPersen(p.jii.cagr)">{{ persen(p.jii.cagr, 1) }}</td>
              <td class="py-2 pr-3 text-right" :class="kelasPersen(p.jii.dd)">{{ persen(p.jii.dd, 1) }}</td>
              <td class="py-2 pr-3 text-right"><span :class="kelasPersen(p.jii.terburuk)">{{ persen(p.jii.terburuk, 1) }}</span> <span class="text-xs">{{ p.jii.th_terburuk }}</span></td>
              <td class="py-2 pr-3 text-right">{{ p.jii.th_negatif }} / {{ p.jii.th_lengkap }}</td>
              <td class="py-2 text-right">—</td>
            </tr>
          </tbody>
        </table>
      </div>

      <details class="mt-4 rounded-2xl bg-surface-2 px-4 py-3 text-xs leading-relaxed text-ink-2">
        <summary class="cursor-pointer font-medium text-ink">Apa itu? Baca dulu sebelum memakai angka ini</summary>
        <ul class="m-0 mt-2 list-disc space-y-1 pl-4">
          <li>Ini hitungan campuran, bukan uji strategi. Tidak ada aturan baru yang diuji, dan hasilnya tidak mengubah status hipotesis apa pun.</li>
          <li>Follow Tren memakai kurva backtest contoh 1 simulasi (seed 7), yang ada di ujung atas 100 simulasi Monte Carlo. Median 2020-2026 lebih rendah (CAGR ±23,6%, penurunan harian ±-37,5%). Harapan realistis lebih rendah lagi.</li>
          <li>Penurunan maks dihitung dari nilai akhir bulan, jadi lebih dangkal daripada penurunan harian yang sebenarnya.</li>
          <li>Inti didekati dengan bunga antarbank − 1,5%/th (data reksa dana pasar uang baru ±1 tahun). Sukuk negara bisa memberi lebih, tapi harganya bisa turun.</li>
          <li>Patokan inti = rata-rata inflasi periode itu ({{ persen(p.inflasi, 1, false) }}) + 1,5%/th. Beli-tahan JII = indeks + dividen 2,5% − expense 2,0%.</li>
          <li>Tahun bertanda * belum genap 12 bulan.</li>
          <li>Penyeimbangan ulang tiap Januari dianggap tanpa biaya. Dev mulai 2011 karena 2010 adalah masa pemanasan sinyal 250 hari.</li>
        </ul>
      </details>
    </template>
  </Panel>
</template>

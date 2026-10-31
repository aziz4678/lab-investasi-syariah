<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { ambil } from "@/api/client";
import { persen, kelasPersen } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import BandingRD from "@/components/produk/BandingRD.vue";
import KalkulatorLapisan from "@/components/produk/KalkulatorLapisan.vue";

const baca = (k, awal) => {
  try {
    const v = localStorage.getItem(k);
    return v == null ? awal : JSON.parse(v);
  } catch {
    return awal;
  }
};
const bandingData = ref(null);
const makro = ref(null);
const deposito = ref(baca("rd_deposito", 4));
watch(deposito, (v) => {
  try {
    localStorage.setItem("rd_deposito", JSON.stringify(Number(v) || 0));
  } catch {
    return;
  }
});
onMounted(async () => {
  [bandingData.value, makro.value] = await Promise.all([ambil("rd/banding").catch(() => ({ data: [] })), ambil("makro").catch(() => ({}))]);
});
const opsiBanding = computed(() => {
  const o = [...(bandingData.value?.data || [])];
  const dep = Number(deposito.value) || 0;
  if (dep > 0) o.push({ nama: "Deposito syariah (angka kamu)", jenis: "Bank", hasil: dep * 0.8, risiko: 1, pajak: "Bagi hasil kena pajak final 20% (angka sudah setelah pajak)", catatan: "Dijamin LPS sampai batas tertentu; dicairkan sebelum jatuh tempo bisa kena penalti", dasar: `${dep}% sebelum pajak` });
  return o.sort((a, b) => (a.risiko - b.risiko) || ((b.hasil ?? 0) - (a.hasil ?? 0)));
});
const inflasi = computed(() => makro.value?.inflasi?.nilai ?? null);
const maksHasil = computed(() => Math.max(1, inflasi.value ?? 0, ...opsiBanding.value.map((x) => Math.abs(x.hasil ?? 0))));
const RISIKO = ["", "Sangat rendah", "Rendah", "Sedang", "Tinggi", "Sangat tinggi"];
</script>

<template>
  <div class="space-y-5">
    <BandingRD />

    <Panel judul="Tangga risiko: semua jenis investasi syariah" ket="Dari yang paling aman · reksa dana: nilai tengah hasil 12 bulan · sukuk: kupon/hasil kalau ditahan saat ini" rapat>
      <template #aksi>
        <label class="flex items-center gap-2 text-xs text-ink-2">Bagi hasil deposito <input v-model.number="deposito" type="number" min="0" max="15" step="0.25" class="!h-8 w-20 text-right tabular-nums" />%</label>
      </template>
      <Kerangka v-if="!bandingData" jenis="tabel" :n="8" />
      <div v-else class="overflow-x-auto">
        <table class="tabel min-w-[760px]">
          <thead><tr><th class="w-[46%]">Instrumen</th><th>Risiko</th><th>Hasil per tahun</th></tr></thead>
          <tbody>
            <tr v-for="o in opsiBanding" :key="o.nama">
              <td class="!h-auto !whitespace-normal py-3"><div class="font-medium">{{ o.nama }}</div><div class="text-[11px] text-muted">{{ o.jenis }} · {{ o.dasar }}</div><div class="mt-1 text-xs leading-relaxed text-ink-2">{{ o.catatan }}</div></td>
              <td class="!h-auto py-3 align-top"><div class="mt-1 flex items-center gap-1" :title="RISIKO[o.risiko]"><span v-for="i in 5" :key="i" class="h-2 w-2 rounded-full" :class="i <= o.risiko ? (o.risiko >= 4 ? 'bg-turun' : o.risiko >= 3 ? 'bg-kuning' : 'bg-naik') : 'bg-surface-3'"></span></div><div class="mt-1 text-[11px] text-muted">{{ RISIKO[o.risiko] }}</div></td>
              <td class="!h-auto !whitespace-normal py-3 align-top">
                <div class="mt-1 flex items-center gap-2">
                  <div class="relative h-2 flex-1 rounded-full bg-surface-2">
                    <div class="h-full rounded-full" :class="(o.hasil ?? 0) < 0 ? 'bg-turun' : 'bg-s1'" :style="{ width: `${(Math.abs(o.hasil ?? 0) / maksHasil) * 100}%` }"></div>
                    <div v-if="inflasi != null" class="absolute -top-1 h-4 w-0.5 rounded bg-kuning" :style="{ left: `${(inflasi / maksHasil) * 100}%` }" :title="`Inflasi ${persen(inflasi, 2, false)}`"></div>
                  </div>
                  <span class="w-16 text-right font-medium tabular-nums" :class="kelasPersen(o.hasil)">{{ o.hasil == null ? "–" : persen(o.hasil, 1) }}</span>
                </div>
                <div class="mt-1 text-[11px] text-muted"><template v-if="inflasi != null && o.hasil != null"><span :class="o.hasil >= inflasi ? 'text-naik' : 'text-kuning'">{{ o.hasil >= inflasi ? "di atas" : "di bawah" }} inflasi</span> · </template>{{ o.pajak }}</div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="inflasi != null" class="m-0 px-6 pt-3 text-xs text-muted">Garis kuning = inflasi tahunan {{ persen(inflasi, 2, false) }} (Bank Indonesia). Hasil di bawah garis ini berarti daya beli uangmu turun.</p>
      <p class="m-0 px-6 py-3 text-xs text-muted">Hasil 12 bulan saja bisa menyesatkan (misalnya saat pasar saham sedang turun). Lihat juga hasil 3 tahun di tab Semua reksa dana.</p>
    </Panel>

    <details class="panel px-6 py-4">
      <summary class="cursor-pointer text-[13px] font-medium">Lanjutan: kalkulator campuran lapisan (Follow Tren + sukuk/RD)</summary>
      <div class="mt-4"><KalkulatorLapisan /></div>
    </details>
  </div>
</template>

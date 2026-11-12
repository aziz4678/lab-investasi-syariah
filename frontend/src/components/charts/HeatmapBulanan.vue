<script setup>
import { computed } from "vue";
import { pakaiTema } from "@/composables/tema";
import { warnaDivergen } from "@/utils/chart";
import { persen } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";

const props = defineProps({ ekuitas: Array, perTahun: Object, catatan: String, terpilih: Object, trade: { type: Array, default: () => [] } });
const emit = defineEmits(["pilih"]);
const bisaKlik = computed(() => !!props.terpilih);
const aktif = (th, bl) => props.terpilih?.tahun === th && (props.terpilih?.bulan || 0) === bl;
const tema = pakaiTema();
const BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];

const petaTrade = computed(() => {
  const m = {};
  for (const t of props.trade) {
    if (t.status === "terbuka" || !t.tgl_jual) continue;
    (m[t.tgl_jual.slice(0, 7)] ||= []).push(t.net);
  }
  return m;
});
const infoTrade = (th, i) => {
  const a = petaTrade.value[`${th}-${String(i + 1).padStart(2, "0")}`];
  if (!a?.length) return "tidak ada trade selesai bulan ini";
  return `${a.length} trade selesai bulan ini · rata-rata hasil ${persen(a.reduce((s, x) => s + x, 0) / a.length, 1)}`;
};

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
  <Panel judul="Return per bulan" :ket="`Hijau = untung, merah = rugi · warna penuh di ±15% · ekuitas harga pasar akhir bulan${catatan ? ` · ${catatan}` : ''}${bisaKlik ? ' · klik bulan atau tahun untuk melihat rinciannya' : ''}`" rapat>
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
            <th class="pr-2 text-left font-normal text-muted"><button v-if="bisaKlik" class="rounded-lg px-1 hover:text-aksen" :class="aktif(r.tahun, 0) ? 'font-medium text-aksen' : ''" title="Lihat trade tahun ini" @click="emit('pilih', r.tahun, 0)">{{ r.tahun }}</button><template v-else>{{ r.tahun }}</template></th>
            <td v-for="(s, i) in r.sel" :key="i" class="h-9 min-w-[54px] rounded-xl text-center transition-transform hover:scale-105"
              :class="[s && bisaKlik ? 'cursor-pointer' : '', s && aktif(r.tahun, i + 1) ? 'ring-2 ring-ink ring-offset-2 ring-offset-surface' : '']"
              :style="s ? { background: s.bg, color: s.fg } : {}" :title="s ? `${s.bulan} ${r.tahun}: ${persen(s.v)}\n${infoTrade(r.tahun, i)}${bisaKlik ? '\nklik untuk melihat rinciannya' : ''}` : ''"
              @click="s && bisaKlik && emit('pilih', r.tahun, i + 1)">
              {{ s ? persen(s.v, 1) : "" }}
            </td>
            <td class="text-center font-medium" :class="[r.total >= 0 ? 'text-naik' : 'text-turun', bisaKlik ? 'cursor-pointer hover:underline' : '']" @click="bisaKlik && emit('pilih', r.tahun, 0)">{{ persen(r.total, 0) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </Panel>
</template>

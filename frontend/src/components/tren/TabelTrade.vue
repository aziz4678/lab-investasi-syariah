<script setup>
import KodeSaham from "@/components/common/KodeSaham.vue";
import { ref, computed, watch } from "vue";
import { persen, rupiah, tanggal } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";

const props = defineProps({ trade: Array });
const tahun = ref("");
const cari = ref("");
const status = ref("");
const urut = ref({ kunci: "tgl_sinyal", naik: false });
const halaman = ref(1);
const PER = 50;

const daftarTahun = computed(() => [...new Set((props.trade || []).map((t) => t.tgl_sinyal.slice(0, 4)))].sort().reverse());

const tersaring = computed(() => {
  let t = props.trade || [];
  if (tahun.value) t = t.filter((x) => x.tgl_sinyal.startsWith(tahun.value));
  if (cari.value) t = t.filter((x) => x.ticker.includes(cari.value.toUpperCase()));
  if (status.value) t = t.filter((x) => x.status === status.value);
  const { kunci, naik } = urut.value;
  return [...t].sort((a, b) => (a[kunci] > b[kunci] ? 1 : a[kunci] < b[kunci] ? -1 : 0) * (naik ? 1 : -1));
});

const ringkas = computed(() => {
  const t = tersaring.value.filter((x) => x.status !== "terbuka");
  if (!t.length) return null;
  const m = t.filter((x) => x.net > 0);
  const rata = (a) => a.reduce((s, x) => s + x.net, 0) / (a.length || 1);
  return { n: tersaring.value.length, wr: (m.length / t.length) * 100, rata: rata(t), menang: rata(m), kalah: rata(t.filter((x) => x.net <= 0)) };
});

const tampil = computed(() => tersaring.value.slice((halaman.value - 1) * PER, halaman.value * PER));
const jumlahHal = computed(() => Math.max(1, Math.ceil(tersaring.value.length / PER)));
watch([tahun, cari, status], () => (halaman.value = 1));

function urutkan(k) {
  urut.value = { kunci: k, naik: urut.value.kunci === k ? !urut.value.naik : false };
}

const KOLOM = [
  ["ticker", "Saham", 0], ["tgl_beli", "Tanggal beli", 0], ["harga_beli", "Harga beli", 1], ["tgl_jual", "Tanggal jual", 0],
  ["harga_jual", "Harga jual", 1], ["hari", "Hari", 1], ["stop_awal_pct", "Stop awal", 1], ["net", "Hasil", 1], ["status", "Status", 0],
];
</script>

<template>
  <Panel judul="Daftar trade" ket="Trade yang masuk portofolio · klik judul kolom untuk mengurutkan · net sudah dipotong biaya" rapat>
    <template #aksi>
      <select v-model="tahun"><option value="">Semua tahun</option><option v-for="t in daftarTahun" :key="t" :value="t">{{ t }}</option></select>
      <select v-model="status"><option value="">Semua status</option><option value="selesai">Selesai</option><option value="terbuka">Masih dipegang</option></select>
      <input v-model="cari" placeholder="Cari saham" class="w-32" />
    </template>
    <div v-if="ringkas" class="flex flex-wrap gap-x-6 gap-y-1 px-6 pb-3 text-xs text-muted tabular-nums">
      <span>{{ ringkas.n }} trade</span>
      <span>Win rate <b class="font-medium text-ink">{{ persen(ringkas.wr, 0, false) }}</b></span>
      <span>Rata-rata <b class="font-medium" :class="ringkas.rata >= 0 ? 'text-naik' : 'text-turun'">{{ persen(ringkas.rata, 2) }}</b></span>
      <span>Menang <b class="font-medium text-naik">{{ persen(ringkas.menang) }}</b></span>
      <span>Kalah <b class="font-medium text-turun">{{ persen(ringkas.kalah) }}</b></span>
    </div>
    <div class="overflow-x-auto">
      <table class="tabel min-w-[780px]">
        <thead>
          <tr>
            <th v-for="[k, l, al] in KOLOM" :key="k" @click="urutkan(k)" class="cursor-pointer select-none hover:text-ink"
              :class="[al ? '!text-right' : '', urut.kunci === k ? '!text-ink' : '']">
              {{ l }}<span v-if="urut.kunci === k" class="ml-0.5">{{ urut.naik ? "↑" : "↓" }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in tampil" :key="t.ticker + t.tgl_sinyal">
            <td><KodeSaham :kode="t.ticker" /></td>
            <td class="text-ink-2">{{ tanggal(t.tgl_beli) }}</td>
            <td class="text-right">{{ rupiah(t.harga_beli) }}</td>
            <td class="text-ink-2">{{ t.status === "terbuka" ? "–" : tanggal(t.tgl_jual) }}</td>
            <td class="text-right">{{ rupiah(t.harga_jual) }}</td>
            <td class="text-right text-ink-2">{{ t.hari }}</td>
            <td class="text-right text-turun/80">{{ persen(-t.stop_awal_pct, 1) }}</td>
            <td class="text-right font-medium" :class="t.net >= 0 ? 'text-naik' : 'text-turun'">{{ persen(t.net) }}</td>
            <td><span class="chip" :class="t.status === 'terbuka' ? 'bg-aksen-lembut text-aksen' : 'bg-surface-2 text-muted'">{{ t.status === "terbuka" ? "Dipegang" : "Selesai" }}</span></td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="flex items-center justify-end gap-2 px-6 pt-2 pb-3 text-xs text-muted">
      <span>Halaman {{ halaman }} dari {{ jumlahHal }}</span>
      <button class="tombol !h-8 !w-8 !justify-center !px-0" :disabled="halaman <= 1" @click="halaman--">‹</button>
      <button class="tombol !h-8 !w-8 !justify-center !px-0" :disabled="halaman >= jumlahHal" @click="halaman++">›</button>
    </div>
  </Panel>
</template>

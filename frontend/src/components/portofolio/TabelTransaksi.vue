<script setup>
import { ref, computed } from "vue";
import { Pencil, Trash2, Check, X, ChevronRight } from "lucide-vue-next";
import { rupiahRingkas } from "@/utils/format";
import { kelompokPerBulan, batasiBulan, MAKS_BULAN_DEFAULT } from "@/utils/portofolioSaya";

const props = defineProps({ transaksi: { type: Array, default: () => [] }, baca: Boolean });
const emit = defineEmits(["ubah", "hapus"]);
const konfirmasi = ref("");
const semua = ref(false);
const diatur = ref({});

const kelompok = computed(() => kelompokPerBulan(props.transaksi));
const tampil = computed(() => batasiBulan(kelompok.value, semua.value));
const terbuka = (g) => diatur.value[g.kunci] ?? g.kunci === kelompok.value[0]?.kunci;
const balik = (g) => {
  diatur.value = { ...diatur.value, [g.kunci]: !terbuka(g) };
};

const tglTeks = (s) => (s ? new Date(s).toLocaleDateString("id-ID", { day: "numeric", month: "short" }) : "–");
const unitTeks = (t) => (t.unit_hitung == null ? "–" : t.unit_hitung.toLocaleString("id-ID", { maximumFractionDigits: 4 }));
const rpLengkap = (v) => (v == null ? "–" : `Rp${Math.round(v).toLocaleString("id-ID")}`);
const hapus = (t) => {
  konfirmasi.value = "";
  emit("hapus", t);
};
</script>

<template>
  <div>
    <div v-if="transaksi.length" class="space-y-2">
      <section v-for="g in tampil" :key="g.kunci" class="overflow-hidden rounded-2xl border border-garis">
        <button type="button" class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition hover:bg-surface-2" :aria-expanded="terbuka(g)" @click="balik(g)">
          <span class="flex min-w-0 items-center gap-2 text-[13px] font-medium"><ChevronRight class="h-4 w-4 shrink-0 transition" :class="terbuka(g) ? 'rotate-90' : ''" />{{ g.label }}</span>
          <span class="shrink-0 text-[12px] text-ink-2 tabular-nums">{{ g.jumlah }} transaksi · {{ rupiahRingkas(g.total) }}</span>
        </button>
        <div v-if="terbuka(g)" class="overflow-x-auto border-t border-garis px-4 pb-2">
          <table class="w-full min-w-[560px] border-collapse text-[12px]">
            <thead>
              <tr class="text-left text-muted">
                <th class="py-1.5 pr-2 font-normal">Tgl</th>
                <th class="px-2 font-normal">Produk</th>
                <th class="px-2 font-normal">Aplikasi</th>
                <th class="px-2 text-right font-normal">Nominal</th>
                <th class="px-2 text-right font-normal">Unit</th>
                <th v-if="!baca" class="pl-2 text-right font-normal"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="t in g.baris" :key="t._id" class="border-t border-garis align-top">
                <td class="py-2 pr-2 whitespace-nowrap">{{ tglTeks(t.tanggal) }}</td>
                <td class="px-2 py-2"><span class="chip mr-1" :class="t.jenis === 'beli' ? 'bg-naik-bg text-naik' : 'bg-turun-bg text-turun'">{{ t.jenis }}</span>{{ t.nama }}
                  <div v-if="t.catatan" class="text-[11px] text-muted">{{ t.catatan }}</div></td>
                <td class="px-2 py-2">{{ t.aplikasi }}</td>
                <td class="px-2 py-2 text-right tabular-nums">{{ rpLengkap(t.nominal) }}<div v-if="t.biaya" class="text-[11px] text-muted">biaya {{ rpLengkap(t.biaya) }}</div></td>
                <td class="px-2 py-2 text-right tabular-nums">
                  <template v-if="t.status_unit === 'menunggu_nav'"><span class="chip bg-kuning-bg text-kuning" title="Harga unit belum terbit; dihitung otomatis begitu tersedia">menunggu NAV</span></template>
                  <template v-else>{{ unitTeks(t) }}</template>
                </td>
                <td v-if="!baca" class="py-2 pl-2 text-right whitespace-nowrap">
                  <template v-if="konfirmasi === t._id">
                    <span class="mr-1 text-[11px] text-turun">Hapus?</span>
                    <button class="tombol !h-7" aria-label="Ya, hapus" @click="hapus(t)"><Check class="h-3.5 w-3.5" /></button>
                    <button class="tombol !h-7" aria-label="Batal" @click="konfirmasi = ''"><X class="h-3.5 w-3.5" /></button>
                  </template>
                  <template v-else>
                    <button class="tombol !h-7" aria-label="Ubah transaksi" @click="emit('ubah', t)"><Pencil class="h-3.5 w-3.5" /></button>
                    <button class="tombol !h-7" aria-label="Hapus transaksi" @click="konfirmasi = t._id"><Trash2 class="h-3.5 w-3.5" /></button>
                  </template>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
      <button v-if="kelompok.length > MAKS_BULAN_DEFAULT" type="button" class="tombol" @click="semua = !semua">{{ semua ? `Tampilkan ${MAKS_BULAN_DEFAULT} bulan terakhir saja` : `Tampilkan semua (${kelompok.length} bulan)` }}</button>
    </div>
    <p v-else class="m-0 text-[13px] text-muted">Belum ada transaksi. Catat pembelian pertamamu dengan tombol "Catat transaksi".</p>
  </div>
</template>

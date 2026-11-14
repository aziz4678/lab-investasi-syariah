<script setup>
import { ref } from "vue";
import { Pencil, Trash2, Check, X } from "lucide-vue-next";
import { rupiahRingkas } from "@/utils/format";

defineProps({ transaksi: { type: Array, default: () => [] } });
const emit = defineEmits(["ubah", "hapus"]);
const konfirmasi = ref("");

const tglTeks = (s) => (s ? new Date(s).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }) : "–");
const unitTeks = (t) => (t.unit_hitung == null ? "–" : t.unit_hitung.toLocaleString("id-ID", { maximumFractionDigits: 4 }));
const rpLengkap = (v) => (v == null ? "–" : `Rp${Math.round(v).toLocaleString("id-ID")}`);
const hapus = (t) => {
  konfirmasi.value = "";
  emit("hapus", t);
};
</script>

<template>
  <div>
    <div v-if="transaksi.length" class="overflow-x-auto">
      <table class="w-full min-w-[640px] border-collapse text-[12px]">
        <thead>
          <tr class="text-left text-muted">
            <th class="py-1.5 pr-2 font-normal">Tanggal</th>
            <th class="px-2 font-normal">Produk</th>
            <th class="px-2 font-normal">Aplikasi</th>
            <th class="px-2 text-right font-normal">Nominal</th>
            <th class="px-2 text-right font-normal">Unit</th>
            <th class="px-2 text-right font-normal">Biaya</th>
            <th class="pl-2 text-right font-normal"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in transaksi" :key="t._id" class="border-t border-garis align-top">
            <td class="py-2 pr-2 whitespace-nowrap">{{ tglTeks(t.tanggal) }}</td>
            <td class="px-2 py-2"><span class="chip mr-1" :class="t.jenis === 'beli' ? 'bg-naik-bg text-naik' : 'bg-turun-bg text-turun'">{{ t.jenis }}</span>{{ t.nama }}
              <div v-if="t.catatan" class="text-[11px] text-muted">{{ t.catatan }}</div></td>
            <td class="px-2 py-2">{{ t.aplikasi }}</td>
            <td class="px-2 py-2 text-right tabular-nums">{{ rpLengkap(t.nominal) }}</td>
            <td class="px-2 py-2 text-right tabular-nums">
              <template v-if="t.status_unit === 'menunggu_nav'"><span class="chip bg-kuning-bg text-kuning" title="Harga unit belum terbit; dihitung otomatis begitu tersedia">menunggu NAV</span></template>
              <template v-else>{{ unitTeks(t) }}</template>
            </td>
            <td class="px-2 py-2 text-right tabular-nums">{{ rpLengkap(t.biaya) }}</td>
            <td class="py-2 pl-2 text-right whitespace-nowrap">
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
    <p v-else class="m-0 text-[13px] text-muted">Belum ada transaksi. Catat pembelian pertamamu lewat formulir di atas.</p>
  </div>
</template>

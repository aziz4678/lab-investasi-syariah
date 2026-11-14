<script setup>
import { computed } from "vue";
import { rupiahRingkas, rupiahBertanda } from "@/utils/format";
import Pemutar from "@/components/common/Pemutar.vue";
import GrafikBanding from "@/components/charts/GrafikBanding.vue";
import BarAlokasi from "@/components/portofolio/BarAlokasi.vue";
import TabelTransaksi from "@/components/portofolio/TabelTransaksi.vue";

const props = defineProps({ a: { type: Object, required: true }, memuat: Boolean, baca: Boolean });
const emit = defineEmits(["ubah", "hapus"]);

const NAMA_KAKI = { lokal: "Saham Indonesia", global: "Saham global", emas: "Emas", lainnya: "Lainnya" };
const kelasUntung = (v) => (v == null ? "" : v >= 0 ? "text-naik" : "text-turun");
const adaTransaksi = computed(() => (props.a.transaksi?.length ?? 0) > 0);
const pb = computed(() => props.a.pembanding);
const grafik = computed(() => {
  const d = props.a.deret ?? [];
  if (d.length < 2) return null;
  return { label: d.map((x) => x.tgl), seri: { "Nilai sekarang": d.map((x) => Math.round(x.nilai)), "Total setor": d.map((x) => Math.round(x.setor)) } };
});
</script>

<template>
  <div class="space-y-5">
    <section id="alokasi" class="space-y-5">
      <div class="panel px-4 py-5 sm:px-6" data-bagian="alokasi">
        <div class="text-[14px] font-medium">Alokasi nyata vs target</div>
        <p class="m-0 mt-1 mb-3 text-[12px] text-muted">{{ a.nama_target }}. Garis hitam = target.</p>
        <BarAlokasi v-if="a.alokasi" :alokasi="a.alokasi" />
      </div>
      <div v-if="a.produk?.length" class="panel px-4 py-5 sm:px-6" data-bagian="produk">
        <div class="text-[14px] font-medium">Nilai per produk</div>
        <ul class="m-0 mt-3 list-none divide-y divide-garis p-0">
          <li v-for="p in a.produk" :key="`${p.tipe_produk}-${p.produk}`" class="flex items-start justify-between gap-3 py-2 text-[13px]">
            <span class="min-w-0"><span class="font-medium">{{ p.nama }}</span><span v-if="p.pengganti_dari" class="chip ml-1.5 bg-kuning-bg text-kuning" :title="`${p.catatan_pengganti} · menggantikan ${p.pengganti_dari}`">pengganti</span>
              <span class="block text-[11px] text-muted">{{ NAMA_KAKI[p.kaki] }} · dibeli {{ rupiahRingkas(p.beli) }}<template v-if="p.jual"> · dijual {{ rupiahRingkas(p.jual) }}</template></span>
              <span v-if="p.pengganti_dari" class="block text-[11px] text-kuning">{{ p.catatan_pengganti }}; menggantikan {{ p.pengganti_dari }}</span></span>
            <span class="shrink-0 text-right tabular-nums"><span class="font-semibold">{{ p.nilai != null ? rupiahRingkas(p.nilai) : "–" }}</span>
              <span v-if="p.nilai != null" class="block text-[11px]" :class="kelasUntung(p.nilai - (p.beli - p.jual))">{{ rupiahBertanda(p.nilai - (p.beli - p.jual)) }}</span></span>
          </li>
        </ul>
      </div>
      <div v-if="adaTransaksi" class="panel px-4 py-5 sm:px-6" data-bagian="pembanding">
        <div class="text-[14px] font-medium">Dibanding apa kalau dulu begini</div>
        <ul class="m-0 mt-3 list-none space-y-3 p-0 text-[13px]">
          <li v-if="pb?.campuran && pb.campuran.nilai != null" class="rounded-2xl bg-surface-2 px-4 py-3">
            <div class="flex flex-wrap items-center justify-between gap-2"><span class="font-medium">Campuran target (indeks)</span>
              <span class="tabular-nums">{{ rupiahRingkas(pb.campuran.nilai) }} · kamu {{ rupiahBertanda(pb.campuran.selisih) }}</span></div>
            <p class="m-0 mt-1 text-[11px] leading-relaxed text-muted">{{ pb.campuran.label }}</p>
          </li>
          <li v-for="u in pb?.uji_maju ?? []" :key="u.kode" class="rounded-2xl bg-surface-2 px-4 py-3">
            <div class="flex flex-wrap items-center justify-between gap-2"><span class="font-medium">{{ u.nama }}</span><span class="tabular-nums">{{ rupiahBertanda(u.selisih) }} dibanding uji maju</span></div>
            <p class="m-0 mt-1 text-[11px] text-muted">Setoranmu dianggap masuk ke kurva uji maju pada tanggal yang sama.</p>
          </li>
          <li v-if="!pb?.uji_maju" class="rounded-2xl bg-surface-2 px-4 py-3 text-[12px] text-muted">Pembanding uji maju H35/H37 muncul setelah uji maju berjalan (mulai 1 Des 2026).</li>
        </ul>
      </div>
      <div v-if="grafik" class="panel relative px-4 py-5 sm:px-6" data-bagian="grafik">
        <Pemutar v-if="memuat" class="absolute top-4 right-4" />
        <div class="text-[14px] font-medium">Nilai portofolio vs total setor</div>
        <div class="mt-2 flex flex-wrap items-center gap-4 text-[12px] text-ink-2"><span class="inline-flex items-center gap-1.5"><span class="h-2 w-4 rounded-full bg-s1"></span>Nilai sekarang</span><span class="inline-flex items-center gap-1.5"><span class="h-2 w-4 rounded-full bg-s4"></span>Total setor</span></div>
        <div class="mt-3"><GrafikBanding :label="grafik.label" :seri="grafik.seri" :warna-seri="['--series-1', '--series-4']" :tinggi="260" /></div>
      </div>
    </section>

    <section id="riwayat" class="panel px-4 py-5 sm:px-6" data-bagian="riwayat">
      <div class="text-[14px] font-medium">Riwayat transaksi</div>
      <p class="m-0 mt-1 mb-3 text-[12px] text-muted">Dikelompokkan per bulan. Tiap tambah, ubah, dan hapus dicatat di log terpisah.</p>
      <TabelTransaksi :transaksi="a.transaksi ?? []" :baca="baca" @ubah="emit('ubah', $event)" @hapus="emit('hapus', $event)" />
    </section>
  </div>
</template>

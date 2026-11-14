<script setup>
import { inject } from "vue";
import { AlertTriangle, Info, ChevronRight, Coins, ExternalLink } from "lucide-vue-next";
import { rupiahRingkas } from "@/utils/format";
import Logo, { kunciMi } from "@/components/common/Logo.vue";

defineProps({
  grup: { type: Array, default: () => [] },
  peringatan: { type: Array, default: () => [] },
  satuan: { type: String, default: "/bulan" },
});
const pindahTab = inject("pindahTab", () => {});

const KELAS_RISIKO = { Rendah: "bg-naik-bg text-naik", Sedang: "bg-kuning-bg text-kuning", Tinggi: "bg-turun-bg text-turun" };
const NAMA_KAKI = { lokal: "Saham Indonesia", global: "Saham global", darurat: "Dana darurat", pt: "RD pendapatan tetap", pu: "RD pasar uang", emas: "Emas" };
const KELAS_BADGE = { hijau: "bg-naik-bg text-naik", kuning: "bg-kuning-bg text-kuning", abu: "bg-surface-2 text-muted" };

const bukaProduk = (id) => {
  pindahTab("reksadana", "katalog");
  history.replaceState(null, "", `#reksadana/katalog/${id}`);
};
const pc = (v) => (v == null ? "–" : `${v >= 0 ? "+" : ""}${(v * 100).toLocaleString("id-ID", { maximumFractionDigits: 1 })}%`);
const feeTeks = (p) => (p.fee == null ? "cek di aplikasi" : `${(p.fee * 100).toLocaleString("id-ID", { maximumFractionDigits: 2 })}% beli dan jual, tanpa PPh`);
</script>

<template>
  <div class="space-y-3">
    <div v-for="(w, i) in peringatan" :key="i" class="flex items-start gap-2 rounded-2xl bg-kuning-bg px-4 py-3 text-[13px] text-kuning">
      <AlertTriangle class="mt-0.5 h-4 w-4 shrink-0" />
      <div class="min-w-0">
        <div class="font-medium">{{ w.teks }}</div>
        <div v-if="w.saran?.length" class="mt-0.5 text-[12px]">Aplikasi yang bisa dipakai: {{ w.saran.join(", ") }}.</div>
      </div>
    </div>

    <section v-for="g in grup" :key="g.aplikasi" class="overflow-hidden rounded-2xl border border-garis">
      <div class="flex flex-wrap items-center justify-between gap-2 bg-surface-2 px-4 py-3">
        <div class="flex items-center gap-2 text-[14px] font-medium"><Logo jenis="platform" :kunci="g.aplikasi" :teks="g.nama" :ukuran="26" />Di {{ g.nama }}</div>
        <div class="text-[13px] text-ink-2">total <b class="text-[16px] font-semibold text-ink tabular-nums">{{ rupiahRingkas(g.total) }}</b><span class="text-[11px] text-muted">{{ satuan }}</span></div>
      </div>
      <ul class="m-0 list-none divide-y divide-garis p-0">
        <li v-for="p in g.produk" :key="`${p.tipe}-${p.kaki}-${p.id ?? p.kode}`" class="px-4 py-3">
          <template v-if="p.tipe === 'etf'">
            <div class="flex items-start gap-3">
              <span class="grid h-[34px] w-[34px] shrink-0 place-items-center rounded-[30%] bg-kuning-bg text-kuning"><Coins class="h-4 w-4" /></span>
              <div class="min-w-0 flex-1">
                <div class="text-[13px] leading-snug font-medium">{{ p.kode }} · {{ p.nama }}</div>
                <div class="mt-0.5 text-[11px] text-muted">ETF emas syariah · beli di bursa lewat akun saham · {{ p.sumber_pilihan === "uji maju" ? "dipilih uji maju" : "pilihan hari ini" }}</div>
                <div class="mt-1.5 flex flex-wrap items-center gap-1.5">
                  <span class="chip" :class="KELAS_BADGE[p.badge.warna]" :title="p.label_premium">{{ p.badge.teks }}<template v-if="p.premium != null"> · {{ pc(p.premium) }}</template></span>
                  <span class="chip bg-surface-2 text-ink-2">Risiko tinggi</span>
                  <span v-if="p.basi" class="chip bg-kuning-bg text-kuning">data harga sudah lama ({{ p.tgl_data }})</span>
                </div>
                <div class="mt-1 text-[11px] text-muted">{{ p.label_premium }}</div>
              </div>
              <div class="shrink-0 text-right">
                <div class="text-[15px] font-semibold tabular-nums">{{ p.lot > 0 ? `${p.lot} lot` : "belum 1 lot" }}</div>
                <div class="text-[11px] text-muted tabular-nums">{{ p.lot > 0 ? `±${rupiahRingkas(p.perkiraan)}` : `1 lot ±${rupiahRingkas(p.harga_per_lot)}` }}</div>
              </div>
            </div>
            <div v-if="p.lot === 0 && p.bulan_kumpul" class="mt-2 text-[12px] text-ink-2">Porsi bulan ini ({{ rupiahRingkas(p.nilai) }}) belum cukup untuk 1 lot ({{ rupiahRingkas(p.harga_per_lot) }}). Simpan dulu, beli tiap ±{{ p.bulan_kumpul }} bulan.</div>
            <div class="mt-2 rounded-xl bg-surface-2 px-3 py-2 text-[12px] leading-relaxed text-ink-2">
              <div><b class="font-medium text-ink">Cari di aplikasi:</b> {{ p.kode }} · 1 lot = 100 unit (±{{ rupiahRingkas(p.harga_per_lot) }}) · fee {{ feeTeks(p) }}</div>
              <div class="mt-1">{{ p.cara }}</div>
              <div class="mt-1">{{ p.aturan_premium }}</div>
              <div class="mt-1 text-muted">{{ p.ketersediaan }}. {{ p.catatan_syariah }}</div>
              <div class="mt-1 text-muted">ETF emas berfatwa DSN-MUI {{ p.fatwa.nomor }} tentang {{ p.fatwa.tentang }}.
                <a v-for="(s, k) in p.fatwa.sumber" :key="s" :href="s" target="_blank" rel="noopener" class="ml-1 inline-flex items-center gap-0.5 text-aksen">sumber {{ k + 1 }}<ExternalLink class="h-3 w-3" /></a></div>
            </div>
          </template>
          <template v-else>
            <div class="flex items-start gap-3">
              <Logo jenis="mi" :kunci="kunciMi(p.mi)" :teks="p.mi" :ukuran="34" />
              <div class="min-w-0 flex-1">
                <a :href="`#reksadana/katalog/${p.id}`" class="text-[13px] leading-snug font-medium text-ink hover:text-aksen" @click.prevent="bukaProduk(p.id)">{{ p.nama }}</a>
                <div class="mt-0.5 text-[11px] text-muted">{{ NAMA_KAKI[p.kaki] ?? p.kaki }}<template v-if="p.mi"> · {{ p.mi }}</template></div>
                <div class="mt-1.5 flex flex-wrap items-center gap-1.5">
                  <span class="chip" :class="KELAS_RISIKO[p.risiko]" :title="p.risiko_sumber === 'resmi' ? `Tingkat risiko ${p.risiko_skala} dari skala 1–9` : 'Diturunkan dari jenis reksa dana'">Risiko {{ p.risiko?.toLowerCase() }}</span>
                  <span v-if="p.pengganti_dari" class="chip bg-surface-2 text-ink-2">pengganti dari {{ p.pengganti_dari }}</span>
                </div>
              </div>
              <div class="shrink-0 text-right">
                <div class="text-[15px] font-semibold tabular-nums" :class="p.nilai ? '' : 'text-muted'">{{ p.nilai ? rupiahRingkas(p.nilai) : "giliran lain bulan" }}</div>
                <div v-if="p.porsi && p.nilai" class="text-[11px] text-muted tabular-nums">{{ (p.porsi * 100).toLocaleString("id-ID", { maximumFractionDigits: 0 }) }}%</div>
              </div>
            </div>
            <div class="mt-2 rounded-xl bg-surface-2 px-3 py-2 text-[12px] leading-relaxed text-ink-2">
              <div><b class="font-medium text-ink">Cari di aplikasi:</b> {{ p.cari_di_aplikasi }}</div>
              <div class="text-muted">Minimal beli: {{ p.min_beli_mi || "tidak tercatat" }} ({{ p.min_beli_teks }})</div>
              <div v-if="p.min_beli_melebihi" class="mt-1 flex items-start gap-1.5 text-kuning"><AlertTriangle class="mt-0.5 h-3.5 w-3.5 shrink-0" />Minimal dari manajer investasi lebih besar dari porsi bulan ini. Cek minimal di aplikasi; kalau tetap lebih besar, beli bergiliran tiap beberapa bulan atau naikkan setoran.</div>
              <div v-if="p.catatan" class="mt-1 flex items-start gap-1.5 text-muted"><Info class="mt-0.5 h-3 w-3 shrink-0 text-aksen" />{{ p.catatan }}</div>
            </div>
            <a :href="`#reksadana/katalog/${p.id}`" class="mt-1 inline-flex items-center text-[11px] text-aksen" @click.prevent="bukaProduk(p.id)">Detail produk<ChevronRight class="h-3 w-3" /></a>
          </template>
        </li>
      </ul>
    </section>
  </div>
</template>

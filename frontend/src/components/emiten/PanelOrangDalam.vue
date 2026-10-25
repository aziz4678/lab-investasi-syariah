<script setup>
import { ref, computed, watch } from "vue";
import { FileText, ArrowUpRight, ArrowDownRight, Minus } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { ringkas, kelasPersen } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import Kerangka from "@/components/common/Kerangka.vue";

const props = defineProps({ kode: String });
const d = ref(null);
const semua = ref(false);
const semuaPemegang = ref(false);

watch(() => props.kode, async (k) => {
  d.value = null;
  semua.value = false;
  semuaPemegang.value = false;
  if (!k) return;
  const r = await ambil(`orang_dalam/${k}`).catch(() => ({ laporan: [], pemegang: [], ringkas: null }));
  if (k === props.kode) d.value = r;
}, { immediate: true });

const rp = (v) => `Rp${ringkas(v)}`;
const lembar = (v) => `${ringkas(v)} lembar`;
const tgl = (t) => (t ? new Date(t).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }) : "–");
const pct = (v) => (v == null ? "–" : `${v.toLocaleString("id-ID", { maximumFractionDigits: 3 })}%`);
const harga = (x) => (x.harga_min == null ? "" : x.harga_min === x.harga_maks ? ` @Rp${x.harga_min.toLocaleString("id-ID")}` : ` @Rp${x.harga_min.toLocaleString("id-ID")}–${x.harga_maks.toLocaleString("id-ID")}`);
const WARNA_PERAN = { Direksi: "bg-aksen-lembut text-aksen", Komisaris: "bg-aksen-lembut text-aksen", "Direksi/Komisaris": "bg-aksen-lembut text-aksen", Pengendali: "bg-kuning-bg text-kuning", "Pemegang ≥5%": "bg-surface-2 text-ink-2", "Pemegang saham": "bg-surface-2 text-ink-2" };

function aksi(x) {
  const bersih = x.beli - x.jual;
  if (x.beli && !x.jual) return { arah: 1, teks: `Membeli ${lembar(x.beli)}${harga(x)}`, nilai: x.nilai_beli };
  if (x.jual && !x.beli) return { arah: -1, teks: `Menjual ${lembar(x.jual)}${harga(x)}`, nilai: x.nilai_jual };
  if (x.beli && x.jual) return { arah: Math.sign(bersih), teks: `Beli ${lembar(x.beli)}, jual ${lembar(x.jual)}${harga(x)}`, nilai: x.nilai_beli - x.nilai_jual };
  return { arah: 0, teks: `${x.jenis.join(", ") || "Perubahan kepemilikan"}${x.lain ? ` · ${lembar(x.lain)}` : ""}`, nilai: null };
}

const laporan = computed(() => (d.value?.laporan || []).slice(0, semua.value ? 80 : 8));
const pemegang = computed(() => (d.value?.pemegang || []).slice(0, semuaPemegang.value ? 999 : 10));
const kotak = computed(() => {
  const r = d.value?.ringkas;
  if (!r) return [];
  return [
    { l: `Orang dalam (${r.hari} hari)`, bersih: r.dalam_beli - r.dalam_jual, ket: `beli ${rp(r.dalam_beli)} · jual ${rp(r.dalam_jual)}`, info: "Direksi dan komisaris emiten" },
    { l: `Pemegang besar (${r.hari} hari)`, bersih: r.besar_beli - r.besar_jual, ket: `beli ${rp(r.besar_beli)} · jual ${rp(r.besar_jual)}`, info: "Pemegang ≥5%, pengendali, dan pihak lain yang wajib lapor" },
    { l: "Laporan masuk", angka: r.laporan, ket: `dalam ${r.hari} hari terakhir` },
  ];
});
const ada = computed(() => d.value && (d.value.laporan.length || d.value.pemegang.length));
</script>

<template>
  <Panel judul="Transaksi orang dalam & pemegang besar"
    :ket="`Laporan kepemilikan saham ke KSEI/OJK (format standar sejak ${tgl(d?.mulai_data || '2025-11-28')}) · nilai = jumlah lembar × harga yang dilaporkan`" rapat>
    <Kerangka v-if="!d" class="px-6 pb-5" jenis="baris" :n="4" />
    <p v-else-if="!ada" class="m-0 px-6 pb-5 text-[13px] text-muted">Belum ada laporan kepemilikan atau data pemegang saham di atas 1% untuk emiten ini.</p>
    <template v-else>
      <div v-if="d.laporan.length" class="grid grid-cols-1 gap-3 px-6 pb-4 sm:grid-cols-3">
        <div v-for="k in kotak" :key="k.l" class="rounded-2xl bg-surface-2 px-4 py-3" :title="k.info">
          <div class="text-xs text-muted">{{ k.l }}</div>
          <div v-if="k.angka != null" class="mt-0.5 text-[17px] font-medium tabular-nums">{{ k.angka }}</div>
          <div v-else class="mt-0.5 text-[17px] font-medium tabular-nums" :class="kelasPersen(k.bersih)">
            {{ k.bersih === 0 ? "Rp0" : `${k.bersih > 0 ? "Beli bersih " : "Jual bersih "}${rp(Math.abs(k.bersih))}` }}
          </div>
          <div class="text-[11px] text-muted">{{ k.ket }}</div>
        </div>
      </div>

      <div v-for="x in laporan" :key="x.id" class="flex gap-4 border-t border-garis px-6 py-3">
        <div class="w-[88px] shrink-0 text-xs tabular-nums">
          <div class="text-ink-2">{{ tgl(x.tgl_transaksi || x.tgl_lapor) }}</div>
          <div class="text-muted">lapor {{ tgl(x.tgl_lapor) }}</div>
        </div>
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-[13px] font-medium">{{ x.nama }}</span>
            <span class="chip" :class="WARNA_PERAN[x.peran]">{{ x.peran }}</span>
          </div>
          <div class="mt-1 flex flex-wrap items-center gap-x-2 text-[13px]" :class="aksi(x).arah > 0 ? 'text-naik' : aksi(x).arah < 0 ? 'text-turun' : 'text-ink-2'">
            <component :is="aksi(x).arah > 0 ? ArrowUpRight : aksi(x).arah < 0 ? ArrowDownRight : Minus" class="h-3.5 w-3.5" />
            <span>{{ aksi(x).teks }}</span>
            <span v-if="aksi(x).nilai" class="tabular-nums">· {{ rp(Math.abs(aksi(x).nilai)) }}</span>
          </div>
          <div class="mt-0.5 flex flex-wrap items-center gap-x-3 text-xs text-muted">
            <span class="tabular-nums">Kepemilikan {{ pct(x.persen_sebelum) }} → {{ pct(x.persen_sesudah) }}</span>
            <span v-if="x.tujuan" class="max-w-[420px] truncate" :title="x.tujuan">Tujuan: {{ x.tujuan }}</span>
            <a v-if="x.url" :href="x.url" target="_blank" rel="noopener" class="inline-flex items-center gap-1 hover:text-aksen"><FileText class="h-3.5 w-3.5" />Laporan</a>
          </div>
        </div>
      </div>
      <div v-if="d.laporan.length > 8" class="border-t border-garis px-6 py-3 text-xs">
        <button type="button" class="text-muted hover:underline" @click="semua = !semua">{{ semua ? "Tampilkan 8 terbaru" : `Tampilkan semua ${d.laporan.length} laporan` }}</button>
      </div>

      <template v-if="d.pemegang.length">
        <div class="border-t border-garis px-6 pt-4 pb-2">
          <div class="text-[13px] font-medium">Pemegang saham di atas 1% (KSEI)</div>
          <div class="text-xs text-muted">Per {{ tgl(d.pemegang_tgl) }}<template v-if="d.pemegang_tgl_lalu"> · perubahan dibanding {{ tgl(d.pemegang_tgl_lalu) }}</template> · data bulanan sejak Mar 2026</div>
        </div>
        <div class="overflow-x-auto">
          <table class="tabel min-w-[640px]">
            <thead><tr><th>Pemegang</th><th>Jenis</th><th class="!text-right">Lembar</th><th class="!text-right">Porsi</th><th class="!text-right">Ubah</th></tr></thead>
            <tbody>
              <tr v-for="p in pemegang" :key="p.investor">
                <td class="max-w-[320px] truncate" :title="p.investor">{{ p.investor }}<span v-if="p.baru" class="chip ml-2 bg-naik-bg text-naik">baru</span></td>
                <td class="text-xs text-ink-2">{{ p.klasifikasi || "–" }}{{ p.lokal_asing ? ` · ${p.lokal_asing === "F" ? "asing" : "lokal"}` : "" }}</td>
                <td class="text-right tabular-nums text-ink-2">{{ ringkas(p.saham) }}</td>
                <td class="text-right font-medium tabular-nums">{{ pct(p.persen) }}</td>
                <td class="text-right tabular-nums" :class="kelasPersen(p.ubah)">{{ p.ubah == null || p.baru ? "–" : `${p.ubah > 0 ? "+" : ""}${p.ubah.toLocaleString("id-ID", { maximumFractionDigits: 2 })} poin` }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="d.keluar.length" class="px-6 pb-2 text-xs text-muted">Keluar dari daftar ≥1%: {{ d.keluar.map((x) => `${x.investor} (${pct(x.persen)})`).join(", ") }}</div>
        <div v-if="d.pemegang.length > 10" class="border-t border-garis px-6 py-3 text-xs">
          <button type="button" class="text-muted hover:underline" @click="semuaPemegang = !semuaPemegang">{{ semuaPemegang ? "Tampilkan 10 terbesar" : `Tampilkan semua ${d.pemegang.length} pemegang` }}</button>
        </div>
      </template>
      <p class="m-0 px-6 py-3 text-[11px] text-muted">Laporan sebelum 28 Nov 2025 berupa surat bebas tiap emiten dan tidak dibaca otomatis; lihat panel Pengumuman (kategori Laporan kepemilikan saham).</p>
    </template>
  </Panel>
</template>

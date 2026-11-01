<script setup>
import { ref, computed, onMounted } from "vue";
import { Line } from "vue-chartjs";
import { RefreshCw, Lock } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { pakaiTema } from "@/composables/tema";
import { pakaiPekerjaan } from "@/composables/pekerjaan";
import { opsiDasar, warna } from "@/utils/chart";
import { rupiah, persen, tanggal, kelasPersen } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import KodeSaham from "@/components/common/KodeSaham.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import PanelPekerjaan from "@/components/sistem/PanelPekerjaan.vue";

const props = defineProps({ biayaRebalance: Boolean });
const tema = pakaiTema();
const r = ref(null);
const siap = ref(false);
const galat = ref("");
const { kerja, galat: galatKerja, sibuk, mulai, lanjutkan } = pakaiPekerjaan();

const SERI = [
  { kunci: "h29", label: "Momentum Blend 50/50", var: "--series-1", lebar: 2.5, putus: [] },
  { kunci: "h29_biaya", label: "Momentum Blend setelah estimasi biaya rebalance", var: "--series-1", lebar: 1.5, putus: [4, 3], biaya: true },
  { kunci: "h11a", label: "Follow Tren (H11a)", var: "--series-2", lebar: 2, putus: [] },
  { kunci: "h22", label: "Bagian RS 12-1 (H22)", var: "--series-4", lebar: 1.5, putus: [] },
  { kunci: "ew", label: "Bobot sama syariah likuid", var: "--series-3", lebar: 1.5, putus: [5, 4] },
  { kunci: "jii", label: "JII (indeks harga)", var: "--series-5", lebar: 1.5, putus: [2, 3] },
];
const AKSI = { beli: "Beli", jual: "Jual", pangkas: "Pangkas", dividen: "Dividen", split: "Split", batal_kas: "Batal · kas kurang", batal_tunda: "Batal · tertunda sampai rebalance" };

async function muat() {
  try {
    r.value = await ambil("paper/h29");
    siap.value = true;
  } catch (e) {
    galat.value = e.message;
  }
}

function perbarui() {
  mulai("aksi/paper_h22", {}, muat);
}

onMounted(async () => {
  await muat();
  await lanjutkan("paper_h22", muat);
});

const seri = computed(() => r.value?.seri || []);
const SERI_AKTIF = computed(() => SERI.filter((s) => !s.biaya || props.biayaRebalance));
const data = computed(() => {
  tema.value;
  return {
    labels: seri.value.map((x) => x.tgl.slice(0, 10)),
    datasets: SERI_AKTIF.value.map((s) => ({
      label: s.label, data: seri.value.map((x) => x[s.kunci]), borderColor: warna(s.var), pointBackgroundColor: warna(s.var),
      pointHoverBorderColor: warna("--surface-1"), backgroundColor: "transparent", fill: false, borderWidth: s.lebar, borderDash: s.putus,
      pointRadius: seri.value.length < 3 ? 3 : 0, tension: 0.35, cubicInterpolationMode: "monotone", spanGaps: true,
    })),
  };
});
const opsi = computed(() => {
  tema.value;
  const o = opsiDasar();
  o.scales.y.ticks.callback = (v) => `${(v / 1e6).toFixed(0)} jt`;
  o.plugins.tooltip.callbacks = { label: (c) => ` ${c.dataset.label}  Rp${rupiah(Math.round(c.parsed.y))} (${persen((c.parsed.y / 1e8 - 1) * 100)})` };
  return o;
});
const kartu = computed(() =>
  SERI_AKTIF.value.map((s) => ({ ...s, x: r.value?.ringkas?.[s.kunci] })).filter((s) => s.x),
);
const status = computed(() => r.value?.evaluasi?.status || {});
const NAMA_ZONA = { normal: "zona normal", waspada: "zona waspada", gagal: "zona GAGAL", belum: "zona belum dinilai" };
const tunda = computed(() => Object.keys(r.value?.tunda_beli || {}));
</script>

<template>
  <Panel judul="Paper Momentum Blend (H29) · 50% Follow Tren + 50% RS 12-1" ket="Berjalan paralel dengan Follow Tren sejak 1 Nov 2026, modal Rp100 jt · angka historis bukan bukti, satu-satunya bukti adalah paper ini">
    <template #aksi>
      <button class="tombol" :disabled="sibuk" @click="perbarui">
        <RefreshCw class="h-3.5 w-3.5" :class="sibuk ? 'animate-spin' : ''" />{{ sibuk ? "Memperbarui..." : "Perbarui H29" }}
      </button>
    </template>
    <PanelPekerjaan :kerja="kerja" :galat="galatKerja" />
    <p v-if="galat" class="m-0 text-turun">{{ galat }}</p>
    <Kerangka v-if="!siap && !galat" jenis="grafik" :tinggi="220" />
    <template v-else-if="r && !r.ada">
      <p class="m-0 text-ink-2">Paper Momentum Blend belum dimulai. Tekan "Perbarui H29" untuk menyiapkan bagian RS 12-1 (titik awal 30 Okt 2026, rebalance pertama di open 2 Nov 2026).</p>
    </template>
    <div v-else-if="r" class="space-y-5">
      <div class="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <div v-for="s in kartu" :key="s.kunci" class="rounded-2xl bg-surface-2 px-4 py-3">
          <div class="flex items-center gap-2 text-xs text-muted"><i class="h-2 w-2 shrink-0 rounded-full" :style="{ background: `var(${s.var})` }"></i>{{ s.label }}</div>
          <div class="mt-1 text-[17px] font-medium tabular-nums" :class="kelasPersen(s.x.return_pct)">{{ persen(s.x.return_pct) }}</div>
          <div class="text-xs text-muted tabular-nums">turun terdalam {{ persen(s.x.dd_maks_pct, 1) }}</div>
        </div>
      </div>
      <p class="m-0 text-xs text-muted">Diproses sampai {{ tanggal(r.tgl_terakhir) }}. Momentum Blend = 50% return paper Follow Tren + 50% return bagian RS 12-1, dikembalikan ke 50/50 tiap akhir bulan. Angka utama tanpa biaya pemindahan (sama dengan simulasi audit)<template v-if="biayaRebalance">; angka kedua memotong {{ persen(r.evaluasi?.biaya_pindah_pct, 2, false) }} dari nilai yang dipindah (fee jual 0,25% + fee beli 0,15% + 2 × tick rata-rata {{ persen(r.evaluasi?.tick_estimasi_pct, 2, false) }}): {{ r.ringkas?.kali_rebalance || 0 }} kali, total Rp{{ rupiah(Math.round(r.ringkas?.biaya_rebalance_rp || 0)) }}</template>. Bobot sama tanpa biaya, JII tanpa dividen.</p>
      <p v-if="r.cek" class="m-0 text-xs" :class="r.cek.cocok ? 'text-muted' : 'text-turun'">Cek ulang bagian RS 12-1 ({{ tanggal(r.cek.sampai) }}, {{ r.cek.hari }} hari): {{ r.cek.cocok ? "COCOK, identik dengan hasil jalankan ulang dari nol" : `${r.cek.jumlah_beda} BEDA, periksa log job Cek ulang paper H29` }}.</p>
      <div class="h-[240px]"><Line :data="data" :options="opsi" /></div>

      <div class="rounded-2xl bg-surface-2 px-5 py-4">
        <div class="mb-2 flex items-center gap-2 text-[13px] font-medium"><Lock class="h-3.5 w-3.5 text-aksen" />Kriteria evaluasi (dikunci 2026-11-01)</div>
        <ul class="m-0 list-disc space-y-1 pl-5 text-xs leading-relaxed text-ink-2">
          <li v-for="k in r.evaluasi?.kriteria || []" :key="k">{{ k }}</li>
        </ul>
        <div class="mt-3 flex flex-wrap gap-2 text-xs">
          <span v-for="(v, k) in status" :key="k" class="chip !h-auto !whitespace-normal py-1 leading-snug" :class="v.gagal ? 'bg-turun-bg text-turun' : 'bg-aksen-lembut text-aksen'">
            {{ k === "h29" ? "Momentum Blend" : "Follow Tren" }} · {{ v.gagal ? `GAGAL: ${v.alasan.join("; ")}` : "belum gagal" }}<template v-if="v.dd_maks_pct != null"> · turun terdalam {{ persen(v.dd_maks_pct, 1) }} (batas -45%)</template><template v-if="v.zona"> · {{ NAMA_ZONA[v.zona] || v.zona }} h11a_v1</template>
          </span>
        </div>
      </div>

      <div v-if="r.rencana" class="rounded-2xl border border-garis px-5 py-4 text-[13px]">
        <div class="font-medium">Rencana rebalance RS 12-1 · sinyal {{ tanggal(r.rencana.sinyal) }}, dieksekusi di open hari bursa berikutnya</div>
        <p class="m-0 mt-1 text-xs text-muted">{{ r.rencana.lolos }} saham lolos, pegang N = {{ r.rencana.n }} · ±Rp{{ rupiah(r.rencana.anggaran_rp) }} per saham baru · otomatis, tidak perlu beli manual</p>
        <div class="mt-2 flex flex-wrap items-center gap-1.5">
          <span class="chip bg-aksen-lembut text-aksen">BELI</span>
          <KodeSaham v-for="t in r.rencana.beli" :key="t" :kode="t" />
          <span v-if="!r.rencana.beli.length" class="text-muted">-</span>
        </div>
        <div class="mt-2 flex flex-wrap items-center gap-1.5">
          <span class="chip bg-turun-bg text-turun">JUAL</span>
          <KodeSaham v-for="t in r.rencana.jual" :key="t" :kode="t" />
          <span v-if="!r.rencana.jual.length" class="text-muted">-</span>
        </div>
      </div>
      <p v-if="tunda.length" class="m-0 text-xs text-muted">Beli tertunda (candle terkunci / tidak ada transaksi): {{ tunda.join(", ") }}</p>

      <div v-if="r.posisi.length" class="overflow-x-auto">
        <div class="label mb-2">Posisi bagian RS 12-1 ({{ r.posisi.length }})</div>
        <table class="tabel min-w-[560px]">
          <thead><tr><th>Saham</th><th>Masuk</th><th class="!text-right">Lot</th><th class="!text-right">Harga masuk</th><th class="!text-right">Close</th><th class="!text-right">Untung</th><th class="!text-right">Nilai</th></tr></thead>
          <tbody>
            <tr v-for="p in r.posisi" :key="p.ticker">
              <td><KodeSaham :kode="p.ticker" /></td>
              <td class="text-ink-2">{{ tanggal(p.tgl_masuk) }}</td>
              <td class="text-right tabular-nums">{{ rupiah(Math.round(p.lembar / 100)) }}</td>
              <td class="text-right tabular-nums">{{ rupiah(Math.round(p.harga_masuk)) }}</td>
              <td class="text-right tabular-nums">{{ p.close != null ? rupiah(Math.round(p.close)) : "–" }}</td>
              <td class="text-right font-medium tabular-nums" :class="kelasPersen(p.untung_pct)">{{ p.untung_pct != null ? persen(p.untung_pct) : "–" }}</td>
              <td class="text-right tabular-nums">{{ p.nilai_rp != null ? `Rp${rupiah(Math.round(p.nilai_rp))}` : "–" }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="r.transaksi.length" class="overflow-x-auto">
        <div class="label mb-2">Transaksi terbaru bagian RS 12-1</div>
        <table class="tabel min-w-[520px]">
          <thead><tr><th>Tanggal</th><th>Aksi</th><th>Saham</th><th class="!text-right">Lot</th><th class="!text-right">Harga</th><th class="!text-right">Hasil</th></tr></thead>
          <tbody>
            <tr v-for="(t, i) in r.transaksi.slice(0, 15)" :key="i">
              <td class="text-ink-2">{{ tanggal(t.tgl) }}</td>
              <td>{{ AKSI[t.aksi] || t.aksi }}</td>
              <td><KodeSaham :kode="t.ticker" /></td>
              <td class="text-right tabular-nums">{{ t.lembar ? rupiah(Math.round(t.lembar / 100)) : "–" }}</td>
              <td class="text-right tabular-nums">{{ t.harga ? rupiah(Math.round(t.harga)) : "–" }}</td>
              <td class="text-right tabular-nums" :class="kelasPersen(t.net_pct)">{{ t.net_pct != null ? persen(t.net_pct) : t.nilai_rp != null ? `Rp${rupiah(t.nilai_rp)}` : "–" }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </Panel>
</template>

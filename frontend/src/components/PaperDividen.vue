<script setup>
import { ref, computed, onMounted } from "vue";
import { RefreshCw, Lock, Clock } from "lucide-vue-next";
import { ambil, persen, rupiah, ringkas, tanggal } from "../util.js";
import { pakaiPekerjaan } from "../pekerjaan.js";
import Panel from "./Panel.vue";
import Stats from "./Stats.vue";
import KodeSaham from "./KodeSaham.vue";
import KurvaMini from "./KurvaMini.vue";
import PanelPekerjaan from "./PanelPekerjaan.vue";
import Kerangka from "./Kerangka.vue";

const data = ref(null);
const { kerja, galat, sibuk, mulai, lanjutkan } = pakaiPekerjaan();

async function muat() {
  data.value = await ambil("dividen/paper").catch(() => ({}));
}
onMounted(async () => {
  await muat();
  await lanjutkan("paper_dividen", muat);
});

const st = computed(() => data.value?.status);
const menunggu = computed(() => !st.value || st.value.tahap === "menunggu");
const aturan = computed(() => data.value?.aturan);
const sisaHari = computed(() => (aturan.value ? Math.max(0, Math.ceil((new Date(aturan.value.mulai) - new Date()) / 864e5)) : null));

const stat = computed(() => {
  const s = st.value;
  if (!s || menunggu.value) return [];
  const tahun = s.tahunan?.at(-1);
  return [
    { label: "Ekuitas", nilai: `Rp${ringkas(Math.round(s.ekuitas))}`, ket: `${persen((s.ekuitas / s.modal - 1) * 100)} dari modal` },
    { label: "Penghasilan dividen", nilai: `Rp${ringkas(Math.round(s.penghasilan_total))}`, ket: "bersih pajak 10%, sejak mulai" },
    { label: `Penghasilan ${tahun?.tahun ?? ""}`, nilai: persen(tahun?.penghasilan_persen ?? 0, 1, false), ket: `syarat ≥ ${aturan.value.kriteria.penghasilan_min_persen}%/tahun` },
    { label: "Turun terdalam", nilai: persen(s.dd, 1), ket: `IHSG ${persen(s.dd_ihsg, 1)}` },
    { label: "vs IHSG", nilai: persen((s.ekuitas / s.ihsg - 1) * 100), ket: "selisih nilai modal" },
  ];
});

const kurva = computed(() => {
  const e = data.value?.ekuitas || [];
  return { label: e.map((x) => x.tgl.slice(0, 10)), nilai: e.map((x) => x.ekuitas), pembanding: e.map((x) => x.ihsg) };
});

const AKSI = { beli: ["Beli", "bg-naik-bg text-naik"], jual: ["Jual", "bg-turun-bg text-turun"], dividen: ["Dividen", "bg-aksen-lembut text-aksen"], cair: ["Cair", "bg-surface-2 text-ink-2"] };
</script>

<template>
  <div v-if="!data" class="space-y-5">
    <Kerangka panel :n="3" />
    <div class="grid gap-5 xl:grid-cols-2">
      <Kerangka panel jenis="grafik" :tinggi="220" />
      <Kerangka panel jenis="tabel" :n="6" logo />
    </div>
  </div>
  <div v-else class="space-y-5">
    <Panel judul="Uji maju Pemburu Dividen" :ket="menunggu ? `Mulai ${tanggal(aturan?.mulai)} · ${sisaHari} hari lagi · berjalan otomatis lewat jadwal 17:30` : `Berjalan sejak ${tanggal(st.mulai)} · data s/d ${tanggal(st.tgl_terakhir)}`">
      <div class="flex flex-wrap items-start gap-4">
        <div class="min-w-0 flex-1 text-[13px] leading-relaxed text-ink-2">
          <p class="m-0">Satu-satunya uji yang masih bersih: data 2027–2028 belum terjadi, jadi aturan tidak mungkin "disesuaikan" dengan hasil. Tujuannya mengukur <b class="font-medium text-ink">penghasilan rutin</b>, bukan mengalahkan pasar.</p>
          <p class="m-0 mt-2 flex items-center gap-1.5 text-xs text-muted"><Lock class="h-3.5 w-3.5" />Aturan dikunci {{ data?.dikunci ? tanggal(data.dikunci) : "–" }} (id dividen_v1). Kode menolak jalan kalau angkanya diubah.</p>
        </div>
        <button class="tombol" :disabled="sibuk" @click="mulai('aksi/paper_dividen', {}, muat)"><RefreshCw class="h-3.5 w-3.5" />Perbarui sekarang</button>
      </div>
      <PanelPekerjaan class="mt-4" :kerja="kerja" :galat="galat" />
    </Panel>

    <Stats v-if="stat.length" :items="stat" kolom="grid-cols-2 md:grid-cols-3 xl:grid-cols-5" />

    <div class="grid gap-5" :class="menunggu ? '' : 'xl:grid-cols-[1.4fr_1fr]'">
      <Panel v-if="!menunggu" judul="Modal vs IHSG" ket="Garis putus-putus = IHSG disetarakan ke modal awal">
        <KurvaMini :label="kurva.label" :nilai="kurva.nilai" :pembanding="kurva.pembanding" :format="(v) => `Rp${ringkas(v)}`" :tinggi="240" />
      </Panel>

      <Panel :judul="menunggu ? `Pratinjau pilihan ${data?.pratinjau?.tahun ?? ''}` : 'Posisi sekarang'"
        :ket="menunggu ? `Kalau dipilih hari ini (data s/d ${tanggal(data?.pratinjau?.acuan)}). Pilihan sebenarnya dihitung dari data hari bursa terakhir Desember 2026` : 'Dipegang sampai pergantian tahun'" rapat>
        <div class="overflow-x-auto">
          <table v-if="menunggu" class="tabel min-w-[460px]">
            <thead><tr><th>#</th><th>Saham</th><th>Sektor</th><th class="!text-right">Yield 12 bln</th></tr></thead>
            <tbody>
              <tr v-for="(x, i) in data?.pratinjau?.saham || []" :key="x.kode">
                <td class="text-muted">{{ i + 1 }}</td>
                <td class="!h-auto py-2.5"><KodeSaham :kode="x.kode" /><div class="max-w-[200px] truncate text-[11px] text-muted">{{ x.nama || "" }}</div></td>
                <td class="text-xs text-ink-2">{{ x.sektor || "–" }}</td>
                <td class="text-right tabular-nums">{{ persen(x.yield, 1, false) }}</td>
              </tr>
            </tbody>
          </table>
          <table v-else class="tabel min-w-[560px]">
            <thead><tr><th>Saham</th><th class="!text-right">Lot</th><th class="!text-right">Nilai</th><th class="!text-right">Harga</th><th class="!text-right">Dividen diterima</th></tr></thead>
            <tbody>
              <tr v-for="p in data.posisi" :key="p.kode">
                <td class="!h-auto py-2.5"><KodeSaham :kode="p.kode" /><div class="max-w-[180px] truncate text-[11px] text-muted">{{ p.sektor || p.nama || "" }}</div></td>
                <td class="text-right tabular-nums">{{ p.lot }}</td>
                <td class="text-right tabular-nums">Rp{{ ringkas(Math.round(p.nilai)) }}</td>
                <td class="text-right">{{ persen(p.untung_persen) }}</td>
                <td class="text-right tabular-nums">Rp{{ ringkas(Math.round(p.dividen)) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="menunggu && data?.pratinjau" class="m-0 px-6 py-3 text-xs text-muted">{{ data.pratinjau.calon }} saham memenuhi syarat dari {{ data.pratinjau.universe }} saham syariah likuid. Masih bisa berubah sampai akhir Desember.</p>
      </Panel>

      <Panel v-if="data?.menunggu_cair?.length" judul="Dividen menunggu cair" rapat>
        <div v-for="x in data.menunggu_cair" :key="x.kode + x.tgl" class="flex items-center justify-between border-t border-garis px-6 py-2.5 text-[13px] first:border-t-0">
          <span class="flex items-center gap-2"><Clock class="h-3.5 w-3.5 text-muted" /><KodeSaham :kode="x.kode" /> <span class="text-xs text-muted">cair {{ tanggal(x.bayar) }}{{ x.bayar_resmi ? "" : " (perkiraan)" }}</span></span>
          <span class="font-medium tabular-nums">Rp{{ rupiah(Math.round(x.nilai)) }}</span>
        </div>
      </Panel>
    </div>

    <Panel v-if="st?.tahunan?.length" judul="Per tahun" rapat>
      <div class="overflow-x-auto">
        <table class="tabel min-w-[560px]">
          <thead><tr><th>Tahun</th><th class="!text-right">Modal awal</th><th class="!text-right">Penghasilan dividen</th><th class="!text-right">Penghasilan %</th><th class="!text-right">Total return</th></tr></thead>
          <tbody>
            <tr v-for="t in st.tahunan" :key="t.tahun">
              <td>{{ t.tahun }}<span v-if="!t.lengkap" class="text-muted">*</span></td>
              <td class="text-right tabular-nums">Rp{{ ringkas(Math.round(t.awal)) }}</td>
              <td class="text-right tabular-nums">Rp{{ ringkas(Math.round(t.penghasilan)) }}</td>
              <td class="text-right" :class="t.lengkap && t.penghasilan_persen < aturan.kriteria.penghasilan_min_persen ? 'text-turun' : ''">{{ persen(t.penghasilan_persen, 1, false) }}</td>
              <td class="text-right">{{ persen(t.total_persen) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </Panel>

    <Panel v-if="data?.transaksi?.length" judul="Transaksi" ket="Dividen dicatat di ex-date, uang masuk kas di tanggal cair" rapat>
      <div class="max-h-[420px] overflow-auto">
        <table class="tabel min-w-[600px]">
          <thead><tr><th>Tanggal</th><th>Aksi</th><th>Saham</th><th class="!text-right">Lot</th><th class="!text-right">Harga / per lembar</th><th class="!text-right">Nilai</th></tr></thead>
          <tbody>
            <tr v-for="(x, i) in data.transaksi" :key="i">
              <td class="tabular-nums">{{ tanggal(x.tgl) }}</td>
              <td><span class="chip" :class="AKSI[x.aksi][1]">{{ AKSI[x.aksi][0] }}</span></td>
              <td><KodeSaham :kode="x.kode" /></td>
              <td class="text-right tabular-nums">{{ x.lot ?? "" }}</td>
              <td class="text-right tabular-nums">{{ x.harga != null ? rupiah(x.harga) : "" }}</td>
              <td class="text-right tabular-nums" :class="x.nilai < 0 ? 'text-ink-2' : ''">Rp{{ rupiah(Math.round(x.nilai)) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </Panel>

    <Panel judul="Aturan yang dikunci" ket="Ditetapkan 23 Okt 2026, sebelum data 2027 ada">
      <ul v-if="aturan" class="m-0 list-disc space-y-1.5 pl-5 text-[13px] text-ink-2">
        <li>Modal Rp{{ ringkas(aturan.modal) }}. Tiap hari bursa pertama Januari: pilih {{ aturan.jumlah }} saham syariah (DES saat itu), harga ≥ Rp{{ aturan.harga_min }}, nilai transaksi rata-rata 20 hari ≥ Rp{{ ringkas(aturan.min_nilai_transaksi) }}, membayar dividen di masing-masing {{ aturan.syarat_bayar_tahun }} tahun terakhir, urut yield 12 bulan tertinggi.</li>
        <li><b class="font-medium">Baru dibanding H17a:</b> maksimal {{ aturan.maks_per_sektor }} saham per sektor, supaya tidak jadi taruhan satu komoditas.</li>
        <li>Beli di harga open, 1/{{ aturan.jumlah }} ekuitas per saham (dibulatkan lot). Saham yang masih terpilih tahun berikutnya tidak dijual. Fee beli {{ aturan.fee_beli }}% / jual {{ aturan.fee_jual }}% + 1 tick.</li>
        <li>Dividen tunai dipotong pajak {{ aturan.pajak * 100 }}%, masuk kas di tanggal cair resmi IDX (kalau tidak ada: ex-date + {{ aturan.jeda_bayar_cadangan }} hari). Dividen <b class="font-medium">tidak</b> diinvestasikan ulang di tengah tahun, dipakai sebagai penghasilan.</li>
        <li><b class="font-medium">Lulus</b> kalau sampai {{ tanggal(aturan.kriteria.evaluasi_sampai) }}: penghasilan bersih ≥ {{ aturan.kriteria.penghasilan_min_persen }}% modal awal tiap tahun, total return ≥ IHSG, dan turun terdalam tidak lebih buruk dari IHSG lebih dari {{ aturan.kriteria.dd_maks_lebih_buruk_dari_ihsg }} poin.</li>
      </ul>
    </Panel>
  </div>
</template>

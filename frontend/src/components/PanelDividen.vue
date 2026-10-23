<script setup>
import { ref, computed, watch } from "vue";
import { Bar } from "vue-chartjs";
import { TriangleAlert, CircleCheck, CalendarClock } from "lucide-vue-next";
import { ambil, opsiDasar, warna, alfa, pakaiTema, persen, rupiah, kelasPersen } from "../util.js";
import Panel from "./Panel.vue";
import Kerangka from "./Kerangka.vue";
import Stats from "./Stats.vue";

const props = defineProps({ kode: String });
const dv = ref(null);
const tema = pakaiTema();
const BULAN = ["", "Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];

watch(() => props.kode, async (k) => {
  dv.value = null;
  if (k) dv.value = await ambil(`dividen/emiten/${k}`).catch(() => ({ ada: false }));
}, { immediate: true });

const stat = computed(() => {
  const x = dv.value;
  if (!x?.pernah) return [];
  return [
    { label: "Dividen 12 bulan", nilai: `Rp${rupiah(x.dps12)}`, ket: "per lembar, sebelum pajak" },
    { label: "Yield", nilai: persen(x.yield, 1, false), ket: `bersih ${persen(x.yield_bersih, 1, false)} (pajak 10%)` },
    { label: "Bayar berturut-turut", nilai: `${x.beruntun} tahun`, ket: x.beruntun >= 5 ? "konsisten" : x.beruntun >= 3 ? "cukup konsisten" : "belum konsisten" },
    { label: "Biasanya ex-date", nilai: x.bulan.map((b) => BULAN[b]).join(", ") || "–", ket: x.jeda_bayar != null ? `cair ±${x.jeda_bayar} hari setelah ex-date (IDX)` : "bulan paling sering 3 tahun terakhir" },
    { label: "Payout", nilai: x.payout != null ? `${x.payout}%` : "–", ket: "dividen 12 bln / laba 12 bln" },
  ];
});

const grafik = computed(() => {
  tema.value;
  const t = dv.value?.tahun || [];
  if (!t.length) return null;
  const s1 = warna("--series-1");
  return {
    labels: t.map((x) => (x.berjalan ? `${x.tahun}*` : String(x.tahun))),
    datasets: [{ label: "Dividen per lembar", data: t.map((x) => x.dps), backgroundColor: t.map((x) => (x.berjalan ? alfa(s1, 0.45) : s1)), borderRadius: 6, borderSkipped: false, maxBarThickness: 34 }],
  };
});
const rt = computed(() => dv.value?.riwayat_trap);
const semuaBayar = ref(false);
const VONIS = {
  sering: ["Sering kena trap ex-date", "bg-turun-bg text-turun"],
  kadang: ["Kadang kena trap ex-date", "bg-kuning-bg text-kuning"],
  jarang: ["Jarang kena trap ex-date", "bg-naik-bg text-naik"],
  "data kurang": ["Riwayat dividen terlalu sedikit", "bg-surface-2 text-muted"],
};

const tglId = (t) => (t ? new Date(t).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }) : "–");

const opsi = computed(() => {
  tema.value;
  const o = opsiDasar();
  o.animation = false;
  o.scales.y.ticks.callback = (n) => `Rp${rupiah(n)}`;
  o.plugins.tooltip.callbacks = { label: (c) => ` Rp${rupiah(c.parsed.y)} per lembar` };
  return o;
});
</script>

<template>
  <Panel judul="Dividen" :ket="dv?.pernah ? `Nilai dari Yahoo Finance (disesuaikan stock split)${dv.idx_ada ? ', tanggal cum & bayar dari IDX' : ''}` : 'Riwayat pembagian dividen'"
    info="Yield = dividen 12 bulan terakhir / harga sekarang. Tanda bahaya dan peluang trap dari analisis 89 kasus yield >= 6% saham syariah 2012-2024.">
    <template v-if="!dv">
      <Kerangka jenis="stat" :n="4" kolom="grid-cols-2 md:grid-cols-4" />
      <Kerangka class="mt-3" jenis="grafik" :tinggi="160" />
    </template>
    <p v-else-if="!dv.ada || !dv.pernah" class="m-0 text-muted">Belum pernah membagikan dividen sejak 2010 (menurut data Yahoo Finance).</p>
    <div v-else class="space-y-5">
      <Stats :items="stat" kolom="grid-cols-2 md:grid-cols-3 xl:grid-cols-5" />

      <div class="grid gap-5 lg:grid-cols-[1.3fr_1fr]">
        <div>
          <div class="mb-2 text-[13px] font-medium">Dividen per tahun <span class="text-xs font-normal text-muted">(* = tahun berjalan)</span></div>
          <div class="h-[220px]"><Bar v-if="grafik" :data="grafik" :options="opsi" /></div>
          <div class="-mx-6 mt-3 overflow-x-auto">
            <table class="tabel min-w-[520px]">
              <thead><tr><th>Tahun</th><th class="!text-right">Dividen</th><th class="!text-right">Yield (harga akhir tahun)</th><th class="!text-right">Payout (laba tahun lalu)</th></tr></thead>
              <tbody>
                <tr v-for="t in [...dv.tahun].reverse()" :key="t.tahun">
                  <td>{{ t.tahun }}<span v-if="t.berjalan" class="text-muted">*</span></td>
                  <td class="text-right tabular-nums">{{ t.dps ? `Rp${rupiah(t.dps)}` : "–" }}</td>
                  <td class="text-right">{{ t.yield != null ? persen(t.yield, 1, false) : "–" }}</td>
                  <td class="text-right" :class="t.payout > 100 ? 'text-turun' : ''">{{ t.payout != null ? `${t.payout}%` : "–" }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="space-y-4">
          <div class="rounded-2xl border border-garis px-5 py-4">
            <div class="mb-2 flex items-center gap-2 text-[13px] font-medium">
              <component :is="dv.tanda.length ? TriangleAlert : CircleCheck" class="h-4 w-4" :class="dv.tanda.length ? 'text-kuning' : 'text-naik'" />
              Cek dividend trap
              <span v-if="dv.trap" class="chip ml-auto" :class="dv.trap.trap >= 65 ? 'bg-turun-bg text-turun' : 'bg-kuning-bg text-kuning'">historis trap {{ dv.trap.trap }}%</span>
            </div>
            <ul v-if="dv.tanda.length" class="m-0 list-disc space-y-1 pl-5 text-[13px] text-ink-2">
              <li v-for="t in dv.tanda" :key="t.kode">{{ t.ket }}</li>
            </ul>
            <p v-else class="m-0 text-[13px] text-ink-2">Tidak ada tanda bahaya yang terdeteksi.</p>
            <p v-if="dv.trap" class="m-0 mt-3 text-xs leading-relaxed text-muted">
              Saham yield ≥ 6% dengan {{ dv.trap.jumlah_tanda }} tanda harga/sektor (spesial, harga turun, di bawah MA200, komoditas) kena trap {{ dv.trap.trap }}% ({{ dv.trap.n }} kasus);
              rata-rata semua {{ dv.trap.rata_trap }}%. Trap = total return 12 bulan negatif atau dividen berikutnya dipotong ≥ 30%.
            </p>
          </div>
          <div v-if="rt" class="rounded-2xl border border-garis px-5 py-4">
            <div class="mb-2 flex flex-wrap items-center gap-2 text-[13px] font-medium">
              Riwayat dividend trap saham ini
              <span class="chip ml-auto" :class="VONIS[rt.ex.vonis][1]">{{ VONIS[rt.ex.vonis][0] }}</span>
            </div>
            <p v-if="rt.ex.n" class="m-0 text-[13px] leading-relaxed text-ink-2">
              <b class="font-medium text-ink">Trap ex-date:</b> {{ rt.ex.kena }} dari {{ rt.ex.n }} kali bagi dividen sejak 2015 ({{ rt.ex.persen }}%) rugi kalau dibeli di cum lalu dijual 20 hari setelah ex, walau sudah dapat dividen.
              Rata-rata semua saham syariah {{ Math.round(rt.ex.acuan_persen ?? 56) }}%.
              <template v-if="rt.ex.median_pulih"> Setelah turun, harga biasanya butuh {{ rt.ex.median_pulih }} hari bursa (±{{ Math.max(1, Math.round(rt.ex.median_pulih / 21)) }} bulan) untuk naik lagi ke harga sebelum dividen</template><template v-if="rt.ex.belum_pulih">; {{ rt.ex.belum_pulih }} kali tidak pernah kembali</template>.
            </p>
            <p class="m-0 mt-2 text-[13px] leading-relaxed text-ink-2">
              <b class="font-medium text-ink">Trap yield tinggi:</b>{{ " " }}
              <template v-if="rt.yield.n">{{ rt.yield.kena }} dari {{ rt.yield.n }} kali yield ≥ 6% di akhir tahun berakhir trap (rugi 12 bulan atau dividen berikutnya dipotong ≥ 30%):
                <span v-for="(y, i) in rt.yield.kejadian" :key="y.tahun">{{ i ? ", " : "" }}{{ y.tahun }} <span :class="y.trap ? 'text-turun' : 'text-naik'">{{ y.trap ? (y.dipotong && y.rugi ? "rugi + dipotong" : y.rugi ? "rugi" : "dipotong") : "aman" }}</span></span>.
              </template>
              <template v-else>tidak pernah punya yield ≥ 6% di akhir tahun 2012–2024, jadi belum pernah masuk kategori ini.</template>
            </p>
          </div>
          <div v-if="dv.mendatang?.length" class="rounded-2xl bg-aksen-lembut px-5 py-4">
            <div class="mb-2 flex items-center gap-2 text-[13px] font-medium text-aksen"><CalendarClock class="h-4 w-4" />Jadwal dividen berikutnya (IDX)</div>
            <div v-for="m in dv.mendatang" :key="m.ex" class="text-[13px] text-ink-2">
              <div class="flex flex-wrap justify-between gap-x-4">
                <span>Cum <b class="font-medium text-ink">{{ tglId(m.cum) }}</b> · ex {{ tglId(m.ex) }}</span>
                <span v-if="m.per_lembar" class="font-medium tabular-nums text-ink">±Rp{{ rupiah(m.per_lembar) }}/lembar</span>
              </div>
              <div class="text-xs text-muted">Cair {{ tglId(m.bayar) }}<template v-if="m.per_lembar && dv.harga"> · yield {{ persen((m.per_lembar / dv.harga) * 100, 1, false) }}</template><template v-if="m.dihitung"> · nilai = total dividen / jumlah saham</template></div>
              <div class="mt-1 text-xs text-muted">Beli paling lambat di tanggal cum supaya dapat dividen ini.</div>
            </div>
          </div>
        </div>
      </div>
      <div>
            <div class="mb-1 flex flex-wrap items-center gap-2 text-[13px] font-medium">Pembayaran terakhir & pergerakan harga
              <button v-if="dv.riwayat.length > 3" class="ml-auto text-xs font-normal text-muted hover:underline" @click="semuaBayar = !semuaBayar">{{ semuaBayar ? "Tampilkan 3 terakhir" : `Tampilkan semua (${dv.riwayat.length})` }}</button>
            </div>
            <p class="m-0 mb-2 text-xs leading-relaxed text-muted">Setelah ex-date harga biasanya turun karena dividen sudah dibayarkan. <b class="font-medium text-ink-2">Trap</b> = kalau beli di harga cum lalu jual 20 hari kemudian, rugi walau sudah dapat dividen (bersih pajak & biaya). <b class="font-medium text-ink-2">Kembali</b> = kapan harga naik lagi ke harga cum.</p>
            <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              <div v-for="r in semuaBayar ? dv.riwayat : dv.riwayat.slice(0, 3)" :key="r.tgl" class="rounded-2xl border border-garis px-4 py-3 text-[13px]">
                <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
                  <span class="font-medium">{{ tglId(r.tgl) }}</span>
                  <span class="text-ink-2">dividen <b class="font-medium tabular-nums text-ink">Rp{{ rupiah(r.dps) }}</b><template v-if="r.yield_saat"> ({{ persen(r.yield_saat, 1, false) }})</template></span>
                  <span v-if="r.total20 != null" class="chip ml-auto" :class="r.total20 < 0 ? 'bg-turun-bg text-turun' : 'bg-naik-bg text-naik'"
                    title="Beli di harga cum, terima dividen bersih pajak, jual 20 hari bursa setelah ex-date, sudah dikurangi biaya">
                    {{ r.total20 < 0 ? "Trap" : "Aman" }} · {{ persen(r.total20, 1) }}
                  </span>
                </div>
                <div v-if="r.harga_cum" class="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-xs">
                  <span class="text-muted">Harga cum</span>
                  <span>Rp{{ rupiah(r.harga_cum) }} <span class="text-muted">· harga terakhir yang masih dapat dividen{{ r.cum ? ` (${tglId(r.cum)})` : "" }}</span></span>
                  <span class="text-muted">Hari ex</span>
                  <span>Rp{{ rupiah(r.harga_ex) }} <span :class="kelasPersen(r.h1)">{{ persen(r.h1, 1) }}</span></span>
                  <template v-if="r.harga_h20 != null">
                    <span class="text-muted">20 hari kemudian</span>
                    <span>Rp{{ rupiah(r.harga_h20) }} <span :class="kelasPersen(r.h20)">{{ persen(r.h20, 1) }}</span> <span class="text-muted">· dipakai untuk menilai trap</span></span>
                  </template>
                  <template v-if="r.pernah_turun && r.hari_terendah > 1">
                    <span class="text-muted">Titik terendah</span>
                    <span>Rp{{ rupiah(r.terendah) }} <span :class="kelasPersen(r.terendah_persen)">{{ persen(r.terendah_persen, 1) }}</span> <span class="text-muted">· hari ke-{{ r.hari_terendah }} setelah ex (dicari dalam 3 bulan)</span></span>
                  </template>
                  <span class="text-muted">{{ r.pulih ? "Kembali" : "Sekarang" }}</span>
                  <span v-if="!r.pernah_turun">tidak pernah ditutup di bawah harga cum dalam 3 bulan setelah ex</span>
                  <span v-else-if="r.pulih">dari titik terendah naik lagi ke ≥ Rp{{ rupiah(r.harga_cum) }}, total {{ r.pulih }} hari bursa setelah ex <span class="text-muted">(±{{ Math.max(1, Math.round(r.pulih / 21)) }} bulan)</span></span>
                  <span v-else><span class="text-turun">belum pernah kembali</span> ke Rp{{ rupiah(r.harga_cum) }} <span class="text-muted">· sekarang</span> <span :class="kelasPersen(r.sekarang_persen)">{{ persen(r.sekarang_persen, 1) }}</span> <span class="text-muted">dari harga cum, {{ r.hari_sejak }} hari bursa setelah ex</span></span>
                  <template v-if="r.bayar">
                    <span class="text-muted">Dividen cair</span>
                    <span>{{ tglId(r.bayar) }}</span>
                  </template>
                </div>
              </div>
            </div>
          </div>
    </div>
  </Panel>
</template>

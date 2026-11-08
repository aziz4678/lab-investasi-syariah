<script setup>
import { ref, computed, onMounted } from "vue";
import { RefreshCw, Lock, Unlock } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { pakaiPekerjaan } from "@/composables/pekerjaan";
import { persen, ringkas } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import Segmen from "@/components/common/Segmen.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import PanelPekerjaan from "@/components/sistem/PanelPekerjaan.vue";

const data = ref(null);
const siap = ref(false);
const porsiSbn = ref("sbn50");
const penghasilan = ref(5000000);
const modal = ref(1000000000);
const kerja = pakaiPekerjaan();

const PILIHAN_SBN = [["sbn30", "SBN 30%"], ["sbn50", "SBN 50%"], ["sbn70", "SBN 70%"]];
const OPSI_HITUNG = ["tanpa_sbn", "sbn30", "sbn50", "sbn70"];

const muat = async () => {
  data.value = await ambil("rd/penarikan").catch(() => null);
  siap.value = true;
};

onMounted(async () => {
  await muat();
  await kerja.lanjutkan("penarikan_hitung", muat);
});

const hitungUlang = () => kerja.mulai("aksi/penarikan_hitung", {}, muat);

const bulanTeks = (s) => {
  if (!s) return "–";
  const [t, b] = s.split("-").map(Number);
  return new Date(t, b - 1, 1).toLocaleDateString("id-ID", { month: "short", year: "numeric" });
};
const waktuTeks = (s) => (s ? new Date(s).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }) : "–");

const ada = computed(() => data.value?.ada);
const patokan = computed(() => data.value?.patokan);
const terbaru = computed(() => data.value?.terbaru);
const cariPortofolio = (dok, kode) => dok?.portofolio?.find((p) => p.kode === kode);
const pat = (kode) => cariPortofolio(patokan.value, kode);
const baru = (kode) => cariPortofolio(terbaru.value, kode);
const geser = (kode) => data.value?.geser?.[kode];
const pr = (v, d = 1) => (v == null ? "–" : persen(v * 100, d, false));
const prTanda = (v, d = 1) => (v == null ? "–" : persen(v * 100, d, true));
const modalRiil = (v) => (v == null ? "–" : `${(v * 100).toLocaleString("id-ID", { maximumFractionDigits: 1 })}%`);

const kartu = computed(() => [
  { kode: "tanpa_sbn", judul: "Tanpa SBN", ikon: Unlock, ket: "RD pendapatan tetap syariah / RD pasar uang syariah 50/50, rebalance tahunan.", sifat: "Bisa dicairkan kapan saja · 0% terkunci" },
  { kode: porsiSbn.value, judul: "Dengan SBN", ikon: Lock, ket: "Sebagian di Sukuk Ritel / Sukuk Tabungan (SR/ST) yang dipegang sampai jatuh tempo, sisanya RD pendapatan tetap / pasar uang 50/50.",
    sifat: `Porsi terkunci rata-rata ${pr(pat(porsiSbn.value)?.kunci_rata, 0)} · SBN tidak bisa dijual sebelum jatuh tempo`, pilih: true },
]);

const angka = (s) => Number(String(s).replace(/\D/g, "")) || 0;
const tampilRp = (v) => (v ? v.toLocaleString("id-ID") : "");
const ubahPenghasilan = (e) => (penghasilan.value = angka(e.target.value));
const ubahModal = (e) => (modal.value = angka(e.target.value));
const rp = (v) => (v == null ? "–" : `Rp${ringkas(Math.round(v))}`);

const hasilKalkulator = computed(() =>
  OPSI_HITUNG.map((k) => {
    const p = pat(k);
    const a = p?.aman_5;
    return { kode: k, nama: k === "tanpa_sbn" ? "Tanpa SBN" : `Dengan SBN ${k.slice(3)}%`, aman: a,
      modalPerlu: a ? (penghasilan.value * 12) / a : null, penghasilanBulan: a ? (modal.value * a) / 12 : null };
  }),
);

const NAMA_BARIS = { tanpa_sbn: "Tanpa SBN (RD 50/50)", sbn30: "Dengan SBN 30%", sbn50: "Dengan SBN 50%", sbn70: "Dengan SBN 70%", jii_pu: "Pembanding: 54% JII / 46% RD pasar uang" };
const kolomTabel = computed(() => patokan.value?.portofolio?.[0]?.tabel?.map((x) => x.tarik) ?? []);
const kelasUtuh = (v) => (v == null ? "text-muted" : v >= 0.8 ? "font-medium text-naik" : v >= 0.5 ? "text-ink" : "text-muted");
</script>

<template>
  <div class="space-y-5">
    <Panel judul="Portofolio Konservatif" ket="Berapa yang aman ditarik rutin tanpa daya beli modal berkurang">
      <template #aksi>
        <span v-if="ada" class="chip" :class="data.basi ? 'bg-kuning-bg text-kuning' : 'bg-surface-2 text-ink-2'">
          Dihitung {{ waktuTeks(terbaru.dihitung) }} · data s/d {{ bulanTeks(terbaru.periode.akhir) }}<template v-if="data.basi"> · data basi</template>
        </span>
        <button class="tombol" :disabled="kerja.sibuk.value" @click="hitungUlang"><RefreshCw class="h-3.5 w-3.5" :class="kerja.sibuk.value ? 'animate-spin' : ''" />Hitung ulang</button>
      </template>
      <PanelPekerjaan class="mb-4" :kerja="kerja.kerja.value" :galat="kerja.galat.value" />
      <Kerangka v-if="!siap" jenis="kartu" :n="2" kolom="grid-cols-1 md:grid-cols-2" />
      <p v-else-if="!ada" class="m-0 text-[13px] text-ink-2">Belum ada hasil hitungan. Tekan "Hitung ulang" (±5 menit).</p>
      <div v-else class="grid gap-4 md:grid-cols-2">
        <div v-for="k in kartu" :key="k.judul" class="flex flex-col rounded-2xl border border-garis px-5 py-4">
          <div class="flex items-center gap-2">
            <component :is="k.ikon" class="h-4 w-4 text-aksen" />
            <div class="text-[15px] font-medium">{{ k.judul }}</div>
          </div>
          <p class="m-0 mt-1 text-[13px] text-ink-2">{{ k.ket }}</p>
          <Segmen v-if="k.pilih" v-model="porsiSbn" :pilihan="PILIHAN_SBN" kecil class="mt-3 self-start" />
          <div class="mt-4">
            <div class="text-xs text-muted">Tingkat aman per tahun · patokan {{ data.patokan_tahun }}</div>
            <div class="mt-0.5 text-[28px] leading-tight font-semibold">
              <template v-if="pat(k.kode)?.aman_5 != null">{{ pr(pat(k.kode).aman_5) }}</template>
              <span v-else class="text-[17px] font-medium text-muted">belum ada tingkat yang aman (≤ 3%)</span>
            </div>
            <div class="text-[11px] text-muted">
              <template v-if="geser(k.kode)">patokan {{ pr(geser(k.kode).patokan) }} → terbaru <span class="font-medium text-kuning">{{ pr(geser(k.kode).terbaru) }}</span></template>
              <template v-else>terbaru {{ pr(baru(k.kode)?.aman_5) }} (data s/d {{ bulanTeks(terbaru.periode.akhir) }})</template>
              · horizon 3 th: {{ pr(pat(k.kode)?.aman_3) }}
            </div>
          </div>
          <div class="mt-4 grid grid-cols-3 gap-3 border-t border-garis pt-3 text-center">
            <div>
              <div class="text-[11px] text-muted">Rata-rata riil/th</div>
              <div class="mt-0.5 text-[15px] font-medium">{{ prTanda(pat(k.kode)?.cagr_riil, 2) }}</div>
              <div class="text-[10px] text-muted">tanpa penarikan</div>
            </div>
            <div>
              <div class="text-[11px] text-muted">Modal riil 5 th</div>
              <div class="mt-0.5 text-[15px] font-medium">{{ modalRiil(pat(k.kode)?.di_aman_5?.median) }}</div>
              <div class="text-[10px] text-muted">biasanya</div>
            </div>
            <div>
              <div class="text-[11px] text-muted">Modal riil 5 th</div>
              <div class="mt-0.5 text-[15px] font-medium">{{ modalRiil(pat(k.kode)?.di_aman_5?.terburuk) }}</div>
              <div class="text-[10px] text-muted">paling sial</div>
            </div>
          </div>
          <p class="m-0 mt-3 text-[11px] text-muted">{{ k.sifat }}</p>
        </div>
      </div>
    </Panel>

    <Panel v-if="ada" judul="Kalkulator" ket="Pakai tingkat aman patokan tahun ini. Dua arah: dari penghasilan yang diinginkan, atau dari modal yang ada.">
      <div class="grid gap-5 lg:grid-cols-2">
        <div class="min-w-0">
          <label class="text-xs text-muted">Penghasilan per bulan yang diinginkan</label>
          <div class="mt-1 flex items-center rounded-full bg-surface-2 px-4">
            <span class="text-[13px] text-muted">Rp</span>
            <input :value="tampilRp(penghasilan)" @input="ubahPenghasilan" inputmode="numeric" class="h-10 w-full min-w-0 bg-transparent px-2 text-[15px] outline-none" />
          </div>
          <div class="mt-3 space-y-1.5">
            <div v-for="h in hasilKalkulator" :key="h.kode" class="flex items-baseline justify-between gap-3 text-[13px]">
              <span class="text-ink-2">{{ h.nama }} <span class="text-[11px] text-muted">({{ pr(h.aman) }})</span></span>
              <span class="font-medium tabular-nums">{{ h.modalPerlu ? `modal ${rp(h.modalPerlu)}` : "tidak ada tingkat aman" }}</span>
            </div>
          </div>
        </div>
        <div class="min-w-0">
          <label class="text-xs text-muted">Modal yang ada</label>
          <div class="mt-1 flex items-center rounded-full bg-surface-2 px-4">
            <span class="text-[13px] text-muted">Rp</span>
            <input :value="tampilRp(modal)" @input="ubahModal" inputmode="numeric" class="h-10 w-full min-w-0 bg-transparent px-2 text-[15px] outline-none" />
          </div>
          <div class="mt-3 space-y-1.5">
            <div v-for="h in hasilKalkulator" :key="h.kode" class="flex items-baseline justify-between gap-3 text-[13px]">
              <span class="text-ink-2">{{ h.nama }} <span class="text-[11px] text-muted">({{ pr(h.aman) }})</span></span>
              <span class="font-medium tabular-nums">{{ h.penghasilanBulan ? `${rp(h.penghasilanBulan)}/bulan` : "tidak ada tingkat aman" }}</span>
            </div>
          </div>
        </div>
      </div>
      <p class="m-0 mt-4 text-[11px] text-muted">Penghasilan naik mengikuti inflasi tiap tahun. Rumus: modal = penghasilan × 12 ÷ tingkat aman.</p>
    </Panel>

    <section v-if="ada" class="panel">
      <details class="group">
        <summary class="cursor-pointer list-none px-6 py-4 text-[15px] font-medium">Lihat detail <span class="text-xs font-normal text-muted">· % tanggal mulai yang modal riilnya utuh setelah 5 tahun</span></summary>
        <div class="overflow-x-auto pb-4">
          <table class="tabel min-w-[640px]">
            <thead>
              <tr><th>Portofolio</th><th v-for="t in kolomTabel" :key="t" class="!text-right">Tarik {{ pr(t) }}/th</th><th class="!text-right">Rata-rata riil/th</th></tr>
            </thead>
            <tbody>
              <tr v-for="p in patokan.portofolio" :key="p.kode">
                <td class="text-[13px]">{{ NAMA_BARIS[p.kode] ?? p.nama }}</td>
                <td v-for="x in p.tabel" :key="x.tarik" class="text-right tabular-nums" :class="kelasUtuh(x.riil5?.utuh)">{{ x.riil5 ? `${Math.round(x.riil5.utuh * 100)}%` : "–" }}</td>
                <td class="text-right tabular-nums">{{ prTanda(p.cagr_riil, 2) }}</td>
              </tr>
            </tbody>
          </table>
          <p class="m-0 px-6 pt-3 text-[11px] text-muted">
            Lolos = modal riil ≥ 100% di ≥ 80% tanggal mulai ({{ patokan.n_mulai_5 }} tanggal mulai, horizon 5 th) dan tidak pernah kehabisan dana cair.
            Pembanding JII memakai asumsi dividen {{ pr(patokan.dividen_jii) }}/th.
          </p>
        </div>
      </details>
    </section>

    <div v-if="ada" class="rounded-2xl bg-surface-2 px-5 py-4 text-[12px] leading-relaxed text-ink-2">
      <div>• Data {{ bulanTeks(patokan.periode.awal) }} – {{ bulanTeks(patokan.periode.akhir) }}: indikatif, bukan jaminan.</div>
      <div>• "Aman" = daya beli modal tidak turun (sudah memperhitungkan inflasi), bukan sekadar nominal tetap.</div>
      <div>• Kupon SBN di masa lalu lebih tinggi dari kupon sekarang, jadi opsi Dengan SBN bisa terlalu optimis.</div>
      <div>• Dana darurat dipisah, 100% di RD pasar uang syariah (tidak di SBN).</div>
    </div>
  </div>
</template>

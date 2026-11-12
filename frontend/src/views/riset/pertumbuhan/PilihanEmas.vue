<script setup>
import { ref, computed, onMounted } from "vue";
import { Coins, AlertTriangle, CheckCircle2, XCircle } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { rupiahRingkas } from "@/utils/format";
import Segmen from "@/components/common/Segmen.vue";
import { prTanda, pr, bulanPendek } from "@/views/riset/pertumbuhan/bantu";

const props = defineProps({ setoran: { type: Number, default: 1000000 } });
const PILIHAN = [["2", "2 kaki (50/50)"], ["3", "3 kaki dengan emas (40/40/20)"]];
const pilih = ref("2");
const e = ref(null);
const siap = ref(false);

onMounted(async () => {
  e.value = await ambil("pertumbuhan/emas").catch(() => null);
  siap.value = true;
});

const ada = computed(() => e.value?.ada && e.value?.dev && e.value?.holdout);
const baris = computed(() => {
  const x = e.value;
  if (!x) return [];
  const f = (a, b, fn) => [fn(a), fn(b)];
  const per = (p) => ({ h35: p.h35, h37: p.h37 });
  const d = per(x.dev);
  const h = per(x.holdout);
  return [
    { judul: "Rata-rata per tahun", dev: f(d.h35.cagr, d.h37.cagr, prTanda), hold: f(h.h35.cagr, h.h37.cagr, prTanda) },
    { judul: "Turun terdalam", dev: f(d.h35.dd, d.h37.dd, (v) => pr(v)), hold: f(h.h35.dd, h.h37.dd, (v) => pr(v)) },
    { judul: "10 tahun terburuk, per tahun", dev: f(d.h35.j10_buruk, d.h37.j10_buruk, prTanda), hold: f(h.h35.j10_buruk, h.h37.j10_buruk, prTanda) },
  ];
});
const bagi = computed(() => [
  { nama: "Saham syariah Indonesia", nilai: props.setoran * 0.4, warna: "bg-s2" },
  { nama: "Saham syariah global", nilai: props.setoran * 0.4, warna: "bg-s4" },
  { nama: "ETF emas syariah", nilai: props.setoran * 0.2, warna: "bg-kuning" },
]);
const terpilih = computed(() => e.value?.etf?.find((x) => x.kode === e.value?.terpilih));
const pc = (v) => (v == null ? "–" : `${v >= 0 ? "+" : ""}${(v * 100).toLocaleString("id-ID", { maximumFractionDigits: 1 })}%`);
const mahal = (v) => v != null && Math.abs(v) > (e.value?.batas_premium ?? 0.01);
</script>

<template>
  <section v-if="ada" class="panel px-4 py-5 sm:px-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-2 text-[14px] font-medium"><Coins class="h-4 w-4 text-kuning" />Pilih: 2 kaki atau 3 kaki dengan emas</div>
      <Segmen v-model="pilih" :pilihan="PILIHAN" kecil />
    </div>
    <div class="mt-2 flex flex-wrap items-center gap-1.5">
      <span class="rounded-2xl bg-kuning-bg px-2.5 py-1 text-[11px] leading-snug font-medium text-kuning">Lolos uji riwayat · uji maju dengan produk nyata mulai 1 Des 2026</span>
      <span class="chip bg-surface-2 text-ink-2">{{ pilih === "2" ? "Pilihan bawaan sampai uji maju selesai" : "Belum jadi bawaan" }}</span>
    </div>

    <div class="mt-4 overflow-x-auto">
      <table class="w-full min-w-[520px] border-collapse text-[12px]">
        <thead>
          <tr class="text-muted">
            <th class="py-1.5 text-left font-normal" rowspan="2"></th>
            <th class="px-2 text-center font-normal" colspan="2">Data lama · Jun 2001 – Des 2013</th>
            <th class="px-2 text-center font-normal" colspan="2">Data uji · Jan 2014 – Okt 2026</th>
          </tr>
          <tr class="text-[11px] text-muted">
            <th class="px-2 py-1 text-right font-normal" :class="pilih === '2' ? 'text-ink' : ''">2 kaki</th>
            <th class="px-2 py-1 text-right font-normal" :class="pilih === '3' ? 'text-ink' : ''">3 kaki</th>
            <th class="px-2 py-1 text-right font-normal" :class="pilih === '2' ? 'text-ink' : ''">2 kaki</th>
            <th class="px-2 py-1 text-right font-normal" :class="pilih === '3' ? 'text-ink' : ''">3 kaki</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="b in baris" :key="b.judul" class="border-t border-garis">
            <td class="py-2 pr-2">{{ b.judul }}</td>
            <td v-for="(v, i) in [...b.dev, ...b.hold]" :key="i" class="px-2 py-2 text-right tabular-nums" :class="(i % 2 === 0) === (pilih === '2') ? 'font-semibold' : 'text-muted'">{{ v }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="m-0 mt-2 text-[11px] leading-relaxed text-muted">Indeks, dalam rupiah, bukan produk nyata: biaya emas dimodelkan spread 3% pulang-pergi + 0,5%/th. Kedua kolom dihitung dengan kode dan data yang sama, masing-masing dimulai dari nol di awal periodenya. 3 kaki lolos semua kriteria yang dikunci di kedua periode; hasil masa lalu, bukan janji.</p>

    <div class="mt-4 rounded-2xl bg-surface-2 px-4 py-3 text-[13px] leading-relaxed text-ink-2">
      <div class="mb-1 text-[13px] font-medium text-ink">Kenapa emas, dan apa bebannya</div>
      Emas cenderung menahan saat saham jatuh atau rupiah melemah (contoh 2008 dan 2020), tetapi jadi beban saat saham naik kencang (2014 dan 2021).
      Sebagian besar keunggulan 2014–2026 datang dari emas di 2024–2025 (+32% dan +70%); masuk setelah emas naik setinggi itu bisa berarti beberapa tahun emas menjadi beban.
      Penyeimbangan tiap Desember otomatis menjual sebagian emas yang sudah naik, dan membeli kembali bagian yang tertinggal.
    </div>

    <div v-if="pilih === '3'" class="mt-4">
      <div class="text-[13px] font-medium">Setoran {{ rupiahRingkas(setoran) }}/bulan, dibagi 40 / 40 / 20</div>
      <div class="mt-2 flex h-2.5 gap-0.5 overflow-hidden rounded-full">
        <div v-for="x in bagi" :key="x.nama" :class="x.warna" :style="{ width: `${(x.nilai / setoran) * 100}%` }" />
      </div>
      <ul class="m-0 mt-2 list-none space-y-1 p-0 text-[12px]">
        <li v-for="x in bagi" :key="x.nama" class="flex items-center justify-between gap-3">
          <span class="flex items-center gap-2"><span class="h-2 w-2 shrink-0 rounded-full" :class="x.warna" />{{ x.nama }}</span>
          <span class="font-medium tabular-nums">{{ rupiahRingkas(x.nilai) }}</span>
        </li>
      </ul>
      <p class="m-0 mt-2 text-[11px] leading-relaxed text-muted">Daftar belanja di bawah masih dihitung untuk 2 kaki (50/50). Untuk 3 kaki pakai produk yang sama dengan nominal 40% + 40% di atas, dan 20% ke ETF emas. Seimbangkan tiap Desember ke 40/40/20.</p>
    </div>
    <p v-else class="m-0 mt-3 text-[12px] text-muted">Daftar belanja dan jadwal di bawah mengikuti 2 kaki (50/50). Pilih "3 kaki" untuk melihat pembagian setoran dengan emas.</p>

    <div class="mt-4 grid gap-3 md:grid-cols-2">
      <div class="rounded-2xl border border-garis p-4">
        <div class="flex items-center gap-2 text-[13px] font-medium text-naik"><CheckCircle2 class="h-4 w-4" />Disarankan: ETF emas syariah{{ terpilih ? ` · terpilih ${terpilih.kode}` : "" }}</div>
        <p class="m-0 mt-1 text-[12px] leading-relaxed text-ink-2">Dibeli lewat rekening saham seperti membeli saham (1 lot = 100 unit). Harga bursa bisa berbeda dari nilai emas di dalamnya (NAV); cek selisihnya sebelum beli.</p>
        <ul class="m-0 mt-3 list-none space-y-2 p-0">
          <li v-for="x in e.etf" :key="x.kode" class="rounded-xl bg-surface-2 px-3 py-2 text-[12px]">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <span class="font-medium">{{ x.kode }} <span class="font-normal text-muted">· {{ x.nama }}</span><span v-if="x.kode === e.terpilih" class="chip ml-1.5 bg-aksen-lembut text-aksen">terpilih</span></span>
              <span v-if="x.premium_terakhir" class="chip" :class="mahal(x.premium_terakhir.premium) ? 'bg-kuning-bg text-kuning' : 'bg-naik-bg text-naik'">
                <AlertTriangle v-if="mahal(x.premium_terakhir.premium)" class="mr-1 h-3 w-3" />harga bursa {{ pc(x.premium_terakhir.premium) }} dari NAV
              </span>
            </div>
            <div class="mt-0.5 text-[11px] text-muted">
              Dana kelolaan {{ rupiahRingkas(x.aum) }}<template v-if="x.aum_tgl"> ({{ bulanPendek(x.aum_tgl) }})</template>
              · selisih harga-NAV tengah {{ pc(x.premium_median) }} sejak {{ x.mulai }}<template v-if="!x.lolos && x.alasan?.length"> · tidak memenuhi syarat: {{ x.alasan.join(", ") }}</template><template v-if="x.premium_terakhir"> · per {{ x.premium_terakhir.tgl }}</template>
            </div>
          </li>
        </ul>
        <p v-if="mahal(terpilih?.premium_terakhir?.premium)" class="m-0 mt-2 flex items-start gap-1.5 text-[11px] leading-relaxed text-kuning">
          <AlertTriangle class="mt-0.5 h-3 w-3 shrink-0" />Peringatan: harga bursa di atas NAV lebih dari {{ (e.batas_premium * 100).toFixed(0) }}%. Aturan uji maju tidak membeli di hari seperti ini; membeli di harga itu berarti membayar lebih mahal dari emas yang didapat.
        </p>
        <p class="m-0 mt-2 text-[11px] leading-relaxed text-muted">Pemilihan menurut aturan uji maju: dana kelolaan ≥ Rp10 M dan median nilai transaksi 60 hari ≥ Rp10 jt, lalu selisih harga-NAV (median 60 hari) paling kecil. Data baru terkumpul sejak Agu–Okt 2026 dan tipis, jadi pilihan ini sementara; ditetapkan resmi 31 Des 2026 dan tiap Desember. Beli hanya di hari selisihnya ≤ +2%.</p>
      </div>
      <div class="rounded-2xl border border-garis p-4">
        <div class="flex items-center gap-2 text-[13px] font-medium text-turun"><XCircle class="h-4 w-4" />Tidak disarankan untuk strategi ini: emas batangan</div>
        <p class="m-0 mt-1 text-[12px] leading-relaxed text-ink-2">Selisih harga beli dan harga jual kembali (buyback) sekitar 7–10%. Strategi ini menyeimbangkan tiap tahun, sehingga biaya itu terkena berulang kali dan memakan keuntungan.</p>
      </div>
    </div>
  </section>
</template>

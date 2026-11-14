<script setup>
import { ref, computed, onMounted } from "vue";
import { Coins, AlertTriangle, CheckCircle2, XCircle } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { rupiahRingkas } from "@/utils/format";
import { prTanda, pr, bulanPendek } from "@/views/riset/pertumbuhan/bantu";

const e = ref(null);

onMounted(async () => {
  e.value = await ambil("pertumbuhan/emas").catch(() => null);
});

const ada = computed(() => e.value?.ada && e.value?.dev && e.value?.holdout);
const baris = computed(() => {
  const x = e.value;
  if (!x) return [];
  const f = (a, b, fn) => [fn(a), fn(b)];
  const d = { h35: x.dev.h35, h37: x.dev.h37 };
  const h = { h35: x.holdout.h35, h37: x.holdout.h37 };
  return [
    { judul: "Rata-rata per tahun", dev: f(d.h35.cagr, d.h37.cagr, prTanda), hold: f(h.h35.cagr, h.h37.cagr, prTanda) },
    { judul: "Turun terdalam", dev: f(d.h35.dd, d.h37.dd, (v) => pr(v)), hold: f(h.h35.dd, h.h37.dd, (v) => pr(v)) },
    { judul: "10 tahun terburuk, per tahun", dev: f(d.h35.j10_buruk, d.h37.j10_buruk, prTanda), hold: f(h.h35.j10_buruk, h.h37.j10_buruk, prTanda) },
  ];
});
const terpilih = computed(() => e.value?.etf?.find((x) => x.kode === e.value?.terpilih));
const pc = (v) => (v == null ? "–" : `${v >= 0 ? "+" : ""}${(v * 100).toLocaleString("id-ID", { maximumFractionDigits: 1 })}%`);
const mahal = (v) => v != null && Math.abs(v) > (e.value?.batas_premium ?? 0.01);
</script>

<template>
  <div v-if="ada" class="space-y-5">
    <section class="panel px-4 py-5 sm:px-6">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div class="flex items-center gap-2 text-[14px] font-medium"><Coins class="h-4 w-4 text-kuning" />Hasil di data lama dan data uji</div>
        <span class="chip bg-kuning-bg text-kuning">Lolos uji riwayat · uji maju mulai 1 Des 2026</span>
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
              <th class="px-2 py-1 text-right font-normal">Saham saja</th>
              <th class="px-2 py-1 text-right font-normal">Saham + emas</th>
              <th class="px-2 py-1 text-right font-normal">Saham saja</th>
              <th class="px-2 py-1 text-right font-normal">Saham + emas</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="b in baris" :key="b.judul" class="border-t border-garis">
              <td class="py-2 pr-2">{{ b.judul }}</td>
              <td v-for="(v, i) in [...b.dev, ...b.hold]" :key="i" class="px-2 py-2 text-right tabular-nums" :class="i % 2 === 1 ? 'font-semibold' : ''">{{ v }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="m-0 mt-2 text-[11px] leading-relaxed text-muted">Saham saja = 50% Indonesia + 50% global. Saham + emas = 40% + 40% + 20% emas. Indeks dalam rupiah, bukan produk nyata: biaya emas dimodelkan spread 3% pulang-pergi + 0,5%/th. Kedua kolom dihitung dengan kode dan data yang sama, masing-masing dimulai dari nol di awal periodenya. Saham + emas lolos semua kriteria yang dikunci di kedua periode; hasil masa lalu, bukan janji.</p>

      <div class="mt-4 rounded-2xl bg-surface-2 px-4 py-3 text-[13px] leading-relaxed text-ink-2">
        <div class="mb-1 text-[13px] font-medium text-ink">Kenapa emas, dan apa bebannya</div>
        Emas cenderung menahan saat saham jatuh atau rupiah melemah (contoh 2008 dan 2020), tetapi jadi beban saat saham naik kencang (2014 dan 2021).
        Sebagian besar keunggulan 2014–2026 datang dari emas di 2024–2025 (+32% dan +70%); masuk setelah emas naik setinggi itu bisa berarti beberapa tahun emas menjadi beban.
        Penyeimbangan tiap Desember otomatis menjual sebagian emas yang sudah naik, dan membeli kembali bagian yang tertinggal.
      </div>
    </section>

    <section class="panel px-4 py-5 sm:px-6">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div class="flex items-center gap-2 text-[14px] font-medium"><CheckCircle2 class="h-4 w-4 text-naik" />ETF emas syariah yang diperiksa</div>
        <span v-if="terpilih" class="chip bg-aksen-lembut text-aksen">terpilih sementara: {{ terpilih.kode }}</span>
      </div>
      <p class="m-0 mt-1 text-[12px] leading-relaxed text-ink-2">Dibeli lewat rekening saham seperti membeli saham (1 lot = 100 unit). Harga bursa bisa berbeda dari nilai emas di dalamnya (NAV); cek selisihnya sebelum beli.</p>
      <ul class="m-0 mt-4 grid list-none gap-3 p-0 md:grid-cols-2">
        <li v-for="x in e.etf" :key="x.kode" class="rounded-2xl border p-3 text-[12px]" :class="x.kode === e.terpilih ? 'border-aksen bg-aksen-lembut/40' : 'border-garis'">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <span class="font-medium">{{ x.kode }}<span v-if="x.kode === e.terpilih" class="chip ml-1.5 bg-aksen-lembut text-aksen">terpilih</span></span>
            <span v-if="x.premium_terakhir" class="chip" :class="mahal(x.premium_terakhir.premium) ? 'bg-kuning-bg text-kuning' : 'bg-naik-bg text-naik'">
              <AlertTriangle v-if="mahal(x.premium_terakhir.premium)" class="mr-1 h-3 w-3" />selisih harga vs nilai emas {{ pc(x.premium_terakhir.premium) }}
            </span>
          </div>
          <div class="mt-0.5 text-[12px] text-ink-2">{{ x.nama }}</div>
          <div class="mt-1.5 text-[11px] leading-relaxed text-muted">
            Dana kelolaan {{ rupiahRingkas(x.aum) }}<template v-if="x.aum_tgl"> ({{ bulanPendek(x.aum_tgl) }})</template>
            · selisih tengah {{ pc(x.premium_median) }} sejak {{ x.mulai }}<template v-if="x.premium_terakhir"> · per {{ x.premium_terakhir.tgl }}</template>
          </div>
          <div v-if="!x.lolos && x.alasan?.length" class="mt-1 text-[11px] text-turun">Tidak memenuhi syarat: {{ x.alasan.join(", ") }}</div>
        </li>
      </ul>
      <p v-if="mahal(terpilih?.premium_terakhir?.premium)" class="m-0 mt-3 flex items-start gap-1.5 text-[12px] leading-relaxed text-kuning">
        <AlertTriangle class="mt-0.5 h-3.5 w-3.5 shrink-0" />Harga bursa di atas nilai emasnya lebih dari {{ (e.batas_premium * 100).toFixed(0) }}%. Aturan uji maju tidak membeli di hari seperti ini; membeli di harga itu berarti membayar lebih mahal dari emas yang didapat.
      </p>
      <p class="m-0 mt-3 text-[11px] leading-relaxed text-muted">Pemilihan menurut aturan uji maju: dana kelolaan ≥ Rp10 M dan median nilai transaksi 60 hari ≥ Rp10 jt, lalu selisih harga-NAV (median 60 hari) paling kecil. Data baru terkumpul sejak Agu–Okt 2026 dan tipis, jadi pilihan ini sementara; ditetapkan resmi 31 Des 2026 dan tiap Desember. Beli hanya di hari selisihnya ≤ +2%.</p>
      <div class="mt-3 flex items-start gap-2 rounded-2xl bg-surface-2 px-4 py-3 text-[12px] leading-relaxed text-ink-2">
        <XCircle class="mt-0.5 h-4 w-4 shrink-0 text-turun" /><span><b class="font-medium text-ink">Emas batangan tidak cocok untuk strategi ini.</b> Selisih harga beli dan jual kembali (buyback) sekitar 7–10%. Strategi ini menyeimbangkan tiap tahun, sehingga biaya itu terkena berulang kali dan memakan keuntungan.</span>
      </div>
    </section>
  </div>
</template>

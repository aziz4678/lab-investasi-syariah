<script setup>
import { ref, computed, watch } from "vue";
import { Line } from "vue-chartjs";
import { Check, X, Minus, Lightbulb, TriangleAlert, Map, Hourglass } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { pakaiTema } from "@/composables/tema";
import { opsiDasar, warna, alfa } from "@/utils/chart";
import { persen, rupiah, ringkas } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import Pemutar from "@/components/common/Pemutar.vue";
import Segmen from "@/components/common/Segmen.vue";

const props = defineProps({ kode: String, yahoo: Object });
const v = ref(null);
const memuat = ref(false);
const jenis = ref("pbv");
const tema = pakaiTema();

async function muat() {
  if (!props.kode) return;
  memuat.value = true;
  v.value = await ambil(`valuasi/${props.kode}`).catch(() => ({ ada: false, alasan: "Gagal memuat valuasi." }));
  memuat.value = false;
}
watch(() => props.kode, muat, { immediate: true });

const VONIS = {
  murah: "bg-naik-bg text-naik", agak: "bg-naik-bg text-naik", wajar: "bg-surface-2 text-ink-2",
  mahal: "bg-turun-bg text-turun", rugi: "bg-turun-bg text-turun", kurang: "bg-surface-2 text-muted",
};
const SIKAP = { layak: "bg-naik text-white", pantau: "bg-kuning-bg text-kuning", hindari: "bg-turun-bg text-turun" };

function x(n, d = 1) {
  return n == null ? "–" : `${n.toLocaleString("id-ID", { minimumFractionDigits: d, maximumFractionDigits: d })}x`;
}
function rp(n) {
  return n == null ? "–" : `Rp${rupiah(Math.round(n))}`;
}

const skala = computed(() => {
  const d = v.value;
  if (!d?.wajar) return null;
  const titik = [d.harga, d.wajar, d.rencana?.area_beli, ...(d.rentang || [])].filter((n) => n != null);
  const lo = Math.min(...titik) * 0.85;
  const hi = Math.max(...titik) * 1.08;
  const pos = (n) => `${Math.min(100, Math.max(0, ((n - lo) / (hi - lo)) * 100))}%`;
  return { pos, lo, hi };
});

const rasio = computed(() => {
  const r = v.value?.rasio;
  if (!r) return [];
  const b = v.value.band;
  const s = v.value.sektor_median;
  return [
    { l: "PER (TTM)", n: x(r.per), k: `median 5 th ${x(b.per?.median)}${s?.per ? ` · ${s.jenis} ${x(s.per)}` : ""}` },
    { l: "PBV", n: x(r.pbv, 2), k: `rata 5 th ${x(b.pbv?.rata, 2)}${s?.pbv ? ` · ${s.jenis} ${x(s.pbv, 2)}` : ""}` },
    { l: "PEG", n: r.peg == null ? "–" : r.peg.toLocaleString("id-ID", { maximumFractionDigits: 2 }), k: "< 1 murah relatif ke pertumbuhan" },
    { l: "P/S", n: x(r.ps, 2), k: "kapitalisasi / pendapatan" },
    { l: "P/CFO", n: x(r.pcfo), k: "proksi P/FCF (tanpa capex)" },
    { l: "Dividend yield", n: persen(r.dy, 1, false), k: `Rp${rupiah(r.dps)}/saham${r.payout ? ` · payout ${r.payout}%` : ""}` },
    { l: "ROE", n: persen(r.roe, 1, false), k: s?.roe != null ? `${s.jenis} ${persen(s.roe, 1, false)}` : "laba / ekuitas" },
    { l: "ROA", n: persen(r.roa, 1, false), k: "laba / aset" },
    { l: "DER", n: x(r.der, 2), k: v.value.bank ? "tidak relevan untuk bank" : "liabilitas / ekuitas" },
    { l: "Margin laba", n: persen(r.npm, 1, false), k: r.gpm != null ? `margin kotor ${persen(r.gpm, 1, false)}` : "laba / pendapatan" },
    { l: "Laba tumbuh", n: persen(r.g_laba3 ?? r.g_laba1, 1), k: r.g_laba3 != null ? `per tahun (3 th) · 1 th ${persen(r.g_laba1, 1)}` : "1 tahun" },
    { l: "Pendapatan tumbuh", n: persen(r.g_pend3 ?? r.g_pend1, 1), k: r.g_pend3 != null ? `per tahun (3 th) · 1 th ${persen(r.g_pend1, 1)}` : "1 tahun" },
  ];
});

const HORIZON = [["21", "1 bln"], ["63", "3 bln"], ["126", "6 bln"], ["252", "1 th"], ["504", "2 th"]];
const kv = computed(() => v.value?.konvergensi || null);
const bulan = (h) => (h == null ? "–" : `±${Math.max(1, Math.round(h / 21))} bulan`);
const p = (x) => (x == null ? "–" : `${Math.round(x)}%`);
const banding = computed(() => {
  const d = kv.value?.perlu_data;
  if (!d) return null;
  const u = d.undervalue?.peluang?.["252"], w = d.wajar?.peluang?.["252"];
  if (u == null || w == null) return null;
  const selisih = u - w;
  return { u, w, teks: selisih >= 5 ? "lebih sering sampai dibanding saham biasa dengan kenaikan yang sama" : selisih <= -5 ? "lebih jarang sampai dibanding saham biasa dengan kenaikan yang sama" : "hampir sama dengan saham biasa yang butuh kenaikan sama: status Undervalue tidak menambah peluang" };
});

const grafik = computed(() => {
  tema.value;
  const d = v.value;
  if (!d?.riwayat?.length) return null;
  const b = d.band[jenis.value];
  const nilai = d.riwayat.map((r) => r[jenis.value]);
  const tetap = (n) => nilai.map(() => n);
  const s1 = warna("--series-1");
  const ds = [{ label: jenis.value.toUpperCase(), data: nilai, borderColor: s1, backgroundColor: s1, borderWidth: 2, pointRadius: 0, tension: 0.25, order: 1 }];
  if (b) {
    ds.push(
      { label: "+1 SD", data: tetap(b.atas), borderWidth: 0, pointRadius: 0, fill: "+1", backgroundColor: alfa(s1, 0.1), order: 3 },
      { label: "−1 SD", data: tetap(b.bawah), borderWidth: 0, pointRadius: 0, order: 3 },
      { label: "Rata-rata 5 th", data: tetap(b.rata), borderColor: warna("--series-3"), borderDash: [5, 4], borderWidth: 1.5, pointRadius: 0, order: 2 },
    );
  }
  return { labels: d.riwayat.map((r) => r.tgl), datasets: ds };
});

const opsi = computed(() => {
  tema.value;
  const o = opsiDasar();
  o.animation = false;
  o.scales.x.ticks.maxTicksLimit = 7;
  o.scales.y.ticks.callback = (n) => `${n.toLocaleString("id-ID")}x`;
  o.plugins.tooltip.callbacks = { label: (c) => ` ${c.dataset.label}  ${c.parsed.y?.toLocaleString("id-ID", { maximumFractionDigits: 2 })}x` };
  return o;
});
</script>

<template>
  <Panel judul="Valuasi" :ket="v?.ada ? `Harga ${v.tgl} · laporan ${v.laporan} (terbit ${v.tgl_laporan})${v.unit === 'USD' ? ` · laporan USD, kurs Rp${rupiah(v.kurs)}` : ''}` : 'Nilai wajar, kualitas, dan rencana'"
    info="Nilai wajar = median beberapa metode (PER/PBV historis 5 tahun, PER/PBV industri atau sektor, Graham, DDM). Angka 12 bulan terakhir (TTM), hanya laporan yang sudah terbit.">
    <template #aksi>
      <span v-if="v?.ada" class="chip !h-7 !px-3 !text-xs" :class="VONIS[v.vonis.kode]">{{ v.vonis.label }}</span>
    </template>

    <template v-if="memuat && !v">
      <Pemutar teks="Menghitung valuasi..." />
      <Kerangka class="mt-4" jenis="stat" :n="4" kolom="grid-cols-2 md:grid-cols-4" />
      <Kerangka class="mt-2" :n="3" />
    </template>
    <div v-else-if="v && !v.ada">
      <p class="m-0 text-muted">{{ v.alasan }}</p>
      <div v-if="yahoo && (yahoo.trailingPE || yahoo.priceToBook)" class="mt-4">
        <div class="mb-2 text-xs text-muted">Sementara pakai snapshot Yahoo Finance (tidak diverifikasi):</div>
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-xs text-muted">PER</div><div class="font-medium">{{ yahoo.trailingPE == null ? "–" : yahoo.trailingPE.toLocaleString("id-ID", { maximumFractionDigits: 1 }) + "x" }}</div></div>
          <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-xs text-muted">PBV</div><div class="font-medium">{{ yahoo.priceToBook == null ? "–" : yahoo.priceToBook.toLocaleString("id-ID", { maximumFractionDigits: 2 }) + "x" }}</div></div>
          <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-xs text-muted">ROE</div><div class="font-medium">{{ yahoo.returnOnEquity == null ? "–" : (yahoo.returnOnEquity * 100).toLocaleString("id-ID", { maximumFractionDigits: 1 }) + "%" }}</div></div>
          <div class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-xs text-muted">Dividend yield</div><div class="font-medium">{{ yahoo.dividendYield == null ? "–" : yahoo.dividendYield.toLocaleString("id-ID", { maximumFractionDigits: 1 }) + "%" }}</div></div>
        </div>
      </div>
    </div>

    <div v-else-if="v" class="space-y-5" :class="memuat ? 'opacity-60' : ''">
      <div class="grid gap-3 sm:grid-cols-3">
        <div class="rounded-2xl bg-surface-2 px-5 py-4">
          <div class="text-xs text-muted">Harga sekarang</div>
          <div class="mt-1 text-[24px] leading-8 font-medium tabular-nums">{{ rp(v.harga) }}</div>
          <div class="text-xs text-muted">kapitalisasi Rp{{ ringkas(v.rasio.mcap) }}</div>
        </div>
        <div class="rounded-2xl bg-surface-2 px-5 py-4">
          <div class="text-xs text-muted">Nilai wajar (median metode)</div>
          <div class="mt-1 text-[24px] leading-8 font-medium tabular-nums">{{ rp(v.wajar) }}</div>
          <div class="text-xs text-muted">{{ v.rentang ? `rentang ${rp(v.rentang[0])} – ${rp(v.rentang[1])}` : "–" }}</div>
        </div>
        <div class="rounded-2xl bg-surface-2 px-5 py-4">
          <div class="text-xs text-muted">Margin of safety</div>
          <div class="mt-1 text-[24px] leading-8 font-medium tabular-nums" :class="v.mos == null ? '' : v.mos >= 20 ? 'text-naik' : v.mos < -15 ? 'text-turun' : ''">{{ persen(v.mos, 1) }}</div>
          <div class="text-xs text-muted">{{ v.vonis.ket }}</div>
        </div>
      </div>

      <div v-if="skala" class="px-1 pt-6 pb-8">
        <div class="relative h-2.5 rounded-full bg-surface-3">
          <div v-if="v.rentang" class="absolute inset-y-0 rounded-full bg-s1/30" :style="{ left: skala.pos(v.rentang[0]), width: `calc(${skala.pos(v.rentang[1])} - ${skala.pos(v.rentang[0])})` }"></div>
          <div v-if="v.rencana" class="absolute -top-2 -bottom-2 w-0 border-l-2 border-dashed border-naik" :style="{ left: skala.pos(v.rencana.area_beli) }">
            <span class="absolute top-full mt-1 -translate-x-1/2 text-[11px] whitespace-nowrap text-naik">area beli {{ rp(v.rencana.area_beli) }}</span>
          </div>
          <div class="absolute -top-2 -bottom-2 w-0 border-l-2 border-s3" :style="{ left: skala.pos(v.wajar) }">
            <span class="absolute top-full mt-1 -translate-x-1/2 text-[11px] whitespace-nowrap text-muted">wajar {{ rp(v.wajar) }}</span>
          </div>
          <div class="absolute top-1/2 h-4.5 w-4.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-[3px] border-surface bg-ink shadow" :style="{ left: skala.pos(v.harga) }">
            <span class="absolute bottom-full left-1/2 mb-1.5 -translate-x-1/2 rounded-full bg-ink px-2 py-0.5 text-[11px] whitespace-nowrap text-surface">harga {{ rp(v.harga) }}</span>
          </div>
        </div>
      </div>

      <div class="flex flex-wrap items-start gap-4 rounded-2xl border border-garis px-5 py-4">
        <span class="chip !h-8 !px-4 !text-[13px]" :class="SIKAP[v.sikap.kode]">{{ v.sikap.label }}</span>
        <div class="min-w-[220px] flex-1">
          <div class="text-[13px] text-ink-2">{{ v.sikap.ket }}</div>
          <div class="mt-2 flex flex-wrap gap-2 text-xs">
            <span class="chip" :class="VONIS[v.vonis.kode]">Valuasi: {{ v.vonis.label }}</span>
            <span class="chip" :class="v.skor >= v.skor_maks - 1 ? 'bg-naik-bg text-naik' : v.skor > v.skor_maks / 2 ? 'bg-kuning-bg text-kuning' : 'bg-turun-bg text-turun'">Kualitas {{ v.skor }}/{{ v.skor_maks }}</span>
            <span class="chip" :class="v.tren.di_atas_ma200 ? 'bg-naik-bg text-naik' : 'bg-kuning-bg text-kuning'">Tren: {{ v.tren.di_atas_ma200 ? "di atas MA200" : "di bawah MA200" }}</span>
            <span class="chip" :class="v.syariah ? 'bg-naik-bg text-naik' : 'bg-turun-bg text-turun'">{{ v.syariah ? "Syariah" : "Bukan syariah" }}</span>
          </div>
        </div>
      </div>

      <div v-if="kv" class="rounded-2xl border border-garis px-5 py-4">
        <div class="flex flex-wrap items-center gap-2">
          <Hourglass class="h-4 w-4 text-aksen" />
          <span class="text-[13px] font-medium">Seberapa sering saham Undervalue sampai ke nilai wajar?</span>
          <span class="chip bg-surface-2 text-muted">data historis {{ kv.jumlah }} kasus · {{ kv.periode }}</span>
          <span class="chip bg-turun-bg text-turun">tesis tidak dipakai sebagai strategi</span>
        </div>

        <div class="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <div class="rounded-xl bg-surface-2 px-4 py-3">
            <div class="text-xs text-muted">Peluang sampai · MoS {{ kv.grup_mos }}%</div>
            <div class="mt-0.5 text-[20px] leading-7 font-medium">{{ p(kv.mos?.peluang?.["252"]) }} <span class="text-[13px] font-normal text-muted">dalam 1 tahun</span></div>
            <div class="text-[11px] text-muted">{{ p(kv.mos?.peluang?.["504"]) }} dalam 2 tahun · {{ p(kv.mos?.peluang?.["126"]) }} dalam 6 bulan · {{ kv.mos?.n }} kasus</div>
          </div>
          <div class="rounded-xl bg-surface-2 px-4 py-3">
            <div class="text-xs text-muted">Butuh naik {{ persen(kv.perlu, 0) }} ke nilai wajar</div>
            <div class="mt-0.5 text-[20px] leading-7 font-medium">{{ p(banding?.w) }} <span class="text-[13px] font-normal text-muted">saham biasa</span></div>
            <div class="text-[11px] text-muted">yang butuh naik {{ kv.grup_perlu }}% juga sampai dalam 1 tahun (Undervalue sejenis {{ p(banding?.u) }})</div>
          </div>
          <div class="rounded-xl bg-surface-2 px-4 py-3">
            <div class="text-xs text-muted">Kalau sampai</div>
            <div class="mt-0.5 text-[20px] leading-7 font-medium">{{ bulan(kv.mos?.median_hari) }}</div>
            <div class="text-[11px] text-muted">median {{ Math.round(kv.mos?.median_hari || 0) }} hari bursa · sempat turun {{ persen(kv.mos?.turun_dulu, 0) }} dulu</div>
          </div>
          <div class="rounded-xl bg-surface-2 px-4 py-3">
            <div class="text-xs text-muted">Kalau tidak sampai</div>
            <div class="mt-0.5 text-[20px] leading-7 font-medium text-turun">{{ persen(kv.semua?.belum_turun, 0) }} <span class="text-[13px] font-normal text-muted">terdalam</span></div>
            <div class="text-[11px] text-muted">kenaikan tertinggi hanya {{ persen(kv.semua?.belum_naik_maks, 0) }} (median)</div>
          </div>
        </div>

        <div class="mt-4">
          <div class="mb-1.5 text-xs text-muted">Peluang sudah sampai setelah... (MoS {{ kv.grup_mos }}% vs semua saham biasa dengan kenaikan sama)</div>
          <div class="space-y-1.5">
            <div v-for="[h, l] in HORIZON" :key="h" class="grid grid-cols-[52px_1fr_88px] items-center gap-3 text-xs">
              <span class="text-muted">{{ l }}</span>
              <div class="relative h-2.5 rounded-full bg-surface-3">
                <div class="absolute inset-y-0 left-0 rounded-full bg-s1" :style="{ width: `${kv.mos?.peluang?.[h] || 0}%` }"></div>
                <div class="absolute -top-0.5 -bottom-0.5 w-0.5 rounded bg-s3" :style="{ left: `${kv.perlu_data?.wajar?.peluang?.[h] || 0}%` }" :title="`saham biasa ${p(kv.perlu_data?.wajar?.peluang?.[h])}`"></div>
              </div>
              <span class="tabular-nums"><b class="font-medium">{{ p(kv.mos?.peluang?.[h]) }}</b> <span class="text-muted">vs {{ p(kv.perlu_data?.wajar?.peluang?.[h]) }}</span></span>
            </div>
          </div>
          <div class="mt-1.5 flex flex-wrap gap-3 text-[11px] text-muted">
            <span class="inline-flex items-center gap-1.5"><span class="h-2 w-4 rounded-full bg-s1"></span>Undervalue MoS {{ kv.grup_mos }}%</span>
            <span class="inline-flex items-center gap-1.5"><span class="h-3 w-0.5 rounded bg-s3"></span>saham biasa, kenaikan sama</span>
          </div>
        </div>

        <ul class="m-0 mt-4 list-disc space-y-1 pl-5 text-[13px] text-ink-2">
          <li v-if="banding">Dibanding saham biasa: {{ banding.teks }}.</li>
          <li v-if="kv.ihsg_naik !== null">Kondisi pasar sekarang: IHSG {{ kv.ihsg_naik ? "di atas" : "di bawah" }} rata-rata 200 hari. Secara historis, Undervalue yang muncul saat kondisi ini sampai {{ p(kv.ihsg_data?.peluang?.["252"]) }} dalam 1 tahun (saat sebaliknya {{ p(kv.ihsg_lain?.peluang?.["252"]) }}).</li>
          <li>Per periode: kasus 2021–2023 {{ p(kv.periode_kejadian?.["kejadian 2021-2023"]?.undervalue?.peluang?.["252"]) }} (saham biasa {{ p(kv.periode_kejadian?.["kejadian 2021-2023"]?.wajar?.peluang?.["252"]) }}), kasus 2024–2026 {{ p(kv.periode_kejadian?.["kejadian 2024-2026"]?.undervalue?.peluang?.["252"]) }} ({{ p(kv.periode_kejadian?.["kejadian 2024-2026"]?.wajar?.peluang?.["252"]) }}). Hasil berbeda antar periode, belum tentu berulang.</li>
          <li>Membeli otomatis semua saham Undervalue tiap bulan (uji H16, 2021–2023) kalah dari rata-rata pasar setelah biaya. Gunakan ini untuk menimbang, bukan sebagai sinyal beli.</li>
        </ul>
      </div>
      <p v-else-if="v.vonis.kode === 'agak'" class="m-0 rounded-2xl border border-garis px-5 py-3 text-xs text-muted">
        Margin of safety di bawah 20% belum termasuk analisis "seberapa sering sampai nilai wajar". Secara umum, diskon kecil lebih sering tercapai, tapi potensi naiknya juga kecil.
      </p>

      <div class="grid gap-5 lg:grid-cols-2">
        <div class="space-y-4">
          <div>
            <div class="mb-2 flex items-center gap-2 text-[13px] font-medium"><Lightbulb class="h-4 w-4 text-naik" />Kenapa nilainya segini</div>
            <ul class="m-0 list-disc space-y-1.5 pl-5 text-[13px] text-ink-2"><li v-for="a in v.alasan" :key="a">{{ a }}</li></ul>
          </div>
          <div v-if="v.risiko.length">
            <div class="mb-2 flex items-center gap-2 text-[13px] font-medium"><TriangleAlert class="h-4 w-4 text-kuning" />Perlu diwaspadai</div>
            <ul class="m-0 list-disc space-y-1.5 pl-5 text-[13px] text-ink-2"><li v-for="a in v.risiko" :key="a">{{ a }}</li></ul>
          </div>
        </div>
        <div class="rounded-2xl bg-surface-2 px-5 py-4">
          <div class="mb-3 flex items-center gap-2 text-[13px] font-medium"><Map class="h-4 w-4 text-aksen" />Rencana (ilustrasi)</div>
          <template v-if="v.rencana">
            <div class="mb-3 grid grid-cols-3 gap-2 text-center">
              <div class="rounded-xl bg-surface px-2 py-2"><div class="text-[11px] text-muted">Area beli</div><div class="font-medium tabular-nums">≤ {{ rp(v.rencana.area_beli) }}</div></div>
              <div class="rounded-xl bg-surface px-2 py-2"><div class="text-[11px] text-muted">Target</div><div class="font-medium tabular-nums">{{ rp(v.rencana.target) }}</div></div>
              <div class="rounded-xl bg-surface px-2 py-2"><div class="text-[11px] text-muted">Potensi</div><div class="font-medium tabular-nums" :class="v.rencana.potensi >= 0 ? 'text-naik' : 'text-turun'">{{ persen(v.rencana.potensi, 1) }}</div></div>
            </div>
            <ol class="m-0 list-decimal space-y-1.5 pl-5 text-[13px] text-ink-2"><li v-for="l in v.rencana.langkah" :key="l">{{ l }}</li></ol>
          </template>
          <p v-else class="m-0 text-[13px] text-muted">Tidak ada rencana nilai: perusahaan rugi atau nilai wajar tidak bisa dihitung.</p>
        </div>
      </div>

      <div>
        <div class="mb-2 text-[13px] font-medium">Metode nilai wajar</div>
        <div class="-mx-6 overflow-x-auto">
          <table class="tabel min-w-[720px]">
            <thead><tr><th>Metode</th><th>Perhitungan</th><th class="!text-right">Nilai wajar</th><th class="!text-right">vs harga</th><th>Dipakai</th></tr></thead>
            <tbody>
              <tr v-for="m in v.metode" :key="m.nama" class="align-top" :class="m.dipakai ? '' : 'opacity-60'">
                <td class="!h-auto py-3 font-medium">{{ m.nama }}</td>
                <td class="!h-auto !whitespace-normal py-3 text-xs text-ink-2">{{ m.rumus }}<div v-if="m.catatan" class="mt-0.5 text-muted">{{ m.catatan }}</div></td>
                <td class="!h-auto py-3 text-right tabular-nums">{{ rp(m.nilai) }}</td>
                <td class="!h-auto py-3 text-right" :class="m.mos >= 0 ? 'text-naik' : 'text-turun'">{{ persen(m.mos, 0) }}</td>
                <td class="!h-auto py-3"><component :is="m.dipakai ? Check : Minus" class="h-4 w-4" :class="m.dipakai ? 'text-naik' : 'text-muted'" /></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <div class="mb-2 text-[13px] font-medium">Rasio</div>
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
          <div v-for="r in rasio" :key="r.l" class="rounded-2xl bg-surface-2 px-4 py-3">
            <div class="text-xs text-muted">{{ r.l }}</div>
            <div class="mt-0.5 font-medium tabular-nums">{{ r.n }}</div>
            <div class="text-[11px] leading-snug text-muted">{{ r.k }}</div>
          </div>
        </div>
      </div>

      <div class="grid gap-5 lg:grid-cols-[1fr_1.2fr]">
        <div>
          <div class="mb-2 text-[13px] font-medium">Cek kualitas (anti value trap)</div>
          <div class="overflow-hidden rounded-2xl border border-garis">
            <div v-for="k in v.kualitas" :key="k.label" class="flex items-start gap-3 border-t border-garis px-4 py-2.5 first:border-t-0">
              <component :is="k.ok === null ? Minus : k.ok ? Check : X" class="mt-0.5 h-4 w-4 shrink-0" :class="k.ok === null ? 'text-muted' : k.ok ? 'text-naik' : 'text-turun'" />
              <div class="min-w-0 flex-1">
                <div class="text-[13px] font-medium">{{ k.label }}</div>
                <div class="text-xs text-muted">{{ k.nilai }} · syarat {{ k.syarat }}{{ k.ok === null ? " · tidak berlaku / data kurang" : "" }}</div>
              </div>
            </div>
          </div>
        </div>
        <div v-if="grafik">
          <div class="mb-2 flex items-center justify-between gap-2">
            <div class="text-[13px] font-medium">Band {{ jenis.toUpperCase() }} 5 tahun</div>
            <Segmen v-model="jenis" :pilihan="[['pbv', 'PBV'], ['per', 'PER']]" kecil />
          </div>
          <div class="mb-2 flex flex-wrap gap-2 text-xs text-ink-2">
            <span class="inline-flex items-center gap-2 rounded-full bg-surface-2 px-3 py-1"><span class="h-0.5 w-4 rounded bg-s1"></span>{{ jenis.toUpperCase() }}</span>
            <span class="inline-flex items-center gap-2 rounded-full bg-surface-2 px-3 py-1"><span class="w-4 border-t-2 border-dashed border-s3"></span>Rata-rata</span>
            <span class="inline-flex items-center gap-2 rounded-full bg-surface-2 px-3 py-1"><span class="h-2.5 w-4 rounded-sm bg-s1/20"></span>±1 SD</span>
          </div>
          <div class="h-[220px]"><Line :data="grafik" :options="opsi" /></div>
          <p v-if="v.band[jenis]" class="m-0 mt-1 text-xs text-muted">Sekarang lebih murah dari {{ 100 - v.band[jenis].persentil }}% bulan dalam 5 tahun terakhir (z = {{ v.band[jenis].z?.toLocaleString("id-ID") }}).</p>
        </div>
      </div>

      <p class="m-0 text-xs leading-relaxed text-muted">
        Belum tersedia: {{ v.tidak_tersedia.join(", ") }}. Metode valuasi ini untuk riset, <b class="font-medium">bukan sinyal</b>: uji H16 (2021-2023) menunjukkan membeli semua saham "Undervalue"
        atau "Layak dipertimbangkan" tiap bulan tidak mengalahkan rata-rata saham syariah setelah biaya, dan uji H14 menunjukkan filter fundamental tidak memperbaiki Follow Tren. Cek laporan keuangan dan berita sebelum memutuskan: murah karena sementara (sentimen, siklus) atau struktural (bisnis rusak). Bukan nasihat keuangan.
      </p>
    </div>
  </Panel>
</template>

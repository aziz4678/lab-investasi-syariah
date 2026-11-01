<script setup>
import { ref, computed } from "vue";
import { ShieldCheck, Droplets, Coins, Activity, Ban, TrendingUp } from "lucide-vue-next";
import Panel from "@/components/common/Panel.vue";
import Stats from "@/components/common/Stats.vue";
import Segmen from "@/components/common/Segmen.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import GrafikSiklus from "@/components/tren/GrafikSiklus.vue";
import SebaranTrade from "@/components/tren/SebaranTrade.vue";
import BatangSeri from "@/components/charts/BatangSeri.vue";

const props = defineProps({ trade: Array, r: Object, contoh: Object, periode: String });
const pilih = ref("tp");

const angka = (v, d = 1) => (v == null || !isFinite(v) ? "–" : v.toFixed(d).replace(".", ","));
const pct = (v, d = 1) => (v == null || !isFinite(v) ? "–" : `${v > 0 ? "+" : ""}${angka(v, d)}%`);
const rp = (v) => (v == null ? "–" : Math.round(v).toLocaleString("id-ID"));
const median = (a) => {
  if (!a.length) return null;
  const s = [...a].sort((x, y) => x - y);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};
const rata = (a) => (a.length ? a.reduce((x, y) => x + y, 0) / a.length : null);
const BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
const tgl = (s) => (s ? `${+s.slice(8, 10)} ${BULAN[+s.slice(5, 7) - 1]} ${s.slice(0, 4)}` : "–");

const semua = computed(() => (props.trade || []).filter((t) => t.status === "selesai").map((t) => ({ t: t.ticker, tgl: String(t.tgl_sinyal).slice(0, 10), h: t.hari, n: t.net })));
const tp = computed(() => semua.value.filter((t) => t.n > 0));
const cl = computed(() => semua.value.filter((t) => t.n <= 0));

const c = computed(() => props.contoh?.[pilih.value]);
const langkahContoh = computed(() => {
  const x = c.value;
  if (!x) return [];
  const n = x.nilai;
  const t = (k) => tgl(x.tgl[x.titik[k]]);
  const untung = pilih.value === "tp";
  return [
    { no: 1, judul: "Sinyal", tgl: t("sinyal"), isi: `Close ${rp(n.close_sinyal)} ≥ tertinggi 250 hari sebelumnya ${rp(n.maks250_sinyal)}. Rekor setahun.` },
    { no: 2, judul: "Beli", tgl: t("beli"), isi: `Dibeli di open ${rp(n.harga_beli)}. Batas jual awal ${rp(n.stop_awal)} (−${angka(n.stop_awal_pct)}%, 3 × ATR ${rp(n.atr_sinyal)}).` },
    { no: 3, judul: "Hold", tgl: `${x.hari} hari`, isi: untung ? `Harga naik sampai ${rp(n.puncak)}. Batas jual ikut naik ke ${rp(n.stop_akhir)}, sudah di atas harga beli.` : `Sempat naik ke ${rp(n.puncak)}, batas naik ke ${rp(n.stop_akhir)}, tapi masih di bawah harga beli.` },
    { no: 4, judul: untung ? "Jual = take profit" : "Jual = cut loss", tgl: t("jual"), isi: `Close ${rp(n.close_jual)} < batas ${rp(n.stop_akhir)} → dijual open besok ${rp(n.harga_jual)}. Hasil bersih ${pct(x.net)}.`, nada: x.net > 0 ? "text-naik" : "text-turun" },
  ];
});

const SARINGAN = [
  { ikon: ShieldCheck, judul: "Syariah", isi: "Masuk DES OJK yang berlaku pada hari itu" },
  { ikon: Droplets, judul: "Likuid", isi: "Transaksi rata-rata 20 hari ≥ Rp5 miliar" },
  { ikon: Coins, judul: "Harga minimum", isi: "Harga penutupan ≥ Rp50" },
  { ikon: Activity, judul: "Gerak wajar", isi: "ATR 1,5%-5% dari harga per hari" },
  { ikon: Ban, judul: "Aktif", isi: "Tidak ada hari tanpa transaksi 5 hari terakhir" },
  { ikon: TrendingUp, judul: "Rekor setahun", isi: "Close ≥ close tertinggi 250 hari bursa sebelumnya" },
];
const dibeliPct = computed(() => (props.r?.sinyal ? (props.r.trade / props.r.sinyal) * 100 : 0));

const TEPI_HARI = [[1, 5], [6, 10], [11, 20], [21, 40], [41, 60], [61, 120], [121, 99999]];
const LABEL_HARI = ["1-5", "6-10", "11-20", "21-40", "41-60", "61-120", "> 120"];
const hitungHari = (a) => TEPI_HARI.map(([x, y]) => a.filter((t) => t.h >= x && t.h <= y).length);

const top10 = computed(() => [...tp.value].sort((a, b) => b.n - a.n).slice(0, 10));
const sumbangTop = computed(() => {
  const jumlah = tp.value.reduce((a, t) => a + t.n, 0);
  return jumlah ? (top10.value.reduce((a, t) => a + t.n, 0) / jumlah) * 100 : null;
});
const rataTanpaTop = computed(() => {
  const ids = new Set(top10.value);
  return rata(semua.value.filter((t) => !ids.has(t)).map((t) => t.n));
});

const TEPI_CL = [[-999, -25], [-25, -20], [-20, -15], [-15, -10], [-10, -5], [-5, 0.0001]];
const LABEL_CL = ["< −25%", "−25 s/d −20", "−20 s/d −15", "−15 s/d −10", "−10 s/d −5", "−5 s/d 0"];
const hitungCl = computed(() => TEPI_CL.map(([x, y]) => cl.value.filter((t) => t.n > x && t.n <= y).length));

const kartuTp = computed(() => [
  { label: "Jumlah TP", nilai: `${tp.value.length}`, ket: `dari ${semua.value.length} trade` },
  { label: "Rata-rata", nilai: pct(rata(tp.value.map((t) => t.n))), ket: `median ${pct(median(tp.value.map((t) => t.n)))}` },
  { label: "Terbesar", nilai: pct(top10.value[0]?.n, 0), ket: top10.value[0] ? `${top10.value[0].t}, ${top10.value[0].h} hari` : "" },
]);
const kartuCl = computed(() => [
  { label: "Jumlah CL", nilai: `${cl.value.length}`, ket: `dari ${semua.value.length} trade` },
  { label: "Rata-rata", nilai: pct(rata(cl.value.map((t) => t.n))), ket: `median ${pct(median(cl.value.map((t) => t.n)))}` },
  { label: "Terdalam", nilai: pct(Math.min(...cl.value.map((t) => t.n)), 0), ket: "karena gap turun / ARB" },
]);

const ATURAN_BELI = [
  "Dicek tiap sore setelah harga penutupan final (≥ 17.00), dibeli besok pagi di harga pembukaan.",
  "±10% dari total modal per saham, maksimal 10 saham. Kalau sinyal lebih banyak dari slot kosong, dipilih acak.",
  "Batal kalau besok pagi terkunci ARA atau 1 lot lebih mahal dari jatah.",
];
const ATURAN_HOLD = [
  "Tiap sore batas jual dihitung ulang: close tertinggi sejak beli − 3 × ATR14. Hanya boleh naik.",
  "Selama close ≥ batas jual, saham tetap dipegang. Tidak ada batas atas dan tidak ada jual sebagian.",
];
const ATURAN_TP = [
  "Tidak ada target angka. TP terjadi saat batas jual yang sudah di atas harga beli tersentuh.",
  "Batas melewati harga beli setelah harga naik ±3×ATR (biasanya ±10%). Sejak itu trade praktis tidak bisa rugi, kecuali gap turun.",
  "Tidak pernah jual tepat di puncak: sekitar 3×ATR dari puncak 'dikembalikan'. Imbalannya, tren besar diikuti sampai patah.",
];
const ATURAN_CL = [
  "Batas jual awal = harga beli − 3 × ATR14 hari sinyal (rata-rata ±10% di bawah harga beli).",
  "Close < batas sebelum harga sempat naik cukup → dijual open besok dengan rugi.",
  "Kalau pagi itu harga dibuka jauh di bawah batas (gap turun) atau terkunci ARB, rugi bisa lebih dalam dari batas.",
];
</script>

<template>
  <div class="space-y-5">
    <Panel judul="Siklus satu trade" :ket="`Contoh trade asli dari backtest ${periode}, dihitung ulang dengan aturan yang sama persis`">
      <template #aksi><Segmen v-model="pilih" kecil :pilihan="[['tp', 'Contoh take profit'], ['cl', 'Contoh cut loss']]" /></template>
      <Kerangka v-if="contoh === undefined" jenis="grafik" />
      <p v-else-if="!c" class="m-0 text-ink-2">Contoh belum tersedia untuk versi ini.</p>
      <template v-else>
        <div class="mb-3 flex flex-wrap items-baseline gap-x-3">
          <span class="text-[15px] font-medium">{{ c.ticker }}</span><span class="text-xs text-muted">{{ tgl(c.tgl[c.titik.sinyal]) }} → {{ tgl(c.tgl[c.titik.jual]) }}</span>
          <span class="chip" :class="c.net > 0 ? 'bg-naik-bg text-naik' : 'bg-turun-bg text-turun'">{{ pct(c.net) }} bersih</span>
        </div>
        <GrafikSiklus :c="c" :jenis="pilih" />
        <ol class="m-0 mt-4 grid list-none gap-2.5 p-0 sm:grid-cols-2 xl:grid-cols-4">
          <li v-for="l in langkahContoh" :key="l.no" class="rounded-2xl bg-surface-2 px-4 py-3">
            <div class="flex items-center gap-2">
              <span class="grid h-6 w-6 place-items-center rounded-full bg-aksen-lembut text-xs font-medium text-aksen">{{ l.no }}</span>
              <span class="text-[13px] font-medium">{{ l.judul }}</span><span class="ml-auto text-[11px] text-muted">{{ l.tgl }}</span>
            </div>
            <p class="m-0 mt-1.5 text-xs leading-relaxed" :class="l.nada || 'text-ink-2'">{{ l.isi }}</p>
          </li>
        </ol>
      </template>
    </Panel>

    <section class="panel">
      <header class="flex items-center gap-3 px-6 pt-5">
        <span class="grid h-8 w-8 place-items-center rounded-full bg-aksen text-[13px] font-medium text-aksen-teks">1</span>
        <div><h2 class="m-0 text-[17px] font-medium">Kapan beli</h2><p class="m-0 text-xs text-muted">Saham harus lolos 6 saringan di hari sinyal</p></div>
      </header>
      <div class="grid gap-6 px-6 pt-4 pb-6 lg:grid-cols-[1.3fr_1fr]">
        <div class="grid gap-2 sm:grid-cols-2">
          <div v-for="(f, i) in SARINGAN" :key="f.judul" class="flex gap-3 rounded-2xl px-4 py-3" :class="i === SARINGAN.length - 1 ? 'bg-aksen-lembut' : 'bg-surface-2'">
            <component :is="f.ikon" class="mt-0.5 h-4 w-4 shrink-0" :class="i === SARINGAN.length - 1 ? 'text-aksen' : 'text-muted'" />
            <div><div class="text-[13px] font-medium">{{ f.judul }}</div><div class="text-xs leading-relaxed text-ink-2">{{ f.isi }}</div></div>
          </div>
        </div>
        <div>
          <ul class="m-0 list-disc space-y-1.5 pl-5 text-[13px] leading-relaxed text-ink-2">
            <li v-for="x in ATURAN_BELI" :key="x">{{ x }}</li>
          </ul>
          <div v-if="r?.sinyal" class="mt-4 rounded-2xl border border-garis px-4 py-3">
            <div class="flex items-baseline justify-between text-xs"><span class="text-muted">Sinyal {{ periode }}</span><span class="font-medium tabular-nums">{{ r.sinyal }} sinyal</span></div>
            <div class="mt-2 flex h-3 overflow-hidden rounded-full bg-surface-2"><div class="h-full rounded-full bg-aksen" :style="{ width: `${dibeliPct}%` }" /></div>
            <div class="mt-2 flex justify-between gap-3 text-xs text-ink-2"><span><b class="font-medium text-ink">{{ r.trade }}</b> dibeli ({{ angka(dibeliPct, 0) }}%)</span><span class="text-right">{{ r.sinyal - r.trade }} dilewati (slot penuh atau batal)</span></div>
          </div>
        </div>
      </div>
    </section>

    <section class="panel">
      <header class="flex items-center gap-3 px-6 pt-5">
        <span class="grid h-8 w-8 place-items-center rounded-full bg-aksen text-[13px] font-medium text-aksen-teks">2</span>
        <div><h2 class="m-0 text-[17px] font-medium">Kapan hold</h2><p class="m-0 text-xs text-muted">Pegang selama harga penutupan masih di atas batas jual</p></div>
      </header>
      <div class="grid gap-6 px-6 pt-4 pb-6 lg:grid-cols-[1fr_1.3fr]">
        <ul class="m-0 list-disc space-y-1.5 pl-5 text-[13px] leading-relaxed text-ink-2">
          <li v-for="x in ATURAN_HOLD" :key="x">{{ x }}</li>
        </ul>
        <div>
          <div class="text-[13px] font-medium">Berapa lama trade dipegang</div>
          <p class="m-0 mt-0.5 text-xs text-ink-2">Trade rugi biasanya selesai cepat (median <b class="font-medium text-turun">{{ median(cl.map((t) => t.h)) }} hari</b>), trade untung dibiarkan jalan (median <b class="font-medium text-naik">{{ median(tp.map((t) => t.h)) }} hari</b>).</p>
          <BatangSeri class="mt-3" legenda tumpuk :label="LABEL_HARI" satuan=" trade" :tinggi="220"
            :seri="[{ nama: 'Cut loss', data: hitungHari(cl), warna: '--turun' }, { nama: 'Take profit', data: hitungHari(tp), warna: '--naik' }]" />
          <p class="m-0 mt-1 text-center text-[11px] text-muted">Lama dipegang (hari bursa)</p>
        </div>
      </div>
    </section>

    <section class="panel">
      <header class="flex items-center gap-3 px-6 pt-5">
        <span class="grid h-8 w-8 place-items-center rounded-full bg-aksen text-[13px] font-medium text-aksen-teks">3</span>
        <div class="flex-1"><h2 class="m-0 flex items-center gap-2 text-[17px] font-medium">Kapan take profit <span class="chip bg-naik-bg text-naik">TP</span></h2><p class="m-0 text-xs text-muted">Tanpa target angka: dijual saat tren patah, setelah batas jual naik melewati harga beli</p></div>
      </header>
      <div class="grid gap-6 px-6 pt-4 pb-6 lg:grid-cols-[1fr_1.3fr]">
        <div>
          <ul class="m-0 list-disc space-y-1.5 pl-5 text-[13px] leading-relaxed text-ink-2">
            <li v-for="x in ATURAN_TP" :key="x">{{ x }}</li>
          </ul>
          <Stats class="mt-4" polos kolom="grid-cols-3" :items="kartuTp" />
        </div>
        <div>
          <div class="text-[13px] font-medium">10 take profit terbesar</div>
          <p class="m-0 mt-0.5 text-xs text-ink-2">10 trade ini = <b class="font-medium text-ink">{{ angka(sumbangTop, 0) }}%</b> dari jumlah untung semua TP. Tanpa mereka, rata-rata per trade turun dari {{ pct(rata(semua.map((t) => t.n))) }} jadi <b class="font-medium text-ink">{{ pct(rataTanpaTop) }}</b>. Itu sebabnya tidak ada target untung: target tetap memotong trade seperti ini.</p>
          <BatangSeri class="mt-3" mendatar :label="top10.map((t) => `${t.t} · ${t.h} hr`)" :format="(v) => pct(v, 0)" :tinggi="260"
            :seri="[{ nama: 'Hasil bersih', data: top10.map((t) => t.n), warna: '--naik' }]" />
        </div>
      </div>
    </section>

    <section class="panel">
      <header class="flex items-center gap-3 px-6 pt-5">
        <span class="grid h-8 w-8 place-items-center rounded-full bg-aksen text-[13px] font-medium text-aksen-teks">4</span>
        <div class="flex-1"><h2 class="m-0 flex items-center gap-2 text-[17px] font-medium">Kapan cut loss <span class="chip bg-turun-bg text-turun">CL</span></h2><p class="m-0 text-xs text-muted">Dijual rugi kalau harga jatuh di bawah batas jual sebelum sempat naik cukup</p></div>
      </header>
      <div class="grid gap-6 px-6 pt-4 pb-6 lg:grid-cols-[1fr_1.3fr]">
        <div>
          <ul class="m-0 list-disc space-y-1.5 pl-5 text-[13px] leading-relaxed text-ink-2">
            <li v-for="x in ATURAN_CL" :key="x">{{ x }}</li>
          </ul>
          <Stats class="mt-4" polos kolom="grid-cols-3" :items="kartuCl" />
        </div>
        <div>
          <div class="text-[13px] font-medium">Seberapa dalam rugi saat cut loss</div>
          <p class="m-0 mt-0.5 text-xs text-ink-2"><b class="font-medium text-ink">{{ cl.filter((t) => t.n > -15).length }} dari {{ cl.length }}</b> CL rugi kurang dari 15%, dan {{ cl.filter((t) => t.h <= 20).length }} selesai dalam 20 hari bursa. Hanya {{ cl.filter((t) => t.n <= -20).length }} yang rugi 20% atau lebih (gap turun / ARB).</p>
          <BatangSeri class="mt-3" :label="LABEL_CL" satuan=" trade" :tinggi="220" :seri="[{ nama: 'Cut loss', data: hitungCl, warna: '--turun' }]" />
          <p class="m-0 mt-1 text-center text-[11px] text-muted">Hasil bersih per trade CL</p>
        </div>
      </div>
    </section>

    <Panel judul="Gambaran besar: semua trade" :ket="`Tiap titik = 1 trade backtest ${periode}. Arahkan kursor untuk melihat sahamnya`">
      <SebaranTrade :trade="semua" />
      <div class="mt-3 grid gap-2.5 md:grid-cols-3">
        <div class="rounded-2xl bg-surface-2 px-4 py-3 text-xs leading-relaxed text-ink-2"><b class="font-medium text-ink">Kiri bawah padat:</b> banyak CL kecil yang selesai cepat. Ini ongkos rutin strategi.</div>
        <div class="rounded-2xl bg-surface-2 px-4 py-3 text-xs leading-relaxed text-ink-2"><b class="font-medium text-ink">Kanan atas jarang:</b> sedikit TP yang dipegang lama dan naik besar. Ini sumber hampir semua untung.</div>
        <div class="rounded-2xl bg-surface-2 px-4 py-3 text-xs leading-relaxed text-ink-2"><b class="font-medium text-ink">Kanan bawah hampir kosong:</b> trade yang dipegang lama hampir selalu untung, karena batas jual sudah naik melewati harga beli.</div>
      </div>
    </Panel>
  </div>
</template>

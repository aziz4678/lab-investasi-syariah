<script setup>
import { ref, computed, watch } from "vue";
import { Line } from "vue-chartjs";
import { TrendingUp, ListOrdered, Scale, Layers } from "lucide-vue-next";
import { pakaiTema } from "@/composables/tema";
import { opsiDasar, warna } from "@/utils/chart";
import { persen, tanggal, kelasPersen } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import KodeSaham from "@/components/common/KodeSaham.vue";
import BatangSeri from "@/components/charts/BatangSeri.vue";

const props = defineProps({ r: Object, periode: String });
const tema = pakaiTema();
const BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];
const namaBulan = (b) => (b ? `${BULAN[Number(b.slice(5, 7)) - 1]} ${b.slice(0, 4)}` : "");
const angka = (v, d = 1) => (v == null ? "–" : persen(v, d));
const koma = (v, d = 2) => (v == null ? "–" : v.toFixed(d).replace(".", ","));

const ft = computed(() => props.r?.bagian?.h11a || {});
const rs = computed(() => props.r?.bagian?.h22 || {});
const mc = computed(() => props.r?.monte_carlo || {});
const blendCagr = computed(() => mc.value.cagr?.median ?? props.r?.cagr);
const blendDd = computed(() => mc.value.dd?.median ?? props.r?.dd_maks);

const KARTU = computed(() => [
  { judul: "Follow Tren", sub: "50% modal · H11a", ikon: TrendingUp, warna: "--series-2", cagr: ft.value.cagr, dd: ft.value.dd,
    isi: [["Trade", ft.value.trade], ["Trade untung", ft.value.win_rate != null ? persen(ft.value.win_rate, 0, false) : "–"],
          ["Rata-rata untung / rugi", `${angka(ft.value.rata_menang, 0)} / ${angka(ft.value.rata_kalah, 0)}`], ["Lama dipegang", `±${Math.round(ft.value.hari || 0)} hari bursa`]],
    cara: "Beli saham yang menembus rekor tertinggi setahun, jual saat turun 3×ATR dari puncak. Sering rugi kecil, sesekali untung besar." },
  { judul: "RS 12-1", sub: "50% modal · H22", ikon: ListOrdered, warna: "--series-4", cagr: rs.value.cagr, dd: rs.value.dd,
    isi: [["Saham dipegang (posisi)", rs.value.trade], ["Posisi untung", rs.value.win_rate != null ? persen(rs.value.win_rate, 0, false) : "–"],
          ["Rata-rata untung / rugi", `${angka(rs.value.rata_menang, 0)} / ${angka(rs.value.rata_kalah, 0)}`], ["Lama dipegang", `±${Math.round(rs.value.hari || 0)} hari bursa`]],
    cara: "Tiap akhir bulan pegang ±20% saham syariah yang paling naik dalam 12 bulan (tanpa bulan terakhir). Tanpa stop; keluar kalau peringkatnya jatuh." },
]);

const kalimat = computed(() => {
  const r = props.r;
  if (!r) return "";
  const lebih = blendCagr.value > r.cagr_beli_tahan ? "lebih tinggi" : "lebih rendah";
  const hal = Math.abs((r.bagian?.h11a?.dd ?? 0)) > Math.abs(blendDd.value) || Math.abs((r.bagian?.h22?.dd ?? 0)) > Math.abs(blendDd.value) ? "lebih dangkal dari bagian yang paling dalam turunnya" : "tidak lebih dangkal";
  return `Di ${props.periode}, Follow Tren sendirian menghasilkan ${angka(ft.value.cagr)} per tahun dan RS 12-1 sendirian ${angka(rs.value.cagr)} per tahun. Digabung 50/50, hasilnya ${angka(blendCagr.value)} per tahun (${lebih} dari membeli semua saham syariah sama banyak, ${angka(r.cagr_beli_tahan)}), dengan penurunan terdalam ${angka(blendDd.value)}, ${hal}. Kedua bagian tidak selalu bergerak bersama (korelasi ${koma(r.korelasi)}), jadi saat satu bagian lesu bagian lain kadang menahan.`;
});

const pt = computed(() => props.r?.per_tahun_bagian || []);
const BATANG = [
  { kunci: "h29", nama: "Momentum Blend", warna: "--series-1" },
  { kunci: "h11a", nama: "Follow Tren saja", warna: "--series-2" },
  { kunci: "h22", nama: "RS 12-1 saja", warna: "--series-4" },
  { kunci: "beli_tahan", nama: "Bobot sama syariah", warna: "--series-3" },
];
const seriTahun = computed(() => BATANG.map((s) => ({ nama: s.nama, warna: s.warna, data: pt.value.map((x) => x[s.kunci]) })));
const KOLOM_TAHUN = [["h29", "Momentum Blend"], ["h11a", "Follow Tren"], ["h22", "RS 12-1"], ["beli_tahan", "Bobot sama"], ["jii", "JII"], ["ihsg", "IHSG"]];

const temuan = computed(() => {
  const t = pt.value.filter((x) => x.h29 != null);
  if (!t.length) return [];
  const menang = t.filter((x) => x.beli_tahan != null && x.h29 > x.beli_tahan).length;
  const beda = t.filter((x) => x.h11a != null && x.h22 != null && Math.sign(x.h11a) !== Math.sign(x.h22));
  const terburuk = t.reduce((a, x) => (x.h29 < a.h29 ? x : a));
  const terbaik = t.reduce((a, x) => (x.h29 > a.h29 ? x : a));
  const out = [`Momentum Blend lebih baik dari bobot sama syariah di ${menang} dari ${t.length} tahun.`];
  if (beda.length) out.push(`Tahun saat satu bagian rugi tapi bagian lain untung: ${beda.slice(0, 5).map((x) => `${x.tahun} (Follow Tren ${angka(x.h11a, 0)}, RS 12-1 ${angka(x.h22, 0)})`).join("; ")}. Di tahun seperti ini gabungan menahan kerugian.`);
  out.push(`Tahun terbaik ${terbaik.tahun} (${angka(terbaik.h29)}), tahun terburuk ${terburuk.tahun} (${angka(terburuk.h29)}). Tahun rugi tetap terjadi: gabungan tidak menghilangkan risiko.`);
  return out;
});

const daftarReb = computed(() => [...(props.r?.rebalance || [])].reverse());
const pilihReb = ref(0);
watch(() => props.r?.versi, () => (pilihReb.value = 0));
const reb = computed(() => daftarReb.value[pilihReb.value] || null);
const barisReb = computed(() => {
  const x = reb.value;
  if (!x) return [];
  const beli = new Set(x.beli), tetap = new Set(x.tetap);
  return x.peringkat.map(([t, m], i) => ({ no: i + 1, t, m, status: beli.has(t) ? "beli" : tetap.has(t) ? "tetap" : i < x.n ? "penuh" : "lewat", dalamN: i < x.n }));
});
const STATUS = { beli: ["Dibeli baru", "bg-aksen-lembut text-aksen"], tetap: ["Tetap dipegang", "bg-surface-2 text-ink-2"], penuh: ["Tidak dibeli · slot penuh", "bg-kuning-bg text-ink-2"], lewat: ["–", "text-muted"] };
const adaPenuh = computed(() => barisReb.value.some((b) => b.status === "penuh"));
const tampilSemua = ref(false);
const barisTampil = computed(() => (tampilSemua.value ? barisReb.value : barisReb.value.slice(0, Math.max(reb.value?.n || 10, 10))));

const porsi = computed(() => props.r?.porsi || []);
const dataPorsi = computed(() => {
  tema.value;
  return {
    labels: porsi.value.map((x) => x.bulan),
    datasets: [
      { label: "Porsi Follow Tren sebelum dikembalikan", data: porsi.value.map((x) => x.porsi_ft), borderColor: warna("--series-2"), backgroundColor: "transparent",
        borderWidth: 2, pointRadius: 0, tension: 0.3 },
      { label: "Target 50%", data: porsi.value.map(() => 50), borderColor: warna("--series-3"), borderDash: [5, 4], borderWidth: 1.5, pointRadius: 0 },
    ],
  };
});
const opsiPorsi = computed(() => {
  tema.value;
  const o = opsiDasar();
  o.scales.y.ticks.callback = (v) => `${v}%`;
  o.plugins.tooltip.callbacks = { label: (c) => ` ${c.dataset.label}: ${c.parsed.y.toFixed(1).replace(".", ",")}%` };
  return o;
});
const terjauh = computed(() => porsi.value.reduce((a, x) => (!a || Math.abs(x.porsi_ft - 50) > Math.abs(a.porsi_ft - 50) ? x : a), null));
</script>

<template>
  <div class="space-y-5">
    <Panel judul="Dua bagian, satu modal" ket="Tiap bagian dihitung seolah memakai seluruh modal, lalu hasilnya digabung 50/50 · angka per tahun = median simulasi Monte Carlo">
      <div class="grid gap-4 lg:grid-cols-3">
        <div v-for="k in KARTU" :key="k.judul" class="rounded-2xl bg-surface-2 px-5 py-4">
          <div class="flex items-center gap-2"><component :is="k.ikon" class="h-4 w-4" :style="{ color: `var(${k.warna})` }" /><span class="font-medium">{{ k.judul }}</span><span class="text-xs text-muted">{{ k.sub }}</span></div>
          <p class="m-0 mt-1.5 text-xs leading-relaxed text-ink-2">{{ k.cara }}</p>
          <div class="mt-3 flex gap-6">
            <div><div class="text-[11px] text-muted">Per tahun</div><div class="text-[20px] font-medium tabular-nums" :class="kelasPersen(k.cagr)">{{ angka(k.cagr) }}</div></div>
            <div><div class="text-[11px] text-muted">Turun terdalam</div><div class="text-[20px] font-medium text-turun tabular-nums">{{ angka(k.dd) }}</div></div>
          </div>
          <dl class="m-0 mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
            <template v-for="[l, v] in k.isi" :key="l"><dt class="text-muted">{{ l }}</dt><dd class="m-0 text-right tabular-nums">{{ v }}</dd></template>
          </dl>
        </div>
        <div class="rounded-2xl border-2 border-aksen/40 bg-aksen-lembut/40 px-5 py-4">
          <div class="flex items-center gap-2"><Layers class="h-4 w-4 text-aksen" /><span class="font-medium">Momentum Blend</span><span class="text-xs text-muted">gabungan 50/50</span></div>
          <p class="m-0 mt-1.5 text-xs leading-relaxed text-ink-2">Kedua bagian berjalan bersamaan. Tiap akhir bulan porsinya disamakan lagi jadi 50/50.</p>
          <div class="mt-3 flex gap-6">
            <div><div class="text-[11px] text-muted">Per tahun</div><div class="text-[20px] font-medium tabular-nums" :class="kelasPersen(blendCagr)">{{ angka(blendCagr) }}</div></div>
            <div><div class="text-[11px] text-muted">Turun terdalam</div><div class="text-[20px] font-medium text-turun tabular-nums">{{ angka(blendDd) }}</div></div>
          </div>
          <dl class="m-0 mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
            <dt class="text-muted">Setelah biaya pindah 50/50</dt><dd class="m-0 text-right tabular-nums" :class="kelasPersen(r?.biaya_rebalance?.cagr_median)">{{ angka(r?.biaya_rebalance?.cagr_median) }}</dd>
            <dt class="text-muted">Korelasi kedua bagian</dt><dd class="m-0 text-right tabular-nums">{{ koma(r?.korelasi) }}</dd>
            <dt class="text-muted">Bulan untung</dt><dd class="m-0 text-right tabular-nums">{{ r?.bulan_positif != null ? persen(r.bulan_positif, 0, false) : "–" }}</dd>
            <dt class="text-muted">Bulan terburuk</dt><dd class="m-0 text-right text-turun tabular-nums">{{ angka(r?.bulan_terburuk) }}</dd>
          </dl>
        </div>
      </div>
      <div class="mt-4 flex flex-wrap items-center gap-2 text-xs">
        <span class="text-muted">Pembanding di periode yang sama:</span>
        <span class="chip bg-surface-2 text-ink-2">Bobot sama syariah <b class="ml-1 font-medium" :class="kelasPersen(r?.cagr_beli_tahan)">{{ angka(r?.cagr_beli_tahan) }}</b></span>
        <span class="chip bg-surface-2 text-ink-2">JII <b class="ml-1 font-medium" :class="kelasPersen(r?.cagr_jii)">{{ angka(r?.cagr_jii) }}</b></span>
        <span class="chip bg-surface-2 text-muted">info: IHSG <b class="ml-1 font-medium" :class="kelasPersen(r?.cagr_ihsg)">{{ angka(r?.cagr_ihsg) }}</b></span>
      </div>
      <p class="m-0 mt-3 rounded-2xl bg-surface-2/60 px-4 py-3 text-[13px] leading-relaxed text-ink-2"><b class="font-medium text-ink">Singkatnya:</b> {{ kalimat }}</p>
    </Panel>

    <Panel judul="Tahun demi tahun: kapan masing-masing bagian membantu" ket="Hasil per tahun kalender, contoh 1 simulasi (seed 7) · tahun pertama dan terakhir bisa tidak penuh">
      <BatangSeri v-if="pt.length" :label="pt.map((x) => x.tahun)" :seri="seriTahun" satuan="%" :tinggi="240" legenda />
      <div class="mt-4 overflow-x-auto">
        <table class="tabel min-w-[640px]">
          <thead><tr><th>Tahun</th><th v-for="[k, l] in KOLOM_TAHUN" :key="k" class="!text-right" :class="k === 'h29' ? 'text-ink' : ''">{{ l }}</th></tr></thead>
          <tbody>
            <tr v-for="x in pt" :key="x.tahun">
              <td class="text-ink-2">{{ x.tahun }}</td>
              <td v-for="[k] in KOLOM_TAHUN" :key="k" class="text-right tabular-nums" :class="[kelasPersen(x[k]), k === 'h29' ? 'font-medium' : '']">{{ angka(x[k]) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <ul class="m-0 mt-4 list-disc space-y-1.5 pl-5 text-[13px] leading-relaxed text-ink-2">
        <li v-for="t in temuan" :key="t">{{ t }}</li>
      </ul>
    </Panel>

    <Panel judul="Contoh rebalance bulanan RS 12-1" ket="Data asli dari simulasi · pilih bulan untuk melihat saham apa yang dibeli, dipegang, dan dijual">
      <template #aksi>
        <select v-model.number="pilihReb"><option v-for="(x, i) in daftarReb" :key="i" :value="i">{{ namaBulan(String(x.eksekusi).slice(0, 7)) }}</option></select>
      </template>
      <template v-if="reb">
        <ol class="m-0 grid list-none gap-2.5 p-0 sm:grid-cols-3">
          <li class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-xs text-muted">1 · Saring</div><div class="mt-0.5 text-[13px]"><b class="font-medium">{{ reb.lolos }}</b> saham syariah lolos syarat likuid pada close {{ tanggal(reb.sinyal) }}.</div></li>
          <li class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-xs text-muted">2 · Urutkan</div><div class="mt-0.5 text-[13px]">Diurutkan dari yang paling naik 12 bulan (tanpa bulan terakhir). Dipegang <b class="font-medium">{{ reb.n }}</b> teratas.</div></li>
          <li class="rounded-2xl bg-surface-2 px-4 py-3"><div class="text-xs text-muted">3 · Eksekusi {{ tanggal(reb.eksekusi) }}</div><div class="mt-0.5 text-[13px]">Beli <b class="font-medium text-aksen">{{ reb.beli.length }}</b>, jual <b class="font-medium text-turun">{{ reb.jual.length }}</b>, tetap <b class="font-medium">{{ reb.tetap.length }}</b>. Di harga pembukaan.</div></li>
        </ol>
        <div class="mt-4 overflow-x-auto">
          <table class="tabel min-w-[520px]">
            <thead><tr><th class="w-20">Peringkat</th><th>Saham</th><th class="!text-right">Naik 12 bulan*</th><th>Keputusan</th></tr></thead>
            <tbody>
              <tr v-for="b in barisTampil" :key="b.t" :class="b.dalamN ? '' : 'opacity-60'">
                <td class="text-ink-2 tabular-nums">{{ b.no }}<span v-if="b.no === reb.n" class="ml-1.5 text-[10px] text-muted">batas N</span></td>
                <td><KodeSaham :kode="b.t" /></td>
                <td class="text-right tabular-nums" :class="kelasPersen(b.m)">{{ angka(b.m) }}</td>
                <td><span class="chip" :class="STATUS[b.status][1]">{{ STATUS[b.status][0] }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="mt-2 flex flex-wrap items-center justify-between gap-2 px-1 text-xs text-muted">
          <span>* Kenaikan harga (disesuaikan dividen) dari akhir bulan 12 bulan lalu sampai akhir bulan lalu. Baris pudar = di luar {{ reb.n }} teratas: tidak dibeli, tapi saham yang sudah dipegang boleh tetap sampai peringkat {{ reb.n * 2 }}.</span>
          <span v-if="adaPenuh" class="w-full">Slot penuh = jumlah saham sudah {{ reb.n }} karena saham lama yang peringkatnya masih di {{ reb.n * 2 }} teratas tetap dipegang (penyangga supaya tidak bolak-balik jual beli). Jadi saham baru di peringkat bawah belum dibeli.</span>
          <button v-if="barisReb.length > reb.n" class="text-aksen hover:underline" @click="tampilSemua = !tampilSemua">{{ tampilSemua ? "Tampilkan lebih sedikit" : `Tampilkan sampai peringkat ${barisReb.length}` }}</button>
        </div>
        <div v-if="reb.jual.length" class="mt-3 flex flex-wrap items-center gap-1.5 rounded-2xl bg-turun-bg/50 px-4 py-2.5 text-xs">
          <span class="chip bg-turun-bg text-turun">Dijual</span><KodeSaham v-for="t in reb.jual" :key="t" :kode="t" />
          <span class="text-ink-2">· peringkatnya jatuh ke luar {{ reb.n * 2 }} teratas, atau tidak lagi lolos syarat syariah/likuid.</span>
        </div>
      </template>
      <p v-else class="m-0 text-muted">Belum ada data rebalance.</p>
    </Panel>

    <Panel judul="Kembali ke 50/50 tiap akhir bulan" ket="Porsi bagian Follow Tren tepat sebelum disamakan lagi · contoh 1 simulasi (seed 7)">
      <div class="grid gap-5 lg:grid-cols-[2fr_1fr]">
        <div class="h-[220px]"><Line v-if="porsi.length" :data="dataPorsi" :options="opsiPorsi" /></div>
        <div class="space-y-3 text-[13px] leading-relaxed text-ink-2">
          <div class="flex items-start gap-2"><Scale class="mt-0.5 h-4 w-4 shrink-0 text-aksen" /><span>Kalau satu bagian naik lebih banyak dalam sebulan, porsinya melebihi 50%. Di akhir bulan kelebihannya dipindah ke bagian yang tertinggal.</span></div>
          <p v-if="terjauh" class="m-0">Contoh paling jauh: akhir <b class="font-medium text-ink">{{ namaBulan(terjauh.bulan) }}</b>, bagian Follow Tren sudah <b class="font-medium text-ink">{{ koma(terjauh.porsi_ft, 1) }}%</b> dari modal, jadi <b class="font-medium text-ink">{{ koma(terjauh.pindah_pct, 1) }}%</b> modal dipindah.</p>
          <p class="m-0">Rata-rata yang dipindah ±<b class="font-medium text-ink">{{ koma(r?.biaya_rebalance?.rata_pindah_pct, 1) }}%</b> modal per bulan. Kalau tiap pemindahan dikenai biaya {{ koma(r?.biaya_rebalance?.persen_dipindah) }}% (jual + beli), hasil per tahun turun dari {{ angka(blendCagr) }} ke {{ angka(r?.biaya_rebalance?.cagr_median) }}.</p>
        </div>
      </div>
    </Panel>
  </div>
</template>

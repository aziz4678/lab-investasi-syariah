<script setup>
import { ref, computed, watch } from "vue";
import { Line } from "vue-chartjs";
import { ArrowUpRight, ArrowDownRight } from "lucide-vue-next";
import { opsiDasar, warna, pakaiTema, gradien, persen } from "../util.js";

const props = defineProps({
  tgl: Array, harga: Array, total: Array, pembanding: Array, namaPembanding: String, nama: String,
  format: { type: Function, default: (v) => v.toLocaleString("id-ID", { maximumFractionDigits: 2 }) },
  awal: { type: String, default: "1Y" }, tinggi: { type: Number, default: 300 }, intraday: Object, polos: Boolean, bulanan: Boolean,
});
const emit = defineEmits(["arah", "rentang"]);
const tema = pakaiTema();

const SEMUA_RENTANG = [
  { k: "1D", ket: "hari ini" }, { k: "1W", ket: "1 minggu terakhir", hari: 7 }, { k: "1M", ket: "1 bulan terakhir", bulan: 1 }, { k: "3M", ket: "3 bulan terakhir", bulan: 3 },
  { k: "YTD", ket: "sejak awal tahun" }, { k: "1Y", ket: "1 tahun terakhir", bulan: 12 }, { k: "3Y", ket: "3 tahun terakhir", bulan: 36 },
  { k: "5Y", ket: "5 tahun terakhir", bulan: 60 }, { k: "ALL", ket: "sejak awal data" },
];
const RENTANG = computed(() => SEMUA_RENTANG.filter((r) => (r.k !== "1D" || props.intraday?.tgl?.length) && !(props.bulanan && ["1D", "1W", "1M"].includes(r.k))));
const rentangPilih = ref(props.awal);
const rentang = computed({
  get: () => (RENTANG.value.some((r) => r.k === rentangPilih.value) ? rentangPilih.value : props.bulanan ? "1Y" : "1W"),
  set: (v) => (rentangPilih.value = v),
});
watch(rentangPilih, (k) => emit("rentang", k));
const harian = computed(() => rentang.value === "1D");
const sesiJam = computed(() => {
  const s = props.intraday?.sesi_jam || [[540, 720], [810, 960]];
  return s.length === 1 ? [s[0], [s[0][1], s[0][1]]] : s;
});
const satuSesi = computed(() => sesiJam.value[1][0] === sesiJam.value[1][1] && sesiJam.value[1][0] === sesiJam.value[0][1]);
const panjang1 = computed(() => sesiJam.value[0][1] - sesiJam.value[0][0]);
const panjangSesi = computed(() => panjang1.value + sesiJam.value[1][1] - sesiJam.value[1][0]);
function keSumbu(t) {
  const m = Number(t.slice(11, 13)) * 60 + Number(t.slice(14, 16));
  const [[a1, b1], [a2]] = sesiJam.value;
  if (m <= b1) return Math.max(0, m - a1);
  if (m >= a2) return panjang1.value + m - a2;
  return panjang1.value;
}
const teksMenit = (m) => `${String(Math.floor(m / 60)).padStart(2, "0")}.${String(m % 60).padStart(2, "0")}`;
function dariSumbu(x) {
  const [[a1, b1], [a2]] = sesiJam.value;
  if (x === panjang1.value) return satuSesi.value ? teksMenit(b1) : `${teksMenit(b1)} | ${teksMenit(a2)}`;
  return teksMenit(x < panjang1.value ? a1 + x : a2 + x - panjang1.value);
}
const jam = (t) => new Date(t).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit", timeZone: props.intraday?.zona || "Asia/Jakarta" });
const src = computed(() => (harian.value
  ? { tgl: props.intraday.tgl, harga: props.intraday.nilai, total: null, pembanding: null, acuan: props.intraday.tutup_kemarin }
  : { tgl: props.tgl || [], harga: props.harga || [], total: props.total, pembanding: props.pembanding, acuan: null }));
const arah = ref(null);
watch(() => [props.tgl, rentangPilih.value], () => (arah.value = null));
watch(arah, (i) => emit("arah", i == null ? null : { harga: src.value.harga[i], tgl: src.value.tgl[i] }));

function isoTgl(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

const dasar = computed(() => {
  const tgl = src.value.tgl;
  const n = tgl.length;
  const r = SEMUA_RENTANG.find((x) => x.k === rentang.value);
  if (n < 2 || r.k === "ALL" || r.k === "1D") return 0;
  const akhir = new Date(tgl[n - 1]);
  let batas;
  if (r.k === "YTD") batas = `${akhir.getFullYear() - 1}-12-31`;
  else {
    const d = new Date(akhir);
    if (r.hari) d.setDate(d.getDate() - r.hari);
    else d.setMonth(d.getMonth() - r.bulan);
    batas = isoTgl(d);
  }
  let i = n - 1;
  while (i > 0 && tgl[i] > batas) i -= 1;
  return i;
});

const potong = computed(() => {
  const i = dasar.value;
  const harga = src.value.harga.slice(i);
  let pemb = null;
  if (src.value.pembanding) {
    const p = src.value.pembanding.slice(i);
    const j = p.findIndex((v) => v != null);
    if (j >= 0) pemb = p.map((v) => (v == null ? null : (v / p[j]) * harga[j]));
  }
  const tgl = src.value.tgl.slice(i);
  return { i, tgl, x: tgl.map((t) => (harian.value ? keSumbu(t) : Date.parse(t))), harga, pemb, acuan: src.value.acuan };
});

const kepala = computed(() => {
  const s = src.value;
  const n = s.tgl.length;
  if (!n) return null;
  const b = dasar.value;
  const i = arah.value ?? n - 1;
  const harga = s.harga[i];
  const awal = s.acuan ?? s.harga[b];
  const r = SEMUA_RENTANG.find((x) => x.k === rentang.value);
  const tot = s.total && s.total[b] ? (s.total[i] / s.total[b] - 1) * 100 : null;
  const ket = harian.value
    ? `${arah.value == null ? "hari ini" : "pukul"} ${jam(s.tgl[i])} · ${props.intraday.sesi} · dari penutupan kemarin ${props.format(awal)}`
    : arah.value == null ? `${r.ket} · ${s.tgl[n - 1]}` : `${s.tgl[i]} · dari ${s.tgl[b]}`;
  return { harga, selisih: harga - awal, pct: awal ? (harga / awal - 1) * 100 : null, tot, ket };
});

const naik = computed(() => {
  const h = potong.value.harga;
  return h.at(-1) >= (potong.value.acuan ?? h[0]);
});

const data = computed(() => {
  tema.value;
  const p = potong.value;
  const w = naik.value ? "--naik" : "--turun";
  const ds = [{
    label: props.nama || "Harga", data: p.harga.map((y, j) => ({ x: p.x[j], y })), order: 1, borderColor: warna(w), backgroundColor: gradien(w, 0.2), fill: "origin",
    borderWidth: 2, pointRadius: 0, pointHoverRadius: 4, pointBackgroundColor: warna(w), pointHoverBorderColor: warna("--surface-1"), tension: 0.2,
    segment: harian.value ? { borderColor: (c) => (c.p1.parsed.x - c.p0.parsed.x > 10 ? "transparent" : undefined), backgroundColor: (c) => (c.p1.parsed.x - c.p0.parsed.x > 10 ? "transparent" : undefined) } : undefined,
  }];
  if (p.pemb) ds.push({
    label: props.namaPembanding || "Pembanding", data: p.pemb.map((y, j) => ({ x: p.x[j], y })), order: 2, borderColor: warna("--text-muted"), borderDash: [5, 4], borderWidth: 1.5,
    pointRadius: 0, pointHoverRadius: 3, pointBackgroundColor: warna("--text-muted"), pointHoverBorderColor: warna("--surface-1"), tension: 0.2,
  });
  if (p.acuan != null) ds.push({
    label: "Penutupan kemarin", data: [{ x: 0, y: p.acuan }, { x: panjangSesi.value, y: p.acuan }], order: 3, borderColor: warna("--text-muted"),
    borderDash: [3, 4], borderWidth: 1, pointRadius: 0, pointHoverRadius: 0,
  });
  return { datasets: ds };
});

const opsi = computed(() => {
  tema.value;
  const o = opsiDasar();
  o.animation = false;
  o.scales.y.grace = "4%";
  o.scales.y.beginAtZero = false;
  const p = potong.value;
  const nilai = [...p.harga, ...(p.pemb || [])].filter((v) => v != null);
  if (nilai.length) {
    const bawah = Math.min(...nilai), atas = Math.max(...nilai);
    if (bawah >= 0 && bawah - (atas - bawah) * 0.04 < 0) o.scales.y.min = 0;
  }
  const hari = (p.x.at(-1) - p.x[0]) / 86400000;
  o.scales.x.type = "linear";
  o.scales.x.min = harian.value ? 0 : p.x[0];
  o.scales.x.max = harian.value ? panjangSesi.value : p.x.at(-1);
  if (harian.value) {
    const [[a1, b1], [a2, b2]] = sesiJam.value;
    const titik = [0];
    for (let m = Math.ceil((a1 + 1) / 60) * 60; m < b1; m += 60) titik.push(m - a1);
    titik.push(panjang1.value);
    if (!satuSesi.value) for (let m = Math.ceil((a2 + 1) / 60) * 60; m <= b2; m += 60) titik.push(panjang1.value + m - a2);
    o.scales.x.afterBuildTicks = (ax) => (ax.ticks = titik.map((value) => ({ value })));
    o.scales.x.ticks.autoSkip = false;
  }
  o.scales.x.ticks.maxTicksLimit = 8;
  o.scales.x.ticks.callback = (v) => {
    if (harian.value) return dariSumbu(v);
    const d = new Date(v);
    return hari > 900 ? String(d.getFullYear()) : d.toLocaleDateString("id-ID", { day: "numeric", month: "short", year: hari > 300 ? "2-digit" : undefined });
  };
  o.scales.y.ticks.callback = (v) => props.format(v);
  o.onHover = (_, el) => {
    const e = el.find((x) => x.datasetIndex === 0);
    arah.value = e ? potong.value.i + e.index : null;
  };
  o.plugins.tooltip.filter = (c) => c.dataset.label !== "Penutupan kemarin";
  o.plugins.tooltip.callbacks = {
    title: (it) => (it.length ? (harian.value ? jam(potong.value.tgl[it[0].dataIndex]) : potong.value.tgl[it[0].dataIndex]) : ""),
    label: (c) => {
      if (c.datasetIndex === 0) return ` ${c.dataset.label}  ${props.format(c.parsed.y)}`;
      const h = potong.value.harga;
      const pct = (c.parsed.y / h[0] - 1) * 100;
      return ` ${c.dataset.label}  ${pct >= 0 ? "+" : ""}${pct.toFixed(1).replace(".", ",")}% sejak awal`;
    },
  };
  return o;
});
</script>

<template>
  <div>
    <div v-if="!polos" class="-mt-1 mb-4 flex flex-wrap items-end justify-between gap-3">
      <div v-if="kepala" class="min-w-0">
        <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span class="text-[32px] leading-none font-medium tracking-tight tabular-nums">{{ format(kepala.harga) }}</span>
          <span class="inline-flex items-center gap-1 text-[15px] font-medium tabular-nums" :class="kepala.selisih > 0 ? 'text-naik' : kepala.selisih < 0 ? 'text-turun' : 'text-muted'">
            <ArrowUpRight v-if="kepala.selisih > 0" class="h-4 w-4" :stroke-width="2.4" />
            <ArrowDownRight v-else-if="kepala.selisih < 0" class="h-4 w-4" :stroke-width="2.4" />
            {{ format(Math.abs(kepala.selisih)) }} ({{ persen(kepala.pct, 2) }})
          </span>
          <span class="text-[13px] text-muted">{{ kepala.ket }}</span>
        </div>
        <div v-if="kepala.tot != null && Math.abs(kepala.tot - kepala.pct) >= 0.05" class="mt-1.5 text-xs text-ink-2">
          Termasuk dividen: <span class="font-medium" :class="kepala.tot >= 0 ? 'text-naik' : 'text-turun'">{{ persen(kepala.tot, 2) }}</span>
        </div>
      </div>
    </div>
    <div v-if="!polos" class="mb-3 flex flex-wrap items-center justify-between gap-2">
      <div class="flex flex-wrap gap-1.5">
        <button v-for="r in RENTANG" :key="r.k" type="button" @click="rentang = r.k"
          class="h-8 min-w-12 rounded-full border px-3 text-xs font-medium transition"
          :class="rentang === r.k ? 'border-aksen bg-aksen-lembut text-aksen' : 'border-garis text-muted hover:border-ink-2 hover:text-ink'">{{ r.k === "ALL" ? "Semua" : r.k }}</button>
      </div>
      <slot name="aksi" />
    </div>
    <div v-if="potong.pemb" class="mb-2 flex flex-wrap gap-2 text-xs text-ink-2">
      <span class="inline-flex items-center gap-2 rounded-full bg-surface-2 px-3 py-1"><span class="h-0.5 w-4 rounded" :class="naik ? 'bg-naik' : 'bg-turun'"></span>{{ nama }}</span>
      <span class="inline-flex items-center gap-2 rounded-full bg-surface-2 px-3 py-1"><span class="w-4 border-t-2 border-dashed border-muted"></span>{{ namaPembanding }} (disetarakan di awal periode)</span>
    </div>
    <div :style="{ height: `${tinggi}px` }" @mouseleave="arah = null"><Line :data="data" :options="opsi" /></div>
    <p v-if="harian && satuSesi" class="m-0 mt-2 text-xs text-muted">
      Sesi perdagangan {{ teksMenit(sesiJam[0][0]) }}–{{ teksMenit(sesiJam[0][1]) }} {{ intraday?.zona === "Europe/London" ? "waktu London" : "waktu New York" }}
    </p>
    <p v-else-if="harian" class="m-0 mt-2 text-xs text-muted">
      Sesi 1 {{ teksMenit(sesiJam[0][0]) }}–{{ teksMenit(sesiJam[0][1]) }} · istirahat · sesi 2 {{ teksMenit(sesiJam[1][0]) }}–15.49, pra-penutupan sampai 16.00{{ sesiJam[0][1] === 690 ? " · jadwal Jumat" : " · jadwal Senin–Kamis" }}
    </p>
  </div>
</template>

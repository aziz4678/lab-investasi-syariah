<script setup>
import KodeSaham from "@/components/common/KodeSaham.vue";
import { ref, computed, watch, nextTick } from "vue";
import { X } from "lucide-vue-next";
import { persen, rupiah, tanggal } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";

const props = defineProps({ trade: Array, ekuitas: { type: Array, default: () => [] }, perTahun: { type: Object, default: null } });
const tahun = ref("");
const bulan = ref("");
const dasar = ref("beli");
const akar = ref(null);
const BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];
const cari = ref("");
const status = ref("");
const bagian = ref("");
const urut = ref({ kunci: "tgl_sinyal", naik: false });
const halaman = ref(1);
const PER = 50;

const daftarTahun = computed(() => [...new Set((props.trade || []).map((t) => t.tgl_beli.slice(0, 4)))].sort().reverse());

const periode = computed(() => {
  if (!tahun.value) return null;
  if (!bulan.value) return { awal: `${tahun.value}-01-01`, akhir: `${tahun.value}-12-31`, label: tahun.value };
  return { awal: `${tahun.value}-${bulan.value}-01`, akhir: `${tahun.value}-${bulan.value}-31`, label: `${BULAN[+bulan.value - 1]} ${tahun.value}` };
});

const petaEk = computed(() => Object.fromEntries((props.ekuitas || []).map((e) => [e.bulan, e])));

function bulanSebelum(b) {
  const [y, m] = b.split("-").map(Number);
  return m === 1 ? `${y - 1}-12` : `${y}-${String(m - 1).padStart(2, "0")}`;
}

const dasarPeriode = computed(() => {
  const p = periode.value;
  if (!p) return null;
  const awal = p.awal.slice(0, 7);
  const akhir = p.akhir.slice(0, 7);
  const ada = (props.ekuitas || []).filter((e) => e.bulan >= awal && e.bulan <= akhir);
  if (!ada.length) return null;
  const ekAwal = petaEk.value[bulanSebelum(ada[0].bulan)]?.ekuitas ?? 1;
  const peta = bulan.value ? ada[0].return : props.perTahun?.[tahun.value] ?? (ada[ada.length - 1].ekuitas / ekAwal - 1) * 100;
  return { awal, akhir, ekAwal, peta };
});

function sumbangan(x, semua = false) {
  const d = dasarPeriode.value;
  if (!d || !x.pnl) return null;
  let s = 0;
  for (const [b, v] of Object.entries(x.pnl)) if (semua || (b >= d.awal && b <= d.akhir)) s += v;
  return (s / d.ekAwal) * 100;
}

function masuk(x, p) {
  const beli = x.tgl_beli.slice(0, 10);
  if (dasar.value === "beli") return beli >= p.awal && beli <= p.akhir;
  return beli <= p.akhir && (x.status === "terbuka" || !x.tgl_jual || x.tgl_jual.slice(0, 10) >= p.awal);
}

const tersaring = computed(() => {
  let t = props.trade || [];
  if (periode.value) t = t.filter((x) => masuk(x, periode.value));
  if (cari.value) t = t.filter((x) => x.ticker.includes(cari.value.toUpperCase()));
  if (status.value) t = t.filter((x) => x.status === status.value);
  if (bagian.value) t = t.filter((x) => x.bagian === bagian.value);
  if (dasarPeriode.value) t = t.map((x) => ({ ...x, sumbangan: sumbangan(x), sumbangan_semua: sumbangan(x, true) }));
  const { kunci, naik } = urut.value;
  return [...t].sort((a, b) => (a[kunci] > b[kunci] ? 1 : a[kunci] < b[kunci] ? -1 : 0) * (naik ? 1 : -1));
});

const ringkas = computed(() => {
  const t = tersaring.value.filter((x) => x.status !== "terbuka");
  if (!t.length) return null;
  const m = t.filter((x) => x.net > 0);
  const rata = (a) => a.reduce((s, x) => s + x.net, 0) / (a.length || 1);
  return { n: tersaring.value.length, wr: (m.length / t.length) * 100, rata: rata(t), menang: rata(m), kalah: rata(t.filter((x) => x.net <= 0)) };
});

const totalSumbangan = computed(() => {
  if (!dasarPeriode.value) return null;
  return tersaring.value.reduce((s, x) => s + (x.sumbangan || 0), 0);
});
const totalSemua = computed(() => {
  if (!dasarPeriode.value) return null;
  return tersaring.value.reduce((s, x) => s + (x.sumbangan_semua || 0), 0);
});
const adaTerbuka = computed(() => tersaring.value.some((x) => x.status === "terbuka"));
const posSumbangan = computed(() => KOLOM.value.findIndex(([k]) => k === "sumbangan"));
const tersaringLain = computed(() => !!(cari.value || status.value || bagian.value));

const tampil = computed(() => tersaring.value.slice((halaman.value - 1) * PER, halaman.value * PER));
const jumlahHal = computed(() => Math.max(1, Math.ceil(tersaring.value.length / PER)));
watch([tahun, bulan, dasar, cari, status, bagian], () => (halaman.value = 1));
watch(tahun, (v) => !v && (bulan.value = ""));

function hapusPeriode() {
  tahun.value = "";
  bulan.value = "";
  dasar.value = "beli";
}

async function saring(th, bl) {
  tahun.value = String(th);
  bulan.value = bl ? String(bl).padStart(2, "0") : "";
  dasar.value = "pegang";
  status.value = "";
  cari.value = "";
  await nextTick();
  akar.value?.$el?.scrollIntoView({ behavior: "smooth", block: "start" });
}

defineExpose({ saring, tahun, bulan });

function urutkan(k) {
  urut.value = { kunci: k, naik: urut.value.kunci === k ? !urut.value.naik : false };
}

const adaBagian = computed(() => (props.trade || []).some((t) => t.bagian));
const adaStop = computed(() => (props.trade || []).some((t) => t.stop_awal_pct != null));
const KOLOM = computed(() => [
  ["ticker", "Saham", 0], ...(adaBagian.value ? [["bagian", "Bagian", 0]] : []), ["tgl_beli", "Tanggal beli", 0], ["harga_beli", "Harga beli", 1], ["tgl_jual", "Tanggal jual", 0],
  ["harga_jual", "Harga jual", 1], ["hari", "Hari", 1], ...(adaStop.value ? [["stop_awal_pct", "Stop awal", 1]] : []),
  ...(dasarPeriode.value ? [["sumbangan", `Sumbangan ${periode.value.label}`, 1], ["net", "Hasil trade", 1]] : [["net", "Hasil", 1]]), ["status", "Status", 0],
]);
</script>

<template>
  <Panel ref="akar" class="scroll-mt-4" judul="Daftar trade" ket="Trade yang masuk portofolio · klik judul kolom untuk mengurutkan · net sudah dipotong biaya" rapat>
    <template #aksi>
      <select v-model="tahun"><option value="">Semua tahun</option><option v-for="t in daftarTahun" :key="t" :value="t">{{ t }}</option></select>
      <select v-model="bulan" :disabled="!tahun"><option value="">Semua bulan</option><option v-for="(b, i) in BULAN" :key="b" :value="String(i + 1).padStart(2, '0')">{{ b }}</option></select>
      <select v-if="tahun" v-model="dasar"><option value="beli">Dibeli di periode ini</option><option value="pegang">Dipegang selama periode ini</option></select>
      <select v-if="adaBagian" v-model="bagian"><option value="">Kedua bagian</option><option value="Follow Tren">Follow Tren</option><option value="RS 12-1">RS 12-1</option></select>
      <select v-model="status"><option value="">Semua status</option><option value="selesai">Selesai</option><option value="terbuka">Masih dipegang</option></select>
      <input v-model="cari" placeholder="Cari saham" class="w-32" />
    </template>
    <div v-if="periode" class="mx-6 mb-3 rounded-2xl bg-aksen-lembut px-4 py-3 text-xs leading-relaxed text-ink-2">
      <div class="flex flex-wrap items-center gap-2">
        <b class="font-medium text-ink">{{ dasar === "pegang" ? "Dipegang selama" : "Dibeli di" }} {{ periode.label }}</b>
        <span v-if="dasarPeriode && totalSumbangan != null" class="tabular-nums">
          · total sumbangan <b class="font-medium" :class="totalSumbangan >= 0 ? 'text-naik' : 'text-turun'">{{ persen(totalSumbangan) }}</b>
          <template v-if="dasar === 'pegang' && !tersaringLain"> = return portofolio di peta <b class="font-medium" :class="dasarPeriode.peta >= 0 ? 'text-naik' : 'text-turun'">{{ persen(dasarPeriode.peta) }}</b></template>
          <template v-else> · return portofolio di peta {{ persen(dasarPeriode.peta) }}</template>
        </span>
        <button class="ml-auto inline-flex items-center gap-1 text-aksen hover:underline" @click="hapusPeriode"><X class="h-3.5 w-3.5" />Hapus filter</button>
      </div>
      <ul v-if="dasarPeriode" class="m-0 mt-1.5 list-disc space-y-0.5 pl-4">
        <li><b class="font-medium text-ink">Sumbangan {{ periode.label }}</b> = untung/rugi trade itu khusus selama {{ periode.label }}, dihitung sebagai persen dari seluruh modal portofolio (besar posisi, biaya, dan dividen ikut dihitung). Jumlah semua trade yang dipegang = angka di peta.</li>
        <li><b class="font-medium text-ink">Hasil trade</b> = untung/rugi dari tanggal beli sampai tanggal jual, bisa mencakup bulan lain dan dihitung dari modal trade itu saja. Karena itu rata-rata Hasil trade tidak sama dengan angka di peta.</li>
        <li>Baris total di bawah tabel: <b class="font-medium text-ink">selama periode</b> (= peta) dan <b class="font-medium text-ink">sampai selesai</b> (untung/rugi trade yang sama dari beli sampai jual, termasuk bulan lain), keduanya dalam persen modal portofolio awal {{ periode.label }}.</li>
        <li v-if="dasar !== 'pegang'">Filter ini hanya menampilkan trade yang <i>dibeli</i> di periode ini, jadi totalnya belum tentu sama dengan peta. Pilih "Dipegang selama periode ini" untuk mencocokkan.</li>
        <li v-else-if="tersaringLain">Filter saham/status/bagian aktif, jadi total hanya dari trade yang tampil.</li>
      </ul>
    </div>
    <div v-if="ringkas" class="flex flex-wrap gap-x-6 gap-y-1 px-6 pb-3 text-xs text-muted tabular-nums">
      <span>{{ ringkas.n }} trade</span>
      <span>Win rate <b class="font-medium text-ink">{{ persen(ringkas.wr, 0, false) }}</b></span>
      <span>{{ dasarPeriode ? "Rata-rata hasil trade" : "Rata-rata" }} <b class="font-medium" :class="ringkas.rata >= 0 ? 'text-naik' : 'text-turun'">{{ persen(ringkas.rata, 2) }}</b></span>
      <span>Menang <b class="font-medium text-naik">{{ persen(ringkas.menang) }}</b></span>
      <span>Kalah <b class="font-medium text-turun">{{ persen(ringkas.kalah) }}</b></span>
    </div>
    <div class="overflow-x-auto">
      <table class="tabel min-w-[780px]">
        <thead>
          <tr>
            <th v-for="[k, l, al] in KOLOM" :key="k" @click="urutkan(k)" class="cursor-pointer select-none hover:text-ink"
              :class="[al ? '!text-right' : '', urut.kunci === k ? '!text-ink' : '']">
              {{ l }}<span v-if="urut.kunci === k" class="ml-0.5">{{ urut.naik ? "↑" : "↓" }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in tampil" :key="t.ticker + t.tgl_sinyal + (t.bagian || '')">
            <td><KodeSaham :kode="t.ticker" /></td>
            <td v-if="adaBagian"><span class="chip" :class="t.bagian === 'RS 12-1' ? 'bg-kuning-bg text-ink-2' : 'bg-aksen-lembut text-aksen'">{{ t.bagian }}</span></td>
            <td class="text-ink-2">{{ tanggal(t.tgl_beli) }}</td>
            <td class="text-right">{{ rupiah(t.harga_beli) }}</td>
            <td class="text-ink-2">{{ t.status === "terbuka" || !t.tgl_jual ? "–" : tanggal(t.tgl_jual) }}</td>
            <td class="text-right">{{ t.harga_jual != null ? rupiah(t.harga_jual) : "–" }}</td>
            <td class="text-right text-ink-2">{{ t.hari }}</td>
            <td v-if="adaStop" class="text-right text-turun/80">{{ t.stop_awal_pct != null ? persen(-t.stop_awal_pct, 1) : "–" }}</td>
            <td v-if="dasarPeriode" class="text-right font-medium" :class="t.sumbangan == null ? 'text-muted' : t.sumbangan >= 0 ? 'text-naik' : 'text-turun'">{{ t.sumbangan == null ? "–" : persen(t.sumbangan, 2) }}</td>
            <td class="text-right" :class="[dasarPeriode ? '' : 'font-medium', t.net >= 0 ? 'text-naik' : 'text-turun']">{{ persen(t.net) }}</td>
            <td><span class="chip" :class="t.status === 'terbuka' ? 'bg-aksen-lembut text-aksen' : 'bg-surface-2 text-muted'">{{ t.status === "terbuka" ? "Dipegang" : "Selesai" }}</span></td>
          </tr>
        </tbody>
        <tfoot v-if="dasarPeriode && tersaring.length" class="border-t border-garis text-xs">
          <tr>
            <td :colspan="posSumbangan" class="!h-auto py-3 text-ink-2">
              <b class="font-medium text-ink">Total {{ tersaring.length }} trade</b> · persen dari modal portofolio awal {{ periode.label }}
            </td>
            <td class="!h-auto py-3 text-right tabular-nums">
              <b class="text-sm font-medium" :class="totalSumbangan >= 0 ? 'text-naik' : 'text-turun'">{{ persen(totalSumbangan, 2) }}</b>
              <div class="text-[11px] text-muted">selama periode</div>
            </td>
            <td class="!h-auto py-3 text-right tabular-nums">
              <b class="text-sm font-medium" :class="totalSemua >= 0 ? 'text-naik' : 'text-turun'">{{ persen(totalSemua, 2) }}</b>
              <div class="text-[11px] text-muted">{{ adaTerbuka ? "sampai selesai / akhir data" : "sampai selesai" }}</div>
            </td>
            <td />
          </tr>
        </tfoot>
      </table>
    </div>
    <div class="flex items-center justify-end gap-2 px-6 pt-2 pb-3 text-xs text-muted">
      <span>Halaman {{ halaman }} dari {{ jumlahHal }}</span>
      <button class="tombol !h-8 !w-8 !justify-center !px-0" :disabled="halaman <= 1" @click="halaman--">‹</button>
      <button class="tombol !h-8 !w-8 !justify-center !px-0" :disabled="halaman >= jumlahHal" @click="halaman++">›</button>
    </div>
  </Panel>
</template>

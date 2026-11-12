<script setup>
import KodeSaham from "@/components/common/KodeSaham.vue";
import Pemutar from "@/components/common/Pemutar.vue";
import { ref, computed, watch, nextTick } from "vue";
import { X } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { persen, rupiah, tanggal, kelasUntung } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";

const props = defineProps({ trade: Array, ekuitas: { type: Array, default: () => [] }, versi: String });
const BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];
const akar = ref(null);
const tahun = ref("");
const bulan = ref("");
const cari = ref("");
const status = ref("");
const bagian = ref("");
const urut = ref({ kunci: "tgl_sinyal", naik: false });
const urutPeriode = ref({ kunci: "sumbangan_pct", naik: false });
const halaman = ref(1);
const PER = 50;
const d = ref(null);
const muat = ref(false);
const galat = ref("");

const daftarTahun = computed(() => [...new Set((props.trade || []).map((t) => t.tgl_beli.slice(0, 4)))].sort().reverse());
const periode = computed(() => {
  if (!tahun.value) return null;
  if (!bulan.value) return { label: tahun.value };
  return { label: `${BULAN[+bulan.value - 1]} ${tahun.value}` };
});

const isi = async () => {
  if (!periode.value || !props.versi) {
    d.value = null;
    return;
  }
  muat.value = true;
  galat.value = "";
  try {
    d.value = await ambil(`rincian/${props.versi}?tahun=${tahun.value}${bulan.value ? `&bulan=${+bulan.value}` : ""}`);
  } catch (e) {
    d.value = null;
    galat.value = `Tidak bisa memuat rincian periode: ${e.message}`;
  } finally {
    muat.value = false;
  }
};
watch([() => props.versi, tahun, bulan], isi);
watch([tahun, bulan, cari, status, bagian], () => (halaman.value = 1));
watch(tahun, (v) => !v && (bulan.value = ""));
watch(() => props.versi, () => hapusPeriode());

const hapusPeriode = () => {
  tahun.value = "";
  bulan.value = "";
};

const saring = async (th, bl) => {
  const b = bl ? String(bl).padStart(2, "0") : "";
  if (tahun.value === String(th) && bulan.value === b) {
    hapusPeriode();
    return;
  }
  tahun.value = String(th);
  bulan.value = b;
  status.value = "";
  cari.value = "";
  urutPeriode.value = { kunci: "sumbangan_pct", naik: false };
  await nextTick();
  akar.value?.$el?.scrollIntoView({ behavior: "smooth", block: "start" });
};
defineExpose({ saring, tahun, bulan });

const urutkan = (k) => {
  urut.value = { kunci: k, naik: urut.value.kunci === k ? !urut.value.naik : false };
};
const urutkanPeriode = (k) => {
  urutPeriode.value = { kunci: k, naik: urutPeriode.value.kunci === k ? !urutPeriode.value.naik : false };
};

const adaBagian = computed(() => (props.trade || []).some((t) => t.bagian));
const adaStop = computed(() => (props.trade || []).some((t) => t.stop_awal_pct != null));
const terbuka = (t) => t.status === "terbuka" || !t.tgl_jual;
const saringLain = (t) => (!cari.value || t.ticker.includes(cari.value.toUpperCase())) && (!bagian.value || t.bagian === bagian.value);
const adaFilter = computed(() => !!(cari.value || status.value || bagian.value));
const urutan = (a, b, { kunci, naik }) => (a[kunci] > b[kunci] ? 1 : a[kunci] < b[kunci] ? -1 : 0) * (naik ? 1 : -1);

const semua = computed(() => {
  let t = (props.trade || []).filter(saringLain);
  if (status.value) t = t.filter((x) => x.status === status.value);
  return [...t].sort((a, b) => urutan(a, b, urut.value));
});

const baris = computed(() => {
  const t = (d.value?.posisi || []).filter((p) => saringLain(p) && (!status.value || (status.value === "terbuka") === p.terbuka));
  return [...t].sort((a, b) => urutan(a, b, urutPeriode.value));
});
const totalSumb = computed(() => baris.value.reduce((s, x) => s + x.sumbangan_pct, 0));
const selesaiPeriode = computed(() => baris.value.filter((p) => p.dijual));

const rata = (a) => a.reduce((s, x) => s + x.net, 0) / (a.length || 1);
const statistik = (sumber) => {
  if (!sumber.length) return null;
  const m = sumber.filter((x) => x.net > 0);
  const k = sumber.filter((x) => x.net <= 0);
  return { n: sumber.length, wr: (m.length / sumber.length) * 100, rata: rata(sumber), menang: m.length ? rata(m) : null, kalah: k.length ? rata(k) : null };
};
const ringkas = computed(() => {
  const s = statistik(semua.value.filter((x) => !terbuka(x)));
  return s && { ...s, n: semua.value.length };
});
const ringkasPeriode = computed(() => statistik(selesaiPeriode.value));

const tampil = computed(() => semua.value.slice((halaman.value - 1) * PER, halaman.value * PER));
const jumlahHal = computed(() => Math.max(1, Math.ceil(semua.value.length / PER)));

const terbesar = computed(() => Math.max(0.0001, ...baris.value.map((p) => Math.abs(p.sumbangan_pct)), Math.abs(d.value?.kas_lain_pct || 0)));
const lebar = (v) => `${Math.max(2, (Math.abs(v) / terbesar.value) * 100)}%`;
const badge = (p) => (p.dibeli && p.dijual ? "dibeli & dijual" : p.dibeli ? "dibeli" : p.dijual ? "dijual" : "dipegang penuh");
const kelasBadge = (p) => (p.dibeli ? "bg-aksen-lembut text-aksen" : p.dijual ? "bg-kuning-bg text-ink-2" : "bg-surface-2 text-muted");
const harga = (v) => (v == null ? "–" : rupiah(Math.round(v)));
const pct = (v) => persen(Math.abs(v) < 0.005 ? 0 : v, 2);

const judul = computed(() => (periode.value ? `${periode.value.label}${d.value ? ` · ${persen(d.value.heatmap_pct, 1)}` : ""}` : "Daftar trade"));
const ket = computed(() => (periode.value
  ? "Semua trade yang dipegang di periode ini. Sumbangan = untung/rugi khusus selama periode, dalam % modal portofolio awal periode. Hasil trade = hasil penuh dari beli sampai jual, dalam % modal trade itu."
  : "Trade yang masuk portofolio · klik judul kolom untuk mengurutkan · hasil sudah dipotong biaya"));

const KOLOM = computed(() => [
  ["ticker", "Saham", 0], ...(adaBagian.value ? [["bagian", "Bagian", 0]] : []), ["tgl_beli", "Tanggal beli", 0], ["harga_beli", "Harga beli", 1], ["tgl_jual", "Tanggal jual", 0],
  ["harga_jual", "Harga jual", 1], ["hari", "Hari", 1], ...(adaStop.value ? [["stop_awal_pct", "Stop awal", 1]] : []), ["net", "Hasil trade", 1], ["status", "Status", 0],
]);
const KOLOM_PERIODE = computed(() => [
  ["ticker", "Saham", 0, ""], ...(adaBagian.value ? [["bagian", "Bagian", 0, ""]] : []), ["dibeli", "Dalam periode", 0, ""], ["tgl_beli", "Tanggal beli", 0, ""], ["tgl_jual", "Tanggal jual", 0, ""],
  ["harga_awal", "Harga awal", 1, "periode"], ["harga_akhir", "Harga akhir", 1, "periode"], ["sumbangan_pct", "Sumbangan", 1, `di ${periode.value?.label}`], ["net", "Hasil trade", 1, "beli → jual"],
]);
</script>

<template>
  <Panel ref="akar" class="scroll-mt-4" :judul="judul" :ket="ket" rapat>
    <template #aksi>
      <select v-model="tahun"><option value="">Semua tahun</option><option v-for="t in daftarTahun" :key="t" :value="t">{{ t }}</option></select>
      <select v-model="bulan" :disabled="!tahun"><option value="">Semua bulan</option><option v-for="(b, i) in BULAN" :key="b" :value="String(i + 1).padStart(2, '0')">{{ b }}</option></select>
      <select v-if="adaBagian" v-model="bagian"><option value="">Kedua bagian</option><option value="Follow Tren">Follow Tren</option><option value="RS 12-1">RS 12-1</option></select>
      <select v-model="status"><option value="">Semua status</option><option value="selesai">Selesai</option><option value="terbuka">Masih dipegang</option></select>
      <input v-model="cari" placeholder="Cari saham" class="w-32" />
      <button v-if="periode" class="tombol" @click="hapusPeriode"><X class="h-3.5 w-3.5" />Semua trade</button>
    </template>
    <p v-if="galat" class="m-0 px-6 pb-4 text-turun">{{ galat }}</p>

    <template v-if="!periode">
      <div v-if="ringkas" class="flex flex-wrap gap-x-6 gap-y-1 px-6 pb-3 text-xs text-muted tabular-nums">
        <span>{{ ringkas.n }} trade</span>
        <span>Win rate <b class="font-medium text-ink">{{ persen(ringkas.wr, 0, false) }}</b></span>
        <span>Rata-rata <b class="font-medium" :class="ringkas.rata >= 0 ? 'text-naik' : 'text-turun'">{{ persen(ringkas.rata, 2) }}</b></span>
        <span>Menang <b class="font-medium text-naik">{{ ringkas.menang != null ? persen(ringkas.menang) : "–" }}</b></span>
        <span>Kalah <b class="font-medium text-turun">{{ ringkas.kalah != null ? persen(ringkas.kalah) : "–" }}</b></span>
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
              <td class="text-ink-2">{{ terbuka(t) ? "–" : tanggal(t.tgl_jual) }}</td>
              <td class="text-right" :class="terbuka(t) ? 'italic text-muted' : ''" :title="terbuka(t) ? 'harga terakhir, belum dijual' : ''">{{ t.harga_jual != null ? rupiah(t.harga_jual) : "–" }}</td>
              <td class="text-right text-ink-2">{{ t.hari }}</td>
              <td v-if="adaStop" class="text-right text-turun/80">{{ t.stop_awal_pct != null ? persen(-t.stop_awal_pct, 1) : "–" }}</td>
              <td class="text-right font-medium" :class="t.net >= 0 ? 'text-naik' : 'text-turun'">{{ persen(t.net) }}</td>
              <td><span class="chip" :class="terbuka(t) ? 'bg-aksen-lembut text-aksen' : 'bg-surface-2 text-muted'">{{ terbuka(t) ? "Dipegang" : "Selesai" }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="flex items-center justify-end gap-2 px-6 pt-2 pb-3 text-xs text-muted">
        <span>Halaman {{ halaman }} dari {{ jumlahHal }}</span>
        <button class="tombol !h-8 !w-8 !justify-center !px-0" :disabled="halaman <= 1" @click="halaman--">‹</button>
        <button class="tombol !h-8 !w-8 !justify-center !px-0" :disabled="halaman >= jumlahHal" @click="halaman++">›</button>
      </div>
    </template>

    <template v-else>
      <Pemutar v-if="muat && !d" class="px-6 pb-4" teks="Memuat rincian..." />
      <template v-else-if="d">
        <div class="flex flex-wrap gap-x-6 gap-y-1 px-6 pb-3 text-xs text-muted tabular-nums">
          <span>{{ baris.length }} trade dipegang</span>
          <span>Total sumbangan <b class="font-medium" :class="kelasUntung(adaFilter ? totalSumb : d.heatmap_pct)">{{ persen(adaFilter ? totalSumb : d.heatmap_pct, 2) }}</b><template v-if="!adaFilter"> = angka peta</template></span>
          <template v-if="ringkasPeriode">
            <span>{{ ringkasPeriode.n }} selesai di periode</span>
            <span>Win rate <b class="font-medium text-ink">{{ persen(ringkasPeriode.wr, 0, false) }}</b></span>
            <span>Rata-rata hasil trade <b class="font-medium" :class="kelasUntung(ringkasPeriode.rata)">{{ persen(ringkasPeriode.rata, 2) }}</b></span>
          </template>
        </div>
        <div class="overflow-x-auto" :class="muat ? 'opacity-60' : ''">
          <table class="tabel min-w-[900px]">
            <thead>
              <tr>
                <th v-for="[k, l, al, sub] in KOLOM_PERIODE" :key="k" class="cursor-pointer select-none align-bottom hover:text-ink" :class="[al ? '!text-right' : '', urutPeriode.kunci === k ? '!text-ink' : '']" @click="urutkanPeriode(k)">
                  {{ l }}<span v-if="urutPeriode.kunci === k" class="ml-0.5">{{ urutPeriode.naik ? "↑" : "↓" }}</span>
                  <div v-if="sub" class="text-[11px] font-normal text-muted">{{ sub }}</div>
                </th>
                <th class="w-28"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in baris" :key="p.ticker + p.tgl_beli + (p.bagian || '')">
                <td><KodeSaham :kode="p.ticker" /></td>
                <td v-if="adaBagian"><span class="chip" :class="p.bagian === 'RS 12-1' ? 'bg-kuning-bg text-ink-2' : 'bg-aksen-lembut text-aksen'">{{ p.bagian }}</span></td>
                <td><span class="chip" :class="kelasBadge(p)">{{ badge(p) }}</span></td>
                <td class="text-ink-2">{{ tanggal(p.tgl_beli) }}</td>
                <td class="text-ink-2">{{ p.terbuka || !p.tgl_jual ? "–" : tanggal(p.tgl_jual) }}</td>
                <td class="text-right tabular-nums">{{ harga(p.harga_awal) }}</td>
                <td class="text-right tabular-nums">{{ harga(p.harga_akhir) }}</td>
                <td class="text-right font-medium tabular-nums" :class="kelasUntung(p.sumbangan_pct)">{{ pct(p.sumbangan_pct) }}</td>
                <td class="text-right tabular-nums" :class="[kelasUntung(p.net), p.terbuka ? 'italic' : '']" :title="p.terbuka ? 'belum dijual: dihitung sampai harga terakhir' : ''">{{ persen(p.net, 2) }}</td>
                <td><div class="h-1.5 rounded-full" :class="p.sumbangan_pct >= 0 ? 'bg-naik/70' : 'bg-turun/70'" :style="{ width: lebar(p.sumbangan_pct) }"></div></td>
              </tr>
              <tr v-if="d.kas_lain_ada && !adaFilter">
                <td class="text-ink-2" :colspan="adaBagian ? 7 : 6">Kas &amp; lain-lain <span class="text-xs text-muted">(biaya, dividen, atau selisih yang tidak menempel ke satu saham)</span></td>
                <td class="text-right font-medium tabular-nums" :class="kelasUntung(d.kas_lain_pct)">{{ pct(d.kas_lain_pct) }}</td>
                <td></td>
                <td><div class="h-1.5 rounded-full" :class="d.kas_lain_pct >= 0 ? 'bg-naik/70' : 'bg-turun/70'" :style="{ width: lebar(d.kas_lain_pct) }"></div></td>
              </tr>
            </tbody>
            <tfoot class="border-t border-garis">
              <tr class="font-medium">
                <td :colspan="adaBagian ? 7 : 6" class="text-ink-2">
                  <template v-if="!adaFilter">Total {{ baris.length }} trade · sama dengan angka peta {{ periode.label }}</template>
                  <template v-else>Total {{ baris.length }} trade yang tampil · angka peta {{ periode.label }} {{ persen(d.heatmap_pct, 2) }}</template>
                </td>
                <td class="text-right tabular-nums" :class="kelasUntung(adaFilter ? totalSumb : d.heatmap_pct)">{{ persen(adaFilter ? totalSumb : d.heatmap_pct, 2) }}</td>
                <td></td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </template>
    </template>
  </Panel>
</template>

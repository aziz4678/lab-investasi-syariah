<script setup>
import { ref, computed, watch } from "vue";
import { Search, RefreshCw, SlidersHorizontal } from "lucide-vue-next";
import { persen, ringkas, kelasPersen } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import Segmen from "@/components/common/Segmen.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import PanelPekerjaan from "@/components/sistem/PanelPekerjaan.vue";
import Logo, { kunciMi } from "@/components/common/Logo.vue";
import LencanaRD from "@/components/produk/LencanaRD.vue";
import TersediaDi from "@/components/produk/TersediaDi.vue";
import KartuRD from "@/components/produk/KartuRD.vue";

const props = defineProps({ daftar: Object, kategori: String, kerja: Object });
const emit = defineEmits(["update:kategori", "muat", "buka", "banding"]);

const KET_KAT = {
  pasar_uang: ["Paling aman. Isinya deposito dan sukuk jangka pendek; nilainya hampir tidak pernah turun.", "Dana darurat, uang yang dipakai kurang dari 1 tahun"],
  pendapatan_tetap: ["Isinya sukuk. Naik-turunnya kecil, tapi bisa turun beberapa persen saat suku bunga naik.", "Tabungan 1–3 tahun"],
  campuran: ["Campuran saham dan sukuk, porsinya diatur manajer investasi.", "Uang yang tidak dipakai 3–5 tahun"],
  saham: ["Isinya saham syariah. Bisa naik besar, bisa turun lebih dari separuh.", "Uang yang tidak dipakai 5 tahun atau lebih"],
  indeks: ["Mengikuti indeks saham syariah (misalnya JII) dengan biaya biasanya lebih rendah.", "Uang yang tidak dipakai 5 tahun atau lebih"],
  etf: ["ETF diperdagangkan di bursa seperti saham; lihat menu ETF.", "Lihat menu ETF"],
  global: ["Berinvestasi di saham luar negeri, umumnya dalam dolar AS. Nilainya ikut naik-turun dengan kurs.", "Jangka panjang, siap dengan risiko kurs"],
  terproteksi: ["Pokok dilindungi sampai jatuh tempo, tapi tidak bisa dicairkan sewaktu-waktu.", "Uang yang pasti tidak dipakai sampai jatuh tempo"],
  penyertaan_terbatas: ["Khusus investor besar (minimal biasanya miliaran rupiah).", "Investor profesional"],
};
const cari = ref("");
const lengkap = ref(false);
const hanyaPlatform = ref(false);
const urut = ref({ kolom: "urut", turun: false });
const semua = ref(false);
watch(() => props.kategori, () => {
  semua.value = false;
  urut.value = { kolom: "urut", turun: false };
});

const data = computed(() => props.daftar?.data || []);
const kategoriList = computed(() => {
  const ada = new Set(data.value.map((r) => r.kategori));
  return Object.entries(props.daftar?.label || {}).filter(([k]) => ada.has(k) && k !== "etf");
});
const jumlahKat = computed(() => data.value.filter((r) => r.kategori === props.kategori).length);
const tersaring = computed(() => {
  const q = cari.value.trim().toLowerCase();
  let x = data.value.filter((r) => (q ? `${r.nama} ${r.mi}`.toLowerCase().includes(q) : r.kategori === props.kategori));
  if (hanyaPlatform.value) x = x.filter((r) => r.platform?.length);
  const { kolom, turun } = urut.value;
  const nilai = (r) => (kolom === "urut" ? (r.mata_uang === "USD" ? 1000 : 0) + (r.urut ?? 999) : kolom === "platform" ? r.platform?.length || 0 : r[kolom]);
  return [...x].sort((a, b) => {
    const va = nilai(a), vb = nilai(b);
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;
    const c = typeof va === "string" ? va.localeCompare(vb) : va - vb;
    return turun ? -c : c;
  });
});
const tampil = computed(() => (semua.value ? tersaring.value : tersaring.value.slice(0, 20)));
function ganti(k) {
  urut.value = urut.value.kolom === k ? { kolom: k, turun: !urut.value.turun } : { kolom: k, turun: !["biaya", "nama", "urut"].includes(k) };
}
const KOLOM = computed(() => [
  ["urut", "#", 1, "Urutan dari jumlah lencana, lalu peringatan paling sedikit, lalu hasil 3 tahun"],
  ["nama", "Reksa dana", 0, ""],
  ["cagr_3", "Rata-rata/th (3 th)", 1, "Hasil rata-rata per tahun selama 3 tahun terakhir, setelah biaya"],
  ["turun_terburuk", "Turun terburuk", 1, "Penurunan terdalam dari titik tertinggi sepanjang riwayat (per akhir bulan)"],
  ["biaya", "Biaya/th", 1, "Biaya pengelolaan per tahun; sudah dipotong dari harga unit"],
  ...(lengkap.value ? [["ret_1th", "Hasil 1 th", 1, "Hasil 12 bulan terakhir"], ["aum", "Dana kelolaan", 1, "Total uang investor di produk ini"], ["risiko", "Risiko", 1, "Tingkat risiko 1 (rendah) – 9 (tinggi) dari prospektus"], ["tahun_data", "Data", 1, "Panjang riwayat harga"]] : []),
  ["platform", "Tersedia di", 0, "Ditemukan di katalog Bibit, Ajaib, atau Makmur"],
]);
const uangRD = (r) => (r.aum == null ? "–" : `${r.mata_uang === "USD" ? "US$" : "Rp"}${ringkas(r.aum)}`);
const waktuData = computed(() => (props.daftar?.info?.diperbarui ? new Date(props.daftar.info.diperbarui).toLocaleString("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "–"));
</script>

<template>
  <div class="space-y-5">
    <template v-if="!daftar">
      <Kerangka panel :n="2" />
      <Kerangka panel jenis="tabel" :n="8" logo />
    </template>
    <template v-else>
      <div class="panel px-6 py-5">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div class="text-[15px] font-medium">Jenis reksa dana</div>
          <div class="relative w-full sm:w-72">
            <Search class="pointer-events-none absolute top-1/2 left-3.5 h-4 w-4 -translate-y-1/2 text-muted" />
            <input v-model="cari" class="!h-9 w-full !border !border-garis !bg-surface !pl-9 text-[13px]" placeholder="Cari nama produk atau manajer investasi" />
          </div>
        </div>
        <Segmen :model-value="kategori" :pilihan="kategoriList" @update:model-value="(v) => { cari = ''; emit('update:kategori', v); }" />
        <div v-if="!cari && KET_KAT[kategori]" class="mt-4 rounded-2xl bg-surface-2 px-5 py-3.5 text-[13px]">
          <span class="text-ink-2">{{ KET_KAT[kategori][0] }}</span>
          <span class="text-muted"> Cocok untuk: {{ KET_KAT[kategori][1] }}.</span>
        </div>
      </div>

      <Panel :judul="cari ? `Hasil pencarian “${cari}”` : `${jumlahKat} ${daftar.label?.[kategori]?.toLowerCase() || 'reksa dana'}`"
        :ket="`Klik produk untuk detail · data per ${waktuData}`" rapat>
        <template #aksi>
          <button class="tombol" :disabled="kerja.sibuk.value" @click="kerja.mulai('aksi/rd_perbarui', {}, () => emit('muat'))"><RefreshCw class="h-3.5 w-3.5" :class="kerja.sibuk.value ? 'animate-spin' : ''" />Perbarui</button>
        </template>
        <PanelPekerjaan class="mx-6 mb-3" :kerja="kerja.kerja.value" :galat="kerja.galat.value" />
        <div class="flex flex-wrap items-center gap-x-5 gap-y-2 px-6 pb-3 text-[13px] text-ink-2">
          <label class="flex items-center gap-2"><input v-model="hanyaPlatform" type="checkbox" class="h-4 w-4" />Hanya yang ada di Bibit / Ajaib / Makmur</label>
          <label class="hidden items-center gap-2 md:flex"><input v-model="lengkap" type="checkbox" class="h-4 w-4" /><SlidersHorizontal class="h-3.5 w-3.5" />Tampilkan kolom lengkap</label>
        </div>

        <div class="hidden overflow-x-auto md:block">
          <table class="tabel" :class="lengkap ? 'min-w-[1180px]' : 'min-w-[900px]'">
            <thead>
              <tr>
                <th v-for="[k, l, kanan, ket] in KOLOM" :key="k" class="cursor-pointer select-none hover:text-ink" :class="kanan ? '!text-right' : ''" :title="ket" @click="ganti(k)">
                  {{ l }}<span v-if="urut.kolom === k" class="ml-0.5">{{ urut.turun ? "↓" : "↑" }}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in tampil" :key="r.id" class="cursor-pointer hover:bg-surface-2/50" @click="emit('buka', r.id)">
                <td class="w-10 text-right text-xs text-muted tabular-nums">{{ r.urut ?? "–" }}</td>
                <td class="!h-auto max-w-[360px] py-2.5">
                  <div class="flex items-center gap-3">
                    <Logo jenis="mi" :kunci="kunciMi(r.mi)" :teks="r.mi" :ukuran="32" />
                    <div class="min-w-0">
                      <div class="truncate font-medium">{{ r.nama }}</div>
                      <div class="truncate text-[11px] text-muted">{{ r.mi }}<template v-if="cari"> · {{ r.kategori_label }}</template><template v-if="r.mata_uang === 'USD'"> · USD</template></div>
                      <LencanaRD class="mt-1" :lencana="r.lencana" :peringatan="r.peringatan" kecil />
                    </div>
                  </div>
                </td>
                <td class="text-right">
                  <span v-if="r.cagr_3 != null" class="font-medium" :class="kelasPersen(r.cagr_3)">{{ persen(r.cagr_3, 1) }}</span>
                  <span v-else class="text-xs text-muted" :title="r.ret_1th != null ? `Hasil 12 bulan terakhir ${persen(r.ret_1th, 1)}` : ''">data &lt; 3 th</span>
                </td>
                <td class="text-right tabular-nums" :class="r.turun_terburuk < -0.05 ? 'text-turun' : 'text-ink-2'">{{ r.turun_terburuk == null ? "–" : Math.abs(r.turun_terburuk) < 0.05 ? "0,0%" : persen(r.turun_terburuk, 1) }}</td>
                <td class="text-right text-ink-2">{{ r.biaya == null ? "–" : persen(r.biaya, 2, false) }}</td>
                <template v-if="lengkap">
                  <td class="text-right" :class="kelasPersen(r.ret_1th)">{{ r.ret_1th == null ? "–" : persen(r.ret_1th, 1) }}</td>
                  <td class="text-right tabular-nums">{{ uangRD(r) }}</td>
                  <td class="text-right text-ink-2">{{ r.risiko == null ? "–" : `${Math.round(r.risiko)}/9` }}</td>
                  <td class="text-right text-ink-2">{{ r.tahun_data == null ? "–" : `${String(r.tahun_data).replace(".", ",")} th` }}</td>
                </template>
                <td><TersediaDi :platform="r.platform" kecil /></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="grid gap-3 px-4 pb-2 md:hidden">
          <KartuRD v-for="r in tampil" :key="r.id" :r="r" @buka="emit('buka', $event)" @banding="emit('banding', $event)" />
        </div>
        <p v-if="!tersaring.length" class="m-0 px-6 py-4 text-[13px] text-muted">Tidak ada produk yang cocok.</p>
        <button v-if="tersaring.length > 20" class="mx-6 my-3 text-xs text-muted hover:underline" @click="semua = !semua">{{ semua ? "Tampilkan 20 teratas" : `Tampilkan seluruh ${tersaring.length} produk` }}</button>
      </Panel>
    </template>
  </div>
</template>

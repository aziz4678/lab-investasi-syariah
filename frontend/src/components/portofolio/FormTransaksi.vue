<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { Search, Star } from "lucide-vue-next";
import { ambil } from "@/api/client";
import Segmen from "@/components/common/Segmen.vue";
import { rupiahRingkas } from "@/utils/format";

const props = defineProps({
  portofolioId: { type: String, default: "" },
  aplikasi: { type: Array, default: () => [] },
  feeDefault: { type: Object, default: () => ({}) },
  nilaiAwal: { type: Object, default: null },
  menyimpan: Boolean,
  galat: { type: String, default: "" },
});
const emit = defineEmits(["simpan", "batal"]);

const hariIni = () => {
  const t = new Date();
  return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
};
const PILIHAN_JENIS = [["beli", "Beli"], ["jual", "Jual"]];
const KELOMPOK = { rd: "Reksa dana", etf: "ETF", saham: "Saham" };

const tanggal = ref(hariIni());
const jenis = ref("beli");
const produk = ref(null);
const cari = ref("");
const hasil = ref([]);
const apl = ref("Bibit");
const nominal = ref("");
const lot = ref("");
const harga = ref("");
const biaya = ref("");
const biayaManual = ref(false);
const catatan = ref("");
const idUbah = ref(null);

const angka = (s) => Number(String(s ?? "").replace(/[^\d.,]/g, "").replace(/\./g, "").replace(",", ".")) || 0;
const tampil = (v) => (v === "" || v == null ? "" : Number(v).toLocaleString("id-ID"));
const pasarLot = computed(() => produk.value && produk.value.tipe_produk !== "rd");

const muatProduk = async () => {
  hasil.value = await ambil(`portofolio-saya/produk?q=${encodeURIComponent(cari.value)}`).catch(() => []);
};
let jeda = null;
watch(cari, () => {
  clearTimeout(jeda);
  jeda = setTimeout(muatProduk, 250);
});
onMounted(muatProduk);

const pilih = (p) => {
  produk.value = p;
  cari.value = "";
  if (p.tipe_produk !== "rd" && ["Bibit", "Makmur"].includes(apl.value)) apl.value = "Stockbit";
};

const dasarNilai = computed(() => (pasarLot.value ? angka(lot.value) * 100 * angka(harga.value) : 0));
const feeApl = computed(() => (pasarLot.value ? props.feeDefault[apl.value] ?? 0 : 0));
watch([dasarNilai, feeApl, pasarLot], () => {
  if (pasarLot.value && !biayaManual.value) biaya.value = dasarNilai.value ? String(Math.round(dasarNilai.value * feeApl.value)) : "";
});
const nominalHitung = computed(() => {
  if (pasarLot.value) {
    if (!dasarNilai.value) return 0;
    const b = angka(biaya.value);
    return jenis.value === "beli" ? dasarNilai.value + b : dasarNilai.value - b;
  }
  return angka(nominal.value);
});

watch(() => props.nilaiAwal, (x) => {
  if (!x) return;
  idUbah.value = x._id ?? null;
  tanggal.value = x.tanggal ?? hariIni();
  jenis.value = x.jenis ?? "beli";
  produk.value = x.produk ? { tipe_produk: x.tipe_produk, produk: x.produk, nama: x.nama ?? x.produk } : null;
  apl.value = x.aplikasi ?? "Bibit";
  nominal.value = x.nominal != null && x.tipe_produk === "rd" ? String(Math.round(x.nominal)) : "";
  lot.value = x.lot != null ? String(x.lot) : x.unit && x.tipe_produk !== "rd" ? String(x.unit / 100) : "";
  harga.value = x.harga != null ? String(x.harga) : "";
  biaya.value = x.biaya != null ? String(x.biaya) : "";
  biayaManual.value = true;
  catatan.value = x.catatan ?? "";
}, { immediate: true });

const kosongkan = () => {
  idUbah.value = null;
  produk.value = null;
  nominal.value = "";
  lot.value = "";
  harga.value = "";
  biaya.value = "";
  biayaManual.value = false;
  catatan.value = "";
  tanggal.value = hariIni();
};
const batal = () => {
  kosongkan();
  emit("batal");
};
const bisa = computed(() => !!props.portofolioId && !!produk.value && nominalHitung.value > 0 && !!tanggal.value);
const simpan = () => {
  if (!bisa.value) return;
  const p = produk.value;
  emit("simpan", {
    id: idUbah.value,
    data: {
      portofolio_id: props.portofolioId, tanggal: tanggal.value, jenis: jenis.value, tipe_produk: p.tipe_produk, produk: p.produk, nama: p.nama, aplikasi: apl.value,
      nominal: nominalHitung.value, lot: pasarLot.value ? angka(lot.value) || null : null, harga: pasarLot.value ? angka(harga.value) || null : null, biaya: angka(biaya.value), catatan: catatan.value,
    },
    selesai: kosongkan,
  });
};
defineExpose({ kosongkan });
</script>

<template>
  <form class="space-y-4" @submit.prevent="simpan">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div class="text-[14px] font-medium">{{ idUbah ? "Ubah transaksi" : "Catat transaksi" }}</div>
      <Segmen v-model="jenis" :pilihan="PILIHAN_JENIS" kecil />
    </div>

    <div>
      <label class="text-xs text-muted">Produk</label>
      <div v-if="produk" class="mt-1 flex items-center justify-between gap-2 rounded-2xl bg-surface-2 px-4 py-2.5 text-[13px]">
        <span class="min-w-0"><span class="chip mr-1.5 bg-aksen-lembut text-aksen">{{ KELOMPOK[produk.tipe_produk] }}</span>{{ produk.nama }}</span>
        <button type="button" class="shrink-0 text-[12px] text-aksen" @click="produk = null">ganti</button>
      </div>
      <template v-else>
        <div class="mt-1 flex items-center rounded-full bg-surface-2 px-4"><Search class="h-4 w-4 shrink-0 text-muted" />
          <input v-model="cari" placeholder="Cari reksa dana, ETF, atau kode saham" class="h-10 w-full min-w-0 bg-transparent px-2 text-[14px] outline-none" /></div>
        <ul class="m-0 mt-2 max-h-56 list-none overflow-y-auto rounded-2xl border border-garis p-0">
          <li v-for="p in hasil" :key="`${p.tipe_produk}-${p.produk}`">
            <button type="button" class="flex w-full items-center gap-2 px-4 py-2 text-left text-[13px] hover:bg-surface-2" @click="pilih(p)">
              <Star v-if="p.prioritas" class="h-3.5 w-3.5 shrink-0 text-kuning" />
              <span class="min-w-0 flex-1 truncate">{{ p.nama }}</span>
              <span class="shrink-0 text-[11px] text-muted">{{ KELOMPOK[p.tipe_produk] }}<template v-if="p.mata_uang === 'USD'"> · USD</template></span>
            </button>
          </li>
          <li v-if="!hasil.length" class="px-4 py-3 text-[12px] text-muted">Tidak ada produk yang cocok.</li>
        </ul>
        <div class="mt-1 text-[11px] text-muted">Bintang = produk di daftar belanja Pertumbuhan.</div>
      </template>
    </div>

    <div class="grid gap-4 sm:grid-cols-3">
      <div class="min-w-0">
        <label class="text-xs text-muted">Tanggal</label>
        <input v-model="tanggal" type="date" class="mt-1 h-10 w-full rounded-full bg-surface-2 px-4 text-[14px] outline-none" />
      </div>
      <div class="min-w-0">
        <label class="text-xs text-muted">Aplikasi</label>
        <select v-model="apl" class="mt-1 h-10 w-full rounded-full bg-surface-2 px-4 text-[14px] outline-none">
          <option v-for="a in aplikasi" :key="a" :value="a">{{ a }}</option>
        </select>
      </div>
      <div v-if="!pasarLot" class="min-w-0">
        <label class="text-xs text-muted">Nominal yang keluar</label>
        <div class="mt-1 flex items-center rounded-full bg-surface-2 px-4"><span class="text-[13px] text-muted">Rp</span>
          <input :value="tampil(nominal)" inputmode="numeric" placeholder="0" class="h-10 w-full min-w-0 bg-transparent px-2 text-[14px] outline-none" @input="(e) => (nominal = String(angka(e.target.value)))" /></div>
      </div>
      <template v-else>
        <div class="min-w-0">
          <label class="text-xs text-muted">Jumlah lot (1 lot = 100 unit)</label>
          <input v-model="lot" inputmode="numeric" placeholder="0" class="mt-1 h-10 w-full rounded-full bg-surface-2 px-4 text-[14px] outline-none" />
        </div>
      </template>
    </div>

    <div v-if="pasarLot" class="grid gap-4 sm:grid-cols-3">
      <div class="min-w-0">
        <label class="text-xs text-muted">Harga per unit</label>
        <div class="mt-1 flex items-center rounded-full bg-surface-2 px-4"><span class="text-[13px] text-muted">Rp</span>
          <input v-model="harga" inputmode="decimal" placeholder="0" class="h-10 w-full min-w-0 bg-transparent px-2 text-[14px] outline-none" /></div>
      </div>
      <div class="min-w-0 sm:col-span-2">
        <label class="text-xs text-muted">Total {{ jenis === "beli" ? "yang keluar" : "yang diterima" }} (dihitung)</label>
        <div class="mt-1 flex h-10 items-center rounded-full bg-surface-2 px-4 text-[14px] tabular-nums">{{ nominalHitung ? `Rp${Math.round(nominalHitung).toLocaleString("id-ID")}` : "–" }}</div>
      </div>
    </div>

    <div class="grid gap-4 sm:grid-cols-3">
      <div class="min-w-0">
        <label class="text-xs text-muted">Biaya</label>
        <div class="mt-1 flex items-center rounded-full bg-surface-2 px-4"><span class="text-[13px] text-muted">Rp</span>
          <input :value="tampil(biaya)" inputmode="numeric" placeholder="0" class="h-10 w-full min-w-0 bg-transparent px-2 text-[14px] outline-none" @input="(e) => { biayaManual = true; biaya = String(angka(e.target.value)); }" /></div>
        <div class="mt-1 text-[11px] text-muted">{{ pasarLot && feeApl ? `otomatis ${(feeApl * 100).toLocaleString("id-ID")}% (${apl}); ubah kalau beda` : "isi 0 kalau tidak ada biaya" }}</div>
      </div>
      <div class="min-w-0 sm:col-span-2">
        <label class="text-xs text-muted">Catatan (opsional)</label>
        <input v-model="catatan" maxlength="500" class="mt-1 h-10 w-full rounded-full bg-surface-2 px-4 text-[14px] outline-none" />
      </div>
    </div>

    <p v-if="!pasarLot && produk" class="m-0 text-[11px] leading-relaxed text-muted">Jumlah unit dihitung otomatis dari (nominal − biaya) ÷ NAV tanggal itu. Kalau NAV belum terbit, transaksi tampil "menunggu NAV" dan terisi sendiri nanti.</p>
    <p v-if="galat" class="m-0 rounded-2xl bg-turun-bg px-4 py-2 text-[13px] text-turun">{{ galat }}</p>
    <div class="flex flex-wrap items-center gap-2">
      <button type="submit" class="tombol" :disabled="!bisa || menyimpan">{{ idUbah ? "Simpan perubahan" : "Simpan transaksi" }}<template v-if="nominalHitung"> · {{ rupiahRingkas(nominalHitung) }}</template></button>
      <button v-if="idUbah" type="button" class="tombol" @click="batal">Batal ubah</button>
    </div>
  </form>
</template>

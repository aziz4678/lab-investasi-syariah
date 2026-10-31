<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { ambil } from "@/api/client";
import { pakaiPekerjaan } from "@/composables/pekerjaan";
import HeaderStrategi from "@/components/common/HeaderStrategi.vue";
import ProdukRD from "@/components/produk/ProdukRD.vue";
import MulaiTab from "@/views/produk/reksadana/MulaiTab.vue";
import KatalogTab from "@/views/produk/reksadana/KatalogTab.vue";
import BandingTab from "@/views/produk/reksadana/BandingTab.vue";
import SukukTab from "@/views/produk/reksadana/SukukTab.vue";
import CaraKerjaTab from "@/views/produk/reksadana/CaraKerjaTab.vue";

const props = defineProps({ sub: String });
const emit = defineEmits(["sub"]);
const SUB = [["mulai", "Mulai di sini"], ["katalog", "Reksa Dana"], ["sukuk", "Sukuk & SBN"], ["banding", "Bandingkan"], ["data", "Cara kerja & istilah"]];
const MAKS_BANDING = 5;

const baca = (k, awal) => {
  try {
    const v = localStorage.getItem(k);
    return v == null ? awal : JSON.parse(v);
  } catch {
    return awal;
  }
};
const simpan = (k, v) => {
  try {
    localStorage.setItem(k, JSON.stringify(v));
  } catch {
    return;
  }
};

const daftar = ref(null);
const mulaiData = ref(null);
const pilih = ref(location.hash.startsWith("#reksadana/katalog/") ? Number(location.hash.split("/")[2]) || null : null);
const kategoriKatalog = ref(baca("rd_kategori", "pasar_uang"));
const kunciBanding = ref(0);
const kerjaRd = pakaiPekerjaan();

async function muat() {
  [daftar.value, mulaiData.value] = await Promise.all([ambil("rd/daftar").catch(() => null), ambil("rd/mulai").catch(() => null)]);
}
onMounted(async () => {
  await muat();
  await kerjaRd.lanjutkan("rd_perbarui", muat);
});
watch(pilih, (id) => history.replaceState(null, "", id ? `#reksadana/katalog/${id}` : `#reksadana/${props.sub}`));
watch(kategoriKatalog, (v) => simpan("rd_kategori", v));

const info = computed(() => daftar.value?.info);
function buka(id) {
  pilih.value = id;
  window.scrollTo({ top: 0 });
}
function keKatalog(kategori) {
  if (kategori) kategoriKatalog.value = kategori;
  pilih.value = null;
  emit("sub", "katalog");
  window.scrollTo({ top: 0 });
}
function keBanding(id) {
  const k = `rd:${id}`;
  const lama = baca("rd_banding", ["x:deposito"]);
  const baru = lama.includes(k) ? lama : lama.length < MAKS_BANDING ? [...lama, k] : [...lama.slice(0, MAKS_BANDING - 1), k];
  simpan("rd_banding", baru);
  kunciBanding.value += 1;
  pilih.value = null;
  emit("sub", "banding");
  window.scrollTo({ top: 0 });
}
function gantiSub(s) {
  pilih.value = null;
  emit("sub", s);
}
</script>

<template>
  <div class="space-y-5">
    <HeaderStrategi judul="Reksa Dana & Sukuk Syariah" :sub="sub" :pilihan="SUB" @sub="gantiSub"
      ringkas="Reksa dana = uang banyak orang dikumpulkan lalu dikelola manajer investasi profesional, diawasi OJK. Di sini kamu bisa memilih sesuai tujuan, membandingkan, dan melihat bisa membelinya di aplikasi mana."
      :chip="[{ teks: `${info?.produk ?? '…'} reksa dana syariah`, kelas: 'bg-aksen-lembut text-aksen' }, { teks: `${info?.sukuk ?? '…'} sukuk`, kelas: 'bg-surface-2 text-ink-2' }, { teks: info?.ojk ? `Riwayat sejak ${info.ojk.dari.slice(0, 4)} (OJK)` : 'Riwayat ±1 tahun', kelas: 'bg-surface-2 text-ink-2' }]" />

    <ProdukRD v-if="pilih" :id="pilih" @kembali="pilih = null" @banding="keBanding" />
    <MulaiTab v-else-if="sub === 'mulai'" :m="mulaiData" :data="daftar?.data" @buka="buka" @banding="keBanding" @katalog="keKatalog" @sukuk="gantiSub('sukuk')" @cara="gantiSub('data')" />
    <KatalogTab v-else-if="sub === 'katalog'" v-model:kategori="kategoriKatalog" :daftar="daftar" :kerja="kerjaRd" @muat="muat" @buka="buka" @banding="keBanding" />
    <BandingTab v-else-if="sub === 'banding'" :key="kunciBanding" />
    <SukukTab v-else-if="sub === 'sukuk'" />
    <CaraKerjaTab v-else :daftar="daftar" :m="mulaiData" />
  </div>
</template>

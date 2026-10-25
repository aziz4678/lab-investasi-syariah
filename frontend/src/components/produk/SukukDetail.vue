<script setup>
import { ref, watch } from "vue";
import { ArrowLeft } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { persen } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import Logo from "@/components/common/Logo.vue";
import GrafikRentang from "@/components/charts/GrafikRentang.vue";
import SimulasiSukuk from "@/components/produk/SimulasiSukuk.vue";

const props = defineProps({ x: Object, ket: String });
const emit = defineEmits(["kembali"]);
const riwayat = ref(null);
const NEGARA = ["SR", "PBS", "SPNS", "Negara lain"];

watch(() => props.x?.kode, async (k) => {
  riwayat.value = null;
  if (k) riwayat.value = await ambil(`rd/sukuk/${k}`).catch(() => ({ tgl: [], harga: [] }));
}, { immediate: true });

const tglPanjang = (t) => (t ? new Date(t).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" }) : "–");
const angka = (v) => (v == null ? "–" : v.toLocaleString("id-ID", { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
</script>

<template>
  <div class="space-y-5">
    <button class="tombol" @click="emit('kembali')"><ArrowLeft class="h-3.5 w-3.5" />Kembali ke daftar sukuk</button>
    <div class="panel px-6 py-5">
      <div class="flex items-start gap-4">
        <Logo :jenis="NEGARA.includes(x.jenis) ? 'negara' : 'emiten'" :kunci="NEGARA.includes(x.jenis) ? 'kemenkeu' : x.penerbit" :teks="x.penerbit" :ukuran="48" />
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-[18px] font-medium">{{ x.kode }}</span>
            <span class="chip bg-naik-bg text-naik">Syariah</span>
            <span class="chip bg-surface-2 text-ink-2">{{ x.jenis }}</span>
            <span v-if="NEGARA.slice(0, 3).includes(x.jenis)" class="chip bg-surface-2 text-ink-2">dijamin negara</span>
            <span v-else-if="x.rating" class="chip bg-surface-2 text-ink-2">rating {{ x.rating }}</span>
          </div>
          <div class="mt-1 text-[13px] text-ink-2">{{ x.nama }} · penerbit {{ x.penerbit }}</div>
        </div>
      </div>
      <p v-if="ket" class="m-0 mt-4 rounded-2xl bg-surface-2 px-4 py-3 text-[13px] leading-relaxed text-ink-2">{{ ket }}</p>
      <div class="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
        <div class="rounded-2xl border border-garis px-4 py-3"><div class="text-xs text-muted">Kupon per tahun</div><div class="mt-0.5 text-[17px] font-medium">{{ x.kupon == null ? "–" : persen(x.kupon * 100, 2, false) }}</div><div class="text-[11px] text-muted">{{ x.jenis_kupon === "Fixed" ? "tetap" : x.jenis_kupon || "" }}</div></div>
        <div class="rounded-2xl border border-garis px-4 py-3"><div class="text-xs text-muted">Yield</div><div class="mt-0.5 text-[17px] font-medium">{{ x.ytm == null ? "–" : persen(x.ytm * 100, 2, false) }}</div><div class="text-[11px] text-muted">kalau dibeli sekarang & ditahan</div></div>
        <div class="rounded-2xl border border-garis px-4 py-3"><div class="text-xs text-muted">Harga</div><div class="mt-0.5 text-[17px] font-medium">{{ angka(x.harga) }}</div><div class="text-[11px] text-muted">% dari nilai pokok</div></div>
        <div class="rounded-2xl border border-garis px-4 py-3"><div class="text-xs text-muted">Jatuh tempo</div><div class="mt-0.5 text-[15px] font-medium">{{ tglPanjang(x.jatuh_tempo) }}</div><div class="text-[11px] text-muted">{{ x.sisa_tahun == null ? "" : `${x.sisa_tahun.toLocaleString("id-ID", { maximumFractionDigits: 1 })} tahun lagi` }}</div></div>
        <div class="rounded-2xl border border-garis px-4 py-3"><div class="text-xs text-muted">Kepekaan harga</div><div class="mt-0.5 text-[17px] font-medium">{{ x.durasi == null ? "–" : x.durasi.toLocaleString("id-ID", { maximumFractionDigits: 1 }) }}</div><div class="text-[11px] text-muted">turun ±{{ x.durasi == null ? "–" : x.durasi.toLocaleString("id-ID", { maximumFractionDigits: 1 }) }}% kalau bunga naik 1%</div></div>
      </div>
    </div>

    <Panel judul="Harga" :ket="`Harga dalam % dari nilai pokok (100 = harga awal) · geser kursor untuk melihat harga per tanggal`">
      <Kerangka v-if="!riwayat" jenis="grafik" :tinggi="260" />
      <GrafikRentang v-else-if="riwayat.tgl.length >= 2" :tgl="riwayat.tgl" :harga="riwayat.harga" :nama="x.kode" awal="ALL" :format="angka" />
      <p v-else class="m-0 rounded-2xl bg-surface-2 px-4 py-3 text-[13px] leading-relaxed text-ink-2">
        Riwayat harga sukuk baru mulai dicatat {{ riwayat.tgl.length ? tglPanjang(riwayat.tgl[0]) : "hari ini" }}. Sumber gratis (Pasardana) hanya memberi harga terakhir; riwayatnya dikunci untuk pengguna login. Harga disimpan otomatis tiap hari bursa (jadwal 17:30), jadi grafik muncul setelah ada minimal 2 hari data dan makin panjang dari waktu ke waktu.
      </p>
    </Panel>

    <SimulasiSukuk :x="x" />
  </div>
</template>

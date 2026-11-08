<script setup>
import { ref, computed, onMounted } from "vue";
import { RefreshCw } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { persen, ringkas } from "@/utils/format";
import { pakaiPekerjaan } from "@/composables/pekerjaan";
import Panel from "@/components/common/Panel.vue";
import PanelPekerjaan from "@/components/sistem/PanelPekerjaan.vue";

const LABEL = { "1b": "1 bln", "3b": "3 bln", "6b": "6 bln", ytd: "Sejak Jan", "1t": "1 th", "3t": "3 th", "5t": "5 th", "10t": "10 th" };
const h = ref(null);
const siap = ref(false);
const { kerja, galat, mulai } = pakaiPekerjaan();
const muat = async () => {
  h.value = await ambil("rd/cek_platform").catch(() => null);
  siap.value = true;
};
onMounted(muat);
const jalankan = () => mulai("aksi/rd_cek_platform", {}, muat);
const sibuk = computed(() => kerja.value?.status === "berjalan");
const sel = (v) => (v == null ? "–" : `${v > 0 ? "+" : ""}${v.toFixed(2).replace(".", ",")}`);
const tgl = (s) => (s ? new Date(s).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }) : "–");
const waktu = (s) => (s ? new Date(s).toLocaleString("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "");
const lolos = computed(() => (h.value?.baris || []).flatMap((b) => b.jendela || []));
</script>

<template>
  <Panel judul="Cek silang dengan aplikasi" :ket="h?.dibuat ? `Terakhir ${waktu(h.dibuat)} · ${h.baris?.length || 0} produk dari ${h.berkas}` : 'Bandingkan angka halaman ini dengan angka yang kamu catat dari aplikasi'">
    <template #aksi>
      <button class="tombol" :disabled="sibuk" @click="jalankan"><RefreshCw class="h-3.5 w-3.5" :class="sibuk ? 'animate-spin' : ''" />Cek ulang</button>
    </template>
    <p class="m-0 mb-3 text-[13px] text-ink-2">Isi <b class="font-medium text-ink">data/cek_silang_platform.csv</b> dengan angka dari Bibit/Ajaib/Makmur (satu baris per produk, persen tanpa tanda %), lalu tekan Cek ulang. Toleransi: ±0,10 poin untuk 1 bulan sampai 1 tahun, ±0,30 poin untuk 3 sampai 10 tahun. "Sebelum" = cara hitung lama (snapshot {{ tgl(h?.sebelum_dibuat) }}).</p>
    <PanelPekerjaan :kerja="kerja" :galat="galat" />
    <p v-if="siap && !h?.baris" class="m-0 text-[13px] text-muted">Belum pernah dijalankan.</p>
    <div v-if="h?.baris?.length" class="space-y-4">
      <div class="flex flex-wrap gap-2 text-xs">
        <span class="chip bg-surface-2 text-ink-2">{{ lolos.filter((j) => j.lolos).length }} dari {{ lolos.length }} angka dalam toleransi</span>
        <span v-if="h.periksa?.length" class="chip bg-kuning-bg text-kuning">{{ h.periksa.length }} perlu diperiksa</span>
      </div>
      <div v-for="b in h.baris" :key="b.id || b.nama" class="rounded-2xl bg-surface-2 px-4 py-3">
        <div class="text-[13px] font-medium">{{ b.nama }}<span v-if="b.platform" class="font-normal text-muted"> · {{ b.platform }}</span></div>
        <p v-if="b.galat" class="m-0 mt-1 text-xs text-turun">{{ b.galat }}</p>
        <template v-else>
          <div class="mt-1 text-xs text-ink-2">
            NAV aplikasi {{ b.nav.sesudah }} ({{ tgl(b.nav.tgl_sesudah) }}) · platform {{ b.nav.platform ?? "–" }} ({{ tgl(b.nav.tgl_platform) }})
            <span :class="b.nav.sama_tgl ? 'text-naik' : 'text-kuning'"> · {{ b.nav.sama_tgl ? "tanggal sama" : "tanggal beda" }}</span>
            <span class="text-muted"> · sebelum: {{ b.nav.sebelum }} ({{ tgl(b.nav.tgl_sebelum) }})</span>
          </div>
          <div class="mt-2 overflow-x-auto">
            <table class="tabel w-full text-xs">
              <thead><tr><th>Periode</th><th class="!text-right">Platform</th><th class="!text-right">Sebelum</th><th class="!text-right">Selisih</th><th class="!text-right">Sesudah</th><th class="!text-right">Selisih</th><th></th></tr></thead>
              <tbody>
                <tr v-for="j in b.jendela" :key="j.k">
                  <td class="text-ink-2">{{ LABEL[j.k] }}</td>
                  <td class="text-right tabular-nums">{{ persen(j.platform, 2) }}</td>
                  <td class="text-right tabular-nums text-muted">{{ j.sebelum == null ? "–" : persen(j.sebelum, 2) }}</td>
                  <td class="text-right tabular-nums text-muted">{{ sel(j.selisih_sebelum) }}</td>
                  <td class="text-right tabular-nums">{{ j.kira ? "≈ " : "" }}{{ j.sesudah == null ? "–" : persen(j.sesudah, 2) }}</td>
                  <td class="text-right font-medium tabular-nums" :class="j.lolos ? 'text-naik' : 'text-kuning'">{{ sel(j.selisih_sesudah) }}</td>
                  <td class="text-right" :class="j.lolos ? 'text-naik' : 'text-kuning'">{{ j.lolos ? "ok" : "periksa" }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="b.aum" class="mt-2 text-xs text-ink-2">
            AUM platform {{ ringkas(b.aum.platform) }} · aplikasi kelas ini {{ ringkas(b.aum.kelas) }} ({{ sel(b.aum.selisih_kelas_pct) }}%)<template v-if="b.aum.semua_kelas"> · semua kelas {{ ringkas(b.aum.semua_kelas) }} ({{ sel(b.aum.selisih_total_pct) }}%)</template> · per {{ tgl(b.aum.tgl) }}
          </div>
        </template>
      </div>
      <div v-if="h.periksa?.length">
        <div class="mb-1.5 text-xs font-medium text-kuning">Daftar periksa</div>
        <ul class="m-0 list-disc space-y-1 pl-5 text-xs text-ink-2">
          <li v-for="(x, i) in h.periksa" :key="i"><b class="font-medium text-ink">{{ x.nama }}, {{ LABEL[x.jendela] }}</b>: selisih {{ sel(x.selisih) }} poin. {{ x.dugaan }}.</li>
        </ul>
      </div>
    </div>
  </Panel>
</template>

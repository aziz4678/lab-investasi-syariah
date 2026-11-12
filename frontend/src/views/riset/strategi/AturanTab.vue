<script setup>
import { ref, computed, onMounted } from "vue";
import { RotateCcw } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { tanggal } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import Kerangka from "@/components/common/Kerangka.vue";

defineProps({ s: Object });
const catatan = ref([]);
onMounted(async () => {
  const r = await ambil("paper/ringkasan").catch(() => null);
  catatan.value = r?.catatan || [];
});
const kalimatSplit = computed(() => catatan.value.map((c) => `${c.ticker} melewati split/bonus x${String(Number(c.rasio).toFixed(4)).replace(".", ",")} pada ${tanggal(c.tgl)}: selisih keputusan dalam 5 hari bursa sesudah split dianggap beda karena split/bonus (diharapkan); di luar jendela itu tetap dihitung penyimpangan.`));
const isiPanel = (d) => (d.judul.startsWith("Selisih metode") ? [...d.isi, ...kalimatSplit.value] : d.isi);
</script>

<template>
  <div class="space-y-5">
    <div class="grid gap-5 md:grid-cols-3">
      <div v-for="(l, i) in s?.aturan_langkah || []" :key="l.judul" class="panel p-6">
        <div class="flex items-center gap-3">
          <span class="grid h-8 w-8 place-items-center rounded-full bg-aksen text-[13px] font-medium text-aksen-teks">{{ i + 1 }}</span>
          <span class="font-medium">{{ l.judul }}</span>
        </div>
        <p class="m-0 mt-2 text-ink-2">{{ l.isi }}</p>
      </div>
    </div>

    <template v-if="!s">
      <Kerangka v-for="i in 3" :key="i" panel jenis="tabel" :n="4" />
    </template>
    <Panel v-for="g in s?.variabel || []" :key="g.grup" :judul="g.grup" rapat>
      <div class="overflow-x-auto">
        <table class="tabel min-w-[860px]">
          <thead><tr><th class="w-44">Variabel</th><th class="w-[30%]">Nilai</th><th>Keterangan</th><th class="w-[24%]">Pembaruan</th></tr></thead>
          <tbody>
            <tr v-for="v in g.isi" :key="v.nama" class="align-top">
              <td class="!h-auto py-3 font-medium">{{ v.nama }}</td>
              <td class="!h-auto !whitespace-normal py-3">{{ v.nilai }}</td>
              <td class="!h-auto !whitespace-normal py-3 text-xs text-muted">{{ v.ket }}</td>
              <td class="!h-auto !whitespace-normal py-3 text-xs" :class="v.pembaruan?.startsWith('Tetap') ? 'text-muted' : 'text-ink-2'">{{ v.pembaruan }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </Panel>

    <Panel v-if="s?.contoh_stop" :judul="s.contoh_stop.judul" :ket="s.contoh_stop.ket" rapat>
      <div class="overflow-x-auto">
        <table class="tabel min-w-[620px]">
          <thead><tr><th>Waktu</th><th class="!text-right">Close</th><th class="!text-right">Close tertinggi</th><th class="!text-right">Stop</th><th>Kalau kena stop</th></tr></thead>
          <tbody>
            <tr v-for="b in s.contoh_stop.baris" :key="b[0]">
              <td class="text-ink-2">{{ b[0] }}</td><td class="text-right">{{ b[1] }}</td><td class="text-right">{{ b[2] }}</td><td class="text-right">{{ b[3] }}</td>
              <td :class="b[5] === 'naik' ? 'text-naik' : b[5] === 'turun' ? 'font-medium text-turun' : 'text-muted'">{{ b[4] }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="m-0 px-6 pt-2 pb-3 text-xs text-muted">{{ s.contoh_stop.catatan }}</p>
    </Panel>

    <div class="grid gap-5 lg:grid-cols-2">
      <Panel v-if="s?.tidak_dipakai?.length" judul="Sengaja tidak dipakai" ket="Sudah diuji dan tidak memperbaiki hasil" rapat>
        <table class="tabel">
          <tbody>
            <tr v-for="t in s.tidak_dipakai" :key="t.nama" class="align-top">
              <td class="!h-auto !whitespace-normal py-3"><div class="font-medium">{{ t.nama }}</div><div class="text-xs text-muted">{{ t.hasil }}</div></td>
              <td class="!h-auto w-16 py-3 text-right"><span class="chip bg-turun-bg text-turun">{{ t.uji }}</span></td>
            </tr>
          </tbody>
        </table>
      </Panel>
      <Panel v-if="s?.reset?.length" judul="Reset paper trade" ket="Cara kerja tombol Reset di halaman Paper trade">
        <template #aksi><RotateCcw class="h-4 w-4 text-muted" /></template>
        <ol class="m-0 list-decimal space-y-2 pl-5 text-ink-2">
          <li v-for="r in s.reset" :key="r">{{ r }}</li>
        </ol>
      </Panel>
      <Panel v-for="d in s?.panel_daftar || []" :key="d.judul" :judul="d.judul" :ket="d.ket">
        <ol class="m-0 list-decimal space-y-2 pl-5 text-ink-2">
          <li v-for="r in isiPanel(d)" :key="r">{{ r }}</li>
        </ol>
      </Panel>
    </div>

    <Panel judul="Yang harus diterima">
      <ul class="m-0 list-disc space-y-1.5 pl-5 text-ink-2">
        <li v-for="x in s?.risiko || []" :key="x">{{ x }}</li>
      </ul>
    </Panel>
  </div>
</template>

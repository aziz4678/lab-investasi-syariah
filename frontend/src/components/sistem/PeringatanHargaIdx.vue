<script setup>
import { ref, computed, inject } from "vue";
import { TriangleAlert, Info as IkonInfo } from "lucide-vue-next";
import { rupiah, persen } from "@/utils/format";

const props = defineProps({ strategi: { type: String, default: "h11a" }, posisiRs: { type: Array, default: () => [] } });
const statusApp = inject("status");
const buka = ref(false);

const idx = computed(() => {
  const x = statusApp?.value?.paper_cek?.idx;
  return x && x.cocok === false ? x : null;
});
const beda = computed(() => idx.value?.beda || []);

const dariBeda = () => {
  const g = {};
  for (const b of beda.value) (g[b.ticker] ||= []).push(b);
  return Object.entries(g).map(([kode, daftar]) => ({
    kode, baris: daftar.length, tgl_awal: daftar[0].tgl, tgl_akhir: daftar.at(-1).tgl, kategori: "harga_berbeda", dipakai: daftar.some((b) => b.dipakai), aksi: null,
  }));
};
const semuaKode = computed(() => (idx.value?.per_kode?.length ? idx.value.per_kode : dariBeda()));
const menyentuh = (k) => k.dipakai || (props.strategi === "h29" && props.posisiRs.includes(k.kode));
const daftarKode = computed(() => (props.strategi === "h29" ? semuaKode.value.filter(menyentuh) : semuaKode.value));
const aksi = computed(() => daftarKode.value.filter((k) => k.kategori === "aksi_korporasi"));
const acak = computed(() => daftarKode.value.filter((k) => k.kategori !== "aksi_korporasi"));
const tampil = computed(() => !!idx.value && daftarKode.value.length > 0);
const namaStrategi = computed(() => (props.strategi === "h29" ? "Momentum Blend (H29)" : "Follow Tren (H11a) dan Momentum Blend (H29)"));

const tglPendek = (s) => (s ? new Date(`${s}T00:00:00`).toLocaleDateString("id-ID", { day: "numeric", month: "short" }) : "");
const kalimatAksi = (k) => `${k.kode}: ${k.aksi.jenis} ${k.aksi.rasio}${k.aksi.ex ? ` (${tglPendek(k.aksi.ex)})` : ""}, harga lama disesuaikan Yahoo, bukan salah data.`;
const sentuhAksi = computed(() => aksi.value.filter(menyentuh));
const sentuhAcak = computed(() => acak.value.filter(menyentuh));
const merahAksi = computed(() => sentuhAksi.value.length > 0);
const merahAcak = computed(() => sentuhAcak.value.length > 0);
const jumlahAcak = computed(() => acak.value.reduce((a, k) => a + k.baris, 0));
const terpotong = computed(() => (idx.value?.jumlah_beda || 0) > beda.value.length);
const kodeAcak = computed(() => acak.value.map((k) => `${k.kode} ${k.baris}`).join(", "));
const dampakAcak = computed(() => (merahAcak.value
  ? `Menyentuh posisi atau keputusan ${namaStrategi.value}: ${sentuhAcak.value.map((k) => k.kode).join(", ")}.`
  : "Tidak menyentuh posisi atau keputusan paper."));

const selisihPct = (b) => (b.paper == null || !b.idx ? null : (b.paper / b.idx - 1) * 100);
const bulat = (v) => (v == null ? "–" : rupiah(Math.round(v)));
const barisRinci = computed(() => {
  const nama = new Set(daftarKode.value.map((k) => k.kode));
  const g = {};
  for (const b of beda.value) if (nama.has(b.ticker)) (g[b.ticker] ||= []).push(b);
  return daftarKode.value.filter((k) => g[k.kode]).map((k) => ({ ...k, daftar: g[k.kode] }));
});
</script>

<template>
  <div v-if="tampil" class="space-y-2">
    <div v-for="k in aksi" :key="k.kode" class="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-2xl px-4 py-3 text-xs"
      :class="menyentuh(k) ? 'bg-turun-bg text-turun' : 'bg-surface-2 text-ink-2'">
      <IkonInfo v-if="!menyentuh(k)" class="h-3.5 w-3.5 shrink-0 text-aksen" />
      <TriangleAlert v-else class="h-3.5 w-3.5 shrink-0" />
      <span class="min-w-0 flex-1 leading-relaxed">{{ kalimatAksi(k) }}<template v-if="menyentuh(k)"> Menyentuh posisi atau keputusan {{ namaStrategi }}: jumlah lembar, harga masuk, dan stop perlu dicek manual.</template></span>
      <button v-if="k === aksi[0] && !acak.length" class="shrink-0 font-medium underline-offset-2 hover:underline" @click="buka = !buka">{{ buka ? "Tutup rincian" : "Lihat rincian" }}</button>
    </div>
    <div v-if="acak.length" class="rounded-2xl px-4 py-3 text-xs" :class="merahAcak ? 'bg-turun-bg text-turun' : 'bg-kuning-bg text-ink-2'">
      <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
        <TriangleAlert class="h-3.5 w-3.5 shrink-0" />
        <span class="min-w-0 flex-1 leading-relaxed">{{ jumlahAcak }} harga paper beda dengan data resmi IDX ({{ kodeAcak }}). Data paper tidak diubah otomatis. {{ dampakAcak }}</span>
        <button class="shrink-0 font-medium underline-offset-2 hover:underline" @click="buka = !buka">{{ buka ? "Tutup rincian" : "Lihat rincian" }}</button>
      </div>
    </div>
    <div v-if="buka" class="overflow-x-auto rounded-2xl bg-surface-2 px-4 py-3 text-xs text-ink-2">
      <table class="w-full min-w-[440px] text-xs">
        <thead>
          <tr class="text-left text-muted">
            <th class="py-1 pr-3 font-normal">Kode</th>
            <th class="py-1 pr-3 font-normal">Tanggal</th>
            <th class="py-1 pr-3 text-right font-normal">IDX</th>
            <th class="py-1 pr-3 text-right font-normal">Paper</th>
            <th class="py-1 text-right font-normal">Selisih</th>
          </tr>
        </thead>
        <tbody v-for="k in barisRinci" :key="k.kode">
          <tr v-for="(b, i) in k.daftar" :key="b.tgl + b.jenis" class="border-t border-garis">
            <td class="py-1 pr-3 font-medium">{{ i === 0 ? k.kode : "" }}</td>
            <td class="py-1 pr-3 tabular-nums">{{ b.tgl }}<span v-if="b.jenis !== 'close'" class="text-muted"> · {{ b.jenis }}</span></td>
            <td class="py-1 pr-3 text-right tabular-nums">{{ bulat(b.idx) }}</td>
            <td class="py-1 pr-3 text-right tabular-nums">{{ bulat(b.paper) }}</td>
            <td class="py-1 text-right tabular-nums">{{ selisihPct(b) == null ? "–" : persen(selisihPct(b), 1) }}</td>
          </tr>
          <tr>
            <td colspan="5" class="pb-2 text-[11px] text-muted">
              {{ k.kode }}: {{ k.baris }} baris, {{ k.tgl_awal }} s/d {{ k.tgl_akhir }}<template v-if="k.rasio_min != null">, rasio IDX/paper {{ k.rasio_min }}<template v-if="k.rasio_maks !== k.rasio_min"> - {{ k.rasio_maks }}</template></template>.
              <template v-if="k.kategori === 'aksi_korporasi'">Selisih konstan dan ada pengumuman {{ k.aksi.jenis }} IDX.</template>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="terpotong" class="m-0 mt-1 text-[11px] text-muted">Menampilkan {{ beda.length }} dari {{ idx.jumlah_beda }} baris.</p>
    </div>
  </div>
</template>

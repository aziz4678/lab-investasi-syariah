<script setup>
import { ref, computed, onMounted } from "vue";
import { ambil, persen } from "../util.js";
import Panel from "../components/Panel.vue";
import Stats from "../components/Stats.vue";
import Segmen from "../components/Segmen.vue";
import Kerangka from "../components/Kerangka.vue";

const data = ref(null);
const filter = ref("semua");

onMounted(async () => {
  data.value = await ambil("riset").catch(() => null);
});

const HASIL = {
  kandidat: { l: "Lulus", k: "bg-naik-bg text-naik" },
  gagal: { l: "Gagal", k: "bg-turun-bg text-turun" },
  menunggu: { l: "Menunggu", k: "bg-kuning-bg text-kuning" },
};
const FILTER = [
  ["semua", "Semua"],
  ["kandidat", "Lulus"],
  ["gagal", "Gagal"],
  ["menunggu", "Menunggu"],
];

const stat = computed(() => {
  const h = data.value?.hipotesis || [];
  return [
    { label: "Ide diuji", nilai: String(h.length) },
    {
      label: "Gagal",
      nilai: String(h.filter((x) => x.hasil === "gagal").length),
      nada: "turun",
    },
    {
      label: "Lulus (paper trade)",
      nilai: String(h.filter((x) => x.hasil === "kandidat").length),
      nada: "naik",
    },
    {
      label: "Menunggu data",
      nilai: String(h.filter((x) => x.hasil === "menunggu").length),
    },
  ];
});

const perTahap = computed(() =>
  (data.value?.tahap || [])
    .map((t) => ({
      ...t,
      isi: data.value.hipotesis.filter(
        (h) =>
          h.tahap === t.kode &&
          (filter.value === "semua" || h.hasil === filter.value),
      ),
    }))
    .filter((t) => t.isi.length),
);
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <p class="m-0 min-w-0 flex-1 text-[13px] leading-relaxed text-ink-2">Semua ide yang sudah diuji. Aturan dikunci dulu, diuji di data lama, lalu dicek sekali di data yang belum pernah dilihat.</p>
      <Segmen v-model="filter" :pilihan="FILTER" />
    </div>

    <template v-if="!data">
      <Kerangka panel jenis="stat" :n="4" :judul="false" kolom="grid-cols-2 lg:grid-cols-4" />
      <Kerangka v-for="i in 2" :key="i" panel jenis="tabel" :n="5" />
    </template>
    <Stats v-if="data" :items="stat" kolom="grid-cols-2 lg:grid-cols-4" />

    <Panel
      v-for="t in perTahap"
      :key="t.kode"
      :judul="`Tahap ${t.kode} · ${t.nama}`"
      :ket="t.ket"
      rapat
    >
      <div class="overflow-x-auto">
        <table class="tabel min-w-[880px]">
          <thead>
            <tr>
              <th class="w-14">Kode</th>
              <th>Ide</th>
              <th class="w-36">Periode</th>
              <th class="w-28 !text-right">Rata-rata / trade</th>
              <th class="w-24 !text-right">Kriteria</th>
              <th class="w-24">Hasil</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="h in t.isi" :key="h.kode" class="align-top">
              <td class="!h-auto py-3.5 font-medium text-muted">
                {{ h.kode }}
              </td>
              <td class="!h-auto !whitespace-normal py-3">
                <div class="font-medium">{{ h.nama }}</div>
                <div class="mt-0.5 text-xs text-muted">{{ h.ide }}</div>
                <div class="mt-1.5 text-xs text-ink-2">{{ h.pelajaran }}</div>
              </td>
              <td class="!h-auto py-3.5 text-ink-2">{{ h.periode }}</td>
              <td
                class="!h-auto py-3.5 text-right font-medium"
                :class="
                  h.net == null
                    ? 'text-muted'
                    : h.net >= 0
                      ? 'text-naik'
                      : 'text-turun'
                "
              >
                {{ h.net == null ? "–" : persen(h.net, 2) }}
              </td>
              <td class="!h-auto py-3.5 text-right text-ink-2">{{ h.skor }}</td>
              <td class="!h-auto py-3.5">
                <span class="chip" :class="HASIL[h.hasil].k">{{
                  HASIL[h.hasil].l
                }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </Panel>

    <div class="grid gap-4 lg:grid-cols-2">
      <Panel
        judul="Syarat lulus"
        ket="Semua harus terpenuhi, di data lama dan data baru"
      >
        <ol class="m-0 list-decimal space-y-1 pl-5 text-ink-2">
          <li v-for="k in data?.kriteria || []" :key="k">{{ k }}</li>
        </ol>
        <p class="m-0 mt-3 text-xs text-muted">
          Biaya: fee beli 0,15% + jual 0,25% + selisih harga 1 tick per sisi
          (±1,2% pulang-pergi).
        </p>
      </Panel>
      <Panel judul="Kesimpulan sejauh ini">
        <div class="space-y-3 text-ink-2">
          <p class="m-0">
            Swing pendek (beberapa hari sampai 2 minggu) dengan data publik
            selalu kalah oleh biaya transaksi: sinyalnya ada, tapi lebih kecil
            dari biaya.
          </p>
          <p class="m-0">
            Satu-satunya yang lulus adalah trend following Follow Tren (H11a): sering rugi
            kecil, sesekali untung sangat besar. Hasilnya sedang dibuktikan
            lewat paper trade.
          </p>
        </div>
      </Panel>
    </div>
  </div>
</template>

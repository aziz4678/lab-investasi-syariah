<script setup>
import { ref, onMounted } from "vue";
import { Coins, ChartPie, Layers, Globe, Bitcoin, Gem, Landmark, Scale, FlaskConical, Database, CircleHelp } from "lucide-vue-next";
import { ambil } from "../util.js";
import Panel from "../components/Panel.vue";
import Kerangka from "../components/Kerangka.vue";

const IKON = { coins: Coins, pie: ChartPie, layers: Layers, globe: Globe, bitcoin: Bitcoin, gem: Gem, landmark: Landmark, scale: Scale };
const r = ref([]);
const WARNA_STATUS = { "Data sudah ada": "bg-naik-bg text-naik", "Data sebagian ada": "bg-aksen-lembut text-aksen", "Menunggu hasil": "bg-surface-2 text-ink-2", "Perlu keputusan": "bg-kuning-bg text-kuning" };
const siap = ref(false);

onMounted(async () => {
  const d = await ambil("strategi").catch(() => null);
  r.value = d?.rencana || [];
  siap.value = true;
});

const ALUR = [
  ["Kunci hipotesis", "Aturan, variabel, dan syarat lulus ditulis sebelum melihat data."],
  ["Uji data lama", "Backtest di periode pengembangan, setelah biaya."],
  ["Buka data baru sekali", "Hanya kalau lulus; tidak boleh diubah setelah melihat hasil."],
  ["Paper trade", "Dijalankan maju dengan zona normal yang dikunci."],
  ["Uang asli kecil", "Hanya setelah 6-12 bulan paper tetap wajar."],
];
</script>

<template>
  <div class="space-y-5">
    <p class="m-0 max-w-[760px] text-muted">Ide yang belum dibangun. Masing-masing nanti jadi section sendiri dengan backtest, aturan yang dikunci, dan uji ke depan, seperti Follow Tren dan Dividen.</p>

    <Panel judul="Alur setiap section" ket="Sama untuk semua aset, supaya hasilnya jujur dan bisa dibandingkan">
      <ol class="m-0 grid list-none gap-2 p-0 sm:grid-cols-5">
        <li v-for="(a, i) in ALUR" :key="a[0]" class="rounded-2xl bg-surface-2 px-4 py-3">
          <div class="flex items-center gap-2"><span class="grid h-6 w-6 place-items-center rounded-full bg-aksen text-[11px] font-medium text-aksen-teks">{{ i + 1 }}</span><span class="text-[13px] font-medium">{{ a[0] }}</span></div>
          <p class="m-0 mt-1.5 text-xs text-muted">{{ a[1] }}</p>
        </li>
      </ol>
    </Panel>

    <div v-if="!siap" class="grid gap-5 lg:grid-cols-2">
      <Kerangka v-for="i in 4" :key="i" panel :n="5" />
    </div>
    <div class="grid gap-5 lg:grid-cols-2">
      <section v-for="x in r" :key="x.id" class="panel flex flex-col p-6">
        <div class="flex items-start gap-3">
          <span class="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-aksen-lembut text-aksen"><component :is="IKON[x.ikon] || FlaskConical" class="h-5 w-5" /></span>
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <h2 class="m-0 text-[17px] font-medium">{{ x.nama }}</h2>
              <span class="chip" :class="WARNA_STATUS[x.status] || 'bg-surface-2 text-muted'">{{ x.status || "Rencana" }}</span>
            </div>
            <div class="text-xs text-muted">{{ x.kelas }}</div>
          </div>
        </div>
        <p class="m-0 mt-3 text-ink-2">{{ x.ide }}</p>
        <p class="m-0 mt-2 text-[13px] text-muted">{{ x.beda }}</p>
        <div class="mt-4 space-y-2 text-[13px]">
          <div class="flex gap-2"><Database class="mt-0.5 h-4 w-4 shrink-0 text-muted" /><span class="text-ink-2">{{ x.data }}</span></div>
          <div class="flex gap-2"><CircleHelp class="mt-0.5 h-4 w-4 shrink-0 text-muted" /><span class="text-ink-2">{{ x.pertanyaan }}</span></div>
        </div>
      </section>
    </div>
  </div>
</template>

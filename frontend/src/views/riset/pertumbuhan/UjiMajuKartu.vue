<script setup>
import { ref, computed, onMounted } from "vue";
import { FlaskConical, Lock } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { rupiahRingkas } from "@/utils/format";
import { pr, prTanda } from "@/views/riset/pertumbuhan/bantu";

const u = ref(null);
onMounted(async () => {
  u.value = await ambil("pertumbuhan/uji_maju").catch(() => null);
});

const aktif = computed(() => u.value?.item?.some((x) => x.aktif));
const hitung = computed(() => {
  const n = u.value?.hari_lagi;
  if (n == null) return "";
  if (n > 1) return `${n} hari lagi`;
  if (n === 1) return "besok";
  return aktif.value ? "sedang berjalan" : "hari pertama bursa Des 2026, menunggu pemrosesan";
});
const tglTeks = (s) => (s ? new Date(s).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" }) : "–");
</script>

<template>
  <section v-if="u?.ada" class="panel px-4 py-5 sm:px-6">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div class="flex items-center gap-2 text-[14px] font-medium"><FlaskConical class="h-4 w-4 text-aksen" />Uji maju H35 &amp; H37</div>
      <div class="flex flex-wrap items-center gap-1.5">
        <span class="chip bg-kuning-bg text-kuning"><Lock class="mr-1 h-3 w-3" />Aturan dikunci</span>
        <span class="chip bg-surface-2 text-ink-2">Mulai {{ tglTeks(u.mulai) }} · {{ hitung }}</span>
      </div>
    </div>
    <p class="m-0 mt-2 text-[12px] leading-relaxed text-ink-2">Modal paper {{ rupiahRingkas(u.item[0].modal) }} masing-masing, sekali masuk dengan produk nyata. Yang dinilai pelaksanaannya (selisih dengan model, selisih harga ETF dengan NAV, biaya nyata), bukan bukti keunggulan. Evaluasi pertama {{ u.evaluasi_pertama }}.</p>

    <div class="mt-3 grid gap-3 md:grid-cols-2">
      <div v-for="x in u.item" :key="x.kode" class="rounded-2xl bg-surface-2 px-4 py-3">
        <div class="flex items-start justify-between gap-2">
          <div class="text-[13px] font-medium">{{ x.kode }} · {{ x.nama }}</div>
          <span class="chip" :class="x.aktif ? 'bg-naik-bg text-naik' : 'bg-surface text-muted'">{{ x.aktif ? "Berjalan" : "Menunggu mulai" }}</span>
        </div>
        <template v-if="x.ekuitas">
          <div class="mt-2 text-[20px] font-semibold tabular-nums">{{ rupiahRingkas(x.ekuitas.nilai) }}</div>
          <div class="text-[12px] text-muted">per {{ x.ekuitas.tgl }} ·
            <span :class="x.ekuitas.ret < 0 ? 'text-turun' : 'text-naik'">{{ prTanda(x.ekuitas.ret, 2) }}</span>
            <template v-if="x.ekuitas.kas > 1"> · kas menunggu {{ rupiahRingkas(x.ekuitas.kas) }}</template>
          </div>
        </template>
        <div v-else class="mt-2 text-[12px] text-muted">Belum ada transaksi. Mesin berjalan otomatis lewat jadwal harian.</div>
        <div class="mt-2 text-[11px] text-muted">
          Target {{ Object.entries(x.bobot).map(([k, v]) => `${pr(v, 0)} ${k}`).join(" / ") }}<template v-if="x.etf_emas"> · ETF emas {{ x.etf_emas }}</template>
          · {{ x.jumlah_transaksi }} transaksi · {{ x.jumlah_kejadian }} kejadian
        </div>
        <ul v-if="x.kejadian.length" class="m-0 mt-2 list-none space-y-0.5 p-0 text-[11px] text-ink-2">
          <li v-for="k in x.kejadian" :key="k.tgl + k.jenis + k.teks"><span class="text-muted">{{ k.tgl }}</span> · {{ k.teks }}</li>
        </ul>
      </div>
    </div>

    <details class="mt-3 text-[12px]">
      <summary class="cursor-pointer text-aksen">Teks aturan terkunci &amp; amandemen</summary>
      <div v-for="a in u.amandemen" :key="a.id" class="mt-2 rounded-xl bg-kuning-bg px-3 py-2 leading-relaxed text-kuning"><b class="font-medium">Amandemen {{ a.id }} · {{ a.tgl }}</b> (sebelum ada transaksi): {{ a.teks }}</div>
      <pre class="m-0 mt-2 overflow-x-auto rounded-xl bg-surface-2 p-3 text-[11px] leading-relaxed whitespace-pre-wrap text-ink-2">{{ u.aturan }}</pre>
    </details>
  </section>
</template>

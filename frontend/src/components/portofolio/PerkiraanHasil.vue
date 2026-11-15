<script setup>
import { ref, computed } from "vue";
import { ChevronRight } from "lucide-vue-next";
import { rupiahRingkas } from "@/utils/format";
import { pr, prTanda, bulanPendek } from "@/views/riset/pertumbuhan/bantu";

const props = defineProps({
  d: { type: Object, default: null },
  gaya: { type: String, default: "saham" },
  modelValue: { type: Number, default: 1000000 },
  modalAwal: { type: Number, default: 0 },
});
const emit = defineEmits(["update:modelValue", "baca"]);

const SETORAN_MIN = 100000;
const PILIHAN_TAHUN = [1, 3, 5, 10];
const tahun = ref(10);
const tahunTulis = ref("");

const angka = (s) => Number(String(s).replace(/\D/g, "")) || 0;
const tampilRp = (v) => (v ? v.toLocaleString("id-ID") : "");
const setoranPakai = computed(() => Math.max(props.modelValue || 0, SETORAN_MIN));
const pilihTahun = (t) => {
  tahun.value = t;
  tahunTulis.value = "";
};
const ubahTahun = (e) => {
  const bersih = String(e.target.value).replace(/\D/g, "").slice(0, 2);
  tahunTulis.value = bersih;
  const t = Number(bersih);
  if (t >= 1 && t <= 20) tahun.value = t;
};

const opsi = computed(() => props.d?.[props.gaya]);
const x = computed(() => opsi.value?.jangka?.[String(tahun.value)] ?? null);
const nilai = (v) => rupiahRingkas(v * setoranPakai.value);
const peluangRugi = computed(() => (x.value ? (x.value.jendela - x.value.untung) / x.value.jendela : null));
const terbatas = computed(() => Boolean(x.value?.terbatas));
const rentangData = computed(() => (props.d?.periode ? `${bulanPendek(props.d.periode[0])}–${bulanPendek(props.d.periode[1])}` : periode.value));
const tanpaRugi = computed(() => peluangRugi.value === 0);
const periodeBeda = computed(() => (x.value ? x.value.periode_terpisah.toLocaleString("id-ID", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) : ""));
const periode = computed(() => (x.value ? `${bulanPendek(x.value.data_dari)}–${bulanPendek(x.value.data_sampai)}` : ""));

const kartu = computed(() => {
  const v = x.value;
  if (!v) return [];
  return [
    { label: "Biasanya", nilai: nilai(v.median), kelas: v.median >= v.total ? "text-naik" : "text-turun", ket: "nilai tengah dari semua periode" },
    { label: "Paling sial", nilai: nilai(v.terburuk), kelas: v.terburuk >= v.total ? "text-naik" : "text-turun", ket: `mulai ${bulanPendek(v.mulai_terburuk)}` },
    { label: "Paling beruntung", nilai: nilai(v.terbaik), kelas: "text-naik", ket: `mulai ${bulanPendek(v.mulai_terbaik)}` },
  ];
});
const ringkasan = computed(() => {
  const v = x.value;
  if (!v) return [];
  return [
    { label: "Pertumbuhan rata-rata per tahun", nilai: prTanda(v.xirr_median), kelas: v.xirr_median < 0 ? "text-turun" : "", ket: "dihitung dari setoran bulanan, bukan satu kali setor" },
    { label: "Kira-kira per bulan", nilai: prTanda(v.per_bulan), kelas: v.per_bulan < 0 ? "text-turun" : "", ket: `per bulan bisa naik-turun antara ${prTanda(v.bulanan_p5)} s.d. ${prTanda(v.bulanan_p95)}` },
    { label: "Pernah turun terdalam", nilai: prTanda(opsi.value.dd.dd), kelas: "text-turun", ket: "dari puncak, di seluruh data" },
    tanpaRugi.value
      ? { label: "Peluang rugi", nilai: "Belum pernah rugi", kelas: "", ket: `Belum pernah rugi di data ${rentangData.value} untuk jangka ini, tapi datanya terbatas, bukan jaminan.` }
      : { label: "Peluang rugi", nilai: `${Math.round(peluangRugi.value * 100)}%`, kelas: "", ket: "dari semua periode yang diuji" },
  ];
});
</script>

<template>
  <section class="panel px-4 py-5 sm:px-6">
    <div class="text-[13px] font-medium text-muted">Perkiraan hasil, berdasarkan masa lalu</div>

    <div class="mt-3 grid gap-4 sm:grid-cols-2">
      <div class="min-w-0">
        <label class="text-xs text-muted">Setoran per bulan</label>
        <div class="mt-1 flex items-center rounded-full bg-surface-2 px-4"><span class="text-[13px] text-muted">Rp</span>
          <input :value="tampilRp(modelValue)" inputmode="numeric" class="h-10 w-full min-w-0 bg-transparent px-2 text-[15px] outline-none" @input="(e) => emit('update:modelValue', angka(e.target.value))" /></div>
        <div v-if="modelValue < SETORAN_MIN" class="mt-1 text-[11px] text-kuning">Minimal Rp100.000, perkiraan dihitung dengan Rp100.000.</div>
      </div>
      <div class="min-w-0">
        <label class="text-xs text-muted">Jangka waktu (tahun)</label>
        <div class="mt-1 flex flex-wrap items-center gap-1.5">
          <button v-for="t in PILIHAN_TAHUN" :key="t" class="h-9 min-w-[44px] rounded-full px-3 text-[13px] font-medium" :class="tahun === t && !tahunTulis ? 'bg-aksen text-aksen-teks' : 'bg-surface-2 text-ink-2'" @click="pilihTahun(t)">{{ t }}</button>
          <input :value="tahunTulis" inputmode="numeric" placeholder="1–20" aria-label="Jangka waktu sendiri dalam tahun" class="h-9 w-[76px] rounded-full bg-surface-2 px-3 text-center text-[13px] outline-none" :class="tahunTulis ? 'ring-2 ring-aksen' : ''" @input="ubahTahun" />
        </div>
      </div>
    </div>

    <template v-if="x">
      <div class="mt-4 text-[34px] leading-tight font-semibold sm:text-[40px]">{{ nilai(x.median) }}<span class="ml-2 text-[18px] font-medium text-ink-2">setelah {{ tahun }} tahun</span></div>
      <p class="m-0 mt-1 text-[14px] leading-relaxed text-ink-2">Kalau dulu setor {{ rupiahRingkas(setoranPakai) }}/bulan selama {{ tahun }} tahun, biasanya jadi {{ nilai(x.median) }} (disetor {{ rupiahRingkas(x.total * setoranPakai) }}). Untung di {{ x.untung }} dari {{ x.jendela }} periode <span class="text-muted">(periode saling tumpang tindih)</span>.</p>

      <div class="mt-4 grid gap-3 sm:grid-cols-3">
        <div v-for="k in kartu" :key="k.label" class="rounded-2xl bg-surface-2 px-4 py-3">
          <div class="text-[11px] text-muted">{{ k.label }}</div>
          <div class="text-[17px] font-semibold tabular-nums" :class="k.kelas">{{ k.nilai }}</div>
          <div class="text-[11px] text-muted">{{ k.ket }}</div>
        </div>
      </div>

      <div class="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div v-for="r in ringkasan" :key="r.label" class="rounded-2xl border border-garis px-4 py-3">
          <div class="text-[11px] text-muted">{{ r.label }}</div>
          <div class="text-[17px] font-semibold tabular-nums" :class="r.kelas">{{ r.nilai }}</div>
          <div class="text-[11px] leading-snug text-muted">{{ r.ket }}</div>
        </div>
      </div>

      <div class="mt-3 space-y-2">
        <div v-if="terbatas" class="rounded-2xl bg-kuning-bg px-4 py-3 text-[13px] leading-relaxed text-kuning">Hanya ada sekitar {{ periodeBeda }} periode {{ tahun }} tahun yang benar-benar berbeda di data {{ rentangData }}. Angka untuk jangka ini kurang bisa diandalkan.</div>
        <div class="rounded-2xl bg-kuning-bg px-4 py-3 text-[13px] leading-relaxed text-kuning">Jangan pakai uang yang dibutuhkan kurang dari 5 tahun lagi.<template v-if="tahun < 5"> Untuk jangka pendek, hasil sangat tidak pasti.</template></div>
      </div>

      <p class="m-0 mt-3 text-[12px] leading-relaxed text-muted">Dihitung dari indeks pasar (periode {{ periode }}) dikurangi biaya produk, bukan dari produk asli. Hanya setoran bulanan; modal awal<template v-if="modalAwal > 0"> ({{ rupiahRingkas(modalAwal) }})</template> tidak ikut dihitung.</p>
    </template>
    <p v-else class="m-0 mt-4 text-[13px] text-muted">{{ d ? "Pilih jangka 1 sampai 20 tahun." : "Perkiraan belum tersedia." }}</p>

    <div class="mt-3 flex flex-wrap items-center justify-between gap-2">
      <div class="inline-flex rounded-full bg-surface-2 px-3 py-1 text-[11px] font-medium text-ink-2">Diuji dengan data masa lalu; belum terbukti di masa depan.</div>
      <button class="inline-flex items-center gap-0.5 text-[12px] text-aksen" @click="emit('baca')">Baca selengkapnya<ChevronRight class="h-3.5 w-3.5" /></button>
    </div>
  </section>
</template>

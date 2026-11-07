<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { ChevronDown, Lock, ShieldAlert, Info as IkonInfo, CalendarClock } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { persen, tanggal } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import Kerangka from "@/components/common/Kerangka.vue";

const props = defineProps({ strategi: { type: String, default: "h11a" }, muatUlang: Number });
const d = ref(null);
const bukaAudit = ref(false);
const bukaAturan = ref(false);

async function muat() {
  d.value = await ambil(`paper/aturan?strategi=${props.strategi}`).catch(() => ({ ada: false }));
}
onMounted(muat);
watch(() => [props.muatUlang, props.strategi], muat);

const STATUS = {
  normal: { l: "Normal", k: "bg-naik-bg text-naik", t: "Rem GAGAL belum tersentuh." },
  waspada: { l: "Info waspada", k: "bg-kuning-bg text-kuning", t: "Ada catatan waspada. Info saja, bukan syarat dan bukan alasan mengubah aturan." },
  gagal: { l: "Gagal", k: "bg-turun-bg text-turun", t: "Rem GAGAL tersentuh: tidak dilanjutkan ke uang asli, aturan tidak boleh diubah lalu diteruskan." },
};
const t = computed(() => d.value?.terakhir);
const st = computed(() => STATUS[t.value?.status] || { l: "Belum dinilai", k: "bg-surface-2 text-muted", t: "Penilaian mulai setelah ada hari bursa yang diproses." });
const nama = computed(() => (props.strategi === "h29" ? "Momentum Blend" : "Follow Tren"));

const kotak = computed(() => {
  const x = t.value;
  if (!x) return [];
  const b = x.batas || {};
  if (props.strategi === "h29") {
    return [
      { l: `Rem hari ke-${b.hari}`, v: `hari ${x.hari}/${b.hari}`, w: `return < ${persen(b.ret, 1)} atau turun terdalam < ${persen(b.dd, 1)} → GAGAL` },
      { l: "Turun terdalam", v: persen(x.dd_maks_pct, 1), w: "GAGAL kalau lebih dalam dari -45%" },
      { l: "Return sejak mulai", v: persen(x.return_pct, 1), w: "laporan, dibanding bobot sama & JII" },
    ];
  }
  const g = b.gagal || {};
  return [
    { l: "Return", v: persen(x.return_pct, 1), w: x.hari >= g.mulai_ret ? `GAGAL < ${persen(g.ret, 1)} hari ini` : `rem return mulai hari ke-${g.mulai_ret} (sekarang hari ${x.hari})` },
    { l: "Turun terdalam", v: persen(x.dd_maks_pct, 1), w: `GAGAL < ${persen(g.dd, 1)} hari ini · selalu < -45%` },
    { l: "Rugi beruntun", v: `${x.beruntun}x`, w: g.ber == null ? "belum ada trade selesai" : `GAGAL > ${g.ber}x (${x.trade} trade)` },
  ];
});

const fmt = (v) => (v == null ? "–" : `${String(v).replace(".", ",")}%`);
const baris = computed(() => (d.value?.audit?.baris || []).filter((r) => (props.strategi === "h29" ? /H29|h29|H22|U1/ : /H11a|U1/).test(r.aturan)));
const lolos = computed(() => (d.value?.audit?.lolos || []).filter((r) => (props.strategi === "h29" ? r.kriteria.startsWith("H29") : r.kriteria.startsWith("H11a"))));
const horizon = computed(() => d.value?.audit?.horizon_minimum?.[props.strategi]);
const NAMA_NULL = { null1: "bobot sama", null2: "JII", null3: "pilihan acak", null: "50% acak + 50% bobot sama" };
</script>

<template>
  <Kerangka v-if="d === null" panel :tinggi="220" />
  <Panel v-else-if="d.ada" :judul="`Aturan evaluasi ${nama} (v2)`" :ket="`Dikunci ${tanggal(d.dikunci)} dari audit sifat aturan · aturan lama ${d.lama.id} tetap dihitung berdampingan`"
    info="Audit 7 Nov 2026: aturan lama terlalu sering menyala di tahun normal, dan 12 bulan tidak bisa membedakan strategi yang punya edge dari yang tidak. Alasan perubahan = sifat aturan, bukan hasil paper.">
    <template #aksi>
      <span class="chip !h-7 !px-3 !text-xs" :class="st.k">{{ st.l }}</span>
    </template>
    <p class="m-0 -mt-1 mb-4 text-[13px] text-ink-2">{{ st.t }}<template v-if="t"> Data {{ tanggal(t.tgl) }}, hari bursa ke-{{ t.hari }}.</template></p>

    <ul v-if="t?.gagal?.length" class="m-0 mb-3 list-disc space-y-1 pl-5 text-[13px] text-turun"><li v-for="a in t.gagal" :key="a">{{ a }}</li></ul>
    <ul v-if="t?.waspada?.length" class="m-0 mb-3 list-disc space-y-1 pl-5 text-[13px] text-kuning"><li v-for="a in t.waspada" :key="a">{{ a }}</li></ul>
    <ul v-if="t?.info_data?.length" class="m-0 mb-3 list-disc space-y-1 pl-5 text-xs text-muted"><li v-for="a in t.info_data" :key="a">{{ a }}</li></ul>

    <div class="mb-4 grid gap-2 sm:grid-cols-3">
      <div v-for="b in kotak" :key="b.l" class="rounded-2xl bg-surface-2 px-4 py-3">
        <div class="text-xs text-muted">{{ b.l }}</div>
        <div class="mt-0.5 text-[17px] font-medium tabular-nums">{{ b.v }}</div>
        <div class="text-[11px] leading-snug text-muted">{{ b.w }}</div>
      </div>
    </div>

    <div class="mb-3 rounded-2xl bg-surface-2 px-5 py-4">
      <div class="mb-2 flex items-center gap-2 text-[13px] font-medium"><CalendarClock class="h-3.5 w-3.5 text-aksen" />Keputusan Okt/Nov 2027 = keputusan manual, bukan bukti edge</div>
      <ul class="m-0 list-disc space-y-1 pl-5 text-xs leading-relaxed text-ink-2">
        <li v-for="k in d.keputusan_2027" :key="k">{{ k }}</li>
      </ul>
    </div>

    <div class="mb-1 flex flex-wrap gap-2 text-xs">
      <span class="chip !h-auto !whitespace-normal bg-surface-2 py-1 leading-snug text-ink-2">
        <ShieldAlert class="h-3.5 w-3.5" />Aturan lama {{ d.lama.id }} (pembanding): {{ d.lama.terakhir || "belum" }}
        · pernah waspada {{ d.lama.pernah_waspada ? tanggal(d.lama.pernah_waspada) : "belum" }} · pernah gagal {{ d.lama.pernah_gagal ? tanggal(d.lama.pernah_gagal) : "belum" }}
      </span>
      <span v-if="d.status_paper_saat_kunci" class="chip !h-auto !whitespace-normal bg-surface-2 py-1 leading-snug text-ink-2">
        <Lock class="h-3.5 w-3.5" />Saat dikunci: {{ d.status_paper_saat_kunci.hari }} hari tercatat s/d {{ tanggal(d.status_paper_saat_kunci.terakhir) }}, status {{ d.status_paper_saat_kunci.status }}
      </span>
    </div>

    <button class="mt-3 inline-flex items-center gap-1 text-xs text-muted hover:text-ink" @click="bukaAudit = !bukaAudit">
      Hasil audit aturan<ChevronDown class="h-3.5 w-3.5 transition-transform" :class="bukaAudit ? 'rotate-180' : ''" />
    </button>
    <div v-if="bukaAudit && d.audit" class="mt-3 space-y-4">
      <p class="m-0 text-xs text-muted">Alarm palsu = peluang aturan menyala dalam 250 hari bursa walau strategi berjalan normal. (a) = 5.000 jalur bootstrap kurva backtest 2020+ (data sudah terbuka), (b) = jendela bergulir 100 simulasi Monte Carlo dev 2010-2019.</p>
      <div class="overflow-x-auto">
        <table class="w-full min-w-[560px] text-xs">
          <thead><tr class="text-left text-muted"><th class="py-1.5 pr-3 font-normal">Aturan</th><th class="py-1.5 pr-3 font-normal">Alarm palsu (a) / (b)</th><th class="py-1.5 pr-3 font-normal">Ambang</th><th class="py-1.5 font-normal">Jadi</th></tr></thead>
          <tbody>
            <tr v-for="r in baris" :key="r.aturan" class="border-t border-garis">
              <td class="py-1.5 pr-3 text-ink-2">{{ r.aturan }}</td>
              <td class="py-1.5 pr-3 tabular-nums" :class="r.lulus === false ? 'text-turun' : ''">{{ fmt(r.alarm[0]) }} / {{ fmt(r.alarm[1]) }}</td>
              <td class="py-1.5 pr-3 text-muted">{{ r.ambang }}</td>
              <td class="py-1.5 text-ink-2">{{ r.jadi }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="overflow-x-auto">
        <div class="label mb-1">Lolos 12 bulan: strategi normal vs tanpa edge</div>
        <table class="w-full min-w-[560px] text-xs">
          <thead><tr class="text-left text-muted"><th class="py-1.5 pr-3 font-normal">Kriteria</th><th class="py-1.5 pr-3 font-normal">Normal (a) / (b)</th><th class="py-1.5 font-normal">Tanpa edge lolos</th></tr></thead>
          <tbody>
            <tr v-for="r in lolos" :key="r.kriteria" class="border-t border-garis">
              <td class="py-1.5 pr-3 text-ink-2">{{ r.kriteria }}</td>
              <td class="py-1.5 pr-3 tabular-nums">{{ fmt(r.normal[0]) }} / {{ fmt(r.normal[1]) }}</td>
              <td class="py-1.5 tabular-nums text-turun">{{ r.null.map(fmt).join(" · ") }}</td>
            </tr>
          </tbody>
        </table>
        <p class="m-0 mt-1 text-[11px] text-muted">{{ strategi === "h29" ? "Tanpa edge = 50% pilihan acak + 50% bobot sama, (a) lalu (b)." : "Tanpa edge = bobot sama, JII, pilihan acak; (a) lalu (b)." }} Di atas 20% berarti kriteria tidak bisa membedakan.</p>
      </div>
      <div v-if="horizon" class="rounded-2xl bg-surface-2 px-4 py-3 text-xs text-ink-2">
        <div class="mb-1 flex items-center gap-2 font-medium"><IkonInfo class="h-3.5 w-3.5 text-aksen" />Berapa lama sampai bisa membedakan edge?</div>
        <p class="m-0 mb-1">{{ d.horizon_bukti }}</p>
        <p class="m-0 text-muted">
          <template v-for="(x, reg) in horizon" :key="reg">
            {{ reg === "a" ? "2020+" : "dev" }}: <template v-for="(v, n) in x" :key="n">vs {{ NAMA_NULL[n] }} {{ v ? `${v} bln` : "tidak tercapai ≤ 60 bln" }}; </template>
          </template>
        </p>
      </div>
    </div>

    <button class="mt-3 ml-4 inline-flex items-center gap-1 text-xs text-muted hover:text-ink" @click="bukaAturan = !bukaAturan">
      Aturan yang dikunci<ChevronDown class="h-3.5 w-3.5 transition-transform" :class="bukaAturan ? 'rotate-180' : ''" />
    </button>
    <ol v-if="bukaAturan" class="m-0 mt-2 list-decimal space-y-1 pl-5 text-xs text-ink-2">
      <li v-for="a in d.aturan" :key="a">{{ a }}</li>
    </ol>
  </Panel>
</template>

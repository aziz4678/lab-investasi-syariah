<script setup>
import { computed } from "vue";
import { Check, X, Minus, Lightbulb, TriangleAlert, GraduationCap, FileText, ArrowRight, Hourglass, Telescope } from "lucide-vue-next";
import { persen } from "@/utils/format";
import TeksWarna from "@/components/common/TeksWarna.vue";
import GrafikHipotesis from "@/components/hipotesis/GrafikHipotesis.vue";
import Info from "@/components/common/Info.vue";
import BatangEdge from "@/components/hipotesis/BatangEdge.vue";

const props = defineProps({ h: Object, kelasStatus: Function, labelStatus: Function, lencana: Object, kelasLencana: Function, kategori: String, eksplorasiInfo: Object });
const emit = defineEmits(["buka"]);

const angka = computed(() => props.h.angka || []);
const utama = computed(() => angka.value.find((x) => x.utama) || angka.value[0] || null);
const edge = computed(() => angka.value.filter((a) => a.kotor != null && a.net != null && a.net_ket === "/trade"));
const belum = computed(() => props.h.status === "belum_dikunci" || props.h.status === "dikunci");

const visual = computed(() => {
  const v = (props.h.grafik || []).map((g) => ({ jenis: "grafik", g }));
  const e = edge.value.length ? [{ jenis: "edge" }] : [];
  return v.length ? [v[0], ...e, ...v.slice(1)] : e;
});
const visualUtama = computed(() => visual.value[0] || null);
const visualLain = computed(() => visual.value.slice(1));

const adaHoldout = computed(() => (props.h.kriteria || []).some((x) => x.holdout));
const kolomKriteria = computed(() => (adaHoldout.value ? ["dev", "holdout"] : ["dev"]));
const skor = (kol) => {
  const isi = (props.h.kriteria || []).filter((x) => x[kol]);
  return { lulus: isi.filter((x) => x[kol].ok === true).length, n: isi.length, titik: isi.map((x) => x[kol].ok) };
};
const LABEL_KOL = { dev: "Dev", holdout: "Holdout" };
const lebarKol = computed(() => (adaHoldout.value ? { wadah: "w-[58%]", sel: "w-[29%]" } : { wadah: "w-[42%]", sel: "w-[42%]" }));

function tiles(a) {
  if (!a) return [];
  const t = (label, v, f, ket) => ({ label, nilai: v == null ? "—" : f(v), kosong: v == null, ket: v == null ? "tidak tercatat" : ket, warna: v != null && /[+-]/.test(f(v)) });
  const pemb = t("Pembanding", a.bh, (v) => persen(v, 1), a.bh != null ? [a.bh_nama, a.bh_dd != null ? `DD ${persen(a.bh_dd, 1)}` : ""].filter(Boolean).join(" · ") : "");
  if (a.tile?.length) return [t(a.cagr_rentang ? "CAGR (median)" : "CAGR", a.cagr, (v) => persen(v, 1)), t(a.dd_label || "Max drawdown", a.dd, (v) => persen(v, 1)), ...a.tile.map((x) => ({ label: x[0], nilai: x[1], ket: x[2], kosong: false, warna: false })), pemb];
  return [
    t("CAGR", a.cagr, (v) => persen(v, 1)),
    t(a.dd_label || "Max drawdown", a.dd, (v) => persen(v, 1)),
    t(`Bersih ${a.net_ket || ""}`.trim(), a.net, (v) => persen(v, 2)),
    t("Jumlah trade", a.trade, (v) => v.toLocaleString("id-ID")),
    t("Winrate", a.wr, (v) => `${v.toLocaleString("id-ID", { maximumFractionDigits: 1 })}%`),
    t("Pembanding", a.bh, (v) => persen(v, 1), a.bh != null ? [a.bh_nama, a.bh_dd != null ? `DD ${persen(a.bh_dd, 1)}` : ""].filter(Boolean).join(" · ") : ""),
  ];
}

const kelasHasil = (h) => (h === "lulus" ? "bg-naik-bg text-naik" : h === "gagal" ? "bg-turun-bg text-turun" : "bg-surface-2 text-muted");
const judulKenapa = computed(() => (["paper", "uji_maju"].includes(props.h.status) ? "Kenapa lanjut" : props.h.status === "gagal" ? "Kenapa gagal" : props.h.status === "tidak_diadopsi" ? "Kenapa tidak diadopsi" : "Status"));
const tglFmt = (s) => (s ? new Date(s).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }) : null);
</script>

<template>
  <section :id="`h-${h.kode}`" class="@container panel overflow-hidden">
    <header class="flex flex-wrap items-start gap-x-6 gap-y-3 border-b border-garis px-5 py-4 @xl:px-6">
      <div class="flex min-w-0 basis-full items-start gap-3.5 @xl:basis-0 @xl:flex-1">
        <span class="grid h-12 min-w-12 shrink-0 place-items-center rounded-2xl px-2 text-[15px] font-semibold tracking-tight" :class="kelasStatus(h.status)">{{ h.kode }}</span>
        <div class="min-w-0">
          <h2 class="m-0 text-[18px] leading-snug font-medium">{{ h.nama }}</h2>
          <div class="mt-1.5 flex flex-wrap items-center gap-1.5">
            <span class="chip" :class="kelasStatus(h.status)">{{ labelStatus(h.status) }}</span>
            <span v-for="l in h.lencana || []" :key="l" class="chip" :class="kelasLencana(l)">{{ lencana[l] }}</span>
            <span class="chip bg-surface-2 text-ink-2">{{ kategori }}</span>
            <span class="text-xs text-muted">{{ tglFmt(h.tgl_uji) ? `Diuji ${tglFmt(h.tgl_uji)}` : "Belum diuji" }}</span>
          </div>
        </div>
      </div>
      <div v-if="kolomKriteria.some((k) => skor(k).n)" class="flex flex-wrap gap-4">
        <div v-for="kol in kolomKriteria" :key="kol" class="min-w-[88px]">
          <div class="text-[11px] text-muted">{{ LABEL_KOL[kol] }}</div>
          <div class="text-[20px] leading-7 font-medium tabular-nums">{{ skor(kol).lulus }}<span class="text-[14px] text-muted">/{{ skor(kol).n }}</span></div>
          <div class="mt-0.5 flex gap-1">
            <span v-for="(t, i) in skor(kol).titik" :key="i" class="h-1.5 w-3 rounded-full" :class="t === true ? 'bg-naik' : t === false ? 'bg-turun' : 'bg-surface-3'"></span>
          </div>
        </div>
      </div>
    </header>

    <div class="space-y-6 px-5 py-5 @xl:px-6">
      <p class="m-0 max-w-[880px] text-[15px] leading-relaxed text-ink">{{ h.awam }}</p>

      <template v-if="belum">
        <div class="flex items-start gap-3 rounded-2xl border border-dashed border-garis px-4 py-4">
          <Hourglass class="mt-0.5 h-5 w-5 shrink-0 text-muted" />
          <dl class="m-0 grid flex-1 gap-x-4 gap-y-2 text-[13px] @md:grid-cols-[130px_1fr]">
            <template v-for="(isi, label) in h.aturan" :key="label">
              <dt class="text-muted">{{ label }}</dt>
              <dd class="m-0 text-ink-2">{{ isi }}</dd>
            </template>
          </dl>
        </div>
        <div v-if="h.kriteria?.length" class="grid gap-4 @3xl:grid-cols-2">
          <div class="rounded-2xl border border-garis">
            <div class="border-b border-garis px-4 py-2.5 text-[13px] font-medium">Kriteria lulus (ditulis sebelum uji)</div>
            <ol class="m-0 list-none p-0">
              <li v-for="x in h.kriteria" :key="x.teks" class="border-b border-garis px-4 py-2.5 text-[13px] text-ink-2 last:border-b-0">{{ x.teks }}</li>
            </ol>
          </div>
          <div class="space-y-2">
            <div v-for="p in h.periode" :key="p.nama" class="rounded-2xl border border-dashed border-garis px-4 py-3">
              <div class="flex items-center gap-2"><span class="text-[13px] font-medium">{{ p.nama }}</span><span class="chip !h-5 text-muted">belum dibuka</span></div>
              <div class="mt-0.5 text-xs text-ink-2">{{ p.rentang }} · {{ p.universe }}</div>
              <div v-if="p.ket" class="mt-1 text-xs text-muted">{{ p.ket }}</div>
            </div>
          </div>
        </div>
      </template>

      <template v-else>
        <div class="grid items-start gap-6" :class="visualUtama && utama ? '@3xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]' : ''">
          <div v-if="visualUtama" class="min-w-0 rounded-2xl border border-garis p-4">
            <GrafikHipotesis v-if="visualUtama.jenis === 'grafik'" :g="visualUtama.g" :tinggi="240" />
            <BatangEdge v-else :grup="edge" />
          </div>
          <div v-if="utama" class="min-w-0">
            <div class="mb-2 text-xs text-muted"><span class="whitespace-nowrap">Angka utama ·</span> <span class="text-ink-2">{{ utama.periode }}</span></div>
            <div class="grid grid-cols-2 gap-2" :class="visualUtama ? '' : '@lg:grid-cols-3 @3xl:grid-cols-6'">
              <div v-for="t in tiles(utama)" :key="t.label" class="min-w-0 rounded-2xl bg-surface-2/70 px-3.5 py-3">
                <div class="truncate text-[11px] text-muted">{{ t.label }}</div>
                <div class="mt-0.5 text-[19px] leading-7 font-medium tabular-nums" :class="t.kosong ? 'text-muted' : ''">
                  <TeksWarna v-if="t.warna" :teks="t.nilai" /><template v-else>{{ t.nilai }}</template>
                </div>
                <div v-if="t.ket" class="line-clamp-2 text-[11px] leading-snug text-muted" :title="t.ket">{{ t.ket }}</div>
              </div>
            </div>
            <p v-if="utama.ket" class="m-0 mt-2 text-xs leading-relaxed text-muted"><TeksWarna :teks="utama.ket" /></p>
            <details v-if="utama.info" class="group mt-2 rounded-2xl bg-surface-2/60 px-3.5 py-2.5 text-xs leading-relaxed text-ink-2">
              <summary class="flex cursor-pointer list-none items-center gap-2 font-medium text-aksen [&::-webkit-details-marker]:hidden">
                <span class="group-open:hidden">Apa itu simulasi Monte Carlo?</span><span class="hidden group-open:inline">Tutup penjelasan</span>
              </summary>
              <p class="m-0 mt-1.5">{{ utama.info }}</p>
            </details>
            <div v-if="utama.ekstra?.length" class="mt-2 flex flex-wrap gap-x-4 text-xs text-ink-2">
              <span v-for="e in utama.ekstra" :key="e[0]">{{ e[0] }}: <TeksWarna :teks="e[1]" /></span>
            </div>
          </div>
        </div>

        <div v-if="visualLain.length" class="grid gap-4" :class="visualLain.length > 1 ? '@2xl:grid-cols-2' : ''">
          <div v-for="(v, i) in visualLain" :key="i" class="min-w-0 rounded-2xl border border-garis p-4">
            <GrafikHipotesis v-if="v.jenis === 'grafik'" :g="v.g" :tinggi="200" />
            <BatangEdge v-else :grup="edge" />
          </div>
        </div>

        <div v-if="angka.length > 1" class="overflow-x-auto rounded-2xl border border-garis">
          <table class="tabel">
            <thead><tr><th>Periode / set</th><th class="!text-right">CAGR</th><th class="!text-right">Max DD</th><th class="!text-right">Trade</th><th class="!text-right">Winrate</th><th class="!text-right">Bersih</th></tr></thead>
            <tbody>
              <tr v-for="a in angka" :key="a.periode">
                <td class="text-ink-2">{{ a.periode }}<span v-if="a.utama" class="chip ml-2 !h-5 bg-surface-2 text-muted">penentu</span><span v-if="a.info" class="ml-1.5"><Info :teks="a.info" /></span></td>
                <td class="text-right"><TeksWarna v-if="a.cagr != null" :teks="persen(a.cagr, 1)" /><span v-else class="text-muted">—</span>
                  <div v-if="a.cagr_rentang" class="text-[11px] whitespace-nowrap text-muted">{{ persen(a.cagr_rentang[0], 1) }} s/d {{ persen(a.cagr_rentang[1], 1) }}</div></td>
                <td class="text-right"><TeksWarna v-if="a.dd != null" :teks="persen(a.dd, 1)" /><span v-else class="text-muted">—</span>
                  <div v-if="a.dd_rentang" class="text-[11px] whitespace-nowrap text-muted">{{ persen(a.dd_rentang[0], 1) }} s/d {{ persen(a.dd_rentang[1], 1) }}</div></td>
                <td class="text-right">{{ a.trade != null ? a.trade.toLocaleString("id-ID") : "—" }}</td>
                <td class="text-right">{{ a.wr != null ? `${a.wr}%` : "—" }}</td>
                <td class="text-right"><TeksWarna v-if="a.net != null" :teks="persen(a.net, 2)" /><span v-else class="text-muted">—</span></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="h.periode?.length" class="flex flex-wrap items-stretch gap-2">
          <template v-for="(p, i) in h.periode" :key="p.nama">
            <ArrowRight v-if="i" class="hidden h-4 w-4 shrink-0 self-center text-muted @lg:block" />
            <div class="min-w-[180px] flex-1 rounded-2xl px-4 py-3" :class="p.dibuka ? 'bg-surface-2/70' : 'border border-dashed border-garis'">
              <div class="flex flex-wrap items-center gap-1.5">
                <span class="text-[13px] font-medium">{{ p.nama }}</span>
                <span v-if="p.hasil" class="chip !h-5" :class="kelasHasil(p.hasil)">{{ p.hasil }}{{ p.skor ? ` ${p.skor}` : "" }}</span>
                <span v-else-if="!p.dibuka" class="chip !h-5 text-muted">tidak dibuka</span>
              </div>
              <div class="mt-0.5 text-xs text-ink-2">{{ p.rentang }} · {{ p.universe }}</div>
              <div v-if="p.ket" class="mt-1 text-xs text-muted">{{ p.ket }}</div>
            </div>
          </template>
        </div>

        <div class="grid gap-4 @4xl:grid-cols-2">
          <div v-if="h.kriteria?.length" class="min-w-0 rounded-2xl border border-garis">
            <div class="flex items-center justify-between gap-3 border-b border-garis px-4 py-2.5 text-[13px] font-medium">
              <span>Kriteria lulus</span>
              <span class="flex gap-3 text-xs font-normal text-muted" :class="lebarKol.wadah"><span v-for="kol in kolomKriteria" :key="kol" class="flex-1">{{ LABEL_KOL[kol] }}</span></span>
            </div>
            <ul class="m-0 list-none p-0">
              <li v-for="x in h.kriteria" :key="x.teks" class="flex items-start gap-3 border-b border-garis px-4 py-2.5 text-[13px] last:border-b-0">
                <span class="min-w-0 flex-1 text-ink-2">{{ x.teks }}</span>
                <span v-for="kol in kolomKriteria" :key="kol" class="flex shrink-0 items-start gap-1.5 text-xs" :class="lebarKol.sel">
                  <template v-if="x[kol]">
                    <Check v-if="x[kol].ok === true" class="h-4 w-4 shrink-0 text-naik" />
                    <X v-else-if="x[kol].ok === false" class="h-4 w-4 shrink-0 text-turun" />
                    <Minus v-else class="h-4 w-4 shrink-0 text-muted" />
                    <TeksWarna class="min-w-0 break-words" :class="String(x[kol].nilai).startsWith('tidak tercatat') ? 'text-muted' : ''" :teks="x[kol].nilai" />
                  </template>
                  <span v-else class="text-muted">—</span>
                </span>
              </li>
            </ul>
          </div>
          <div class="min-w-0 rounded-2xl bg-surface-2/60 px-4 py-3.5">
            <div class="mb-2 text-[13px] font-medium">Aturan</div>
            <dl class="m-0 grid gap-x-4 gap-y-2 text-[13px] @md:grid-cols-[120px_1fr]">
              <template v-for="(isi, label) in h.aturan" :key="label">
                <dt class="text-muted">{{ label }}</dt>
                <dd class="m-0 text-ink-2">{{ isi }}</dd>
              </template>
            </dl>
          </div>
        </div>

        <div v-if="h.tabel" class="min-w-0">
          <div class="mb-2 text-[13px] font-medium">{{ h.tabel.judul }}</div>
          <div class="overflow-x-auto rounded-2xl border border-garis">
            <table class="tabel">
              <thead><tr><th v-for="c in h.tabel.kolom" :key="c">{{ c }}</th></tr></thead>
              <tbody>
                <tr v-for="(b, i) in h.tabel.baris" :key="i">
                  <td v-for="(c, j) in b" :key="j" :class="j === 0 ? 'text-ink-2' : ''"><TeksWarna :teks="c" /></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>

      <div class="grid gap-3 @3xl:grid-cols-3">
        <div class="rounded-2xl bg-surface-2/60 px-4 py-3.5">
          <div class="mb-1 flex items-center gap-1.5 text-[13px] font-medium"><Lightbulb class="h-4 w-4 text-muted" />{{ judulKenapa }}</div>
          <p class="m-0 text-[13px] text-ink-2"><TeksWarna :teks="h.kenapa" /></p>
        </div>
        <div class="rounded-2xl bg-surface-2/60 px-4 py-3.5">
          <div class="mb-1 flex items-center gap-1.5 text-[13px] font-medium"><TriangleAlert class="h-4 w-4 text-kuning" />Kelemahan</div>
          <ul v-if="h.kelemahan?.length" class="m-0 list-disc space-y-1 pl-4 text-[13px] text-ink-2">
            <li v-for="x in h.kelemahan" :key="x"><TeksWarna :teks="x" /></li>
          </ul>
          <p v-else class="m-0 text-[13px] text-muted">—</p>
        </div>
        <div class="rounded-2xl bg-aksen-lembut px-4 py-3.5">
          <div class="mb-1 flex items-center gap-1.5 text-[13px] font-medium"><GraduationCap class="h-4 w-4 text-aksen" />Pelajaran</div>
          <p class="m-0 text-[13px] text-ink-2">{{ h.pelajaran || "—" }}</p>
        </div>
      </div>

      <div v-if="h.eksplorasi" class="rounded-2xl border border-dashed border-garis px-4 py-3.5">
        <div class="flex flex-wrap items-center gap-2">
          <Telescope class="h-4 w-4 shrink-0 text-muted" />
          <span class="text-[13px] font-medium">{{ eksplorasiInfo?.judul || "Eksplorasi 2020+ (Okt 2026) — bukan bukti" }}</span>
          <span class="chip !h-5 bg-surface-2 text-ink-2">{{ h.eksplorasi.lulus_semua ? "semua kriteria terpenuhi" : "tetap gagal" }} · {{ h.eksplorasi.lulus }}</span>
          <span class="chip !h-5 bg-surface-2 text-muted">status tetap {{ labelStatus(h.status) }}</span>
        </div>
        <div class="mt-2.5 flex flex-wrap gap-x-5 gap-y-1.5 text-xs">
          <span v-for="m in h.eksplorasi.metrik" :key="m[0]" class="text-muted">{{ m[0] }} <span class="font-medium text-ink-2 tabular-nums"><TeksWarna :teks="m[1]" /></span></span>
        </div>
        <p v-if="h.eksplorasi.gagal_di?.length" class="m-0 mt-2 text-xs text-ink-2">Tidak terpenuhi: {{ h.eksplorasi.gagal_di.join(" · ") }}</p>
        <p v-if="h.eksplorasi.catatan" class="m-0 mt-1.5 text-xs text-ink-2"><TeksWarna :teks="h.eksplorasi.catatan" /></p>
        <p class="m-0 mt-2 text-[11px] leading-relaxed text-muted">Bukan bukti: {{ eksplorasiInfo?.catatan }} Periode {{ eksplorasiInfo?.periode }}, {{ eksplorasiInfo?.universe }}.</p>
      </div>

      <div class="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted">
        <span>Dikunci {{ tglFmt(h.tgl_kunci) || "—" }}</span>
        <span class="inline-flex items-center gap-1"><FileText class="h-3.5 w-3.5" />{{ h.sumber }}</span>
        <span v-if="h.terkait?.length" class="flex flex-wrap items-center gap-1">
          Terkait
          <button v-for="t in h.terkait" :key="t" class="chip bg-surface-2 text-ink-2 hover:bg-surface-3" @click="emit('buka', t)">{{ t }}</button>
        </span>
      </div>
    </div>
  </section>
</template>

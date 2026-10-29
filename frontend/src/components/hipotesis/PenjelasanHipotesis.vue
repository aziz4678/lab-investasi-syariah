<script setup>
import { ref, computed, watch } from "vue";
import { FileText, ChevronDown, MessageCircleQuestion, ListOrdered, Scale, Flag, Lightbulb, BookOpen, CircleCheck, CircleX } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { persen } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import Pemutar from "@/components/common/Pemutar.vue";
import TeksWarna from "@/components/common/TeksWarna.vue";

const props = defineProps({ kode: String, kodeAda: Object, analisis: Array, status: String });
const emit = defineEmits(["buka"]);

const isi = ref(null);
const siap = ref(false);
const muat = ref(false);
const gagal = ref(false);

watch(() => props.kode, async (k) => {
  if (!k) return;
  muat.value = true;
  gagal.value = false;
  const hasil = await ambil(`hipotesis/${encodeURIComponent(k)}/penjelasan`).catch(() => null);
  if (props.kode !== k) return;
  isi.value = hasil;
  gagal.value = !hasil;
  muat.value = false;
  siap.value = true;
}, { immediate: true });

const awam = computed(() => isi.value?.awam || null);
const pembanding = computed(() => awam.value?.pelaku.find((p) => p.pembanding) || null);
const lulus = computed(() => ["paper", "uji_maju"].includes(props.status));

function warnaPelaku(p) {
  if (p.id === props.kode) return "var(--series-1)";
  if (p.pembanding) return "var(--series-2)";
  return "var(--series-3)";
}

function nilaiTeks(mt, v) {
  if (v === null || v === undefined) return "—";
  if (mt.satuan === "%") return persen(v, mt.id.startsWith("net") || mt.id === "kotor" ? 2 : 1);
  if (mt.id === "trade") return v.toLocaleString("id-ID");
  return v.toLocaleString("id-ID", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function lebar(mt, v) {
  if (v === null || v === undefined) return "0%";
  const maks = Math.max(...Object.values(mt.nilai).map((x) => Math.abs(x ?? 0)));
  return maks ?`${Math.max((Math.abs(v ?? 0) / maks) * 100, 1.5)}%` : "0%";
}

function vonis(mt) {
  const p = pembanding.value;
  if (!mt.arah || !p || p.id === props.kode) return null;
  const a = mt.nilai[props.kode];
  const b = mt.nilai[p.id];
  if (a == null || b == null) return null;
  const d = (a - b) * mt.arah;
  if (Math.abs(d) < 1e-9) return { teks: "setara", kelas: "bg-surface-2 text-muted" };
  return d > 0 ? { teks: "lebih baik", kelas: "bg-naik-bg text-naik" } : { teks: "lebih buruk", kelas: "bg-turun-bg text-turun" };
}

const skor = computed(() => {
  if (!awam.value || !pembanding.value) return [];
  return awam.value.kelompok.map((g) => {
    const v = g.metrik.map(vonis).filter(Boolean);
    return { nama: g.nama, menang: v.filter((x) => x.teks === "lebih baik").length, total: v.length };
  });
});

const POLA = /(\*\*[^*]+\*\*|`[^`]+`|\bH\d{1,2}[a-g]?\b)/;
function potong(teks) {
  return String(teks).split(POLA).filter((x) => x).map((x) => {
    if (x.startsWith("**") && x.endsWith("**") && x.length > 4) return { t: "b", x: x.slice(2, -2) };
    if (x.startsWith("`") && x.endsWith("`") && x.length > 2) return { t: "c", x: x.slice(1, -1) };
    if (/^H\d{1,2}[a-g]?$/.test(x) && props.kodeAda?.has(x) && x !== props.kode) return { t: "k", x };
    return { t: "s", x };
  });
}
const INDEN = ["pl-0", "pl-5", "pl-10"];
</script>

<template>
  <Kerangka v-if="!siap" panel jenis="baris" :n="10" />
  <Panel v-else :judul="`Penjelasan lengkap · ${kode}`" ket="Dalam bahasa sederhana: pertanyaannya, cara mengujinya, hasil dibanding pembanding, dan artinya untuk kita">
    <template v-if="muat" #aksi><Pemutar /></template>

    <p v-if="gagal" class="m-0 rounded-2xl bg-turun-bg px-4 py-3 text-[13px] text-turun">Penjelasan gagal dimuat.</p>

    <div v-else class="@container space-y-5" :class="muat ? 'opacity-60 transition-opacity' : ''">
      <template v-if="awam">
        <div class="flex gap-3 rounded-2xl px-4 py-4" :class="lulus ? 'bg-naik-bg' : 'bg-surface-2/70'">
          <component :is="lulus ? CircleCheck : CircleX" class="mt-0.5 h-5 w-5 shrink-0" :class="lulus ? 'text-naik' : 'text-turun'" />
          <div class="min-w-0">
            <div class="text-[11px] font-medium tracking-wide text-muted uppercase">Jawaban singkat</div>
            <p class="m-0 mt-1 max-w-[900px] text-[15px] leading-relaxed text-ink"><TeksWarna :teks="awam.jawaban" /></p>
          </div>
        </div>

        <div class="grid gap-4 @3xl:grid-cols-2">
          <div class="space-y-4">
            <div>
              <div class="mb-1.5 flex items-center gap-1.5 text-[13px] font-medium"><MessageCircleQuestion class="h-4 w-4 text-aksen" />Pertanyaannya</div>
              <p class="m-0 text-[14px] leading-relaxed text-ink-2">{{ awam.pertanyaan }}</p>
            </div>
            <div>
              <div class="mb-1.5 flex items-center gap-1.5 text-[13px] font-medium"><ListOrdered class="h-4 w-4 text-aksen" />Cara mengujinya</div>
              <ol class="m-0 list-none space-y-2 p-0">
                <li v-for="(c, i) in awam.cara" :key="i" class="flex gap-2.5 text-[13px] leading-relaxed text-ink-2">
                  <span class="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-surface-2 text-[11px] font-medium text-ink">{{ i + 1 }}</span>
                  <span class="min-w-0">{{ c }}</span>
                </li>
              </ol>
            </div>
          </div>
          <div class="space-y-4">
            <div class="rounded-2xl border border-garis px-4 py-3.5">
              <div class="mb-1.5 flex items-center gap-1.5 text-[13px] font-medium"><Scale class="h-4 w-4" style="color: var(--series-2)" />Dibanding apa?</div>
              <p class="m-0 text-[13px] leading-relaxed text-ink-2">{{ awam.pembanding }}</p>
            </div>
            <div class="rounded-2xl border border-garis px-4 py-3.5">
              <div class="mb-1.5 flex items-center gap-1.5 text-[13px] font-medium"><Flag class="h-4 w-4 text-kuning" />Syarat lulus</div>
              <p class="m-0 text-[13px] leading-relaxed text-ink-2">{{ awam.syarat }}</p>
            </div>
          </div>
        </div>

        <div>
          <div class="flex flex-wrap items-end justify-between gap-x-4 gap-y-2">
            <div>
              <div class="text-[15px] font-medium">Hasilnya</div>
              <div class="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-2">
                <span v-for="p in awam.pelaku" :key="p.id" class="inline-flex items-center gap-1.5">
                  <span class="inline-block h-2.5 w-2.5 rounded-[3px]" :style="{ background: warnaPelaku(p) }"></span>
                  <span :class="p.id === kode ? 'font-medium text-ink' : ''">{{ p.id }} · {{ p.nama }}</span>
                  <span v-if="p.pembanding" class="text-muted">(pembanding)</span>
                </span>
              </div>
            </div>
            <div v-if="skor.length" class="flex flex-wrap gap-1.5">
              <span v-for="s in skor" :key="s.nama" class="chip !h-auto min-h-6 max-w-full !whitespace-normal bg-surface-2 py-0.5 text-ink-2">{{ kode }} menang {{ s.menang }}/{{ s.total }} · {{ s.nama.replace(/ 20\d\d-20\d\d.*/, '') }}</span>
            </div>
          </div>

          <div class="mt-3 grid gap-4" :class="awam.kelompok.length > 1 ? '@3xl:grid-cols-2' : ''">
            <div v-for="g in awam.kelompok" :key="g.nama" class="min-w-0 rounded-2xl bg-surface-2/50 px-4 py-4">
              <div class="text-[14px] font-medium">{{ g.nama }}</div>
              <p v-if="g.ket" class="m-0 mt-0.5 text-xs leading-relaxed text-muted">{{ g.ket }}</p>
              <div class="mt-3 space-y-4">
                <div v-for="mt in g.metrik" :key="mt.id">
                  <div class="mb-1.5 flex items-baseline justify-between gap-2">
                    <span class="text-[13px] font-medium">{{ mt.nama }}<span v-if="mt.ket" class="ml-1.5 text-[11px] font-normal text-muted">{{ mt.ket }}</span></span>
                    <span v-if="vonis(mt)" class="chip !h-5 shrink-0 !text-[10.5px]" :class="vonis(mt).kelas">{{ vonis(mt).teks }}</span>
                  </div>
                  <div class="space-y-1">
                    <div v-for="p in awam.pelaku" :key="p.id" class="grid grid-cols-[44px_minmax(0,1fr)_64px] items-center gap-2">
                      <span class="text-[11.5px]" :class="p.id === kode ? 'font-medium text-ink' : 'text-muted'">{{ p.id }}</span>
                      <span class="h-3.5 overflow-hidden rounded-full bg-surface">
                        <span class="block h-full rounded-full transition-[width] duration-500" :style="{ width: lebar(mt, mt.nilai[p.id]), background: (mt.nilai[p.id] ?? 0) < 0 ? 'var(--turun)' : warnaPelaku(p), opacity: p.id === kode || p.pembanding ? 1 : 0.55 }"></span>
                      </span>
                      <span class="text-right text-[12px] tabular-nums" :class="[p.id === kode ? 'font-medium' : '', (mt.nilai[p.id] ?? 0) < 0 ? 'text-turun' : p.id === kode ? 'text-ink' : 'text-ink-2']">{{ nilaiTeks(mt, mt.nilai[p.id]) }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="rounded-2xl bg-aksen-lembut px-4 py-4">
          <div class="mb-2 flex items-center gap-1.5 text-[13px] font-medium"><Lightbulb class="h-4 w-4 text-aksen" />Artinya untuk kita</div>
          <ul class="m-0 list-none space-y-2 p-0">
            <li v-for="(x, i) in awam.arti" :key="i" class="flex gap-2.5 text-[13px] leading-relaxed text-ink-2">
              <span class="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-aksen"></span>
              <span class="min-w-0"><TeksWarna :teks="x" /></span>
            </li>
          </ul>
        </div>

        <div v-if="awam.istilah?.length">
          <div class="mb-2 flex items-center gap-1.5 text-[13px] font-medium"><BookOpen class="h-4 w-4 text-muted" />Kamus istilah</div>
          <dl class="m-0 grid gap-x-6 gap-y-2.5 @2xl:grid-cols-2">
            <div v-for="t in awam.istilah" :key="t.id" class="min-w-0">
              <dt class="text-[12.5px] font-medium">{{ t.nama }}</dt>
              <dd class="m-0 text-xs leading-relaxed text-ink-2"><TeksWarna :teks="t.arti" /></dd>
            </div>
          </dl>
        </div>
      </template>

      <p v-else class="m-0 rounded-2xl bg-surface-2/60 px-4 py-3 text-[13px] text-ink-2">Penjelasan sederhana untuk hipotesis ini belum ditulis. Sementara itu, catatan teknisnya ada di bawah.</p>

      <div v-if="analisis?.length">
        <div class="mb-2 text-[11px] font-medium tracking-wide text-muted uppercase">Analisis pendukung terkait · deskriptif, bukan uji</div>
        <div class="grid gap-3 @3xl:grid-cols-2">
          <div v-for="a in analisis" :key="a.id" class="rounded-2xl bg-surface-2/60 px-4 py-3.5">
            <div class="flex flex-wrap items-baseline justify-between gap-2">
              <span class="text-[14px] font-medium">{{ a.nama }}</span>
              <span class="text-xs text-muted">{{ a.tgl }}</span>
            </div>
            <p class="m-0 mt-1 text-[13px] text-ink-2"><TeksWarna :teks="a.isi" /></p>
            <div class="mt-2 flex flex-wrap items-center gap-1 text-xs">
              <button v-for="t in a.terkait.filter((t) => t !== kode)" :key="t" class="chip bg-surface text-ink-2 ring-1 ring-garis hover:bg-surface-3" @click="emit('buka', t)">{{ t }}</button>
            </div>
          </div>
        </div>
      </div>

      <details v-if="isi?.bagian?.length" class="group rounded-2xl border border-garis" :open="!awam">
        <summary class="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-[13px] [&::-webkit-details-marker]:hidden">
          <FileText class="h-4 w-4 shrink-0 text-muted" />
          <span class="font-medium">Catatan teknis asli</span>
          <span class="hidden truncate text-xs text-muted sm:inline">{{ isi.berkas }} · untuk yang ingin detail lengkap</span>
          <ChevronDown class="ml-auto h-4 w-4 shrink-0 text-muted transition-transform group-open:rotate-180" />
        </summary>
        <div class="space-y-6 border-t border-garis px-4 pt-4 pb-5">
          <article v-for="b in isi.bagian" :key="b.baris" class="min-w-0">
            <div class="mb-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <h3 class="m-0 text-[14px] font-medium leading-snug">{{ b.judul }}</h3>
              <span class="text-[11px] text-muted">baris {{ b.baris }}</span>
            </div>
            <div class="max-w-[860px] space-y-2 text-[13px] leading-relaxed text-ink-2">
              <template v-for="(x, i) in b.blok" :key="i">
                <h4 v-if="x.t === 'h'" class="m-0 pt-3 text-[13.5px] font-medium text-ink">
                  <template v-for="(s, j) in potong(x.x)" :key="j"><code v-if="s.t === 'c'" class="kode">{{ s.x }}</code><span v-else>{{ s.x }}</span></template>
                </h4>
                <div v-else-if="x.t === 'tabel'" class="overflow-x-auto rounded-2xl border border-garis">
                  <table class="tabel !text-xs">
                    <thead><tr><th v-for="(k, j) in x.kolom" :key="j">{{ k }}</th></tr></thead>
                    <tbody>
                      <tr v-for="(r, j) in x.baris" :key="j">
                        <td v-for="(c, n) in r" :key="n" class="!h-auto !whitespace-normal py-2 tabular-nums">
                          <template v-for="(s, q) in potong(c)" :key="q"><b v-if="s.t === 'b'" class="font-medium text-ink"><TeksWarna :teks="s.x" /></b><code v-else-if="s.t === 'c'" class="kode">{{ s.x }}</code><button v-else-if="s.t === 'k'" class="font-medium text-aksen hover:underline" @click="emit('buka', s.x)">{{ s.x }}</button><TeksWarna v-else :teks="s.x" /></template>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-else-if="x.t === 'li'" class="flex gap-2" :class="INDEN[x.n]">
                  <span class="w-4 shrink-0 text-right text-muted">{{ x.m || "•" }}</span>
                  <span class="min-w-0 flex-1">
                    <template v-for="(s, j) in potong(x.x)" :key="j"><b v-if="s.t === 'b'" class="font-medium text-ink"><TeksWarna :teks="s.x" /></b><code v-else-if="s.t === 'c'" class="kode">{{ s.x }}</code><button v-else-if="s.t === 'k'" class="font-medium text-aksen hover:underline" @click="emit('buka', s.x)">{{ s.x }}</button><TeksWarna v-else :teks="s.x" /></template>
                  </span>
                </div>
                <p v-else class="m-0">
                  <template v-for="(s, j) in potong(x.x)" :key="j"><b v-if="s.t === 'b'" class="font-medium text-ink"><TeksWarna :teks="s.x" /></b><code v-else-if="s.t === 'c'" class="kode">{{ s.x }}</code><button v-else-if="s.t === 'k'" class="font-medium text-aksen hover:underline" @click="emit('buka', s.x)">{{ s.x }}</button><TeksWarna v-else :teks="s.x" /></template>
                </p>
              </template>
            </div>
          </article>
        </div>
      </details>
    </div>
  </Panel>
</template>

<style scoped>
.kode {
  border-radius: 6px;
  background: var(--surface-2);
  padding: 1px 5px;
  font-size: 0.92em;
  overflow-wrap: anywhere;
}
</style>

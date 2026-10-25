<script setup>
import { ref, computed, onMounted, onUnmounted, provide } from "vue";
import { House, TrendingUp, Coins, ChartPie, Layers, Compass, FlaskConical, ScanSearch, BookOpen, Sun, Moon, Monitor, PanelLeftClose, PanelLeftOpen, RefreshCw } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { modeTema, setTema, temaGelap } from "@/composables/tema";
import logoTerang from "@/assets/logo/logo.svg";
import logoGelap from "@/assets/logo/logo-gelap.svg";
import BerandaView from "@/views/BerandaView.vue";
import FollowTrenView from "@/views/riset/FollowTrenView.vue";
import DividenView from "@/views/riset/DividenView.vue";
import ReksadanaView from "@/views/produk/ReksadanaView.vue";
import EtfView from "@/views/produk/EtfView.vue";
import RencanaView from "@/views/lainnya/RencanaView.vue";
import HipotesisView from "@/views/riset/HipotesisView.vue";
import EmitenView from "@/views/produk/EmitenView.vue";
import PanduanView from "@/views/lainnya/PanduanView.vue";

const NAMA_APP = "Lab Investasi";
const logo = computed(() => (temaGelap() ? logoGelap : logoTerang));
const GRUP = [
  { judul: "", isi: [{ k: "beranda", l: "Beranda", ikon: House }] },
  { judul: "Riset / Strategi", isi: [{ k: "tren52", l: "Follow Tren", ikon: TrendingUp, ket: "Saham syariah IDX", sub: "Saham syariah", lencana: "Paper" }, { k: "dividen", l: "Dividen", ikon: Coins, ket: "Pemburu dividen saham syariah", sub: "Daftar & kalender" }, { k: "hipotesis", l: "Hipotesis", ikon: FlaskConical, ket: "Semua uji riset", sub: "Semua uji H0-H23" }] },
  { judul: "Produk", isi: [{ k: "emiten", l: "Emiten", ikon: ScanSearch, ket: "Saham IDX", sub: "Saham IDX" }, { k: "reksadana", l: "Reksa Dana", ikon: ChartPie, ket: "Reksa dana & sukuk syariah", sub: "Termasuk sukuk" }, { k: "etf", l: "ETF", ikon: Layers, ket: "ETF Indonesia & luar negeri", sub: "Indonesia & luar" }] },
  { judul: "Lainnya", isi: [{ k: "rencana", l: "Rencana", ikon: Compass, ket: "Section berikutnya" }, { k: "panduan", l: "Panduan", ikon: BookOpen }] },
];
const TAB = GRUP.flatMap((g) => g.isi);
let simpanLebar = "1";
try {
  simpanLebar = localStorage.getItem("sidebar_lebar") ?? "1";
} catch {
  simpanLebar = "1";
}
const lebar = ref(simpanLebar === "1");
function alihSidebar() {
  lebar.value = !lebar.value;
  try {
    localStorage.setItem("sidebar_lebar", lebar.value ? "1" : "0");
  } catch {
    lebar.value = lebar.value;
  }
}
const SUB_TAB = { tren52: ["paper", "backtest", "aturan", "riset"], dividen: ["daftar", "kalkulator", "uji", "trap", "aturan"], reksadana: ["katalog", "sukuk", "banding", "alokasi", "data"], etf: ["daftar", "luar", "banding", "data"] };
const LAMA = { paper: ["tren52", "paper"], backtest: ["tren52", "backtest"], riset: ["tren52", "riset"] };
const URUT_TEMA = ["sistem", "terang", "gelap"];
const IKON_TEMA = { sistem: Monitor, terang: Sun, gelap: Moon };
const LABEL_TEMA = { sistem: "Tema: ikuti sistem", terang: "Tema: terang", gelap: "Tema: gelap" };

const tab = ref("beranda");
const subTab = ref({ tren52: "paper", dividen: "daftar", reksadana: "katalog", etf: "daftar" });
const sub = computed(() => subTab.value[tab.value]);
const status = ref(null);
const kodeEmiten = ref("");
const aktif = computed(() => TAB.find((t) => t.k === tab.value));
const judul = computed(() => aktif.value?.l);
const atasJudul = computed(() => (aktif.value?.ket ? `${NAMA_APP} · ${aktif.value.ket}` : NAMA_APP));

async function muatStatus() {
  status.value = await ambil("status").catch(() => null);
}

function tulisHash() {
  const h = SUB_TAB[tab.value] ? `${tab.value}/${sub.value}` : tab.value === "emiten" && kodeEmiten.value ? `emiten/${kodeEmiten.value}` : tab.value;
  history.replaceState(null, "", `#${h}`);
}

function pilih(k, s) {
  if (LAMA[k]) [k, s] = LAMA[k];
  tab.value = k;
  if (SUB_TAB[k]?.includes(s)) subTab.value = { ...subTab.value, [k]: s };
  tulisHash();
  if (k === "beranda" && s === "data") setTimeout(() => document.getElementById("sumber-data")?.scrollIntoView({ behavior: "smooth" }), 400);
  else window.scrollTo({ top: 0, behavior: "smooth" });
}

function gantiSub(s) {
  subTab.value = { ...subTab.value, [tab.value]: s };
  tulisHash();
}

function gantiTema() {
  setTema(URUT_TEMA[(URUT_TEMA.indexOf(modeTema.value) + 1) % URUT_TEMA.length]);
}

provide("status", status);
provide("muatStatus", muatStatus);
provide("pindahTab", pilih);
provide("kodeEmiten", kodeEmiten);
provide("bukaEmiten", (kode) => {
  kodeEmiten.value = kode;
  pilih("emiten");
});

const build = ref(null);
const adaBaru = ref(false);
let pantau = null;
async function cekBuild() {
  try {
    const r = await fetch("/api/build", { cache: "no-store" });
    if (!r.ok) return;
    const b = (await r.json()).build;
    if (build.value == null) build.value = b;
    else if (b && b !== build.value) adaBaru.value = true;
  } catch {}
}
onUnmounted(() => clearInterval(pantau));
const muatUlang = () => window.location.reload();

onMounted(() => {
  cekBuild();
  pantau = setInterval(cekBuild, 20000);
  const [h, x] = location.hash.replace("#", "").split("/");
  if (LAMA[h]) pilih(h);
  else if (TAB.some((t) => t.k === h)) {
    tab.value = h;
    if (SUB_TAB[h]?.includes(x)) subTab.value = { ...subTab.value, [h]: x };
    if (h === "emiten" && x) kodeEmiten.value = x.toUpperCase();
  }
  muatStatus();
});
</script>

<template>
  <div class="min-h-screen transition-[padding] duration-200" :class="lebar ? 'md:pl-[248px]' : 'md:pl-[88px]'">
    <aside class="fixed inset-y-0 left-0 z-30 hidden flex-col border-r border-garis bg-sidebar py-6 transition-[width] duration-200 md:flex"
      :class="lebar ? 'w-[248px] px-4' : 'w-[88px] items-center px-0'">
      <div class="mb-7 flex items-center gap-3" :class="lebar ? 'px-2' : ''">
        <img :src="logo" alt="" class="h-10 w-10 shrink-0" :title="NAMA_APP" />
        <div v-if="lebar" class="min-w-0 leading-tight">
          <div class="font-medium">{{ NAMA_APP }}</div>
          <div class="text-xs text-muted">Syariah</div>
        </div>
      </div>
      <nav class="flex flex-1 flex-col overflow-y-auto" :class="lebar ? '' : 'items-center'">
        <div v-for="(g, i) in GRUP" :key="i" :class="i ? 'mt-5' : ''">
          <div v-if="g.judul && lebar" class="mb-1.5 px-3 text-[11px] font-medium tracking-wide text-muted uppercase">{{ g.judul }}</div>
          <span v-else-if="i && !lebar" class="mx-auto mb-3 block h-px w-8 bg-garis"></span>
          <div class="flex flex-col gap-1" :class="lebar ? '' : 'items-center gap-2'">
            <button v-for="t in g.isi" :key="t.k" @click="pilih(t.k)" :title="t.l" :aria-label="t.l"
              class="group relative flex items-center rounded-2xl transition"
              :class="[lebar ? 'h-11 w-full gap-3 px-3 text-left' : 'h-11 w-11 justify-center', tab === t.k ? 'bg-surface-2 text-ink' : 'text-muted hover:bg-surface-2/60 hover:text-ink']">
              <component :is="t.ikon" class="h-5 w-5 shrink-0" :stroke-width="tab === t.k ? 2.2 : 1.8" />
              <template v-if="lebar">
                <span class="min-w-0 flex-1 leading-tight">
                  <span class="block truncate text-[13px]" :class="tab === t.k ? 'font-medium' : ''">{{ t.l }}</span>
                  <span v-if="t.ket" class="block truncate text-[11px] text-muted">{{ t.sub || t.ket }}</span>
                </span>
                <span v-if="t.lencana" class="chip !h-5 !px-2 !text-[10px] bg-aksen-lembut text-aksen">{{ t.lencana }}</span>
              </template>
              <span v-else class="pointer-events-none absolute left-full ml-3 hidden rounded-full bg-surface-3 px-3 py-1 text-xs whitespace-nowrap text-ink shadow-lg group-hover:block">{{ t.l }}</span>
            </button>
          </div>
        </div>
      </nav>
      <div class="mt-4 flex gap-1" :class="lebar ? 'items-center' : 'flex-col items-center gap-2'">
        <button @click="gantiTema" :title="LABEL_TEMA[modeTema]" :aria-label="LABEL_TEMA[modeTema]"
          class="flex h-11 items-center rounded-2xl text-muted transition hover:bg-surface-2 hover:text-ink" :class="lebar ? 'flex-1 gap-3 px-3' : 'w-11 justify-center'">
          <component :is="IKON_TEMA[modeTema]" class="h-5 w-5 shrink-0" />
          <span v-if="lebar" class="truncate text-[13px]">{{ LABEL_TEMA[modeTema].replace("Tema: ", "Tema ") }}</span>
        </button>
        <button @click="alihSidebar" :title="lebar ? 'Ciutkan sidebar' : 'Lebarkan sidebar'" :aria-label="lebar ? 'Ciutkan sidebar' : 'Lebarkan sidebar'"
          class="grid h-11 w-11 shrink-0 place-items-center rounded-2xl text-muted transition hover:bg-surface-2 hover:text-ink">
          <component :is="lebar ? PanelLeftClose : PanelLeftOpen" class="h-5 w-5" />
        </button>
      </div>
    </aside>

    <header class="sticky top-0 z-20 border-b border-garis bg-sidebar/90 backdrop-blur md:hidden" style="padding-top: env(safe-area-inset-top, 0px)">
      <div class="flex items-center gap-3 px-4 pt-3">
        <img :src="logo" alt="" class="h-7 w-7" />
        <span class="font-medium">{{ NAMA_APP }}</span>
        <button @click="gantiTema" class="ml-auto grid h-9 w-9 place-items-center rounded-full bg-surface-2 text-ink-2" :aria-label="LABEL_TEMA[modeTema]">
          <component :is="IKON_TEMA[modeTema]" class="h-4 w-4" />
        </button>
      </div>
      <nav class="flex gap-1 overflow-x-auto px-3 py-2.5">
        <button v-for="t in TAB" :key="t.k" @click="pilih(t.k)" class="h-8 shrink-0 rounded-full px-3.5 text-[13px] font-medium whitespace-nowrap transition"
          :class="tab === t.k ? 'bg-aksen text-aksen-teks' : 'text-muted'">{{ t.l }}</button>
      </nav>
    </header>

    <main class="mx-auto max-w-[1360px] px-4 py-6 md:px-8 md:py-8">
      <div class="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div class="text-xs text-muted">{{ atasJudul }}</div>
          <h1 class="m-0 text-[26px] leading-tight font-medium tracking-tight">{{ judul }}</h1>
        </div>
        <div v-if="status || adaBaru" class="flex items-center gap-2">
          <button v-if="adaBaru" class="tombol-utama !h-9" title="Ada pembaruan tampilan; muat ulang halaman" @click="muatUlang">
            <RefreshCw class="h-3.5 w-3.5" />Tampilan baru · muat ulang
          </button>
          <span v-if="status" class="inline-flex h-9 items-center gap-2 rounded-full bg-surface px-4 text-xs text-ink-2 shadow-kartu">
            <span class="h-2 w-2 rounded-full" :class="status.bursa_buka ? 'bg-naik' : 'bg-muted'"></span>
            {{ status.bursa_buka ? "Bursa buka" : "Bursa tutup" }}
          </span>
          <span v-if="status" class="hidden h-9 items-center rounded-full bg-surface px-4 text-xs text-ink-2 shadow-kartu sm:inline-flex">
            Follow Tren s/d&nbsp;<b class="font-medium text-ink">{{ status.paper_tgl_terakhir || "–" }}</b>
          </span>
        </div>
      </div>
      <BerandaView v-if="tab === 'beranda'" />
      <FollowTrenView v-else-if="tab === 'tren52'" :sub="sub" @sub="gantiSub" />
      <DividenView v-else-if="tab === 'dividen'" :sub="sub" @sub="gantiSub" />
      <ReksadanaView v-else-if="tab === 'reksadana'" :sub="sub" @sub="gantiSub" />
      <EtfView v-else-if="tab === 'etf'" :sub="sub" @sub="gantiSub" />
      <EmitenView v-else-if="tab === 'emiten'" />
      <HipotesisView v-else-if="tab === 'hipotesis'" />
      <RencanaView v-else-if="tab === 'rencana'" />
      <PanduanView v-else />
    </main>
  </div>
</template>

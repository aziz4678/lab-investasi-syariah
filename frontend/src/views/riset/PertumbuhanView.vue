<script setup>
import { ref, computed, watch, onMounted, inject } from "vue";
import { Repeat, Scale, CalendarClock, FlaskConical, ChevronRight } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { pakaiPekerjaan } from "@/composables/pekerjaan";
import { rupiahRingkas } from "@/utils/format";
import Kerangka from "@/components/common/Kerangka.vue";
import Panel from "@/components/common/Panel.vue";
import Segmen from "@/components/common/Segmen.vue";
import Pemutar from "@/components/common/Pemutar.vue";
import NavLengket from "@/components/portofolio/NavLengket.vue";
import PilihAplikasi from "@/components/portofolio/PilihAplikasi.vue";
import KartuRingkasan from "@/components/portofolio/KartuRingkasan.vue";
import GrupBelanja from "@/components/portofolio/GrupBelanja.vue";
import ChecklistBulan from "@/components/portofolio/ChecklistBulan.vue";
import KartuRisiko from "@/components/portofolio/KartuRisiko.vue";
import PilihanEmas from "@/views/riset/pertumbuhan/PilihanEmas.vue";
import HistorisTab from "@/views/riset/pertumbuhan/HistorisTab.vue";
import CaraTab from "@/views/riset/pertumbuhan/CaraTab.vue";
import { pr, prTanda, dariSeratus } from "@/views/riset/pertumbuhan/bantu";

const props = defineProps({ sub: { type: String, default: "rencana" } });
defineEmits(["sub"]);
const pindahTab = inject("pindahTab", () => {});

const NAV = [["rencana", "Rencana"], ["belanja", "Belanja"], ["jadwal", "Jadwal"], ["risiko", "Risiko"], ["dasar", "Dasar hitungan"]];
const PILIHAN_GAYA = [["saham", "Saham saja"], ["emas", "Saham + emas"]];
const APLIKASI_RD = ["bibit", "ajaib", "makmur"];

const dasar = ref(null);
const rencana = ref(null);
const belanja = ref(null);
const emas = ref(null);
const siap = ref(false);
const memuat = ref(false);
const kerja = pakaiPekerjaan();
const setoran = ref(1000000);
const modalAwal = ref(0);
const apps = ref(["bibit", "ajaib", "makmur", "stockbit"]);
const gaya = ref("saham");

const appAngka = computed(() => {
  const rd = apps.value.filter((a) => APLIKASI_RD.includes(a));
  return rd.length === 1 ? rd[0] : "semua";
});
const angka = (s) => Number(String(s).replace(/\D/g, "")) || 0;
const tampilRp = (v) => (v ? v.toLocaleString("id-ID") : "");

const muatDasar = async () => {
  dasar.value = await ambil("pertumbuhan").catch(() => null);
  emas.value = await ambil("pertumbuhan/emas").catch(() => null);
};
const muatRencana = async () => {
  memuat.value = true;
  const q = new URLSearchParams({ setoran: setoran.value || 0, modal_awal: modalAwal.value || 0, aplikasi: appAngka.value });
  const b = new URLSearchParams({ setoran: setoran.value || 0, modal_awal: modalAwal.value || 0, apps: apps.value.join(","), gaya: gaya.value });
  const [r, bl] = await Promise.all([ambil(`pertumbuhan/rencana?${q}`).catch(() => null), ambil(`belanja/pertumbuhan?${b}`).catch(() => null)]);
  rencana.value = r;
  belanja.value = bl;
  memuat.value = false;
  siap.value = true;
};
const muatSemua = async () => {
  await Promise.all([muatDasar(), muatRencana()]);
};
let jeda = null;
watch([setoran, modalAwal, apps, gaya], () => {
  clearTimeout(jeda);
  jeda = setTimeout(muatRencana, 300);
});
onMounted(async () => {
  await muatSemua();
  await kerja.lanjutkan("pertumbuhan_hitung", muatSemua);
  if (props.sub === "historis" || props.sub === "cara") document.getElementById("dasar")?.scrollIntoView({ behavior: "smooth", block: "start" });
});
const hitungUlang = () => kerja.mulai("aksi/pertumbuhan_hitung", {}, muatSemua);

const ada = computed(() => rencana.value?.ada && dasar.value?.ada);
const hasil = computed(() => ["5", "10"].map((t) => rencana.value?.rentang?.[t]).filter(Boolean));
const h10 = computed(() => rencana.value?.rentang?.["10"]);
const h5 = computed(() => rencana.value?.rentang?.["5"]);
const campuranIndeks = computed(() => dasar.value?.indeks?.["50/50"]);
const holdoutEmas = computed(() => emas.value?.holdout?.h37);

const kalimatRingkas = computed(() => {
  const x = h10.value ?? h5.value;
  if (!x) return "";
  const m = rencana.value.masukan;
  const setor = m.modal_awal > 0 ? `modal awal ${rupiahRingkas(m.modal_awal)} lalu setor ${rupiahRingkas(m.setoran)}/bulan` : `setor ${rupiahRingkas(m.setoran)}/bulan`;
  return `Kalau dulu ${setor} selama ${x.tahun} tahun, biasanya jadi ${rupiahRingkas(x.median)} (disetor ${rupiahRingkas(x.total)}).`;
});
const itemRingkas = computed(() =>
  hasil.value.map((x) => ({ label: `${x.tahun} tahun`, nilai: rupiahRingkas(x.median), kelas: x.median >= x.total ? "text-naik" : "text-turun", ket: `paling sial ${rupiahRingkas(x.terburuk)} · ${dariSeratus(x.untung)} dari 100 periode untung` })),
);
const kalimatRisiko = computed(() => {
  const c = campuranIndeks.value;
  const turun = c?.dd != null ? `Pernah turun ${pr(Math.abs(c.dd), 0)} dari puncak.` : "";
  return `${turun} Jangan pakai uang yang dibutuhkan kurang dari 5 tahun lagi.`.trim();
});
const catatanEmas = computed(() => {
  if (gaya.value !== "emas") return "";
  const h = holdoutEmas.value;
  const bagian = h ? ` Di data uji 2014–2026, campuran dengan emas rata-rata ${prTanda(h.cagr)} per tahun dan pernah turun ${pr(Math.abs(h.dd), 0)}.` : "";
  return `Perkiraan di atas dihitung untuk bagian saham saja (50/50). Dengan emas, 20% setoran pindah ke emas.${bagian}`;
});

const langkah = computed(() => {
  const b = belanja.value;
  if (!b?.ada) return [];
  const daftar = [];
  b.grup.forEach((g) => {
    g.produk.forEach((p) => {
      if (p.tipe === "etf") {
        const isi = p.lot > 0 ? `${p.lot} lot ${p.kode} (±${rupiahRingkas(p.perkiraan)}) di jam bursa, kalau selisih harga vs nilai emas tidak lebih dari 2%` : `${p.kode}: simpan ${rupiahRingkas(p.nilai)} dulu sampai cukup 1 lot`;
        daftar.push({ id: `${g.aplikasi}:${p.kode}`, teks: `Buka ${g.nama} → beli ${isi}` });
      } else if (p.nilai > 0) {
        daftar.push({ id: `${g.aplikasi}:${p.id}`, teks: `Buka ${g.nama} → beli ${p.cari_di_aplikasi} ${rupiahRingkas(p.nilai)}` });
      }
    });
  });
  return daftar;
});

const des = computed(() => rencana.value?.desember);
const risiko = computed(() => {
  const i = dasar.value?.indeks ?? {};
  const c = i["50/50"] ?? {};
  const lima = rencana.value?.rentang?.["5"];
  const kartu = [
    { judul: "Bisa turun dalam", angka: c.dd != null ? prTanda(-Math.abs(c.dd), 0) : "", kelas: "text-turun", teks: `Di data lama, campuran ini pernah turun ${pr(Math.abs(c.dd ?? 0), 0)} dari puncak dan butuh ${c.pulih ?? "–"} bulan untuk pulih. Semua produknya berisiko tinggi.` },
    { judul: "Jangka pendek bisa rugi", angka: lima ? `${dariSeratus(lima.untung)} dari 100` : "", kelas: "text-ink", teks: lima ? `Ditahan 5 tahun, ${dariSeratus(lima.untung)} dari 100 periode masa lalu untung. Di bawah 5 tahun, peluang rugi jauh lebih besar.` : "Tahan minimal 5 tahun." },
  ];
  if (gaya.value === "emas") kartu.push({ judul: "Emas bisa jadi beban", angka: "", kelas: "", teks: "Emas menahan saat saham jatuh, tapi tertinggal saat saham naik kencang. Sebagian besar keunggulan di data uji datang dari emas 2024–2025; masuk setelah emas naik tinggi bisa berarti beberapa tahun emas jadi beban." });
  else kartu.push({ judul: "Kurs dua arah", angka: "", kelas: "", teks: "Produk global dalam dolar. Kalau rupiah menguat, bagian global bisa berkurang walau sahamnya naik." });
  kartu.push({ judul: "Belum terbukti", angka: "", kelas: "", teks: "Diuji dengan data masa lalu; belum terbukti di masa depan. Hasil masa lalu bukan janji." });
  return kartu;
});
</script>

<template>
  <div class="space-y-5">
    <header>
      <p class="m-0 text-[13px] leading-relaxed text-ink-2">Uang yang tidak dipakai minimal 5 tahun. Setor rutin tiap bulan ke saham syariah Indonesia dan global, lalu tinggal ikuti daftar belanja di bawah.</p>
    </header>
    <NavLengket :item="NAV" />

    <section id="rencana" class="scroll-mt-16 space-y-5">
      <div class="panel px-4 py-5 sm:px-6">
        <div class="text-[14px] font-medium">Isi data</div>
        <div class="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div class="min-w-0">
            <label class="text-xs text-muted">Setoran per bulan</label>
            <div class="mt-1 flex items-center rounded-full bg-surface-2 px-4"><span class="text-[13px] text-muted">Rp</span>
              <input :value="tampilRp(setoran)" inputmode="numeric" class="h-10 w-full min-w-0 bg-transparent px-2 text-[15px] outline-none" @input="(e) => (setoran = angka(e.target.value))" /></div>
          </div>
          <div class="min-w-0">
            <label class="text-xs text-muted">Modal awal <span>(opsional)</span></label>
            <div class="mt-1 flex items-center rounded-full bg-surface-2 px-4"><span class="text-[13px] text-muted">Rp</span>
              <input :value="tampilRp(modalAwal)" inputmode="numeric" placeholder="0" class="h-10 w-full min-w-0 bg-transparent px-2 text-[15px] outline-none" @input="(e) => (modalAwal = angka(e.target.value))" /></div>
          </div>
          <div class="min-w-0">
            <div class="text-xs text-muted">Aplikasi yang kamu punya</div>
            <PilihAplikasi v-model="apps" class="mt-1.5" />
          </div>
          <div class="min-w-0">
            <div class="text-xs text-muted">Gaya</div>
            <Segmen v-model="gaya" :pilihan="PILIHAN_GAYA" kecil class="mt-1.5" />
            <div class="mt-1 text-[11px] text-muted">{{ gaya === "saham" ? "50% Indonesia + 50% global" : "40% Indonesia + 40% global + 20% emas" }}</div>
          </div>
        </div>
      </div>

      <Kerangka v-if="!siap" jenis="kartu" :n="2" kolom="grid-cols-1 md:grid-cols-2" />
      <Panel v-else-if="!ada" judul="Belum ada hasil hitungan"><p class="m-0 text-[13px] text-ink-2">Tekan "Hitung ulang" di bagian Dasar hitungan (±1 menit).</p></Panel>
      <KartuRingkasan v-else judul="Perkiraan hasil, berdasarkan masa lalu" :besar="h10 ? rupiahRingkas(h10.median) : h5 ? rupiahRingkas(h5.median) : ''" :satuan="h10 ? 'setelah 10 tahun' : 'setelah 5 tahun'"
        :kalimat="kalimatRingkas" :item="itemRingkas" :risiko="kalimatRisiko" label="Diuji dengan data masa lalu; belum terbukti di masa depan.">
        <p v-if="catatanEmas" class="m-0 mt-3 text-[12px] leading-relaxed text-ink-2">{{ catatanEmas }}</p>
      </KartuRingkasan>
    </section>

    <section id="belanja" class="scroll-mt-16 space-y-5">
      <div class="panel relative px-4 py-5 sm:px-6">
        <Pemutar v-if="memuat" class="absolute top-4 right-4" />
        <div class="text-[14px] font-medium">Daftar belanja bulan ini</div>
        <p class="m-0 mt-1 text-[12px] text-muted">Hanya produk yang ada di aplikasimu. Dipilih dengan aturan tetap (biaya termurah di antara yang cukup besar), bukan dari hasil terbaik.</p>
        <div v-if="belanja?.ada" class="mt-3">
          <div v-if="belanja.awal" class="mb-3 rounded-2xl bg-surface-2 px-4 py-3 text-[13px] text-ink-2">Modal awal {{ rupiahRingkas(belanja.awal.total) }}: {{ rupiahRingkas(belanja.awal.lokal_per_produk) }} ke tiap RD Indonesia<template v-if="belanja.awal.global_per_produk"> dan {{ rupiahRingkas(belanja.awal.global_per_produk) }} ke RD global</template><template v-if="belanja.awal.emas"> dan {{ rupiahRingkas(belanja.awal.emas) }} ke ETF emas</template>.</div>
          <GrupBelanja :grup="belanja.grup" :peringatan="belanja.peringatan" />
        </div>
        <p v-else class="m-0 mt-3 text-[13px] text-muted">Daftar belanja belum tersedia.</p>
      </div>
      <ChecklistBulan kunci="pertumbuhan" :langkah="langkah" />
    </section>

    <section id="jadwal" class="panel scroll-mt-16 px-4 py-5 sm:px-6">
      <div class="flex items-center gap-2 text-[14px] font-medium"><CalendarClock class="h-4 w-4 text-aksen" />Jadwal rutin</div>
      <ul class="m-0 mt-3 grid list-none gap-3 p-0 md:grid-cols-3">
        <li class="rounded-2xl bg-surface-2 px-4 py-3">
          <div class="flex items-center gap-2 text-[11px] text-muted"><Repeat class="h-3.5 w-3.5" />Tiap bulan</div>
          <div class="mt-1 text-[14px] font-medium">Setor {{ rupiahRingkas(setoran) }} di tanggal yang sama</div>
          <p class="m-0 mt-1 text-[12px] text-ink-2">Paling mudah lewat beli rutin otomatis di aplikasi. ETF emas dibeli manual.</p>
        </li>
        <li class="rounded-2xl bg-surface-2 px-4 py-3">
          <div class="flex items-center gap-2 text-[11px] text-muted"><Scale class="h-3.5 w-3.5" />Tiap Desember</div>
          <div class="mt-1 text-[14px] font-medium">Kembalikan ke {{ gaya === "emas" ? "40/40/20" : "separuh-separuh" }}</div>
          <p v-if="des && gaya === 'saham'" class="m-0 mt-1 text-[12px] text-ink-2">Contoh {{ des.tahun }}: jual ±{{ rupiahRingkas(des.pindah) }} dari bagian {{ des.dari === "lokal" ? "Indonesia" : "global" }}, belikan ke bagian {{ des.ke === "lokal" ? "Indonesia" : "global" }}. Tanpa menjual juga boleh: arahkan setoran berikutnya ke bagian yang tertinggal.</p>
          <p v-else class="m-0 mt-1 text-[12px] text-ink-2">Bagian yang lebih besar dijual sebagian, dibelikan ke bagian yang tertinggal. Atau arahkan setoran berikutnya ke yang tertinggal.</p>
        </li>
        <li class="rounded-2xl bg-surface-2 px-4 py-3">
          <div class="flex items-center gap-2 text-[11px] text-muted"><CalendarClock class="h-3.5 w-3.5" />Tiap Januari</div>
          <div class="mt-1 text-[14px] font-medium">Cek isi daftar belanja</div>
          <p class="m-0 mt-1 text-[12px] text-ink-2">Daftar dibentuk ulang otomatis. Setoran baru ikuti daftar baru; produk lama tidak perlu dijual kecuali bubar.</p>
        </li>
      </ul>
    </section>

    <section id="risiko" class="scroll-mt-16 space-y-3">
      <KartuRisiko :daftar="risiko" />
      <div class="rounded-2xl border border-garis px-4 py-3 text-[12px] leading-relaxed text-ink-2"><b class="font-medium text-ink">Uang yang dipakai kurang dari 5 tahun lagi jangan di sini.</b> Taruh di <a href="#konservatif" class="text-aksen" @click.prevent="pindahTab('konservatif')">Portofolio Konservatif</a>.</div>
    </section>

    <section id="dasar" class="scroll-mt-16 space-y-5">
      <div class="px-1">
        <div class="text-[14px] font-medium">Dasar hitungan</div>
        <p class="m-0 mt-1 text-[12px] leading-relaxed text-muted">Bagian teknis di balik angka di atas: data historis, perbandingan dengan emas, dan cara kerja.</p>
        <button class="mt-2 inline-flex items-center gap-1 text-[12px] text-aksen" @click="pindahTab('hipotesis', 'H35')"><FlaskConical class="h-3.5 w-3.5" />Sedang diuji maju sejak 1 Des 2026, lihat Lab<ChevronRight class="h-3 w-3" /></button>
      </div>
      <div class="space-y-5 text-[12px]">
        <PilihanEmas :setoran="setoran || 0" />
        <HistorisTab v-if="ada" :r="rencana" :d="dasar" />
        <CaraTab :d="ada ? dasar : null" :kerja="kerja" @hitung="hitungUlang" />
      </div>
    </section>
  </div>
</template>

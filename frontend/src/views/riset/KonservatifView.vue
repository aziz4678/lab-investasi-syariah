<script setup>
import { ref, computed, watch, onMounted, inject } from "vue";
import { RefreshCw, Lock, Unlock, ExternalLink, CalendarClock, Repeat, Landmark, ShieldCheck, ChevronRight } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { pakaiPekerjaan } from "@/composables/pekerjaan";
import { persen, rupiahRingkas } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import Segmen from "@/components/common/Segmen.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import Pemutar from "@/components/common/Pemutar.vue";
import Logo, { kunciMi } from "@/components/common/Logo.vue";
import PanelPekerjaan from "@/components/sistem/PanelPekerjaan.vue";
import TersediaDi from "@/components/produk/TersediaDi.vue";
import GrafikJalurModal from "@/components/charts/GrafikJalurModal.vue";

const dasar = ref(null);
const rencana = ref(null);
const siap = ref(false);
const memuat = ref(false);
const kerja = pakaiPekerjaan();
const pindahTab = inject("pindahTab");

const modal = ref(1000000000);
const pengeluaran = ref(10000000);
const bulanDarurat = ref(6);
const aplikasi = ref("semua");
const gaya = ref("fleksibel");
const porsiSbn = ref("sbn50");
const tarikGrafik = ref("");

const PILIHAN_APLIKASI = [["semua", "Semua"], ["bibit", "Bibit"], ["makmur", "Makmur"], ["ajaib", "Ajaib"]];
const PILIHAN_SBN = [["sbn30", "30% di SBN"], ["sbn50", "50% di SBN"], ["sbn70", "70% di SBN"]];
const NAMA_OPSI = { tanpa_sbn: "Reksa Dana Saja", sbn30: "Reksa Dana + Sukuk Negara 30%", sbn50: "Reksa Dana + Sukuk Negara 50%", sbn70: "Reksa Dana + Sukuk Negara 70%", jii_pu: "Pembanding: 54% JII / 46% RD pasar uang" };
const RISIKO_SBN = "Rendah";
const AMBANG_RENDAH = 0.7;
const KELAS_RISIKO = { Rendah: "bg-naik-bg text-naik", Sedang: "bg-kuning-bg text-kuning", Tinggi: "bg-turun-bg text-turun", "Rendah–Sedang": "bg-kuning-bg text-kuning", "Rendah–Tinggi": "bg-turun-bg text-turun" };
const teksKomposisi = (k) => [`${pr(k.rendah, 0)} rendah`, `${pr(k.sedang, 0)} sedang`, k.tinggi > 0 ? `${pr(k.tinggi, 0)} tinggi` : null].filter(Boolean).join(" · ")
  + (k.dariJenis ? ` · ${k.dariJenis} produk dari jenis RD` : "");
const NAMA_SKENARIO = { kategori: "rata-rata semua RD sejenis", keranjang: "keranjang produk di bawah" };

const opsi = computed(() => (gaya.value === "fleksibel" ? "tanpa_sbn" : porsiSbn.value));
const terkunci = computed(() => gaya.value === "terkunci");
const TEMA = {
  fleksibel: { teks: "text-aksen", latar: "bg-aksen-lembut", garis: "border-aksen", isi: "bg-aksen" },
  terkunci: { teks: "text-s2", latar: "bg-s2/10", garis: "border-s2", isi: "bg-s2" },
};
const tema = computed(() => TEMA[gaya.value]);

const muatDasar = async () => {
  dasar.value = await ambil("konservatif").catch(() => null);
};
const muatRencana = async () => {
  memuat.value = true;
  const q = new URLSearchParams({ modal: modal.value, pengeluaran: pengeluaran.value, darurat: bulanDarurat.value || 0, opsi: opsi.value, aplikasi: aplikasi.value });
  rencana.value = await ambil(`konservatif/rencana?${q}`).catch(() => null);
  memuat.value = false;
  siap.value = true;
};
const muatSemua = async () => {
  await Promise.all([muatDasar(), muatRencana()]);
};
let jeda = null;
watch([modal, pengeluaran, bulanDarurat, opsi, aplikasi], () => {
  clearTimeout(jeda);
  jeda = setTimeout(muatRencana, 300);
});
onMounted(async () => {
  await muatSemua();
  await kerja.lanjutkan("penarikan_hitung", muatSemua);
});
const hitungUlang = () => kerja.mulai("aksi/penarikan_hitung", {}, muatSemua);

const bukaProduk = (id) => {
  pindahTab("reksadana", "katalog");
  history.replaceState(null, "", `#reksadana/katalog/${id}`);
};
const angka = (s) => Number(String(s).replace(/\D/g, "")) || 0;
const tampilRp = (v) => (v ? v.toLocaleString("id-ID") : "");
const bulanTeks = (s) => {
  if (!s) return "–";
  const [t, b] = String(s).slice(0, 7).split("-").map(Number);
  return new Date(t, b - 1, 1).toLocaleDateString("id-ID", { month: "long", year: "numeric" });
};
const tglTeks = (s) => (s ? new Date(s).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" }) : "–");
const pr = (v, d = 1) => (v == null ? "–" : persen(v * 100, d, false));
const prTanda = (v, d = 1) => (v == null ? "–" : persen(v * 100, d, true));
const modalPersen = (v) => (v == null ? "–" : `${(v * 100).toLocaleString("id-ID", { maximumFractionDigits: 0 })}%`);

const ada = computed(() => rencana.value?.ada);
const r = computed(() => rencana.value);
const port = computed(() => r.value?.portofolio);
const sbn = computed(() => r.value?.sbn);
const belanja = computed(() => r.value?.belanja ?? { darurat: [], pt: [], pu: [] });
const jumlahKartu = computed(() => belanja.value.darurat.length + belanja.value.pt.length + belanja.value.pu.length);
const tanpaAplikasi = computed(() => [...belanja.value.pt, ...belanja.value.pu].filter((x) => !x.platform.length).length);
const tutupPengeluaran = computed(() => (r.value?.penghasilan && pengeluaran.value ? r.value.penghasilan / pengeluaran.value : null));

const kapanCair = computed(() => {
  if (!terkunci.value || !sbn.value) return { utama: "Kapan saja", ket: "dana masuk rekening ±1–7 hari kerja setelah dijual" };
  const tahap = [...sbn.value.varian].sort((a, b) => String(a.jatuh_tempo).localeCompare(String(b.jatuh_tempo)))
    .map((v) => `${bulanTeks(v.jatuh_tempo).replace(/^(\w{3})\w*/, "$1")} (${v.seri})`);
  return { utama: "Bertahap", ket: `Bagian reksa dana: kapan saja · Bagian SBN: bertahap mulai ${tahap.join(" dan ")}` };
});

const komposisiRisiko = (kode) => {
  const p = r.value?.opsi?.find((x) => x.kode === kode);
  if (!r.value || !p) return null;
  const modalTotal = r.value.masukan.modal || 1;
  const rd = r.value.sisa * (1 - p.porsi_sbn);
  const { darurat, pt, pu } = belanja.value;
  const bagian = [
    ...darurat.map((x) => [x.risiko, x.nilai, x.risiko_sumber]),
    ...pt.map((x) => [x.risiko, rd / 2 / pt.length, x.risiko_sumber]),
    ...pu.map((x) => [x.risiko, rd / 2 / pu.length, x.risiko_sumber]),
    [RISIKO_SBN, r.value.sisa * p.porsi_sbn, "resmi"],
  ];
  const jumlah = (label) => bagian.filter(([l]) => l === label).reduce((a, [, v]) => a + v, 0) / modalTotal;
  const bulat = (v) => Math.round(v * 100) / 100;
  const rendah = bulat(jumlah("Rendah"));
  const tinggi = bulat(jumlah("Tinggi"));
  const sedang = Math.max(Math.min(bulat(jumlah("Sedang")), 1 - rendah - tinggi), 0);
  const label = rendah >= AMBANG_RENDAH ? "Rendah" : tinggi > 0 ? "Rendah–Tinggi" : "Rendah–Sedang";
  return { rendah, sedang, tinggi, label, dariJenis: bagian.filter(([, v, s]) => s === "jenis" && v > 0).length };
};
const risikoGaya = computed(() => ({ fleksibel: komposisiRisiko("tanpa_sbn"), terkunci: komposisiRisiko(porsiSbn.value) }));

const jumlahNilai = (isi) => isi.reduce((a, x) => a + x.nilai, 0);
const grupBelanja = computed(() => {
  const g = [
    { kode: "darurat", judul: "Dana darurat", ket: `${bulanDarurat.value} bulan pengeluaran di 2 RD pasar uang, supaya tidak bergantung ke satu manajer investasi. Tidak ikut diambil.`, isi: belanja.value.darurat, kelas: "bg-s4" },
    { kode: "pt", judul: "RD pendapatan tetap syariah", ket: "Bagian yang tumbuh. Dibagi rata.", isi: belanja.value.pt, kelas: "bg-s1" },
    { kode: "pu", judul: "RD pasar uang syariah", ket: "Bagian yang stabil, dijual sedikit tiap bulan untuk penghasilan. Dibagi rata.", isi: belanja.value.pu, kelas: "bg-s3" },
  ].filter((x) => x.isi.length).map((x) => ({ ...x, total: jumlahNilai(x.isi), rincian: `${x.isi.length} produk × ${rupiahRingkas(x.isi[0].nilai)}` }));
  if (sbn.value && r.value?.terkunci > 0) {
    g.push({ kode: "sbn", judul: `Sukuk negara ${sbn.value.seri} (${sbn.value.jenis === "ST" ? "Sukuk Tabungan" : "Sukuk Ritel"})`, ket: "Ditahan sampai jatuh tempo, kupon masuk tiap bulan.", isi: sbn.value.varian, kelas: "bg-s2",
      total: r.value.terkunci, rincian: `${sbn.value.varian.length} seri × ${rupiahRingkas(sbn.value.varian[0]?.nilai)}` });
  }
  return g;
});

const jadwal = computed(() => {
  if (!r.value) return [];
  const daftar = [];
  const [ini, depan] = r.value.bulanan ?? [];
  const s = sbn.value;
  if (s) {
    const masa = s.status === "dibuka" ? `masa penawaran ${tglTeks(s.mulai)} – ${tglTeks(s.tutup)}` : `perkiraan dibuka sekitar ${bulanTeks(s.bulan)} (bukan jadwal resmi)`;
    daftar.push({ ikon: Landmark, kapan: "Saat penawaran SBN", judul: `Beli ${s.seri} senilai ${rupiahRingkas(r.value.terkunci)}`, isi: [`${masa}.`, s.parkir_di ? `Sampai uangnya dipakai, simpan dulu di ${s.parkir_di.nama}.` : null].filter(Boolean) });
  }
  if (ini) {
    const isi = [`${bulanTeks(ini.bulan)}: jual ${rupiahRingkas(ini.jual)} dari ${ini.produk.nama}.`];
    if (depan) isi.push(`${bulanTeks(depan.bulan)}: jual ${rupiahRingkas(depan.jual)} dari ${depan.produk.nama}.`);
    isi.push(`Berikutnya bergiliran ke 5 RD pasar uang, satu produk per bulan.`);
    if (s?.kupon_bersih_bulan) {
      const sisaJual = (r.value.penghasilan ?? 0) - s.kupon_bersih_bulan;
      isi.push(sisaJual > 0
        ? `Mulai ${bulanTeks(s.kupon_mulai)} kupon SBN ±${rupiahRingkas(s.kupon_bersih_bulan)}/bulan (setelah pajak) masuk dulu, jadi yang dijual tinggal ${rupiahRingkas(sisaJual)}.`
        : `Mulai ${bulanTeks(s.kupon_mulai)} kupon SBN ±${rupiahRingkas(s.kupon_bersih_bulan)}/bulan (setelah pajak) sudah cukup: tidak perlu menjual, kelebihannya ±${rupiahRingkas(-sisaJual)} dibelikan RD pendapatan tetap & pasar uang separuh-separuh.`);
    }
    daftar.push({ ikon: Repeat, kapan: "Tiap bulan", judul: `Ambil ${rupiahRingkas(r.value.penghasilan)}`, isi });
  }
  daftar.push({ ikon: CalendarClock, kapan: "Tiap Januari", judul: "Naikkan penghasilan sesuai inflasi tahun lalu", isi: ["Misal inflasi 3%, penghasilan bulanan dinaikkan 3%.", "Daftar produk dicek ulang otomatis di halaman ini; kalau ada yang berubah, ikuti daftar belanja yang baru."] });
  const d = r.value.desember;
  if (d) {
    daftar.push({ ikon: Repeat, kapan: "Tiap Desember", judul: "Samakan lagi RD pendapatan tetap & pasar uang (50/50)", isi: [
      `Contoh setelah setahun (pakai rata-rata hasil masa lalu): pendapatan tetap ±${rupiahRingkas(d.pt_sebelum)}, pasar uang ±${rupiahRingkas(d.pu_sebelum)}.`,
      `Jual ±${rupiahRingkas(d.pindah)} dari ${d.dari === "pt" ? "RD pendapatan tetap" : "RD pasar uang"}, belikan ke ${d.ke === "pt" ? "RD pendapatan tetap" : "RD pasar uang"}.`] });
  }
  if (s) {
    daftar.push({ ikon: Landmark, kapan: `Saat SBN jatuh tempo (pertama ${bulanTeks(s.cair_paling_awal)})`, judul: "Putar uangnya ke penawaran SBN berikutnya", isi: [`Uang pokok kembali utuh, simpan dulu di RD pasar uang, lalu dibelikan seri SR/ST yang dibuka berikutnya supaya porsi SBN tetap ${pr(port.value?.porsi_sbn, 0)}.`, "SR & ST biasanya dibuka beberapa kali setahun; halaman ini menampilkan penawaran terdekat."] });
  }
  return daftar;
});

const profil = computed(() => dasar.value?.profil ?? null);
const cariProfil = (kode) => profil.value?.profil?.find((p) => p.kode === kode);
const tahunAwalProfil = computed(() => String(profil.value?.periode?.awal ?? "").slice(0, 4));
const NAMA_PROFIL_PENDEK = { konservatif: "Konservatif (halaman ini)", moderat: "Moderat · 30% RD saham", agresif: "Agresif · 60% RD saham", campuran: "RD campuran" };
const rentangAman = computed(() => {
  const nilai = (r.value?.opsi ?? []).map((x) => x.aman_5).filter((x) => x != null);
  return nilai.length ? `${pr(Math.min(...nilai))}–${pr(Math.max(...nilai))}` : "sebagian kecil";
});
const ddKonservatif = computed(() => {
  const p = cariProfil("konservatif");
  return p ? prTanda(p.dd, 1) : "kecil";
});
const NAMA_PROFIL ={ konservatif: "Konservatif (RD pendapatan tetap / pasar uang 50/50)", moderat: "Moderat (30% RD saham)", agresif: "Agresif (60% RD saham)", campuran: "RD campuran 100%" };
const lamaPulih = (p) => (p.pulih_bulan == null ? "belum pulih" : `${p.pulih_bulan} bulan`);

const jalur = computed(() => port.value?.jalur ?? []);
const pilihanTarik = computed(() => jalur.value.map((j) => [String(j.tarik), `${pr(j.tarik)}${j.tarik === port.value?.aman_5 ? " (aman)" : ""}`]));
watch(port, (p) => {
  tarikGrafik.value = String(p?.aman_5 ?? jalur.value[0]?.tarik ?? "");
}, { immediate: true });
const jalurPilih = computed(() => jalur.value.find((j) => String(j.tarik) === tarikGrafik.value));
const kolomTabel = computed(() => dasar.value?.terbaru?.portofolio?.[0]?.tabel?.map((x) => x.tarik) ?? []);
const kelasUtuh = (v) => (v == null ? "text-muted" : v >= 0.8 ? "font-medium text-naik" : v >= 0.5 ? "text-ink" : "text-muted");
</script>

<template>
  <div class="space-y-5">
    <Panel judul="Portofolio Konservatif" ket="Penghasilan rutin dari reksa dana syariah (dan SBN ritel), tanpa daya beli modal berkurang">
      <template #aksi>
        <span v-if="ada" class="chip" :class="dasar?.basi ? 'bg-kuning-bg text-kuning' : 'bg-surface-2 text-ink-2'">
          Dihitung {{ tglTeks(r.dihitung) }} · data s/d {{ bulanTeks(r.periode.akhir) }}<template v-if="dasar?.basi"> · data basi</template>
        </span>
        <button class="tombol" :disabled="kerja.sibuk.value" @click="hitungUlang"><RefreshCw class="h-3.5 w-3.5" :class="kerja.sibuk.value ? 'animate-spin' : ''" />Hitung ulang</button>
      </template>
      <PanelPekerjaan class="mb-4" :kerja="kerja.kerja.value" :galat="kerja.galat.value" />
      <div class="mb-6 grid gap-4 lg:grid-cols-2">
        <div class="rounded-2xl bg-aksen-lembut px-5 py-4">
          <div class="flex items-center gap-2 text-[15px] font-medium"><ShieldCheck class="h-4 w-4 text-aksen" />Apa itu gaya konservatif?</div>
          <ul class="m-0 mt-2 space-y-1.5 pl-4 text-[13px] leading-relaxed text-ink-2">
            <li><b class="font-medium text-ink">Tujuannya</b> penghasilan rutin tiap bulan, tanpa membuat daya beli modal berkurang. Yang dijaga adalah modal, bukan mengejar untung besar.</li>
            <li><b class="font-medium text-ink">Isinya</b> RD pendapatan tetap syariah (bagian yang tumbuh) dan RD pasar uang syariah (bagian yang stabil, sumber uang bulanan). Boleh ditambah sukuk negara ritel (SR/ST) yang dijamin negara dan ditahan sampai jatuh tempo.</li>
            <li><b class="font-medium text-ink">Aturannya</b> ambil sedikit saja: {{ rentangAman }} per tahun dari modal, dinaikkan ikut inflasi tiap tahun. Dana darurat dipisah dan tidak ikut diambil.</li>
            <li><b class="font-medium text-ink">Yang perlu diterima</b> penghasilannya kecil. Imbalannya, penurunan terdalam di masa lalu hanya {{ ddKonservatif }}.</li>
          </ul>
        </div>
        <div v-if="profil" class="rounded-2xl bg-surface-2 px-5 py-4">
          <div class="text-[15px] font-medium">Kenapa tidak pakai RD saham?</div>
          <p class="m-0 mt-2 text-[13px] leading-relaxed text-ink-2">
            Di {{ tahunAwalProfil }}–{{ String(profil.periode.akhir).slice(0, 4) }}, menambah RD saham justru menghapus tingkat penarikan yang aman. Periode ini buruk untuk saham Indonesia, jadi belum tentu berulang.
          </p>
          <div class="mt-3 grid grid-cols-2 gap-2">
            <div v-for="p in profil.profil" :key="p.kode" class="rounded-xl px-3 py-2" :class="p.kode === 'konservatif' ? 'bg-surface ring-1 ring-aksen' : 'bg-surface'">
              <div class="text-[12px] font-medium">{{ NAMA_PROFIL_PENDEK[p.kode] ?? p.nama }}</div>
              <div class="mt-0.5 text-[11px] text-muted">setelah inflasi <span class="tabular-nums" :class="p.cagr_riil < 0 ? 'text-turun' : 'text-naik'">{{ prTanda(p.cagr_riil, 1) }}/th</span></div>
              <div class="text-[11px] text-muted">turun terdalam <span class="tabular-nums text-turun">{{ prTanda(p.dd, 1) }}</span> · pulih {{ lamaPulih(p) }}</div>
              <div class="text-[11px] text-muted">aman ditarik <b class="font-medium text-ink">{{ p.aman_5 != null ? `${pr(p.aman_5)}/th` : "tidak ada" }}</b></div>
              <div v-if="p.jendela_n" class="text-[11px] text-muted">{{ p.jendela_menang }} dari {{ p.jendela_n }} periode 5 th lebih baik</div>
            </div>
          </div>
          <p class="m-0 mt-2 text-[11px] leading-relaxed text-muted">
            Data {{ bulanTeks(profil.periode.awal) }} – {{ bulanTeks(profil.periode.akhir) }}, rata-rata semua RD sejenis termasuk yang bubar. Hanya dari NAV, tanpa biaya; RD saham dikelola aktif oleh manajer investasi, bukan indeks.
            Rata-rata RD saham cenderung terlalu bagus karena {{ profil.lompatan.saham_nov2019_turun }} penurunan tajam di November 2019 dikeluarkan sebagai lompatan data. Moderat/Agresif = RD saham + sisanya RD pendapatan tetap & pasar uang 50/50.
          </p>
        </div>
      </div>
      <div class="text-[13px] font-medium">1 · Isi data</div>
      <div class="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div class="min-w-0">
          <label class="text-xs text-muted">Modal</label>
          <div class="mt-1 flex items-center rounded-full bg-surface-2 px-4"><span class="text-[13px] text-muted">Rp</span>
            <input :value="tampilRp(modal)" @input="(e) => (modal = angka(e.target.value))" inputmode="numeric" class="h-10 w-full min-w-0 bg-transparent px-2 text-[15px] outline-none" /></div>
          <div class="mt-1 text-[11px] text-muted">{{ rupiahRingkas(modal) }}</div>
        </div>
        <div class="min-w-0">
          <label class="text-xs text-muted">Pengeluaran per bulan</label>
          <div class="mt-1 flex items-center rounded-full bg-surface-2 px-4"><span class="text-[13px] text-muted">Rp</span>
            <input :value="tampilRp(pengeluaran)" @input="(e) => (pengeluaran = angka(e.target.value))" inputmode="numeric" class="h-10 w-full min-w-0 bg-transparent px-2 text-[15px] outline-none" /></div>
          <div class="mt-1 text-[11px] text-muted">{{ rupiahRingkas(pengeluaran) }}</div>
        </div>
        <div class="min-w-0">
          <label class="text-xs text-muted">Dana darurat</label>
          <div class="mt-1 flex items-center rounded-full bg-surface-2 px-4">
            <input v-model.number="bulanDarurat" type="number" min="0" max="36" class="h-10 w-full min-w-0 bg-transparent text-[15px] outline-none" /><span class="text-[13px] text-muted">bulan</span></div>
          <div class="mt-1 text-[11px] text-muted">= {{ rupiahRingkas(pengeluaran * (bulanDarurat || 0)) }}, dipisah dari modal investasi</div>
        </div>
        <div class="min-w-0">
          <div class="text-xs text-muted">Aplikasi yang aku pakai <span class="text-muted">(opsional)</span></div>
          <Segmen v-model="aplikasi" :pilihan="PILIHAN_APLIKASI" kecil class="mt-1.5" />
          <div class="mt-1 text-[11px] text-muted">{{ aplikasi === "semua" ? "produk dari semua tempat beli" : "hanya produk yang ditemukan di aplikasi ini" }}</div>
        </div>
      </div>
      <p v-if="r?.darurat_kurang" class="m-0 mt-3 text-xs text-kuning">Dana darurat lebih besar dari modal; seluruh modal dipakai sebagai dana darurat.</p>
    </Panel>

    <Kerangka v-if="!siap" jenis="kartu" :n="2" kolom="grid-cols-1 md:grid-cols-2" />
    <Panel v-else-if="!ada" judul="Belum ada hasil hitungan"><p class="m-0 text-[13px] text-ink-2">Tekan "Hitung ulang" (±2 menit).</p></Panel>
    <template v-else>
      <section class="panel overflow-hidden">
        <div class="px-6 pt-5 text-[13px] font-medium">2 · Pilih gaya</div>
        <div class="grid gap-3 px-6 pt-3 sm:grid-cols-2">
          <button class="flex items-start gap-3 rounded-2xl border-2 px-4 py-4 text-left transition" :class="!terkunci ? 'border-aksen bg-aksen-lembut' : 'border-garis hover:bg-surface-2'" @click="gaya = 'fleksibel'">
            <span class="grid h-11 w-11 shrink-0 place-items-center rounded-full" :class="!terkunci ? 'bg-aksen text-white' : 'bg-surface-2 text-muted'"><Unlock class="h-5 w-5" /></span>
            <span class="min-w-0">
              <span class="flex flex-wrap items-center gap-2"><span class="text-[16px] font-semibold" :class="!terkunci ? 'text-aksen' : ''">Reksa Dana Saja</span>
                <span v-if="risikoGaya.fleksibel" class="chip" :class="KELAS_RISIKO[risikoGaya.fleksibel.label]">Risiko {{ risikoGaya.fleksibel.label.toLowerCase() }}</span></span>
              <span class="block text-[12px] text-ink-2">Semua di reksa dana syariah. Bisa dicairkan kapan saja (1–7 hari kerja).</span>
              <span v-if="risikoGaya.fleksibel" class="mt-1 block text-[11px] text-muted">Komposisi risiko: {{ teksKomposisi(risikoGaya.fleksibel) }}</span>
            </span>
          </button>
          <button class="flex items-start gap-3 rounded-2xl border-2 px-4 py-4 text-left transition" :class="terkunci ? 'border-s2 bg-s2/10' : 'border-garis hover:bg-surface-2'" @click="gaya = 'terkunci'">
            <span class="grid h-11 w-11 shrink-0 place-items-center rounded-full" :class="terkunci ? 'bg-s2 text-white' : 'bg-surface-2 text-muted'"><Lock class="h-5 w-5" /></span>
            <span class="min-w-0">
              <span class="flex flex-wrap items-center gap-2"><span class="text-[16px] font-semibold" :class="terkunci ? 'text-s2' : ''">Reksa Dana + Sukuk Negara</span>
                <span v-if="risikoGaya.terkunci" class="chip" :class="KELAS_RISIKO[risikoGaya.terkunci.label]">Risiko {{ risikoGaya.terkunci.label.toLowerCase() }}</span></span>
              <span class="block text-[12px] text-ink-2">Sebagian di sukuk negara ritel (SR/ST) yang ditahan sampai jatuh tempo. Penghasilan lebih besar.</span>
              <span v-if="risikoGaya.terkunci" class="mt-1 block text-[11px] text-muted">Komposisi risiko: {{ teksKomposisi(risikoGaya.terkunci) }}</span>
            </span>
          </button>
        </div>
        <div v-if="terkunci" class="px-6 pt-3"><Segmen v-model="porsiSbn" :pilihan="PILIHAN_SBN" kecil /></div>
        <div class="mt-5 grid grid-cols-1 border-t sm:grid-cols-3" :class="[tema.garis, tema.latar]">
          <div class="px-6 py-4">
            <div class="text-xs text-muted">Penghasilan per bulan</div>
            <div class="mt-0.5 text-[20px] font-semibold" :class="tema.teks">{{ r.penghasilan != null ? rupiahRingkas(r.penghasilan) : "–" }}</div>
            <div class="text-[11px] text-muted">{{ pr(r.aman) }} per tahun dari modal investasi</div>
          </div>
          <div class="border-t px-6 py-4 sm:border-t-0 sm:border-l" :class="tema.garis">
            <div class="text-xs text-muted">Uang terkunci</div>
            <div class="mt-0.5 text-[20px] font-semibold">{{ rupiahRingkas(r.terkunci) }} <span class="text-[14px] font-medium text-muted">· {{ pr(r.terkunci_porsi, 0) }}</span></div>
            <div class="text-[11px] text-muted">{{ r.terkunci ? "di SBN, tidak bisa dijual sebelum jatuh tempo" : "tidak ada yang terkunci" }}</div>
          </div>
          <div class="border-t px-6 py-4 sm:border-t-0 sm:border-l" :class="tema.garis">
            <div class="text-xs text-muted">Kapan bisa dicairkan</div>
            <div class="mt-0.5 text-[20px] font-semibold">{{ kapanCair.utama }}</div>
            <div class="text-[11px] text-muted">{{ kapanCair.ket }}</div>
          </div>
        </div>
      </section>

      <section class="panel relative px-6 py-6">
        <Pemutar v-if="memuat" class="absolute top-5 right-6" />
        <div class="text-[13px] font-medium">3 · Hasilnya</div>
        <div v-if="r.penghasilan != null" class="mt-2">
          <div class="text-[34px] leading-tight font-semibold sm:text-[40px]" :class="tema.teks">{{ rupiahRingkas(r.penghasilan) }} <span class="text-[18px] font-medium text-ink-2">per bulan</span></div>
          <div class="mt-1 text-[14px] text-ink-2">naik ikut inflasi tiap tahun · modal investasi {{ rupiahRingkas(r.sisa) }} tetap terjaga daya belinya</div>
          <div class="mt-4 grid gap-3 sm:grid-cols-3">
            <div class="rounded-2xl bg-surface-2 px-4 py-3">
              <div class="text-[11px] text-muted">Setelah 5 tahun, biasanya</div>
              <div class="text-[17px] font-medium">{{ modalPersen(port?.di_aman_5?.median) }} <span class="text-[12px] font-normal text-muted">daya beli modal</span></div>
            </div>
            <div class="rounded-2xl bg-surface-2 px-4 py-3">
              <div class="text-[11px] text-muted">Setelah 5 tahun, kondisi terburuk</div>
              <div class="text-[17px] font-medium">{{ modalPersen(port?.di_aman_5?.terburuk) }} <span class="text-[12px] font-normal text-muted">daya beli modal</span></div>
            </div>
            <div class="rounded-2xl bg-surface-2 px-4 py-3">
              <div class="text-[11px] text-muted">Dibanding pengeluaranmu</div>
              <div class="text-[17px] font-medium">{{ tutupPengeluaran != null ? `${Math.round(tutupPengeluaran * 100)}%` : "–" }} <span class="text-[12px] font-normal text-muted">tertutup</span></div>
            </div>
          </div>
        </div>
        <p v-else class="m-0 mt-2 text-[15px] text-ink-2">Dari data masa lalu belum ada tingkat penarikan yang aman (sampai 3% per tahun) untuk gaya ini.</p>
        <p class="m-0 mt-3 text-[11px] text-muted">Dihitung dari {{ NAMA_SKENARIO[r.skenario] }}, yang hasilnya lebih kecil (lebih hati-hati). Berdasarkan {{ r.n_mulai_5 }} kali mulai berbeda sejak {{ bulanTeks(r.periode.awal) }}; hasil masa lalu, bukan jaminan.</p>
      </section>

      <Panel judul="4 · Daftar belanja" :ket="`Beli ${jumlahKartu} reksa dana${sbn ? ` dan ${sbn.varian.length} seri sukuk negara` : ''}, total ${rupiahRingkas(r.masukan.modal)}. Urutkan dari langkah 1.`">
        <div class="flex h-2.5 w-full overflow-hidden rounded-full bg-surface-2">
          <div v-for="g in grupBelanja" :key="g.kode" :class="g.kelas" :style="{ width: `${(g.total / (r.masukan.modal || 1)) * 100}%` }" :title="g.judul"></div>
        </div>

        <ol class="m-0 mt-5 list-none space-y-4 p-0">
          <li v-for="(g, i) in grupBelanja" :key="g.kode" class="overflow-hidden rounded-2xl border border-garis">
            <div class="flex items-start gap-3 bg-surface-2 px-4 py-3">
              <span class="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full text-[13px] font-semibold text-white" :class="g.kelas">{{ i + 1 }}</span>
              <div class="min-w-0 flex-1">
                <div class="text-[14px] font-medium">{{ g.judul }}</div>
                <div class="text-[12px] text-muted">{{ g.ket }}</div>
                <div class="mt-1 text-[13px] sm:hidden"><b class="text-[16px] font-semibold tabular-nums">{{ rupiahRingkas(g.total) }}</b> <span class="text-[11px] text-muted">· {{ g.rincian }}</span></div>
              </div>
              <div class="hidden shrink-0 text-right sm:block">
                <div class="text-[17px] font-semibold tabular-nums">{{ rupiahRingkas(g.total) }}</div>
                <div class="text-[11px] text-muted">{{ g.rincian }}</div>
              </div>
            </div>

            <ul v-if="g.kode !== 'sbn'" class="m-0 list-none divide-y divide-garis p-0">
              <li v-for="p in g.isi" :key="`${g.kode}-${p.id}`" class="flex items-center gap-3 px-4 py-3">
                <Logo jenis="mi" :kunci="kunciMi(p.mi)" :teks="p.mi" :ukuran="34" />
                <div class="min-w-0 flex-1">
                  <a :href="`#reksadana/katalog/${p.id}`" class="text-[13px] leading-snug font-medium text-ink hover:text-aksen" @click.prevent="bukaProduk(p.id)">{{ p.nama }}</a>
                  <div class="mt-1 flex flex-wrap items-center gap-1.5">
                    <span class="chip" :class="KELAS_RISIKO[p.risiko]" :title="p.risiko_sumber === 'resmi' ? `Tingkat risiko ${p.risiko_skala} dari skala 1–9 (detail produk / fund fact sheet)` : 'Diturunkan dari jenis RD, data resmi tidak ada'">Risiko {{ p.risiko.toLowerCase() }}<template v-if="p.risiko_sumber === 'jenis'"> · dari jenis RD</template></span>
                    <TersediaDi v-if="p.platform.length" :platform="p.platform" kecil />
                    <span v-else class="text-[11px] text-muted">belum ditemukan di Bibit/Makmur/Ajaib</span>
                  </div>
                </div>
                <div class="shrink-0 text-right">
                  <div class="text-[15px] font-semibold tabular-nums">{{ rupiahRingkas(p.nilai) }}</div>
                  <a :href="`#reksadana/katalog/${p.id}`" class="inline-flex items-center text-[11px] text-aksen" @click.prevent="bukaProduk(p.id)">Detail<ChevronRight class="h-3 w-3" /></a>
                </div>
              </li>
            </ul>

            <template v-else>
              <ul class="m-0 list-none divide-y divide-garis p-0">
                <li v-for="v in sbn.varian" :key="v.seri" class="flex items-center gap-3 px-4 py-3">
                  <span class="grid h-[34px] w-[34px] shrink-0 place-items-center rounded-[30%] bg-s2/10 text-s2"><Landmark class="h-4 w-4" /></span>
                  <div class="min-w-0 flex-1">
                    <div class="text-[13px] font-medium">{{ v.seri }} · {{ v.tenor }} tahun</div>
                    <div class="text-[11px] text-muted">jatuh tempo {{ bulanTeks(v.jatuh_tempo) }} · kupon {{ v.kupon != null ? pr(v.kupon, 2) : "–" }}/th{{ v.kupon_perkiraan ? " (perkiraan)" : "" }}<template v-if="v.kupon_bersih_bulan"> · ±{{ rupiahRingkas(v.kupon_bersih_bulan) }}/bulan setelah pajak</template></div>
                    <span class="chip mt-1 bg-naik-bg text-naik">Risiko rendah · dijamin negara</span>
                  </div>
                  <div class="shrink-0 text-[15px] font-semibold tabular-nums">{{ rupiahRingkas(v.nilai) }}</div>
                </li>
              </ul>
              <p class="m-0 border-t border-garis px-4 py-3 text-[11px] text-muted">
                <template v-if="sbn.status === 'dibuka'">Sedang dibuka: {{ tglTeks(sbn.mulai) }} – {{ tglTeks(sbn.tutup) }}, terbit {{ tglTeks(sbn.terbit) }}.</template>
                <template v-else>Perkiraan dibuka sekitar {{ bulanTeks(sbn.bulan) }} (dari pola sebelumnya, bukan jadwal resmi).</template>
                Beli lewat bank atau aplikasi mitra distribusi resmi DJPPR. Sampai uangnya dipakai, simpan dulu di RD pasar uang.<a v-if="sbn.sumber" :href="sbn.sumber" target="_blank" rel="noopener" class="ml-1 inline-flex items-center gap-0.5 text-aksen">info resmi<ExternalLink class="h-3 w-3" /></a>
              </p>
            </template>
          </li>
        </ol>

        <p class="m-0 mt-4 flex items-start gap-1.5 text-[11px] text-muted"><ShieldCheck class="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>Produk dipilih dari aturan, bukan dari hasil masa lalu: syariah, rupiah, masih aktif, riwayat ≥ {{ r.keranjang.kriteria.min_tahun }} tahun, tidak membagi hasil tunai, biayanya diketahui, dana kelolaan di atas tengah-tengah, lalu yang biayanya paling murah. Bukan rekomendasi.
            Daftar dibentuk {{ tglTeks(r.keranjang.dibentuk) }}; dicek ulang tiap Januari, dan produk yang bermasalah diganti di tengah tahun.
            <template v-if="tanpaAplikasi"> {{ tanpaAplikasi }} dari {{ belanja.pt.length + belanja.pu.length }} produk belum ditemukan di Bibit, Makmur, atau Ajaib (bisa jadi dijual di tempat lain).</template>
            <template v-if="!r.keranjang.sama_dengan_hitungan"> Daftar ini lebih baru dari hitungan terakhir; tekan "Hitung ulang".</template>
          </span>
        </p>
      </Panel>

      <Panel judul="5 · Jadwal rutin" ket="Yang dilakukan setelah semua dibeli">
        <ol class="m-0 list-none space-y-0 p-0">
          <li v-for="(j, i) in jadwal" :key="i" class="relative flex gap-4 pb-5 last:pb-0">
            <div class="flex flex-col items-center">
              <span class="grid h-9 w-9 shrink-0 place-items-center rounded-full" :class="[tema.latar, tema.teks]"><component :is="j.ikon" class="h-4 w-4" /></span>
              <span v-if="i < jadwal.length - 1" class="mt-1 w-px flex-1 bg-garis"></span>
            </div>
            <div class="min-w-0 pt-1">
              <div class="text-[11px] font-medium tracking-wide text-muted uppercase">{{ j.kapan }}</div>
              <div class="text-[14px] font-medium">{{ j.judul }}</div>
              <div v-for="(x, k) in j.isi" :key="k" class="text-[12px] text-ink-2">{{ x }}</div>
            </div>
          </li>
        </ol>
      </Panel>

      <section class="panel">
        <div>
          <header class="px-6 pt-5 pb-4"><h2 class="m-0 text-[17px] font-medium">6 · Dasar perhitungan</h2><p class="m-0 mt-0.5 text-xs text-muted">Dari mana angka di atas berasal</p></header>
          <div class="space-y-6 px-6 pb-6">
            <div v-if="jalurPilih">
              <div class="text-[14px] font-medium">Perjalanan modal riil · {{ NAMA_OPSI[opsi] }}</div>
              <div class="text-[11px] text-muted">Tarik {{ pr(jalurPilih.tarik) }}/th dari modal awal, naik ikut inflasi · {{ r.n_mulai_5 }} tanggal mulai · dari {{ NAMA_SKENARIO[r.skenario] }}</div>
              <div class="my-3"><Segmen v-model="tarikGrafik" :pilihan="pilihanTarik" kecil /></div>
              <GrafikJalurModal :tahun="jalurPilih.tahun" />
              <div class="mt-3 grid grid-cols-2 gap-3 text-center sm:grid-cols-4">
                <div class="rounded-2xl bg-surface-2 px-3 py-2"><div class="text-[11px] text-muted">Modal riil th 5, median</div><div class="text-[15px] font-medium">{{ modalPersen(jalurPilih.tahun.at(-1)?.median) }}</div></div>
                <div class="rounded-2xl bg-surface-2 px-3 py-2"><div class="text-[11px] text-muted">Modal riil th 5, terburuk</div><div class="text-[15px] font-medium">{{ modalPersen(jalurPilih.tahun.at(-1)?.terburuk) }}</div></div>
                <div class="rounded-2xl bg-surface-2 px-3 py-2"><div class="text-[11px] text-muted">Penurunan terdalam</div><div class="text-[15px] font-medium text-turun">{{ prTanda(jalurPilih.dd_terdalam) }}</div></div>
                <div class="rounded-2xl bg-surface-2 px-3 py-2"><div class="text-[11px] text-muted">Penurunan median</div><div class="text-[15px] font-medium">{{ prTanda(jalurPilih.dd_median) }}</div></div>
              </div>
            </div>

            <div>
              <div class="text-[14px] font-medium">Keranjang vs rata-rata kategori</div>
              <div class="text-[11px] text-muted">Tingkat aman = penarikan tertinggi (langkah 0,1%, 0–3%) yang modal riilnya ≥ 100% di ≥ 80% tanggal mulai dan tidak pernah kehabisan dana cair. Yang dipakai = yang lebih kecil.</div>
              <div class="mt-2 overflow-x-auto">
                <table class="tabel min-w-[640px]">
                  <thead><tr><th>Opsi</th><th class="!text-right">Aman 5 th kategori</th><th class="!text-right">Aman 5 th keranjang</th><th class="!text-right">Aman 3 th kat / ker</th><th class="!text-right">CAGR riil kat / ker</th><th>Dipakai</th></tr></thead>
                  <tbody>
                    <tr v-for="b in r.banding" :key="b.kode" :class="b.kode === opsi ? 'bg-surface-2' : ''">
                      <td class="text-[13px]">{{ NAMA_OPSI[b.kode] ?? b.nama }}</td>
                      <td class="text-right tabular-nums">{{ pr(b.kategori.aman_5) }}</td>
                      <td class="text-right tabular-nums">{{ b.keranjang ? pr(b.keranjang.aman_5) : "–" }}</td>
                      <td class="text-right tabular-nums">{{ pr(b.kategori.aman_3) }} / {{ b.keranjang ? pr(b.keranjang.aman_3) : "–" }}</td>
                      <td class="text-right tabular-nums">{{ prTanda(b.kategori.cagr_riil, 2) }} / {{ b.keranjang ? prTanda(b.keranjang.cagr_riil, 2) : "–" }}</td>
                      <td class="text-[12px]">{{ b.dipakai ?? "–" }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p class="m-0 mt-2 text-[11px] text-muted">Keranjang = 5 RD pendapatan tetap + 5 RD pasar uang di daftar belanja, bobot sama. Bulan sebelum produk ada / data bolong diisi rata-rata kategori: pendapatan tetap {{ pr(r.keranjang.isian?.PT) }}, pasar uang {{ pr(r.keranjang.isian?.PU) }} dari bulan sejak {{ bulanTeks(r.periode.awal) }}. Keranjang dipilih dari produk yang masih hidup, jadi hasil masa lalunya cenderung terlalu bagus (survivorship).</p>
            </div>

            <div v-if="dasar?.terbaru">
              <div class="text-[14px] font-medium">% tanggal mulai yang modal riilnya utuh setelah 5 tahun (rata-rata kategori)</div>
              <div class="mt-2 overflow-x-auto">
                <table class="tabel min-w-[600px]">
                  <thead><tr><th>Portofolio</th><th v-for="t in kolomTabel" :key="t" class="!text-right">Tarik {{ pr(t) }}</th><th class="!text-right">CAGR riil</th></tr></thead>
                  <tbody>
                    <tr v-for="p in dasar.terbaru.portofolio" :key="p.kode">
                      <td class="text-[13px]">{{ NAMA_OPSI[p.kode] ?? p.nama }}</td>
                      <td v-for="x in p.tabel" :key="x.tarik" class="text-right tabular-nums" :class="kelasUtuh(x.riil5?.utuh)">{{ x.riil5 ? `${Math.round(x.riil5.utuh * 100)}%` : "–" }}</td>
                      <td class="text-right tabular-nums">{{ prTanda(p.cagr_riil, 2) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p class="m-0 mt-2 text-[11px] text-muted">Pembanding JII memakai asumsi dividen {{ pr(dasar.terbaru.dividen_jii) }}/th.</p>
            </div>

            <div v-if="dasar?.sr?.length">
              <div class="text-[14px] font-medium">Sukuk Ritel (SR) yang beredar di pasar sekunder</div>
              <div class="mt-2 overflow-x-auto">
                <table class="tabel min-w-[520px]">
                  <thead><tr><th>Seri</th><th class="!text-right">Kupon</th><th>Jatuh tempo</th><th class="!text-right">Harga</th><th class="!text-right">YTM bersih</th></tr></thead>
                  <tbody>
                    <tr v-for="s in dasar.sr" :key="s.kode">
                      <td class="font-medium">{{ s.kode }}</td>
                      <td class="text-right tabular-nums">{{ pr(s.kupon, 2) }}</td>
                      <td class="tabular-nums">{{ bulanTeks(s.jatuh_tempo) }}</td>
                      <td class="text-right tabular-nums">{{ s.harga?.toLocaleString("id-ID", { maximumFractionDigits: 2 }) ?? "–" }}<div class="text-[10px] text-muted">{{ tglTeks(s.tgl_harga) }}</div></td>
                      <td class="text-right font-medium tabular-nums">{{ pr(s.ytm_bersih, 2) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p class="m-0 mt-2 text-[11px] text-muted">YTM bersih = hasil kalau ditahan sampai jatuh tempo, setelah pajak kupon 10%. Harga = transaksi terakhir di Pasardana (seri jarang ditransaksikan bisa basi). Simulasi membeli SBN di pasar perdana, bukan sekunder.</p>
            </div>

            <div class="rounded-2xl bg-surface-2 px-5 py-4 text-[12px] leading-relaxed text-ink-2">
              <div class="mb-1 font-medium text-ink">Keterbatasan</div>
              <div>• Data {{ bulanTeks(r.periode.awal) }} – {{ bulanTeks(r.periode.akhir) }} (±10 tahun); jendela 5 tahun saling tumpang tindih, hanya ±6 yang benar-benar terpisah. Indikatif, bukan bukti.</div>
              <div>• NAV bulanan OJK, tanpa biaya beli/jual; RD yang membagi hasil tunai tidak dipakai. Rata-rata kategori termasuk RD yang sudah bubar, keranjang tidak.</div>
              <div>• "Aman" = daya beli modal tidak turun (sudah memperhitungkan inflasi). SBN dinilai 100 karena dipegang sampai jatuh tempo; kupon SBN masa lalu lebih tinggi dari sekarang, jadi gaya Reksa Dana + Sukuk Negara bisa terlalu optimis.</div>
              <div>• Simulasi mengambil penarikan proporsional dari RD pendapatan tetap & pasar uang lalu menyamakan 50/50 tiap Desember; cara di jadwal (jual 1 RD pasar uang bergiliran) diuji terpisah dan memberi tingkat aman yang sama persis.</div>
              <div>• Label risiko produk dari skala resmi 1–9 (1–3 rendah, 4–6 sedang, 7–9 tinggi). Komposisi risiko gaya = jumlah porsi produk menurut label resminya, SBN dihitung rendah (dijamin negara); label dari jenis RD hanya bila data resmi kosong; ≥ 70% rendah = "Rendah".</div>
              <div>• Contoh Desember memakai rata-rata hasil per tahun masa lalu (pendapatan tetap {{ pr(r.desember?.rata_pt) }}, pasar uang {{ pr(r.desember?.rata_pu) }}); angka sebenarnya akan berbeda.</div>
            </div>
          </div>
        </div>
      </section>
    </template>

  </div>
</template>

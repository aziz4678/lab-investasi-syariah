<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { Plus, ListChecks, AlertTriangle, FlaskConical, Bell } from "lucide-vue-next";
import { ambil, kirim } from "@/api/client";
import { rupiahRingkas, rupiahBertanda } from "@/utils/format";
import Kerangka from "@/components/common/Kerangka.vue";
import Segmen from "@/components/common/Segmen.vue";
import Pemutar from "@/components/common/Pemutar.vue";
import GrafikBanding from "@/components/charts/GrafikBanding.vue";
import NavLengket from "@/components/portofolio/NavLengket.vue";
import KartuRingkasan from "@/components/portofolio/KartuRingkasan.vue";
import FormTransaksi from "@/components/portofolio/FormTransaksi.vue";
import TabelTransaksi from "@/components/portofolio/TabelTransaksi.vue";
import BarAlokasi from "@/components/portofolio/BarAlokasi.vue";

const NAV = [["ringkasan", "Ringkasan"], ["catat", "Catat"], ["alokasi", "Alokasi"], ["riwayat", "Riwayat"]];
const NAMA_KAKI = { lokal: "Saham Indonesia", global: "Saham global", emas: "Emas", lainnya: "Lainnya" };

const meta = ref(null);
const pid = ref("");
const a = ref(null);
const siap = ref(false);
const memuat = ref(false);
const menyimpan = ref(false);
const galat = ref("");
const nilaiAwal = ref(null);
const draf = ref(null);
const skenario = ref("");
const daftarContoh = ref([]);
const modeContoh = computed(() => !!skenario.value);
const formPorto = ref({ nama: "", target: "pertumbuhan_saham", setoran_rutin: 0, tanggal_setor: 1 });
const pesanPorto = ref("");

const daftar = computed(() => meta.value?.portofolio ?? []);
const pilihanPorto = computed(() => daftar.value.map((p) => [p._id, p.nama]));
const pilihanTarget = computed(() => Object.entries(meta.value?.target ?? {}));
const ringkas = computed(() => a.value?.ringkasan);
const adaTransaksi = computed(() => (a.value?.transaksi?.length ?? 0) > 0);
const angka = (s) => Number(String(s ?? "").replace(/\D/g, "")) || 0;
const tampilRp = (v) => (v ? Number(v).toLocaleString("id-ID") : "");

const muatDaftar = async () => {
  meta.value = await ambil("portofolio-saya").catch(() => null);
  if (meta.value && !pid.value) pid.value = meta.value.portofolio[0]?._id ?? "";
};
const isiFormPorto = () => {
  const p = daftar.value.find((x) => x._id === pid.value);
  if (p) formPorto.value = { nama: p.nama, target: p.target, setoran_rutin: p.setoran_rutin ?? 0, tanggal_setor: p.tanggal_setor ?? 1, tanggal_mulai: p.tanggal_mulai };
};
const muatAnalisis = async () => {
  if (!modeContoh.value && !pid.value) return;
  memuat.value = true;
  const jalur = modeContoh.value ? `portofolio-saya/contoh/${skenario.value}` : `portofolio-saya/${pid.value}/analisis`;
  a.value = await ambil(jalur).catch(() => null);
  memuat.value = false;
  siap.value = true;
};
onMounted(async () => {
  ambil("portofolio-saya/contoh").then((x) => (daftarContoh.value = x.skenario)).catch(() => {});
  await muatDaftar();
  isiFormPorto();
  await muatAnalisis();
});
watch(skenario, () => {
  nilaiAwal.value = null;
  galat.value = "";
  muatAnalisis();
});
watch(pid, () => {
  isiFormPorto();
  draf.value = null;
  muatAnalisis();
});

const simpanPorto = async () => {
  pesanPorto.value = "";
  try {
    await kirim("portofolio-saya/portofolio", { ...formPorto.value, id: pid.value });
    await muatDaftar();
    await muatAnalisis();
    pesanPorto.value = "Tersimpan.";
  } catch (e) {
    pesanPorto.value = e.message;
  }
};
const baruPorto = async () => {
  pesanPorto.value = "";
  try {
    const x = await kirim("portofolio-saya/portofolio", { nama: `Portofolio ${daftar.value.length + 1}`, target: "bebas", setoran_rutin: 0, tanggal_setor: 1 });
    await muatDaftar();
    pid.value = x._id;
  } catch (e) {
    pesanPorto.value = e.message;
  }
};

const simpanTransaksi = async ({ id, data, selesai }) => {
  galat.value = "";
  menyimpan.value = true;
  try {
    if (id) await kirim(`portofolio-saya/transaksi/${id}/ubah`, data);
    else await kirim("portofolio-saya/transaksi", data);
    nilaiAwal.value = null;
    selesai?.();
    await muatAnalisis();
  } catch (e) {
    galat.value = e.message;
  }
  menyimpan.value = false;
};
const hapusTransaksi = async (t) => {
  galat.value = "";
  try {
    await kirim(`portofolio-saya/transaksi/${t._id}/hapus`);
    await muatAnalisis();
  } catch (e) {
    galat.value = e.message;
  }
};
const ubahTransaksi = (t) => {
  nilaiAwal.value = { ...t };
  document.getElementById("catat")?.scrollIntoView({ behavior: "smooth", block: "start" });
};
const batalUbah = () => {
  nilaiAwal.value = null;
  galat.value = "";
};
const isiDariBelanja = async () => {
  draf.value = await ambil(`portofolio-saya/${pid.value}/isi-belanja`).catch(() => ({ ada: false, alasan: "Gagal memuat daftar belanja.", draf: [] }));
};
const pakaiDraf = (d) => {
  nilaiAwal.value = { ...d, _id: null };
  document.getElementById("catat")?.scrollIntoView({ behavior: "smooth", block: "start" });
};

const kelasUntung = (v) => (v == null ? "" : v >= 0 ? "text-naik" : "text-turun");
const itemRingkas = computed(() => {
  const r = ringkas.value;
  if (!r) return [];
  return [
    { label: "Total setor", nilai: rupiahRingkas(r.total_setor), ket: `biaya dibayar ${rupiahRingkas(r.biaya)}` },
    { label: "Untung / rugi", nilai: rupiahBertanda(r.untung), kelas: kelasUntung(r.untung), ket: r.untung_persen != null ? `${(r.untung_persen * 100).toLocaleString("id-ID", { maximumFractionDigits: 2 })}% dari yang dibeli` : "" },
    { label: "Hasil per tahun (XIRR)", nilai: r.xirr != null ? `${(r.xirr * 100).toLocaleString("id-ID", { maximumFractionDigits: 1 })}%` : "–", kelas: kelasUntung(r.xirr), ket: r.xirr == null ? r.xirr_pesan : "dihitung dari tanggal tiap transaksi" },
  ];
});
const grafik = computed(() => {
  const d = a.value?.deret ?? [];
  if (d.length < 2) return null;
  return { label: d.map((x) => x.tgl), seri: { "Nilai sekarang": d.map((x) => Math.round(x.nilai)), "Total setor": d.map((x) => Math.round(x.setor)) } };
});
const peringatanData = computed(() => {
  const out = [];
  if (a.value?.menunggu_nav?.length) out.push(`${a.value.menunggu_nav.length} transaksi masih menunggu NAV; jumlah unitnya terisi otomatis begitu NAV terbit.`);
  (a.value?.produk ?? []).forEach((p) => {
    if (p.basi) out.push(`Harga ${p.nama} terakhir ${p.tgl_data}, sudah lebih dari 3 hari bursa; nilainya bisa tertinggal.`);
    if (p.tanpa_harga) out.push(`Harga ${p.nama} belum ada di data; nilainya belum dihitung.`);
  });
  return out;
});
const pb = computed(() => a.value?.pembanding);
const kalimatRugi = computed(() => {
  const r = ringkas.value;
  if (!r || r.untung == null || r.untung >= 0 || r.untung_persen == null) return "";
  return `Turun ${Math.abs(r.untung_persen * 100).toLocaleString("id-ID", { maximumFractionDigits: 1 })}% dari yang dibeli. Wajar untuk saham; yang menentukan adalah tetap setor rutin.`;
});
</script>

<template>
  <div class="space-y-5">
    <header class="space-y-3">
      <p class="m-0 text-[13px] leading-relaxed text-ink-2">Catat pembelian nyata yang kamu lakukan sendiri. Aplikasi ini menghitung nilai dan analisanya. Data ini milikmu, terpisah dari paper dan uji maju.</p>
      <div v-if="!modeContoh" class="flex flex-wrap items-center gap-2">
        <Segmen v-if="pilihanPorto.length > 1" v-model="pid" :pilihan="pilihanPorto" kecil />
        <button class="tombol" @click="baruPorto"><Plus class="h-3.5 w-3.5" />Portofolio baru</button>
        <button v-if="daftarContoh.length" class="tombol sm:ml-auto" @click="skenario = daftarContoh[0].kunci"><FlaskConical class="h-3.5 w-3.5 text-s5" />Lihat contoh tampilan</button>
      </div>
    </header>
    <section v-if="modeContoh" class="space-y-3 rounded-3xl border-2 border-s5 bg-s5/10 px-4 py-4 sm:px-6 sm:py-5" role="status">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="flex min-w-0 flex-wrap items-center gap-2">
          <span class="inline-flex items-center gap-1.5 rounded-full bg-s5 px-3 py-1 text-[11px] font-semibold tracking-wide text-white"><FlaskConical class="h-3.5 w-3.5" />MODE CONTOH</span>
          <span class="text-[13px] text-ink-2">Data simulasi dari harga masa lalu, bukan portofoliomu.</span>
        </div>
        <button class="tombol shrink-0" @click="skenario = ''">Kembali ke portofolio saya</button>
      </div>
      <div class="flex flex-wrap gap-2" role="group" aria-label="Pilih skenario contoh">
        <button v-for="x in daftarContoh" :key="x.kunci" type="button" :aria-pressed="skenario === x.kunci" class="h-8 shrink-0 rounded-full border px-3.5 text-[13px] font-medium whitespace-nowrap transition"
          :class="skenario === x.kunci ? 'border-s5 bg-s5 text-white' : 'border-garis bg-surface text-ink-2 hover:border-s5'" @click="skenario = x.kunci">{{ x.label }}</button>
      </div>
      <div v-if="a?.contoh" class="space-y-2">
        <div class="text-[15px] font-semibold">{{ a.contoh.label }} <span class="font-normal text-ink-2">· {{ a.contoh.periode }}</span></div>
        <p class="m-0 text-[13px] leading-relaxed text-ink">{{ a.contoh.kalimat }}</p>
        <p v-if="a.contoh.catatan_periode" class="m-0 text-[12px] leading-relaxed text-ink-2">{{ a.contoh.catatan_periode }}</p>
        <div v-if="a.contoh.pengganti" class="flex items-start gap-2 rounded-2xl bg-kuning-bg px-3 py-2 text-[12px] leading-relaxed text-kuning"><AlertTriangle class="mt-0.5 h-3.5 w-3.5 shrink-0" />{{ a.contoh.pengganti }}</div>
        <div v-if="a.contoh.pengingat" class="flex items-start gap-2 rounded-2xl bg-kuning-bg px-3 py-2 text-[12px] leading-relaxed text-kuning"><Bell class="mt-0.5 h-3.5 w-3.5 shrink-0" /><span><b class="font-medium">Pengingat yang akan muncul:</b> belum ada setoran bulan ini, padahal sudah lewat tanggal setor (tanggal 3). Hanya tampilan; tidak masuk pemeriksa kesehatan.</span></div>
        <details class="text-[12px] text-muted"><summary class="cursor-pointer">Tentang data contoh</summary><p v-for="(c, i) in a.contoh.catatan" :key="i" class="m-0 mt-1 leading-relaxed">{{ c }} Tanggal acuan {{ new Date(a.contoh.acuan).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" }) }}.</p></details>
      </div>
    </section>
    <NavLengket :item="NAV" />

    <section id="ringkasan" class="scroll-mt-16 space-y-5">
      <Kerangka v-if="!siap" jenis="kartu" :n="2" kolom="grid-cols-1 md:grid-cols-2" />
      <KartuRingkasan v-else-if="!adaTransaksi" judul="Nilai sekarang" besar="Rp0" kalimat="Belum ada transaksi. Catat pembelian pertamamu di bagian Catat, lalu nilai dan analisanya muncul di sini." label="Catatan pribadi, bukan nasihat keuangan." />
      <KartuRingkasan v-else judul="Nilai sekarang" :besar="rupiahRingkas(ringkas.nilai)" :kalimat="`${a.nama_target} · ${a.transaksi.length} transaksi sejak ${a.transaksi[0].tanggal}`" :item="itemRingkas" label="Catatan pribadi dari transaksi yang kamu isi sendiri; bukan nasihat keuangan.">
        <p v-if="kalimatRugi" class="m-0 mt-3 rounded-2xl bg-turun-bg px-4 py-2 text-[12px] leading-relaxed text-ink-2">{{ kalimatRugi }}</p>
        <ul v-if="peringatanData.length" class="m-0 mt-3 list-none space-y-1 p-0">
          <li v-for="(x, i) in peringatanData" :key="i" class="flex items-start gap-2 rounded-2xl bg-kuning-bg px-4 py-2 text-[12px] text-kuning"><AlertTriangle class="mt-0.5 h-3.5 w-3.5 shrink-0" />{{ x }}</li>
        </ul>
      </KartuRingkasan>

      <div v-if="!modeContoh" class="panel px-4 py-5 sm:px-6">
        <div class="text-[14px] font-medium">Pengaturan portofolio</div>
        <div class="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div class="min-w-0"><label class="text-xs text-muted">Nama</label>
            <input v-model="formPorto.nama" class="mt-1 h-10 w-full rounded-full bg-surface-2 px-4 text-[14px] outline-none" /></div>
          <div class="min-w-0"><label class="text-xs text-muted">Target alokasi</label>
            <select v-model="formPorto.target" class="mt-1 h-10 w-full rounded-full bg-surface-2 px-4 text-[14px] outline-none"><option v-for="[k, l] in pilihanTarget" :key="k" :value="k">{{ l }}</option></select></div>
          <div class="min-w-0"><label class="text-xs text-muted">Setoran rutin per bulan</label>
            <div class="mt-1 flex items-center rounded-full bg-surface-2 px-4"><span class="text-[13px] text-muted">Rp</span>
              <input :value="tampilRp(formPorto.setoran_rutin)" inputmode="numeric" class="h-10 w-full min-w-0 bg-transparent px-2 text-[14px] outline-none" @input="(e) => (formPorto.setoran_rutin = angka(e.target.value))" /></div></div>
          <div class="min-w-0"><label class="text-xs text-muted">Tanggal setor (1–28)</label>
            <input v-model.number="formPorto.tanggal_setor" type="number" min="1" max="28" class="mt-1 h-10 w-full rounded-full bg-surface-2 px-4 text-[14px] outline-none" /></div>
        </div>
        <div class="mt-3 flex flex-wrap items-center gap-3"><button class="tombol" @click="simpanPorto">Simpan pengaturan</button><span v-if="pesanPorto" class="text-[12px] text-ink-2">{{ pesanPorto }}</span></div>
      </div>
    </section>

    <section id="catat" class="scroll-mt-16 space-y-5">
      <div class="panel px-4 py-5 sm:px-6" :class="modeContoh ? 'pointer-events-none opacity-50' : ''" :inert="modeContoh">
        <p v-if="modeContoh" class="m-0 mb-3 rounded-2xl bg-s5/10 px-4 py-2 text-[12px] text-s5">Dinonaktifkan di mode contoh: transaksi tidak bisa ditambah, diubah, atau dihapus.</p>
        <FormTransaksi :portofolio-id="pid" :aplikasi="meta?.aplikasi ?? []" :fee-default="meta?.fee_default ?? {}" :nilai-awal="nilaiAwal" :menyimpan="menyimpan" :galat="galat" @simpan="simpanTransaksi" @batal="batalUbah" />
      </div>
      <div v-if="!modeContoh" class="panel px-4 py-5 sm:px-6">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex items-center gap-2 text-[14px] font-medium"><ListChecks class="h-4 w-4 text-aksen" />Isi dari daftar belanja bulan ini</div>
          <button class="tombol" @click="isiDariBelanja">Tampilkan draf</button>
        </div>
        <p class="m-0 mt-1 text-[12px] text-muted">Draf mengikuti daftar belanja Pertumbuhan sesuai setoran rutin portofolio ini. Pilih satu, koreksi dengan angka nyata dari aplikasi, lalu simpan.</p>
        <p v-if="draf && !draf.ada" class="m-0 mt-3 text-[13px] text-kuning">{{ draf.alasan }}</p>
        <ul v-else-if="draf?.draf?.length" class="m-0 mt-3 list-none space-y-2 p-0">
          <li v-for="(d, i) in draf.draf" :key="i" class="flex items-center justify-between gap-3 rounded-2xl border border-garis px-4 py-2.5 text-[13px]">
            <span class="min-w-0"><span class="chip mr-1.5 bg-surface-2 text-ink-2">{{ d.aplikasi }}</span>{{ d.nama }} <span class="tabular-nums text-muted">· {{ rupiahRingkas(d.nominal) }}</span></span>
            <button class="tombol !h-7 shrink-0" @click="pakaiDraf(d)">Pakai</button>
          </li>
        </ul>
      </div>
    </section>

    <section id="alokasi" class="scroll-mt-16 space-y-5">
      <div class="panel px-4 py-5 sm:px-6">
        <div class="text-[14px] font-medium">Alokasi nyata vs target</div>
        <p class="m-0 mt-1 mb-3 text-[12px] text-muted">{{ a?.nama_target }}. Garis hitam = target.</p>
        <BarAlokasi v-if="a?.alokasi" :alokasi="a.alokasi" />
      </div>
      <div v-if="a?.produk?.length" class="panel px-4 py-5 sm:px-6">
        <div class="text-[14px] font-medium">Nilai per produk</div>
        <ul class="m-0 mt-3 list-none divide-y divide-garis p-0">
          <li v-for="p in a.produk" :key="`${p.tipe_produk}-${p.produk}`" class="flex items-start justify-between gap-3 py-2 text-[13px]">
            <span class="min-w-0"><span class="font-medium">{{ p.nama }}</span><span class="block text-[11px] text-muted">{{ NAMA_KAKI[p.kaki] }} · dibeli {{ rupiahRingkas(p.beli) }}<template v-if="p.jual"> · dijual {{ rupiahRingkas(p.jual) }}</template></span></span>
            <span class="shrink-0 text-right tabular-nums"><span class="font-semibold">{{ p.nilai != null ? rupiahRingkas(p.nilai) : "–" }}</span>
              <span v-if="p.nilai != null" class="block text-[11px]" :class="kelasUntung(p.nilai - (p.beli - p.jual))">{{ rupiahBertanda(p.nilai - (p.beli - p.jual)) }}</span></span>
          </li>
        </ul>
      </div>
      <div v-if="adaTransaksi" class="panel px-4 py-5 sm:px-6">
        <div class="text-[14px] font-medium">Dibanding apa kalau dulu begini</div>
        <ul class="m-0 mt-3 list-none space-y-3 p-0 text-[13px]">
          <li v-if="pb?.campuran && pb.campuran.nilai != null" class="rounded-2xl bg-surface-2 px-4 py-3">
            <div class="flex flex-wrap items-center justify-between gap-2"><span class="font-medium">Campuran target (indeks)</span>
              <span class="tabular-nums">{{ rupiahRingkas(pb.campuran.nilai) }} · kamu {{ rupiahBertanda(pb.campuran.selisih) }}</span></div>
            <p class="m-0 mt-1 text-[11px] leading-relaxed text-muted">{{ pb.campuran.label }}</p>
          </li>
          <template v-if="pb?.uji_maju">
            <li v-for="u in pb.uji_maju" :key="u.kode" class="rounded-2xl bg-surface-2 px-4 py-3">
              <div class="flex flex-wrap items-center justify-between gap-2"><span class="font-medium">{{ u.nama }}</span><span class="tabular-nums">{{ rupiahBertanda(u.selisih) }} dibanding uji maju</span></div>
              <p class="m-0 mt-1 text-[11px] text-muted">Setoranmu dianggap masuk ke kurva uji maju pada tanggal yang sama.</p>
            </li>
          </template>
          <li v-if="!pb?.uji_maju" class="rounded-2xl bg-surface-2 px-4 py-3 text-[12px] text-muted">Pembanding uji maju H35/H37 muncul setelah uji maju berjalan (mulai 1 Des 2026).</li>
        </ul>
      </div>
      <div v-if="grafik" class="panel relative px-4 py-5 sm:px-6">
        <Pemutar v-if="memuat" class="absolute top-4 right-4" />
        <div class="text-[14px] font-medium">Nilai portofolio vs total setor</div>
        <div class="mt-2 flex flex-wrap items-center gap-4 text-[12px] text-ink-2"><span class="inline-flex items-center gap-1.5"><span class="h-2 w-4 rounded-full bg-s1"></span>Nilai sekarang</span><span class="inline-flex items-center gap-1.5"><span class="h-2 w-4 rounded-full bg-s4"></span>Total setor</span></div>
        <div class="mt-3"><GrafikBanding :label="grafik.label" :seri="grafik.seri" :warna-seri="['--series-1', '--series-4']" :tinggi="260" /></div>
      </div>
    </section>

    <section id="riwayat" class="panel scroll-mt-16 px-4 py-5 sm:px-6">
      <div class="text-[14px] font-medium">Riwayat transaksi</div>
      <p class="m-0 mt-1 mb-3 text-[12px] text-muted">Tiap tambah, ubah, dan hapus dicatat di log terpisah.</p>
      <TabelTransaksi :transaksi="a?.transaksi ?? []" :baca="modeContoh" @ubah="ubahTransaksi" @hapus="hapusTransaksi" />
    </section>
  </div>
</template>

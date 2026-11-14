<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { Plus, ListChecks, AlertTriangle, FlaskConical, Bell, Trash2 } from "lucide-vue-next";
import { ambil, kirim } from "@/api/client";
import { rupiahRingkas, rupiahBertanda } from "@/utils/format";
import { kalimatKonteks, buatPemuat, kunciHasil } from "@/utils/portofolioSaya";
import Kerangka from "@/components/common/Kerangka.vue";
import Segmen from "@/components/common/Segmen.vue";
import TabHalaman from "@/components/portofolio/TabHalaman.vue";
import KartuRingkasan from "@/components/portofolio/KartuRingkasan.vue";
import FormTransaksi from "@/components/portofolio/FormTransaksi.vue";
import HasilAnalisis from "@/components/portofolio/HasilAnalisis.vue";
import LaciGeser from "@/components/portofolio/LaciGeser.vue";

const TAB = [["portofolio", "Portofolio"], ["contoh", "Contoh"]];

const meta = ref(null);
const pid = ref("");
const a = ref(null);
const siap = ref(false);
const memuat = ref(false);
const menyimpan = ref(false);
const galat = ref("");
const nilaiAwal = ref(null);
const formTerbuka = ref(false);
const draf = ref(null);
const skenario = ref("");
const daftarContoh = ref([]);
const modeContoh = computed(() => !!skenario.value);
const formPorto = ref({ nama: "", target: "pertumbuhan_saham", pengingat_setoran: false, setoran_rutin: 0, tanggal_setor: 1 });
const pesanPorto = ref("");
const konfirmasiHapusPorto = ref(false);
const setoranDraf = ref(1000000);

const daftar = computed(() => meta.value?.portofolio ?? []);
const pilihanPorto = computed(() => daftar.value.map((p) => [p._id, p.nama]));
const pilihanTarget = computed(() => Object.entries(meta.value?.target ?? {}));
const ringkas = computed(() => a.value?.ringkasan);
const adaTransaksi = computed(() => (a.value?.transaksi?.length ?? 0) > 0);
const kunciKonten = computed(() => kunciHasil(modeContoh.value, skenario.value, pid.value));
const konteks = computed(() => kalimatKonteks(ringkas.value));
const angka = (s) => Number(String(s ?? "").replace(/\D/g, "")) || 0;
const tampilRp = (v) => (v ? Number(v).toLocaleString("id-ID") : "");

const pilihTab = async (x) => {
  if (x !== "contoh") {
    skenario.value = "";
    return;
  }
  if (!daftarContoh.value.length) daftarContoh.value = (await ambil("portofolio-saya/contoh").catch(() => null))?.skenario ?? [];
  skenario.value = skenario.value || daftarContoh.value[0]?.kunci || "";
};

const muatDaftar = async () => {
  meta.value = await ambil("portofolio-saya").catch(() => null);
  if (meta.value && !pid.value) pid.value = meta.value.portofolio[0]?._id ?? "";
};
const isiFormPorto = () => {
  const p = daftar.value.find((x) => x._id === pid.value);
  if (p) formPorto.value = { nama: p.nama, target: p.target, pengingat_setoran: !!p.pengingat_setoran, setoran_rutin: p.setoran_rutin ?? 0, tanggal_setor: p.tanggal_setor ?? 1, tanggal_mulai: p.tanggal_mulai };
};
const pemuatAnalisis = buatPemuat((jalur) => ambil(jalur), (hasil) => {
  a.value = hasil;
  memuat.value = false;
  siap.value = true;
});
const muatAnalisis = async () => {
  if (!modeContoh.value && !pid.value) return;
  memuat.value = true;
  await pemuatAnalisis(modeContoh.value ? `portofolio-saya/contoh/${skenario.value}` : `portofolio-saya/${pid.value}/analisis`);
};
onMounted(async () => {
  ambil("portofolio-saya/contoh").then((x) => (daftarContoh.value = x.skenario)).catch(() => {});
  await muatDaftar();
  isiFormPorto();
  await muatAnalisis();
});
watch(skenario, () => {
  formTerbuka.value = false;
  muatAnalisis();
});
watch(pid, () => {
  konfirmasiHapusPorto.value = false;
  isiFormPorto();
  draf.value = null;
  muatAnalisis();
});
watch(formTerbuka, (buka) => {
  if (!buka) {
    nilaiAwal.value = null;
    galat.value = "";
  }
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
const hapusPorto = async () => {
  pesanPorto.value = "";
  try {
    await kirim(`portofolio-saya/portofolio/${pid.value}/hapus`);
    konfirmasiHapusPorto.value = false;
    pid.value = "";
    await muatDaftar();
    isiFormPorto();
    await muatAnalisis();
  } catch (e) {
    pesanPorto.value = e.message;
    konfirmasiHapusPorto.value = false;
  }
};
const baruPorto = async () => {
  pesanPorto.value = "";
  try {
    const x = await kirim("portofolio-saya/portofolio", { nama: `Portofolio ${daftar.value.length + 1}`, target: "bebas" });
    await muatDaftar();
    pid.value = x._id;
  } catch (e) {
    pesanPorto.value = e.message;
  }
};

const bukaCatat = () => {
  nilaiAwal.value = null;
  galat.value = "";
  formTerbuka.value = true;
};
const simpanTransaksi = async ({ id, data, selesai }) => {
  galat.value = "";
  menyimpan.value = true;
  try {
    if (id) await kirim(`portofolio-saya/transaksi/${id}/ubah`, data);
    else await kirim("portofolio-saya/transaksi", data);
    selesai?.();
    formTerbuka.value = false;
    await muatAnalisis();
  } catch (e) {
    galat.value = e.message;
  }
  menyimpan.value = false;
};
const hapusTransaksi = async (t) => {
  try {
    await kirim(`portofolio-saya/transaksi/${t._id}/hapus`);
    await muatAnalisis();
  } catch (e) {
    galat.value = e.message;
  }
};
const ubahTransaksi = (t) => {
  nilaiAwal.value = { ...t };
  formTerbuka.value = true;
};
const isiDariBelanja = async () => {
  draf.value = await ambil(`portofolio-saya/${pid.value}/isi-belanja?setoran=${setoranDraf.value || 0}`).catch(() => ({ ada: false, alasan: "Gagal memuat daftar belanja.", draf: [] }));
};
const pakaiDraf = (d) => {
  nilaiAwal.value = { ...d, _id: null };
  formTerbuka.value = true;
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
const peringatanData = computed(() => {
  const out = [];
  if (a.value?.menunggu_nav?.length) out.push(`${a.value.menunggu_nav.length} transaksi masih menunggu NAV; jumlah unitnya terisi otomatis begitu NAV terbit.`);
  (a.value?.produk ?? []).forEach((p) => {
    if (p.basi) out.push(`Harga ${p.nama} terakhir ${p.tgl_data}, sudah lebih dari 3 hari bursa; nilainya bisa tertinggal.`);
    if (p.tanpa_harga) out.push(`Harga ${p.nama} belum ada di data; nilainya belum dihitung.`);
  });
  return out;
});
</script>

<template>
  <div class="space-y-5">
    <header>
      <p class="m-0 text-[13px] leading-relaxed text-ink-2">Catat pembelian nyata yang kamu lakukan sendiri. Aplikasi ini menghitung nilai dan analisanya. Data ini milikmu, terpisah dari paper dan uji maju.</p>
    </header>
    <TabHalaman :model-value="modeContoh ? 'contoh' : 'portofolio'" :pilihan="TAB" @update:model-value="pilihTab" />
    <div v-if="!modeContoh" class="flex flex-wrap items-center gap-2">
      <Segmen v-if="pilihanPorto.length > 1" v-model="pid" :pilihan="pilihanPorto" kecil />
      <button class="tombol" @click="baruPorto"><Plus class="h-3.5 w-3.5" />Portofolio baru</button>
    </div>

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
        <div v-if="a.contoh.pengganti_rd?.length" class="flex items-start gap-2 rounded-2xl bg-kuning-bg px-3 py-2 text-[12px] leading-relaxed text-kuning">
          <AlertTriangle class="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span><b class="font-medium">Produk pengganti (data produk asli belum ada di periode ini):</b> <template v-for="(p, i) in a.contoh.pengganti_rd" :key="p.nama">{{ i ? "; " : "" }}{{ p.nama }} menggantikan {{ p.pengganti_dari }}</template>.</span>
        </div>
        <div v-if="a.contoh.pengganti" class="flex items-start gap-2 rounded-2xl bg-kuning-bg px-3 py-2 text-[12px] leading-relaxed text-kuning"><AlertTriangle class="mt-0.5 h-3.5 w-3.5 shrink-0" />{{ a.contoh.pengganti }}</div>
        <div v-if="a.contoh.pengingat" class="flex items-start gap-2 rounded-2xl bg-kuning-bg px-3 py-2 text-[12px] leading-relaxed text-kuning"><Bell class="mt-0.5 h-3.5 w-3.5 shrink-0" /><span><b class="font-medium">Pengingat yang akan muncul:</b> belum ada setoran bulan ini, padahal sudah lewat tanggal setor (tanggal 3). Hanya tampilan; tidak masuk pemeriksa kesehatan.</span></div>
        <details class="text-[12px] text-muted"><summary class="cursor-pointer">Tentang data contoh</summary><p v-for="(c, i) in a.contoh.catatan" :key="i" class="m-0 mt-1 leading-relaxed">{{ c }}</p>
          <p class="m-0 mt-1 leading-relaxed">Tanggal acuan {{ new Date(a.contoh.acuan).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" }) }}.</p></details>
      </div>
    </section>

    <div :key="kunciKonten" class="space-y-5" data-konten>
      <section id="ringkasan" class="space-y-5">
        <Kerangka v-if="!siap" jenis="kartu" :n="2" kolom="grid-cols-1 md:grid-cols-2" />
        <KartuRingkasan v-else-if="!adaTransaksi" judul="Nilai sekarang" besar="Rp0" :kalimat="modeContoh ? 'Skenario ini belum punya transaksi.' : 'Belum ada transaksi. Catat pembelian pertamamu dengan tombol Catat transaksi.'" label="Catatan pribadi, bukan nasihat keuangan." />
        <KartuRingkasan v-else judul="Nilai sekarang" :besar="rupiahRingkas(ringkas.nilai)" :kalimat="`${a.nama_target} · ${a.transaksi.length} transaksi sejak ${a.transaksi[0].tanggal}`" :item="itemRingkas" label="Catatan pribadi dari transaksi yang kamu isi sendiri; bukan nasihat keuangan.">
          <p v-if="konteks" class="m-0 mt-3 rounded-2xl px-4 py-2 text-[12px] leading-relaxed text-ink-2" :class="konteks.jenis === 'naik' ? 'bg-naik-bg' : 'bg-turun-bg'">{{ konteks.teks }}</p>
          <ul v-if="peringatanData.length" class="m-0 mt-3 list-none space-y-1 p-0">
            <li v-for="(x, i) in peringatanData" :key="i" class="flex items-start gap-2 rounded-2xl bg-kuning-bg px-4 py-2 text-[12px] text-kuning"><AlertTriangle class="mt-0.5 h-3.5 w-3.5 shrink-0" />{{ x }}</li>
          </ul>
        </KartuRingkasan>

        <div v-if="!modeContoh" class="panel px-4 py-5 sm:px-6">
          <div class="text-[14px] font-medium">Pengaturan portofolio</div>
          <div class="mt-3 grid gap-4 sm:grid-cols-2">
            <div class="min-w-0"><label class="text-xs text-muted">Nama</label>
              <input v-model="formPorto.nama" class="mt-1 h-10 w-full rounded-full bg-surface-2 px-4 text-[14px] outline-none" /></div>
            <div class="min-w-0"><label class="text-xs text-muted">Target alokasi</label>
              <select v-model="formPorto.target" class="mt-1 h-10 w-full rounded-full bg-surface-2 px-4 text-[14px] outline-none"><option v-for="[k, l] in pilihanTarget" :key="k" :value="k">{{ l }}</option></select></div>
          </div>
          <div class="mt-4 rounded-2xl bg-surface-2 px-4 py-3">
            <label class="flex cursor-pointer items-center justify-between gap-3 text-[13px]">
              <span class="min-w-0"><span class="font-medium">Pengingat setoran <span class="font-normal text-muted">(opsional)</span></span><span class="block text-[11px] text-muted">Kalau menyetor tidak rutin, biarkan mati. Analisa tidak bergantung pada ini.</span></span>
              <span class="relative inline-flex h-6 w-11 shrink-0">
                <input v-model="formPorto.pengingat_setoran" type="checkbox" role="switch" class="peer sr-only" aria-label="Pengingat setoran" />
                <span class="absolute inset-0 rounded-full bg-garis transition peer-checked:bg-aksen peer-focus-visible:ring-2 peer-focus-visible:ring-aksen"></span>
                <span class="absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white shadow transition peer-checked:translate-x-5"></span>
              </span>
            </label>
            <div v-if="formPorto.pengingat_setoran" class="mt-3 grid gap-4 sm:grid-cols-2">
              <div class="min-w-0"><label class="text-xs text-muted">Setoran per bulan</label>
                <div class="mt-1 flex items-center rounded-full bg-surface px-4"><span class="text-[13px] text-muted">Rp</span>
                  <input :value="tampilRp(formPorto.setoran_rutin)" inputmode="numeric" class="h-10 w-full min-w-0 bg-transparent px-2 text-[14px] outline-none" @input="(e) => (formPorto.setoran_rutin = angka(e.target.value))" /></div></div>
              <div class="min-w-0"><label class="text-xs text-muted">Tanggal setor (1–28)</label>
                <input v-model.number="formPorto.tanggal_setor" type="number" min="1" max="28" class="mt-1 h-10 w-full rounded-full bg-surface px-4 text-[14px] outline-none" /></div>
            </div>
          </div>
          <div class="mt-3 flex flex-wrap items-center gap-3">
            <button class="tombol" @click="simpanPorto">Simpan pengaturan</button>
            <button v-if="!konfirmasiHapusPorto && daftar.length > 1" class="tombol text-turun" @click="konfirmasiHapusPorto = true"><Trash2 class="h-3.5 w-3.5" />Hapus portofolio</button>
            <span v-if="pesanPorto" class="text-[12px] text-ink-2">{{ pesanPorto }}</span>
          </div>
          <div v-if="konfirmasiHapusPorto" class="mt-3 flex flex-wrap items-center gap-3 rounded-2xl bg-turun-bg px-4 py-3 text-[13px]">
            <span class="min-w-0 text-ink-2">Hapus <b class="font-medium text-ink">{{ formPorto.nama }}</b> beserta {{ a?.transaksi?.length ?? 0 }} transaksinya? Tidak bisa dibatalkan.</span>
            <button class="tombol" @click="hapusPorto">Ya, hapus</button>
            <button class="tombol" @click="konfirmasiHapusPorto = false">Batal</button>
          </div>
          <p v-if="daftar.length <= 1" class="m-0 mt-2 text-[11px] text-muted">Portofolio terakhir tidak bisa dihapus; ubah pengaturannya kalau mau memulai dari awal.</p>
        </div>
      </section>

      <section v-if="!modeContoh" id="catat" class="panel px-4 py-5 sm:px-6">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="text-[14px] font-medium">Catat transaksi</div>
          <button class="tombol !bg-aksen !text-aksen-teks" @click="bukaCatat"><Plus class="h-3.5 w-3.5" />Catat transaksi</button>
        </div>
        <div class="mt-4 border-t border-garis pt-4">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div class="flex items-center gap-2 text-[13px] font-medium"><ListChecks class="h-4 w-4 text-aksen" />Isi dari daftar belanja bulan ini</div>
            <div class="flex flex-wrap items-center gap-2">
              <div class="flex items-center rounded-full bg-surface-2 px-3"><span class="text-[12px] text-muted">Rp</span>
                <input :value="tampilRp(setoranDraf)" inputmode="numeric" class="h-8 w-28 bg-transparent px-2 text-[13px] outline-none" aria-label="Nominal setoran bulan ini" @input="(e) => (setoranDraf = angka(e.target.value))" /></div>
              <button class="tombol" @click="isiDariBelanja">Tampilkan draf</button>
            </div>
          </div>
          <p class="m-0 mt-1 text-[12px] text-muted">Draf mengikuti daftar belanja Pertumbuhan untuk nominal setoran bulan ini. Pilih satu, koreksi dengan angka nyata dari aplikasi, lalu simpan.</p>
          <p v-if="draf && !draf.ada" class="m-0 mt-3 text-[13px] text-kuning">{{ draf.alasan }}</p>
          <ul v-else-if="draf?.draf?.length" class="m-0 mt-3 list-none space-y-2 p-0">
            <li v-for="(d, i) in draf.draf" :key="i" class="flex items-center justify-between gap-3 rounded-2xl border border-garis px-4 py-2.5 text-[13px]">
              <span class="min-w-0"><span class="chip mr-1.5 bg-surface-2 text-ink-2">{{ d.aplikasi }}</span>{{ d.nama }} <span class="tabular-nums text-muted">· {{ rupiahRingkas(d.nominal) }}</span></span>
              <button class="tombol !h-7 shrink-0" @click="pakaiDraf(d)">Pakai</button>
            </li>
          </ul>
        </div>
      </section>

      <HasilAnalisis v-if="a" :a="a" :memuat="memuat" :baca="modeContoh" @ubah="ubahTransaksi" @hapus="hapusTransaksi" />
    </div>

    <LaciGeser v-model="formTerbuka" :judul="nilaiAwal?._id ? 'Ubah transaksi' : 'Catat transaksi'">
      <FormTransaksi v-if="formTerbuka && !modeContoh" :portofolio-id="pid" :aplikasi="meta?.aplikasi ?? []" :fee-default="meta?.fee_default ?? {}" :nilai-awal="nilaiAwal" :menyimpan="menyimpan" :galat="galat" @simpan="simpanTransaksi" @batal="formTerbuka = false" />
    </LaciGeser>
  </div>
</template>

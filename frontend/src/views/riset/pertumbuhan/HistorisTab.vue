<script setup>
import { ref, computed, inject } from "vue";
import { rupiahRingkas } from "@/utils/format";
import Segmen from "@/components/common/Segmen.vue";
import GrafikBanding from "@/components/charts/GrafikBanding.vue";
import BatangSeri from "@/components/charts/BatangSeri.vue";
import { prTanda, kelasTanda, dariSeratus, bulanPendek, NAMA_PORTO, NAMA_SUMBER, WARNA, NAMA_SERI, lamaPulih } from "@/views/riset/pertumbuhan/bantu";

const props = defineProps({ r: Object, d: Object, bagian: { type: String, default: "" } });
const tampil = (b) => !props.bagian || props.bagian === b;
const pindahTab = inject("pindahTab");

const SUMBER_KURVA = [["indeks", "Indeks 2001–2026"], ["keranjang", "Produk di keranjang 2016–2026"], ["kategori", "Rata-rata RD sejenis 2016–2026"]];
const KET_KURVA = {
  indeks: "JII + dividen (Indonesia) dan indeks saham syariah global (DJIM Titans 100, lalu MSCI World Islamic mulai 2008), dalam rupiah. Bukan produk yang bisa dibeli, tapi riwayatnya paling panjang.",
  keranjang: "Reksa dana di daftar belanja; bulan sebelum produk ada diisi rata-rata RD sejenis. Biaya RD sudah termasuk.",
  kategori: "",
};
const sumberKurva = ref("indeks");
const tahunSip = ref("10");

const kurva = computed(() => props.d?.kurva?.[sumberKurva.value] ?? props.d?.kurva?.indeks);
const ketKurva = computed(() => (sumberKurva.value === "kategori" ? props.d?.sumber?.kategori ?? "" : KET_KURVA[sumberKurva.value]));
const urutSeri = ["campuran", "lokal", "global"];
const grafikNilai = computed(() => {
  const k = kurva.value;
  if (!k) return null;
  return { label: k.bulan.map(bulanPendek), seri: Object.fromEntries(urutSeri.map((s) => [NAMA_SERI[s], k.nilai[s].map((v) => Math.round(v * 100) / 100)])), warna: urutSeri.map((s) => WARNA[s]) };
});
const grafikTurun = computed(() => {
  const k = kurva.value;
  if (!k) return null;
  return { label: k.bulan.map(bulanPendek), seri: Object.fromEntries(urutSeri.map((s) => [NAMA_SERI[s], k.turun[s].map((v) => Math.round(v * 1000) / 10)])), warna: urutSeri.map((s) => WARNA[s]) };
});
const akhirKurva = computed(() => {
  const k = kurva.value;
  if (!k) return [];
  return urutSeri.map((s) => ({ s, nilai: k.nilai[s].at(-1), turun: Math.min(...k.turun[s]) }));
});
const perTahun = computed(() => {
  const k = kurva.value;
  if (!k) return [];
  return Object.keys(k.per_tahun.campuran).map((y) => ({ y, lk: k.per_tahun.lokal[y], gl: k.per_tahun.global[y], c: k.per_tahun.campuran[y] })).reverse();
});
const catatanTahun = computed(() => {
  const k = kurva.value;
  if (!k) return "";
  return `${String(k.tahun_sebagian.awal).slice(0, 4)} dihitung mulai ${bulanPendek(k.tahun_sebagian.awal)}, ${String(k.tahun_sebagian.akhir).slice(0, 4)} sampai ${bulanPendek(k.tahun_sebagian.akhir)}.`;
});

const ringkas = computed(() => {
  const i = props.d?.indeks ?? {};
  return ["100% IDX", "50/50", "100% global"].filter((k) => i[k]).map((k) => ({ k, x: i[k] }));
});

const DEKADE_LABEL = { "Jun 2001-2009": "2001–2009", "2010-2019": "2010–2019", "2020-Okt 2026": "2020–2026" };
const dekade = computed(() => {
  const i = props.d?.indeks;
  if (!i) return null;
  const kunci = Object.keys(i["50/50"].dekade);
  const bulat = (v) => Math.round(v * 1000) / 10;
  return {
    label: kunci.map((k) => DEKADE_LABEL[k] ?? k),
    seri: [
      { nama: "100% Indonesia", data: kunci.map((k) => bulat(i["100% IDX"].dekade[k])), warna: WARNA.lokal },
      { nama: "100% global", data: kunci.map((k) => bulat(i["100% global"].dekade[k])), warna: WARNA.global },
      { nama: "Campuran 50/50", data: kunci.map((k) => bulat(i["50/50"].dekade[k])), warna: WARNA.campuran },
    ],
    baris: kunci.map((k) => ({ k: DEKADE_LABEL[k] ?? k, lk: i["100% IDX"].dekade[k], gl: i["100% global"].dekade[k], c: i["50/50"].dekade[k] })),
  };
});
const formatPersen = (v) => `${v.toLocaleString("id-ID")}%`;

const sip = computed(() => props.r?.rentang?.[tahunSip.value]);
const grafikSip = computed(() => {
  const x = sip.value;
  if (!x?.deret?.length) return null;
  const juta = (v) => Math.round(v / 1e5) / 10;
  return { label: x.deret.map((p) => bulanPendek(p.mulai)), seri: { "Nilai akhir": x.deret.map((p) => juta(p.nilai)), "Total disetor": x.deret.map(() => juta(x.total)) }, warna: [WARNA.campuran, "--text-muted"] };
});

const tabelSip = computed(() => {
  const s = props.d?.sip ?? {};
  const baris = [["keranjang", "Produk di keranjang, 50/50"], ["kategori", "Rata-rata RD sejenis, 50/50"], ["kategori_lokal", "Rata-rata RD sejenis, 100% Indonesia"], ["kategori_global", "Rata-rata RD sejenis, 100% global"],
    ["indeks", "Indeks, 50/50"], ["indeks_lokal", "Indeks, 100% Indonesia"], ["indeks_global", "Indeks, 100% global"]];
  return baris.filter(([k]) => s[k]).map(([k, nama]) => ({ k, nama, lima: s[k]["5"], sepuluh: s[k]["10"] }));
});
const sumberPakai = (t) => NAMA_SUMBER[props.d?.pakai?.semua?.[t]] ?? "–";
const versiLama = computed(() => props.d?.versi_lama);

const KRITERIA_TEKS = { K1: "Periode 10 tahun terburuk campuran lebih baik dari 100% Indonesia", K2: "Hasil dibanding risiko (rata-rata per tahun ÷ turun terdalam) tidak lebih jelek dari 100% Indonesia", K3: "Rata-rata per tahun tidak lebih rendah dari 100% Indonesia lebih dari 2 poin" };
const nilaiKriteria = (k, v) => (k === "K2" ? `${v[1].toFixed(2)} vs ${v[2].toFixed(2)}`.replaceAll(".", ",") : `${prTanda(v[1])} vs ${prTanda(v[2])}`);
const pecah = computed(() => props.d?.pecah ?? {});
const PECAH_LABEL = { Penuh: "Seluruh periode", "Jun 2001-2009": "2001–2009", "2010-2019": "2010–2019", "2020-Okt 2026": "2020–2026" };
</script>

<template>
  <div class="space-y-5">
    <section v-if="tampil('ringkas')" class="panel px-4 py-5 sm:px-6">
      <div class="text-[14px] font-medium">Ringkasan 25 tahun (indeks, Jun 2001 – Okt 2026, dalam rupiah)</div>
      <p class="m-0 mt-1 text-[12px] text-muted">Memegang sejak Juni 2001 tanpa setoran tambahan, dikembalikan ke porsi awal tiap Desember.</p>
      <div class="mt-3 grid gap-3 md:grid-cols-3">
        <div v-for="p in ringkas" :key="p.k" class="rounded-2xl border p-4" :class="p.k === '50/50' ? 'border-aksen bg-aksen-lembut' : 'border-garis'">
          <div class="text-[14px] font-semibold">{{ NAMA_PORTO[p.k] }}</div>
          <dl class="m-0 mt-2 grid grid-cols-2 gap-x-3 gap-y-2 text-[12px]">
            <div><dt class="text-muted">Rata-rata per tahun</dt><dd class="m-0 text-[16px] font-semibold tabular-nums" :class="kelasTanda(p.x.cagr)">{{ prTanda(p.x.cagr) }}</dd></div>
            <div><dt class="text-muted">Turun terdalam</dt><dd class="m-0 text-[16px] font-semibold tabular-nums text-turun">{{ prTanda(p.x.dd) }}</dd></div>
            <div><dt class="text-muted">Lama pulih dari turun terdalam</dt><dd class="m-0 font-medium">{{ lamaPulih(p.x) }}</dd></div>
            <div><dt class="text-muted">10 tahun terburuk</dt><dd class="m-0 font-medium tabular-nums" :class="kelasTanda(p.x.j_buruk)">{{ prTanda(p.x.j_buruk) }}/th</dd></div>
            <div><dt class="text-muted">10 tahun terbaik</dt><dd class="m-0 font-medium tabular-nums" :class="kelasTanda(p.x.j_baik)">{{ prTanda(p.x.j_baik) }}/th</dd></div>
            <div><dt class="text-muted">10 th lebih baik dari 100% Indonesia</dt><dd class="m-0 font-medium">{{ p.k === "100% IDX" ? "–" : `${dariSeratus(p.x.j_menang)} dari 100 periode` }}</dd></div>
          </dl>
        </div>
      </div>
    </section>

    <section v-if="tampil('ringkas')" class="panel px-4 py-5 sm:px-6">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="text-[14px] font-medium">Rp1 yang ditanam di awal jadi berapa?</div>
        <Segmen v-model="sumberKurva" :pilihan="SUMBER_KURVA" kecil />
      </div>
      <p class="m-0 mt-1 text-[12px] leading-relaxed text-muted">{{ ketKurva }}</p>
      <div class="mt-3 grid grid-cols-3 gap-2">
        <div v-for="a in akhirKurva" :key="a.s" class="rounded-xl bg-surface-2 px-3 py-2">
          <div class="text-[11px] text-muted">{{ NAMA_SERI[a.s] }}</div>
          <div class="text-[16px] font-semibold tabular-nums">Rp{{ a.nilai.toLocaleString("id-ID", { maximumFractionDigits: 2 }) }}</div>
          <div class="text-[11px] text-muted">turun terdalam <span class="text-turun">{{ prTanda(a.turun) }}</span></div>
        </div>
      </div>
      <GrafikBanding v-if="grafikNilai" class="mt-3" :label="grafikNilai.label" :seri="grafikNilai.seri" :warna-seri="grafikNilai.warna" :tinggi="280" />
      <div class="mt-5 text-[13px] font-medium">Seberapa jauh di bawah puncak (%)</div>
      <p class="m-0 mt-0.5 text-[12px] text-muted">0% = sedang di titik tertinggi. Makin ke bawah, makin dalam turunnya.</p>
      <GrafikBanding v-if="grafikTurun" class="mt-2" :label="grafikTurun.label" :seri="grafikTurun.seri" :warna-seri="grafikTurun.warna" :tinggi="200" />
    </section>

    <section v-if="dekade && tampil('ringkas')" class="panel px-4 py-5 sm:px-6">
      <div class="text-[14px] font-medium">Kenapa dicampur: per dekade</div>
      <p class="m-0 mt-2 text-[14px] leading-relaxed">{{ d.dekade.teks }}</p>
      <p class="m-0 mt-1 text-[11px] text-muted">Sumber: {{ d.dekade.sumber }}. Rata-rata per tahun di tiap dekade. Korelasi bulanan Indonesia vs global {{ d.korelasi?.toFixed(2).replace(".", ",") }} (0 = tidak bergerak bersama, 1 = selalu bersama).</p>
      <div class="mt-4 grid gap-4 lg:grid-cols-[1fr_300px]">
        <BatangSeri :label="dekade.label" :seri="dekade.seri" legenda :format="formatPersen" :tinggi="230" />
        <table class="w-full self-start text-[12px]">
          <thead><tr class="text-left text-muted"><th class="pb-1 font-normal">Dekade</th><th class="pb-1 text-right font-normal">Indonesia</th><th class="pb-1 text-right font-normal">Global</th><th class="pb-1 text-right font-normal">50/50</th></tr></thead>
          <tbody>
            <tr v-for="b in dekade.baris" :key="b.k" class="border-t border-garis">
              <td class="py-1.5">{{ b.k }}</td>
              <td class="py-1.5 text-right tabular-nums" :class="kelasTanda(b.lk)">{{ prTanda(b.lk) }}</td>
              <td class="py-1.5 text-right tabular-nums" :class="kelasTanda(b.gl)">{{ prTanda(b.gl) }}</td>
              <td class="py-1.5 text-right font-medium tabular-nums" :class="kelasTanda(b.c)">{{ prTanda(b.c) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="tampil('riwayat')" class="panel px-4 py-5 sm:px-6">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="text-[14px] font-medium">Hasil per tahun</div>
        <Segmen v-model="sumberKurva" :pilihan="SUMBER_KURVA" kecil />
      </div>
      <p class="m-0 mt-1 text-[12px] text-muted">{{ catatanTahun }} Tahun merah di satu sisi sering hijau di sisi lain.</p>
      <div class="mt-3 max-h-[440px] overflow-y-auto">
        <table class="w-full text-[12px]">
          <thead class="sticky top-0 bg-surface"><tr class="text-left text-muted"><th class="pb-1 font-normal">Tahun</th><th class="pb-1 text-right font-normal">100% Indonesia</th><th class="pb-1 text-right font-normal">100% global</th><th class="pb-1 text-right font-normal">Campuran 50/50</th></tr></thead>
          <tbody>
            <tr v-for="b in perTahun" :key="b.y" class="border-t border-garis">
              <td class="py-1.5">{{ b.y }}</td>
              <td class="py-1.5 text-right tabular-nums" :class="kelasTanda(b.lk)">{{ prTanda(b.lk) }}</td>
              <td class="py-1.5 text-right tabular-nums" :class="kelasTanda(b.gl)">{{ prTanda(b.gl) }}</td>
              <td class="py-1.5 text-right font-medium tabular-nums" :class="kelasTanda(b.c)">{{ prTanda(b.c) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="tampil('riwayat')" class="panel px-4 py-5 sm:px-6">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="text-[14px] font-medium">Setor rutin: hasil untuk setiap bulan mulai</div>
        <Segmen v-model="tahunSip" :pilihan="[['5', '5 tahun'], ['10', '10 tahun']]" kecil />
      </div>
      <p v-if="sip" class="m-0 mt-1 text-[12px] leading-relaxed text-muted">
        Setor {{ rupiahRingkas(r.masukan.setoran) }}/bulan<template v-if="r.masukan.modal_awal"> + modal awal {{ rupiahRingkas(r.masukan.modal_awal) }}</template>, campuran 50/50, ditahan {{ sip.tahun }} tahun. Tiap titik = satu bulan mulai.
        Sumber: {{ NAMA_SUMBER[sip.sumber] }} ({{ sip.sumber_teks }}). Nilai dalam juta rupiah.
      </p>
      <GrafikBanding v-if="grafikSip" class="mt-3" :label="grafikSip.label" :seri="grafikSip.seri" :warna-seri="grafikSip.warna" :tinggi="240" />
      <div v-if="sip" class="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <div class="rounded-xl bg-surface-2 px-3 py-2"><div class="text-[11px] text-muted">Biasanya</div><div class="text-[15px] font-semibold tabular-nums">{{ rupiahRingkas(sip.median) }}</div></div>
        <div class="rounded-xl bg-surface-2 px-3 py-2"><div class="text-[11px] text-muted">Paling sial</div><div class="text-[15px] font-semibold tabular-nums">{{ rupiahRingkas(sip.terburuk) }}</div></div>
        <div class="rounded-xl bg-surface-2 px-3 py-2"><div class="text-[11px] text-muted">Paling beruntung</div><div class="text-[15px] font-semibold tabular-nums">{{ rupiahRingkas(sip.terbaik) }}</div></div>
        <div class="rounded-xl bg-surface-2 px-3 py-2"><div class="text-[11px] text-muted">Periode untung</div><div class="text-[15px] font-semibold tabular-nums">{{ dariSeratus(sip.untung) }} dari 100</div></div>
      </div>
    </section>

    <section v-if="tampil('riwayat')" class="panel px-4 py-5 sm:px-6">
      <div class="text-[14px] font-medium">Semua sumber, setor {{ rupiahRingkas(d.setoran_contoh) }}/bulan</div>
      <p class="m-0 mt-1 text-[12px] text-muted">Biasanya · paling sial · periode untung (jumlah bulan mulai). Total setor 5 tahun {{ rupiahRingkas(d.setoran_contoh * 60) }}, 10 tahun {{ rupiahRingkas(d.setoran_contoh * 120) }}.</p>
      <div class="mt-2 overflow-x-auto">
        <table class="w-full min-w-[600px] text-[12px]">
          <thead><tr class="text-left text-muted"><th class="pb-1 font-normal">Sumber</th><th class="pb-1 text-right font-normal">5 tahun</th><th class="pb-1 text-right font-normal">10 tahun</th></tr></thead>
          <tbody>
            <tr v-for="b in tabelSip" :key="b.k" class="border-t border-garis">
              <td class="py-1.5">{{ b.nama }}</td>
              <td class="py-1.5 text-right tabular-nums">{{ b.lima ? `${rupiahRingkas(b.lima.median)} · ${rupiahRingkas(b.lima.terburuk)} · ${dariSeratus(b.lima.untung)}% (${b.lima.n_mulai})` : "–" }}</td>
              <td class="py-1.5 text-right tabular-nums">{{ b.sepuluh ? `${rupiahRingkas(b.sepuluh.median)} · ${rupiahRingkas(b.sepuluh.terburuk)} · ${dariSeratus(b.sepuluh.untung)}% (${b.sepuluh.n_mulai})` : "–" }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="m-0 mt-2 text-[12px] text-ink-2">Yang dipakai di tab Rencana (paling rendah): 5 tahun = <b class="font-medium">{{ sumberPakai("5") }}</b>, 10 tahun = <b class="font-medium">{{ sumberPakai("10") }}</b>.</p>
      <p class="m-0 mt-1 text-[11px] leading-relaxed text-muted">Rata-rata RD sejenis: {{ d.sumber.kategori }}.</p>
      <div v-if="versiLama?.sip" class="mt-3 rounded-2xl border border-dashed border-garis px-4 py-3 text-[12px] text-ink-2">
        <div class="font-medium text-ink">Versi lama (sebelum 8 Nov 2026, untuk transparansi)</div>
        <p class="m-0 mt-1">Dulu sisi global "rata-rata RD sejenis" mencampur semua RD saham syariah dolar, termasuk RD Asia/China/ASEAN/India dan RD satu sektor yang justru dikeluarkan dari keranjang. Hasilnya: 5 tahun biasanya {{ rupiahRingkas(versiLama.sip["5"].median) }}, paling sial {{ rupiahRingkas(versiLama.sip["5"].terburuk) }}, {{ dariSeratus(versiLama.sip["5"].untung) }} dari 100 periode untung; 10 tahun biasanya {{ rupiahRingkas(versiLama.sip["10"].median) }}, paling sial {{ rupiahRingkas(versiLama.sip["10"].terburuk) }}.</p>
        <p class="m-0 mt-1 text-muted">Diganti SETELAH melihat hasil, karena pembandingnya tidak sejenis dengan isi keranjang. Dicatat di dokumen riset.</p>
      </div>
    </section>

    <section v-if="tampil('uji')" class="panel px-4 py-5 sm:px-6">
      <div class="text-[14px] font-medium">Hasil uji H35 "Syariah Global"</div>
      <p class="m-0 mt-1 text-[12px] text-muted">Aturan dan kriteria ditulis sebelum dihitung, tapi gambaran umum data sudah diketahui sebelumnya. Jadi statusnya "lolos setelah data diketahui", wajib dipantau maju mulai Januari 2027.</p>
      <ul class="m-0 mt-3 list-none space-y-2 p-0 text-[13px]">
        <li v-for="(v, k) in d.kriteria" :key="k" class="flex items-start justify-between gap-3 rounded-xl bg-surface-2 px-4 py-2.5">
          <span><b class="font-medium">{{ k }}</b> · {{ KRITERIA_TEKS[k] }}<span class="block text-[12px] text-muted">{{ nilaiKriteria(k, v) }}</span></span>
          <span class="chip shrink-0" :class="v[0] ? 'bg-naik-bg text-naik' : 'bg-turun-bg text-turun'">{{ v[0] ? "lulus" : "gagal" }}</span>
        </li>
        <li class="flex items-start justify-between gap-3 rounded-xl bg-surface-2 px-4 py-2.5">
          <span><b class="font-medium">K4</b> · K1–K3 tetap lulus dengan asumsi lebih pesimis (dividen JII 0%, dividen global 1%, indeks DJIM US sebelum 2008)</span>
          <span class="chip shrink-0" :class="d.k4 ? 'bg-naik-bg text-naik' : 'bg-turun-bg text-turun'">{{ d.k4 ? "lulus" : "gagal" }}</span>
        </li>
      </ul>
      <div class="mt-4 text-[13px] font-medium">Dari mana hasil bagian global?</div>
      <div class="mt-2 overflow-x-auto">
        <table class="w-full min-w-[480px] text-[12px]">
          <thead><tr class="text-left text-muted"><th class="pb-1 font-normal">Periode</th><th class="pb-1 text-right font-normal">Kenaikan saham (dolar)</th><th class="pb-1 text-right font-normal">Efek kurs</th><th class="pb-1 text-right font-normal">Total rupiah</th><th class="pb-1 text-right font-normal">Indonesia</th></tr></thead>
          <tbody>
            <tr v-for="(x, k) in pecah" :key="k" class="border-t border-garis">
              <td class="py-1.5">{{ PECAH_LABEL[k] ?? k }}</td>
              <td class="py-1.5 text-right tabular-nums" :class="kelasTanda(x.usd)">{{ prTanda(x.usd) }}</td>
              <td class="py-1.5 text-right tabular-nums" :class="kelasTanda(x.kurs)">{{ prTanda(x.kurs) }}</td>
              <td class="py-1.5 text-right font-medium tabular-nums" :class="kelasTanda(x.rupiah)">{{ prTanda(x.rupiah) }}</td>
              <td class="py-1.5 text-right tabular-nums" :class="kelasTanda(x.idx)">{{ prTanda(x.idx) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="m-0 mt-2 text-[11px] text-muted">Per tahun. Efek kurs positif = rupiah melemah terhadap dolar (menambah hasil global dalam rupiah). <a href="#hipotesis/H35" class="text-aksen" @click.prevent="pindahTab('hipotesis', 'H35')">Buka H35 di halaman Hipotesis</a></p>
    </section>
  </div>
</template>

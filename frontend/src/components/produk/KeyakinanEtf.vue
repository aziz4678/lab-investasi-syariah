<script setup>
import { computed } from "vue";
import { ShieldCheck, History, TriangleAlert } from "lucide-vue-next";
import { persen, tanggal, kelasPersen } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import PenyebabTurun from "@/components/produk/PenyebabTurun.vue";
import PeluangTahan from "@/components/produk/PeluangTahan.vue";
import PosisiKini from "@/components/produk/PosisiKini.vue";

const props = defineProps({ k: Object, x: Object });
const tgl = (v) => (v ? tanggal(v) : "–");
const bln = (v) => (v == null ? "–" : v < 1 ? "< 1 bln" : v < 12 ? `${Math.round(v)} bln` : `${(v / 12).toFixed(1).replace(".", ",")} th`);
const maksTahun = computed(() => Math.max(1, ...(props.k?.per_tahun || []).map((r) => Math.abs(r.usd))));
const rp = (th) => props.k?.jendela_rp?.find((j) => j.tahun === th);
const j = (th) => props.k?.jendela?.find((r) => r.tahun === th);
const lengkap = computed(() => (props.k?.per_tahun || []).filter((r) => !r.berjalan));
const tahunTurun = computed(() => lengkap.value.filter((r) => r.usd < 0));
const catatan = computed(() => {
  const k = props.k, x = props.x, c = [];
  if (!k) return c;
  if (k.tahun < 10) c.push(`Data baru ${String(k.tahun).replace(".", ",")} tahun. Angka "per tahun" dari periode sependek ini sangat dipengaruhi kapan ETF mulai terdaftar.`);
  if (k.krisis?.[0]?.turun == null) c.push("ETF ini belum pernah melewati krisis sebesar 2008, saat pasar saham dunia turun lebih dari 50%.");
  if (k.proksi && x?.cagr_2020 != null && k.proksi.cagr != null && x.cagr_2020 > k.proksi.cagr + 2)
    c.push(`Sejak 2020 ETF ini naik ${persen(x.cagr_2020, 1, false)}/th, jauh di atas rata-rata jangka panjang pembandingnya (${persen(k.proksi.cagr, 1, false)}/th selama ${String(k.proksi.tahun).replace(".", ",")} th). Periode 2020-an termasuk masa bagus untuk saham; jangan pakai angka ini sebagai harapan ke depan.`);
  if (k.sumber?.kurs != null && k.sumber.kurs > 1)
    c.push(`Sekitar ${persen(k.sumber.kurs, 1, false)} poin per tahun dari hasil dalam rupiah datang dari rupiah yang melemah, bukan dari ETF-nya. Kalau rupiah menguat, hasil dalam rupiah ikut berkurang.`);
  if (tahunTurun.value.length) c.push(`Dalam ${lengkap.value.length} tahun penuh, ${tahunTurun.value.length} tahun ditutup rugi (terburuk ${tahunTurun.value.reduce((a, b) => (b.usd < a.usd ? b : a)).tahun}: ${persen(Math.min(...tahunTurun.value.map((r) => r.usd)), 1)}).`);
  return c;
});
</script>

<template>
  <Panel v-if="k" judul="Seberapa bisa dipercaya angka return-nya?" :ket="`Harga harian Yahoo dengan dividen diinvestasikan ulang · ${tgl(k.mulai)} s.d. ${tgl(k.sampai)} (${String(k.tahun).replace('.', ',')} tahun)`">
    <PosisiKini :p="k.posisi" :rupiah="k.posisi_rupiah" />
    <p v-if="k.dipotong_sejak" class="m-0 mb-4 flex gap-2 rounded-2xl bg-kuning-bg px-4 py-2.5 text-xs text-ink-2">
      <TriangleAlert class="mt-0.5 h-3.5 w-3.5 shrink-0 text-kuning" />
      <span>Data harga dari Yahoo sejak {{ tgl(k.data_asli_mulai) }} punya loncatan palsu (harga melompat puluhan persen dalam sehari lalu bertahan berminggu-minggu). Semua angka di halaman ini hanya memakai data sejak {{ tgl(k.dipotong_sejak) }}.</span>
    </p>

    <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
      <div class="rounded-2xl bg-surface-2 px-4 py-3">
        <div class="text-xs text-muted">Panjang data</div>
        <div class="mt-0.5 text-[17px] font-medium">{{ String(k.tahun).replace(".", ",") }} tahun</div>
        <div class="text-[11px] text-muted">{{ lengkap.length }} tahun penuh · {{ lengkap.length - tahunTurun.length }} naik</div>
      </div>
      <div v-for="th in [1, 3, 5]" :key="th" class="rounded-2xl bg-surface-2 px-4 py-3">
        <div class="text-xs text-muted">Beli hari apa saja, tahan {{ th }} th</div>
        <template v-if="j(th)">
          <div class="mt-0.5 text-[17px] font-medium" :class="j(th).untung >= 90 ? 'text-naik' : j(th).untung < 70 ? 'text-turun' : ''">untung {{ persen(j(th).untung, 0, false) }}</div>
          <div class="text-[11px]" :class="j(th).n < 504 ? 'text-kuning' : 'text-muted'">hari beli selama {{ (j(th).n / 252).toFixed(1).replace(".", ",") }} th{{ j(th).n < 504 ? " · terlalu pendek, belum mewakili" : "" }}</div>
        </template>
        <template v-else>
          <div class="mt-0.5 text-[17px] font-medium text-muted">–</div>
          <div class="text-[11px] text-muted">data belum cukup</div>
        </template>
      </div>
    </div>

    <div class="mt-5 grid gap-6 lg:grid-cols-2">
      <div>
        <div class="mb-2 text-[13px] font-medium">Hasil per tahun</div>
        <div class="space-y-1.5">
          <div v-for="r in k.per_tahun" :key="r.tahun" class="grid grid-cols-[52px_1fr_64px_64px] items-center gap-2 text-[13px]">
            <span class="text-ink-2"><span v-if="r.tanda" class="mr-1 inline-block h-1.5 w-1.5 rounded-full align-middle" :class="r.tanda === 'rugi' ? 'bg-turun' : 'bg-kuning'"></span>{{ r.tahun }}</span>
            <div class="relative h-2 rounded-full bg-surface-2">
              <div class="absolute top-0 h-full rounded-full" :class="r.usd >= 0 ? 'left-1/2 bg-naik' : 'right-1/2 bg-turun'" :style="{ width: `${(Math.abs(r.usd) / maksTahun) * 50}%` }"></div>
              <div class="absolute top-[-2px] left-1/2 h-3 w-px bg-garis"></div>
            </div>
            <span class="text-right tabular-nums" :class="kelasPersen(r.usd)">{{ persen(r.usd, 1) }}</span>
            <span class="text-right text-[11px] tabular-nums" :class="kelasPersen(r.rp)">{{ r.rp == null ? "–" : persen(r.rp, 1) }}</span>
          </div>
        </div>
        <p class="m-0 mt-2 text-[11px] text-muted">Kolom kanan: dalam rupiah. {{ k.per_tahun.some((r) => r.berjalan) ? `Tahun ${k.per_tahun.at(-1).tahun} masih berjalan (s.d. ${tgl(k.sampai)}).` : "" }}</p>
        <PenyebabTurun :p="k.penyebab" satuan=" (Rp)" />
      </div>

      <div class="space-y-5">
        <div>
          <PeluangTahan :jendela="k.jendela" :jendela-rp="k.jendela_rp" satuan="hari bursa" />
        </div>

        <div v-if="k.sumber">
          <div class="mb-2 text-[13px] font-medium">Dari mana hasilnya (per tahun sejak {{ tgl(k.sumber.mulai) }})</div>
          <div class="rounded-2xl border border-garis text-[13px]">
            <div class="flex justify-between px-4 py-1.5"><span class="text-ink-2">Kenaikan harga</span><span class="tabular-nums" :class="kelasPersen(k.sumber.harga)">{{ persen(k.sumber.harga, 1) }}</span></div>
            <div class="flex justify-between border-t border-garis px-4 py-1.5"><span class="text-ink-2">+ Dividen (diinvestasikan ulang)</span><span class="tabular-nums" :class="kelasPersen(k.sumber.dividen)">{{ persen(k.sumber.dividen, 1) }}</span></div>
            <div class="flex justify-between border-t border-garis px-4 py-1.5"><span class="text-ink-2">= Hasil dalam {{ x.mata_uang === "USD" ? "dolar" : "mata uang asal" }}</span><span class="font-medium tabular-nums" :class="kelasPersen(k.sumber.total)">{{ persen(k.sumber.total, 1) }}</span></div>
            <template v-if="k.sumber.kurs != null">
              <div class="flex justify-between border-t border-garis px-4 py-1.5"><span class="text-ink-2">+ Perubahan kurs rupiah</span><span class="tabular-nums" :class="kelasPersen(k.sumber.kurs)">{{ persen(k.sumber.kurs, 1) }}</span></div>
              <div class="flex justify-between border-t border-garis px-4 py-1.5"><span class="font-medium">= Hasil dalam rupiah</span><span class="font-medium tabular-nums" :class="kelasPersen(k.sumber.rupiah)">{{ persen(k.sumber.rupiah, 1) }}</span></div>
            </template>
          </div>
          <p class="m-0 mt-1.5 text-[11px] text-muted">Selisih per tahun (dibulatkan), sudah setelah biaya pengelolaan ETF; belum dipotong pajak dividen dan fee broker.</p>
        </div>
      </div>
    </div>

    <div class="mt-6 grid gap-6 lg:grid-cols-2">
      <div>
        <div class="mb-2 text-[13px] font-medium">Penurunan terbesar & berapa lama pulih</div>
        <table v-if="k.penurunan.length" class="tabel">
          <thead><tr><th>Dari puncak</th><th class="!text-right">Turun</th><th class="!text-right">Lama turun</th><th class="!text-right">Lama pulih</th></tr></thead>
          <tbody>
            <tr v-for="p in k.penurunan" :key="p.puncak">
              <td>{{ tgl(p.puncak) }}</td>
              <td class="text-right tabular-nums text-turun">{{ persen(p.turun, 1) }}</td>
              <td class="text-right tabular-nums">{{ bln(p.bulan_turun) }}</td>
              <td class="text-right tabular-nums">{{ p.pulih ? bln(p.bulan_pulih) : "belum pulih" }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="m-0 text-[13px] text-muted">Belum pernah turun lebih dari 10% dari puncak.</p>
        <div class="mt-3 flex flex-wrap gap-1.5 text-xs">
          <span v-for="c in k.krisis" :key="c.nama" class="chip" :class="c.turun == null ? 'bg-surface-2 text-muted' : 'bg-turun-bg text-turun'">
            {{ c.nama }}: {{ c.turun == null ? "belum terdaftar" : persen(c.turun, 1) }}
          </span>
        </div>
      </div>

      <div v-if="k.proksi" class="rounded-2xl border border-dashed border-garis px-4 py-3">
        <div class="flex items-center gap-2 text-[13px] font-medium"><History class="h-4 w-4 text-muted" />Gambaran jangka panjang dari ETF yang mirip</div>
        <p class="m-0 mt-1.5 text-xs leading-relaxed text-ink-2">
          {{ x.kode }} baru {{ String(k.tahun).replace(".", ",") }} tahun. <b class="font-medium text-ink">{{ k.proksi.kode }}</b> ({{ k.proksi.nama }}, {{ k.proksi.syariah ? "syariah" : "bukan syariah" }})
          punya data {{ String(k.proksi.tahun).replace(".", ",") }} tahun dan gerak mingguannya {{ Math.round(k.proksi.korelasi * 100) }}% searah. Ini <b class="font-medium text-ink">pembanding, bukan {{ x.kode }}</b>.
        </p>
        <div class="mt-3 grid grid-cols-2 gap-2 text-[13px]">
          <div class="rounded-xl bg-surface-2 px-3 py-2"><div class="text-[11px] text-muted">Rata-rata per tahun</div><div class="font-medium" :class="kelasPersen(k.proksi.cagr)">{{ persen(k.proksi.cagr, 1) }}</div></div>
          <div class="rounded-xl bg-surface-2 px-3 py-2"><div class="text-[11px] text-muted">Turun terdalam</div><div class="font-medium text-turun">{{ persen(k.proksi.dd, 1) }}</div></div>
          <div class="rounded-xl bg-surface-2 px-3 py-2"><div class="text-[11px] text-muted">Tahun terburuk</div><div class="font-medium" :class="kelasPersen(k.proksi.tahun_terburuk?.usd)">{{ k.proksi.tahun_terburuk ? `${k.proksi.tahun_terburuk.tahun}: ${persen(k.proksi.tahun_terburuk.usd, 1)}` : "–" }}</div></div>
          <div class="rounded-xl bg-surface-2 px-3 py-2"><div class="text-[11px] text-muted">Tahun naik</div><div class="font-medium">{{ k.proksi.tahun_naik }} dari {{ k.proksi.tahun_dihitung }}</div></div>
        </div>
        <div class="mt-2 flex flex-wrap gap-1.5 text-xs">
          <span v-for="w in k.proksi.jendela.filter((w) => w.tahun >= 5)" :key="w.tahun" class="chip bg-surface-2 text-ink-2">tahan {{ w.tahun }} th: untung {{ persen(w.untung, 0, false) }}, terburuk {{ persen(w.terburuk, 1) }}/th</span>
          <span v-for="c in k.proksi.krisis.filter((c) => c.turun != null)" :key="c.nama" class="chip bg-turun-bg text-turun">{{ c.nama }}: {{ persen(c.turun, 1) }}</span>
        </div>
      </div>
    </div>

    <div v-if="catatan.length" class="mt-6 rounded-2xl bg-surface-2 px-4 py-3">
      <div class="flex items-center gap-2 text-[13px] font-medium"><ShieldCheck class="h-4 w-4 text-aksen" />Cara membaca angka ini dengan jujur</div>
      <ul class="m-0 mt-2 space-y-1 pl-5 text-[13px] leading-relaxed text-ink-2">
        <li v-for="c in catatan" :key="c">{{ c }}</li>
      </ul>
    </div>
  </Panel>
</template>

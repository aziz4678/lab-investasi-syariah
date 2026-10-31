<script setup>
import { computed } from "vue";
import { ShieldCheck, History, TriangleAlert } from "lucide-vue-next";
import { persen, tanggal, kelasPersen } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import PenyebabTurun from "@/components/produk/PenyebabTurun.vue";
import PeluangTahan from "@/components/produk/PeluangTahan.vue";
import PosisiKini from "@/components/produk/PosisiKini.vue";

const props = defineProps({ k: Object, p: Object });
const tgl = (v) => (v ? tanggal(v) : "–");
const koma = (v) => String(v).replace(".", ",");
const bln = (v) => (v == null ? "–" : v < 1 ? "< 1 bln" : v < 12 ? `${Math.round(v)} bln` : `${koma((v / 12).toFixed(1))} th`);
const maks = computed(() => Math.max(1, ...(props.k?.per_tahun || []).map((r) => Math.abs(r.ret))));
const lengkap = computed(() => (props.k?.per_tahun || []).filter((r) => !r.berjalan));
const rugi = computed(() => lengkap.value.filter((r) => r.ret < 0));
const kalahInflasi = computed(() => lengkap.value.filter((r) => r.inflasi != null && r.ret <= r.inflasi));
const berjalan = computed(() => props.k?.per_tahun?.find((r) => r.berjalan));
const tile = computed(() => {
  const k = props.k;
  if (!k) return [];
  const t = [{ label: "Kalahkan inflasi", n: k.di_atas_inflasi, dari: k.tahun_inflasi }, { label: "Di atas median kategori", n: k.di_atas_kategori, dari: k.tahun_kategori }];
  if (k.patokan) t.push({ label: `Di atas ${k.patokan.label.replace(" (perkiraan)", "")}`, n: k.di_atas_patokan, dari: k.tahun_patokan });
  return t;
});
const catatan = computed(() => {
  const k = props.k, p = props.p, c = [];
  if (!k) return c;
  if (k.tahun < 5) c.push(`Data baru ${koma(k.tahun)} tahun. Satu atau dua tahun bagus belum cukup untuk menilai produk; tunggu sampai ada tahun yang sulit.`);
  if (k.krisis?.find((x) => x.nama.includes("2018"))?.turun == null && ["pendapatan_tetap", "campuran", "saham", "indeks"].includes(p?.kategori))
    c.push("Produk ini belum pernah melewati 2018, saat rupiah melemah dan suku bunga naik cepat. Banyak RD pendapatan tetap dan saham syariah rugi tahun itu.");
  if (k.bagi_dividen) c.push("Produk ini tercatat membagi dividen tunai. Angka di sini hanya dari NAV, jadi hasil sebenarnya lebih besar (dividen tidak ikut terhitung).");
  if (k.proksi && k.cagr != null && k.proksi.cagr != null && k.cagr > k.proksi.cagr + 2)
    c.push(`Rata-rata ${persen(k.cagr, 1, false)}/th produk ini jauh di atas pembanding jangka panjangnya (${persen(k.proksi.cagr, 1, false)}/th selama ${koma(k.proksi.tahun)} th). Bisa karena periodenya sedang bagus; jangan pakai sebagai harapan ke depan.`);
  if (kalahInflasi.value.length) c.push(`Dalam ${lengkap.value.length} tahun penuh, ${kalahInflasi.value.length} tahun hasilnya tidak mengalahkan inflasi (${kalahInflasi.value.map((r) => r.tahun).join(", ")}).`);
  if (rugi.value.length) c.push(`${rugi.value.length} tahun ditutup rugi (terburuk ${rugi.value.reduce((a, b) => (b.ret < a.ret ? b : a)).tahun}: ${persen(Math.min(...rugi.value.map((r) => r.ret)), 1)}).`);
  return c;
});
</script>

<template>
  <Panel v-if="k" judul="Seberapa bisa dipercaya angka return-nya?" :ket="`NAV akhir bulan dari laporan OJK + Pasardana · ${tgl(k.mulai)} s.d. ${tgl(k.sampai)} (${koma(k.tahun)} tahun) · setelah biaya`">
    <PosisiKini :p="k.posisi" />
    <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
      <div class="rounded-2xl bg-surface-2 px-4 py-3">
        <div class="text-xs text-muted">Panjang data</div>
        <div class="mt-0.5 text-[17px] font-medium">{{ koma(k.tahun) }} tahun</div>
        <div class="text-[11px] text-muted">{{ lengkap.length }} tahun penuh · {{ lengkap.length - rugi.length }} naik</div>
      </div>
      <div v-for="t in tile" :key="t.label" class="rounded-2xl bg-surface-2 px-4 py-3">
        <div class="text-xs text-muted">{{ t.label }}</div>
        <template v-if="t.dari">
          <div class="mt-0.5 text-[17px] font-medium" :class="t.n === t.dari ? 'text-naik' : t.n / t.dari < 0.6 ? 'text-turun' : ''">{{ t.n }} dari {{ t.dari }} tahun</div>
          <div class="text-[11px]" :class="t.dari < 3 ? 'text-kuning' : 'text-muted'">{{ t.dari < 3 ? "terlalu sedikit tahun, belum mewakili" : "tahun penuh" }}</div>
        </template>
        <template v-else>
          <div class="mt-0.5 text-[17px] font-medium text-muted">–</div>
          <div class="text-[11px] text-muted">belum ada tahun penuh</div>
        </template>
      </div>
    </div>

    <div class="mt-5">
      <div class="mb-2 text-[13px] font-medium">Hasil per tahun dibanding pembanding</div>
      <div class="overflow-x-auto">
        <table class="tabel">
          <thead>
            <tr>
              <th>Tahun</th><th class="w-[34%]">Produk ini</th><th class="!text-right">Median kategori</th>
              <th v-if="k.patokan" class="!text-right">{{ k.patokan.label }}</th><th class="!text-right">Inflasi</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in k.per_tahun" :key="r.tahun">
              <td class="text-ink-2"><span v-if="r.tanda" class="mr-1.5 inline-block h-1.5 w-1.5 rounded-full align-middle" :class="r.tanda === 'rugi' ? 'bg-turun' : 'bg-kuning'" :title="r.tanda === 'rugi' ? 'Rugi; lihat Kenapa turun?' : 'Melambat; lihat Kenapa turun?'"></span>{{ r.tahun }}<span v-if="r.berjalan" class="text-[10.5px] text-muted"> · s.d. {{ tgl(k.sampai) }}</span></td>
              <td>
                <div class="flex items-center gap-2">
                  <div class="relative hidden h-2 flex-1 rounded-full bg-surface-2 sm:block">
                    <div class="absolute top-0 h-full rounded-full" :class="r.ret >= 0 ? 'left-1/2 bg-naik' : 'right-1/2 bg-turun'" :style="{ width: `${(Math.abs(r.ret) / maks) * 50}%` }"></div>
                    <div class="absolute top-[-2px] left-1/2 h-3 w-px bg-garis"></div>
                  </div>
                  <span class="ml-auto w-14 text-right font-medium tabular-nums" :class="kelasPersen(r.ret)">{{ persen(r.ret, 1) }}</span>
                </div>
              </td>
              <td class="text-right tabular-nums" :class="kelasPersen(r.kategori)">{{ r.kategori == null ? "–" : persen(r.kategori, 1) }}<span v-if="r.jumlah_kategori" class="text-[10.5px] text-muted"> ({{ r.jumlah_kategori }})</span></td>
              <td v-if="k.patokan" class="text-right tabular-nums" :class="kelasPersen(r.patokan)">{{ r.patokan == null ? "–" : persen(r.patokan, 1) }}</td>
              <td class="text-right tabular-nums text-ink-2">{{ r.inflasi == null ? "–" : persen(r.inflasi, 1, false) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <details class="mt-2 text-xs text-ink-2">
        <summary class="cursor-pointer text-muted">Dari mana angka pembandingnya?</summary>
        <ul class="m-0 mt-1.5 space-y-1 pl-5 leading-relaxed">
          <li><b class="font-medium text-ink">Median kategori</b>: nilai tengah hasil RD {{ p.kategori_label.toLowerCase() }} syariah lain yang punya data di tahun itu (angka dalam kurung = jumlah produk). Hanya RD yang masih ada; yang sudah bubar tidak terhitung, jadi median cenderung sedikit terlalu bagus.{{ k.dikecualikan ? ` ${k.dikecualikan} RD yang tercatat membagi dividen tunai tidak dihitung karena NAV-nya turun tiap bagi dividen; RD lain yang membagi dividen tanpa tercatat mungkin masih terhitung.` : "" }}</li>
          <li v-if="k.patokan"><b class="font-medium text-ink">{{ k.patokan.label }}</b>: {{ k.patokan.ket }}.</li>
          <li><b class="font-medium text-ink">Inflasi</b>: inflasi tahunan (Desember ke Desember) dari BI.</li>
          <li v-if="berjalan">Tahun {{ berjalan.tahun }} masih berjalan: angka pembanding dihitung sebagian tahun (bunga dan inflasi dibagi proporsional) supaya sebanding dengan hasil sejak awal tahun.</li>
        </ul>
      </details>
      <PenyebabTurun :p="k.penyebab" />
    </div>

    <div class="mt-6 grid gap-6 lg:grid-cols-2 [&>div]:min-w-0">
      <div>
        <PeluangTahan :jendela="k.jendela" satuan="bulan" />
      </div>

      <div>
        <div class="mb-2 text-[13px] font-medium">Penurunan terbesar & berapa lama pulih</div>
        <div v-if="k.penurunan.length" class="overflow-x-auto"><table class="tabel">
          <thead><tr><th>Dari puncak</th><th class="!text-right">Turun</th><th class="!text-right">Lama turun</th><th class="!text-right">Lama pulih</th></tr></thead>
          <tbody>
            <tr v-for="x in k.penurunan" :key="x.puncak">
              <td>{{ tgl(x.puncak) }}</td>
              <td class="text-right tabular-nums text-turun">{{ persen(x.turun, 1) }}</td>
              <td class="text-right tabular-nums">{{ bln(x.bulan_turun) }}</td>
              <td class="text-right tabular-nums">{{ x.pulih ? bln(x.bulan_pulih) : "belum pulih" }}</td>
            </tr>
          </tbody>
        </table></div>
        <p v-else class="m-0 text-[13px] text-muted">Belum pernah turun lebih dari 2% dari puncak (dilihat per akhir bulan).</p>
        <div class="mt-3 flex flex-wrap gap-1.5 text-xs">
          <span v-for="c in k.krisis" :key="c.nama" class="chip" :class="c.turun == null ? 'bg-surface-2 text-muted' : c.turun < 0 ? 'bg-turun-bg text-turun' : 'bg-naik-bg text-naik'">
            {{ c.nama }}: {{ c.turun == null ? "belum ada data" : persen(c.turun, 1) }}
          </span>
        </div>
      </div>
    </div>

    <div v-if="k.proksi" class="mt-6 rounded-2xl border border-dashed border-garis px-4 py-3">
      <div class="flex items-center gap-2 text-[13px] font-medium"><History class="h-4 w-4 text-muted" />Gambaran jangka panjang dari RD yang mirip</div>
      <p class="m-0 mt-1.5 text-xs leading-relaxed text-ink-2">
        Produk ini baru {{ koma(k.tahun) }} tahun. <b class="font-medium text-ink">{{ k.proksi.nama }}</b> punya data {{ koma(k.proksi.tahun) }} tahun; selama periode yang sama gerak bulanannya {{ Math.round(k.proksi.korelasi * 100) }}% searah dan hasilnya selisih tidak lebih dari 2 poin per tahun. Ini <b class="font-medium text-ink">pembanding, bukan produk ini</b>.
      </p>
      <div class="mt-3 grid grid-cols-2 gap-2 text-[13px] md:grid-cols-4">
        <div class="rounded-xl bg-surface-2 px-3 py-2"><div class="text-[11px] text-muted">Rata-rata per tahun</div><div class="font-medium" :class="kelasPersen(k.proksi.cagr)">{{ persen(k.proksi.cagr, 1) }}</div></div>
        <div class="rounded-xl bg-surface-2 px-3 py-2"><div class="text-[11px] text-muted">Turun terdalam</div><div class="font-medium text-turun">{{ persen(k.proksi.dd, 1) }}</div></div>
        <div class="rounded-xl bg-surface-2 px-3 py-2"><div class="text-[11px] text-muted">Tahun terburuk</div><div class="font-medium" :class="kelasPersen(k.proksi.tahun_terburuk?.ret)">{{ k.proksi.tahun_terburuk ? `${k.proksi.tahun_terburuk.tahun}: ${persen(k.proksi.tahun_terburuk.ret, 1)}` : "–" }}</div></div>
        <div class="rounded-xl bg-surface-2 px-3 py-2"><div class="text-[11px] text-muted">Tahun naik</div><div class="font-medium">{{ k.proksi.tahun_naik }} dari {{ k.proksi.tahun_dihitung }}</div></div>
      </div>
      <div class="mt-2 flex flex-wrap gap-1.5 text-xs">
        <span v-for="w in k.proksi.jendela.filter((w) => w.tahun >= 3)" :key="w.tahun" class="chip bg-surface-2 text-ink-2">tahan {{ w.tahun }} th: untung {{ persen(w.untung, 0, false) }}, terburuk {{ persen(w.terburuk, 1) }}/th</span>
        <span v-for="c in k.proksi.krisis.filter((c) => c.turun != null)" :key="c.nama" class="chip" :class="c.turun < 0 ? 'bg-turun-bg text-turun' : 'bg-naik-bg text-naik'">{{ c.nama }}: {{ persen(c.turun, 1) }}</span>
      </div>
    </div>
    <p v-else-if="k.tahun < 8" class="m-0 mt-6 flex gap-2 rounded-2xl bg-surface-2 px-4 py-2.5 text-xs text-ink-2">
      <TriangleAlert class="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted" />
      <span>Tidak ada RD syariah sejenis dengan data ≥ 10 tahun yang geraknya dan hasilnya cukup mirip untuk dijadikan gambaran jangka panjang. Pakai median kategori di tabel atas sebagai pembanding.</span>
    </p>

    <div v-if="catatan.length" class="mt-6 rounded-2xl bg-surface-2 px-4 py-3">
      <div class="flex items-center gap-2 text-[13px] font-medium"><ShieldCheck class="h-4 w-4 text-aksen" />Cara membaca angka ini dengan jujur</div>
      <ul class="m-0 mt-2 space-y-1 pl-5 text-[13px] leading-relaxed text-ink-2">
        <li v-for="c in catatan" :key="c">{{ c }}</li>
      </ul>
    </div>
  </Panel>
</template>

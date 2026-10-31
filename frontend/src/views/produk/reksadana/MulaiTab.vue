<script setup>
import { ref, computed, watch } from "vue";
import { Wallet, PiggyBank, Sprout, Shield, ShieldHalf, Flame, ArrowRight, Info as IkonInfo, TriangleAlert } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { persen, rupiah, kelasPersen } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import Pemutar from "@/components/common/Pemutar.vue";
import KartuRD from "@/components/produk/KartuRD.vue";
import { pakaiPlatform } from "@/composables/platformRD";

const props = defineProps({ m: Object, data: Array });
const emit = defineEmits(["buka", "banding", "katalog", "sukuk", "cara"]);
const { info: platform } = pakaiPlatform();

const baca = (k, awal) => {
  try {
    const v = localStorage.getItem(k);
    return v == null ? awal : JSON.parse(v);
  } catch {
    return awal;
  }
};
const simpan = (k, v) => {
  try {
    localStorage.setItem(k, JSON.stringify(v));
  } catch {
    return;
  }
};

const JANGKA = [
  { k: "pendek", ikon: Wallet, judul: "Kurang dari 1 tahun", ket: "Dana darurat, rencana dalam beberapa bulan", tahun: 1 },
  { k: "menengah", ikon: PiggyBank, judul: "1–3 tahun", ket: "Tabungan menikah, DP, biaya sekolah", tahun: 3 },
  { k: "panjang", ikon: Sprout, judul: "5 tahun atau lebih", ket: "Pensiun, pendidikan anak yang masih lama", tahun: 5 },
];
const PROFIL = [
  { k: "rendah", ikon: Shield, judul: "Rendah", ket: "Hampir tidak mau melihat nilainya turun" },
  { k: "sedang", ikon: ShieldHalf, judul: "Sedang", ket: "Turun ±10–20% sementara masih tenang" },
  { k: "tinggi", ikon: Flame, judul: "Tinggi", ket: "Turun 30–50% tetap tahan, tidak panik jual" },
];
const WARNA = { sukuk: "bg-s2", pendapatan_tetap: "bg-s1", pasar_uang: "bg-s4", saham_global: "bg-s5", saham: "bg-s3" };
const PENJELASAN = {
  pasar_uang: "Isinya deposito dan sukuk jangka sangat pendek. Nilainya hampir tidak pernah turun dan bisa dicairkan kapan saja (uang masuk 1–2 hari kerja).",
  pendapatan_tetap: "Isinya sukuk negara dan perusahaan, dikelola manajer investasi. Hasil biasanya di atas deposito, tapi nilainya bisa turun beberapa persen saat suku bunga naik.",
  saham: "Isinya saham perusahaan syariah Indonesia. Bisa naik besar, tapi juga bisa turun lebih dari 30–50% dan butuh bertahun-tahun untuk pulih. Beberapa tahun terakhir kebanyakan masih minus.",
  saham_global: "Isinya saham syariah luar negeri (banyak saham teknologi AS), dalam dolar. Angka di sini sudah dalam rupiah, jadi termasuk efek kurs: untung saat rupiah melemah, berkurang saat rupiah menguat. 3 tahun terakhir sangat bagus karena saham teknologi AS naik tinggi; jangan jadikan patokan.",
  sukuk: "Dibeli langsung tanpa manajer investasi dan dijamin negara. Kalau dipegang sampai jatuh tempo, hasilnya sudah terkunci sejak membeli; harga bisa naik-turun kalau dijual sebelum jatuh tempo.",
};

const jangka = ref(baca("rd_jangka", "menengah"));
const profil = ref(baca("rd_profil_risiko", "rendah"));
const modal = ref(baca("rd_modal", 10000000));
const r = ref(null);
const memuat = ref(false);
async function muat() {
  simpan("rd_jangka", jangka.value);
  simpan("rd_profil_risiko", profil.value);
  memuat.value = true;
  r.value = await ambil(`rd/racikan?jangka=${jangka.value}&profil=${profil.value}`).catch(() => null);
  memuat.value = false;
}
watch([jangka, profil], muat, { immediate: true });
watch(modal, (v) => simpan("rd_modal", Number(v) || 0));

const tahun = computed(() => JANGKA.find((x) => x.k === jangka.value)?.tahun || 1);
const nanti = (p) => (p == null ? null : (Number(modal.value) || 0) * Math.pow(1 + p / 100, tahun.value));
const peta = computed(() => Object.fromEntries((props.data || []).map((x) => [x.id, x])));
const nol = (v) => (v == null ? "–" : Math.abs(v) < 0.05 ? "0,0%" : persen(v, 1));
const koma = (v, d = 1) => (v == null ? "–" : v.toLocaleString("id-ID", { minimumFractionDigits: d, maximumFractionDigits: d }));
const tglBulan = (t) => (t ? new Date(t).toLocaleDateString("id-ID", { month: "short", year: "numeric" }) : "–");
const adaSaham = computed(() => r.value?.bagian?.some((b) => b.kode === "saham" || b.kode === "saham_global"));
const KATALOG = { saham_global: "global", saham: "saham" };
</script>

<template>
  <div class="space-y-5">
    <div class="panel px-6 py-5">
      <div class="text-[17px] font-medium">1. Kapan uangnya akan dipakai?</div>
      <div class="mt-3 grid gap-3 md:grid-cols-3">
        <button v-for="x in JANGKA" :key="x.k" type="button" class="flex items-start gap-3 rounded-2xl border-2 px-4 py-3 text-left transition"
          :class="jangka === x.k ? 'border-aksen bg-aksen-lembut' : 'border-garis hover:border-aksen/50'" @click="jangka = x.k">
          <span class="grid h-10 w-10 shrink-0 place-items-center rounded-full" :class="jangka === x.k ? 'bg-aksen text-aksen-teks' : 'bg-surface-2 text-ink-2'"><component :is="x.ikon" class="h-5 w-5" /></span>
          <span class="min-w-0"><span class="block text-[14px] font-medium">{{ x.judul }}</span><span class="block text-xs text-ink-2">{{ x.ket }}</span></span>
        </button>
      </div>
      <div class="mt-5 text-[17px] font-medium">2. Seberapa tahan melihat nilainya turun?</div>
      <div class="mt-3 grid gap-3 md:grid-cols-3">
        <button v-for="x in PROFIL" :key="x.k" type="button" class="flex items-start gap-3 rounded-2xl border-2 px-4 py-3 text-left transition"
          :class="profil === x.k ? 'border-aksen bg-aksen-lembut' : 'border-garis hover:border-aksen/50'" @click="profil = x.k">
          <span class="grid h-10 w-10 shrink-0 place-items-center rounded-full" :class="profil === x.k ? 'bg-aksen text-aksen-teks' : 'bg-surface-2 text-ink-2'"><component :is="x.ikon" class="h-5 w-5" /></span>
          <span class="min-w-0"><span class="block text-[14px] font-medium">Risiko {{ x.judul.toLowerCase() }}</span><span class="block text-xs text-ink-2">{{ x.ket }}</span></span>
        </button>
      </div>
    </div>

    <Kerangka v-if="!r" panel :n="4" />
    <template v-else>
      <Panel :judul="`Racikan untuk ${r.jangka_label.toLowerCase()}, risiko ${r.profil}`" ket="Pembagian umum berdasarkan jangka waktu dan profil risiko; perkiraan hasil dari data masa lalu, bukan jaminan">
        <div v-if="memuat" class="mb-3"><Pemutar teks="Menghitung ulang..." /></div>
        <div class="flex h-3 overflow-hidden rounded-full">
          <div v-for="b in r.bagian" :key="b.kode" :style="{ width: `${b.persen}%` }" :class="WARNA[b.kode]" class="border-r-2 border-surface last:border-r-0"></div>
        </div>
        <div class="mt-2.5 flex flex-wrap gap-x-5 gap-y-1 text-[13px] text-ink-2">
          <span v-for="b in r.bagian" :key="b.kode" class="inline-flex items-center gap-2"><span class="h-2.5 w-2.5 rounded-full" :class="WARNA[b.kode]"></span>{{ b.nama }} <b class="font-medium text-ink">{{ b.persen }}%</b></span>
        </div>

        <div class="mt-5 grid grid-cols-2 gap-3 md:grid-cols-4">
          <div class="rounded-2xl bg-aksen-lembut px-4 py-3">
            <div class="text-xs text-ink-2">Perkiraan hasil per tahun</div>
            <div class="mt-0.5 text-[22px] font-medium tabular-nums" :class="kelasPersen(r.atas)">{{ persen(r.atas, 1) }}</div>
            <div class="text-[11px] text-muted">kalau memilih produk teratas di bawah</div>
          </div>
          <div class="rounded-2xl bg-surface-2 px-4 py-3">
            <div class="text-xs text-muted">Kalau dapat produk biasa</div>
            <div class="mt-0.5 text-[19px] font-medium tabular-nums" :class="kelasPersen(r.biasa)">{{ persen(r.biasa, 1) }}</div>
            <div class="text-[11px] text-muted">nilai tengah produk sejenis</div>
          </div>
          <div class="rounded-2xl bg-surface-2 px-4 py-3">
            <div class="text-xs text-muted">Bisa turun sementara</div>
            <div class="mt-0.5 text-[19px] font-medium tabular-nums" :class="r.turun < -1 ? 'text-turun' : ''">{{ nol(r.turun) }}</div>
            <div class="text-[11px] text-muted">perkiraan dari turun terburuk RD di racikan</div>
          </div>
          <div class="rounded-2xl bg-surface-2 px-4 py-3">
            <div class="text-xs text-muted">Pembanding</div>
            <div class="mt-0.5 text-[13px] leading-snug text-ink-2">Deposito ±<b class="font-medium text-ink">{{ koma(r.deposito) }}%</b><br />Inflasi <b class="font-medium text-ink">{{ koma(r.inflasi?.nilai, 2) }}%</b></div>
          </div>
        </div>

        <div class="mt-4 flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px] text-ink-2">
          Contoh: <span class="inline-flex items-center gap-1">Rp <input v-model.number="modal" type="number" min="0" step="1000000" class="!h-8 w-36 tabular-nums" /></span>
          setelah {{ tahun }} tahun menjadi sekitar <b class="font-medium text-ink">Rp{{ rupiah(Math.round((nanti(r.atas) || 0) / 1000) * 1000) }}</b>
          <span class="text-muted">(produk biasa: Rp{{ rupiah(Math.round((nanti(r.biasa) || 0) / 1000) * 1000) }})</span>
        </div>

        <p v-if="jangka === 'pendek' && profil !== 'rendah'" class="m-0 mt-4 flex gap-2 rounded-2xl bg-surface-2 px-4 py-3 text-[13px] text-ink-2">
          <IkonInfo class="mt-0.5 h-4 w-4 shrink-0 text-aksen" />
          <span>Untuk uang yang dipakai kurang dari 1 tahun, risiko lebih tinggi hampir tidak menambah hasil, tapi bisa membuat nilainya turun pas mau dipakai. Pasar uang tetap pilihan paling masuk akal.</span>
        </p>
        <p v-if="adaSaham" class="m-0 mt-4 flex gap-2 rounded-2xl bg-kuning-bg px-4 py-3 text-[13px] text-ink-2">
          <TriangleAlert class="mt-0.5 h-4 w-4 shrink-0 text-kuning" />
          <span>Porsi saham di racikan ini lebih banyak ke <b class="font-medium text-ink">saham global</b> karena data 2013–2026 menunjukkan RD saham syariah Indonesia rata-rata minus, sedangkan saham global (dalam rupiah) naik. Porsi ini ditetapkan setelah melihat data, bukan hasil uji. Hasil saham global sangat bergantung pada saham teknologi AS dan kurs rupiah; bisa berbalik.</span>
        </p>
      </Panel>

      <div v-for="b in r.bagian" :key="b.kode" class="panel px-6 py-5">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="flex items-center gap-2.5">
            <span class="h-3 w-3 rounded-full" :class="WARNA[b.kode]"></span>
            <div>
              <div class="text-[15px] font-medium">{{ b.nama }} · {{ b.persen }}%</div>
              <div class="text-xs text-muted">Rp{{ rupiah(Math.round(((Number(modal) || 0) * b.persen) / 100)) }} dari contoh di atas</div>
            </div>
          </div>
          <div class="flex flex-wrap gap-2 text-xs">
            <span class="chip bg-aksen-lembut text-aksen" :title="b.dasar">{{ b.kode === "sukuk" ? "Hasil terkunci" : "Teratas" }} {{ persen(b.atas, 1) }}/th</span>
            <span v-if="b.kode !== 'sukuk'" class="chip bg-surface-2 text-ink-2" :title="b.dasar">Biasa {{ persen(b.biasa, 1) }}/th</span>
            <span v-if="b.turun != null" class="chip" :class="b.turun < -1 ? 'bg-turun-bg text-turun' : 'bg-surface-2 text-ink-2'">Turun terburuk {{ nol(b.turun) }}</span>
          </div>
        </div>
        <p class="m-0 mt-3 text-[13px] leading-relaxed text-ink-2">{{ PENJELASAN[b.kode] }}</p>
        <p class="m-0 mt-1 text-[11px] text-muted">Dasar angka: {{ b.dasar }}.<template v-if="b.dihitung"> {{ b.rugi }} dari {{ b.dihitung }} produk minus.</template><template v-if="b.terbaik && b.kode !== 'pasar_uang'"> Terbaik: <button class="text-aksen hover:underline" @click="emit('buka', b.terbaik.id)">{{ b.terbaik.nama }}</button> {{ persen(b.terbaik.nilai, 1) }}/th (hasil masa lalu, belum tentu terulang).</template></p>

        <div v-if="b.kode === 'sukuk'" class="mt-4">
          <div class="overflow-x-auto">
            <table class="tabel min-w-[560px]">
              <thead><tr><th>Seri</th><th>Jatuh tempo</th><th class="!text-right">Harga</th><th class="!text-right" title="Perkiraan hasil per tahun kalau dibeli di harga sekarang dan dipegang sampai jatuh tempo, dikurangi pajak kupon 10%">Hasil bersih/th</th></tr></thead>
              <tbody>
                <tr v-for="s in b.sukuk" :key="s.kode">
                  <td><span class="font-medium">{{ s.kode }}</span> <span class="text-xs text-muted">{{ s.jenis }} · kupon {{ koma(s.kupon, 2) }}%</span></td>
                  <td class="tabular-nums">{{ tglBulan(s.jatuh_tempo) }} <span class="text-xs text-muted">· {{ koma(s.sisa_tahun) }} th</span></td>
                  <td class="text-right tabular-nums">{{ s.harga == null ? "–" : koma(s.harga, 2) }}</td>
                  <td class="text-right font-medium tabular-nums" :class="kelasPersen(s.bersih)">{{ persen(s.bersih, 2) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="m-0 mt-2 text-xs leading-relaxed text-muted">Sukuk ritel (SR) dijual saat masa penawaran lewat bank/aplikasi mitra (termasuk Bibit, Ajaib, Bareksa); PBS dan seri lama dibeli di pasar sekunder lewat sekuritas atau bank. Harga di atas 100 berarti hasil bersih lebih kecil dari kupon. <button class="text-aksen hover:underline" @click="emit('sukuk')">Lihat semua sukuk</button></p>
        </div>
        <div v-else class="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <KartuRD v-for="(id, i) in b.produk.filter((x) => peta[x])" :key="id" :r="peta[id]" :nomor="i + 1" @buka="emit('buka', $event)" @banding="emit('banding', $event)" />
        </div>
        <button v-if="b.kode !== 'sukuk'" class="tombol mt-4" @click="emit('katalog', KATALOG[b.kode] || b.kode)">Lihat semua {{ b.nama.toLowerCase() }}<ArrowRight class="h-3.5 w-3.5" /></button>
      </div>
    </template>

    <Panel judul="Sebelum membeli" ket="Lima hal yang sering dilewatkan pemula">
      <ol class="m-0 space-y-2.5 pl-0 text-[13px] leading-relaxed text-ink-2">
        <li class="flex gap-3"><span class="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-aksen-lembut text-xs font-semibold text-aksen">1</span><span><b class="font-medium text-ink">Beli hanya lewat aplikasi berizin OJK.</b> Jangan pernah transfer ke rekening pribadi. <button class="text-aksen hover:underline" @click="emit('cara')">Lihat daftar {{ platform?.pto?.length || "" }} aplikasi berizin</button></span></li>
        <li class="flex gap-3"><span class="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-aksen-lembut text-xs font-semibold text-aksen">2</span><span><b class="font-medium text-ink">Cocokkan jangka waktu.</b> Sukuk yang jatuh temponya lebih lama dari rencanamu harus dijual di harga pasar; RD saham jangan untuk uang tahun depan.</span></li>
        <li class="flex gap-3"><span class="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-aksen-lembut text-xs font-semibold text-aksen">3</span><span><b class="font-medium text-ink">Lihat peringatan kuning</b> di tiap produk dan baca fund fact sheet terbarunya.</span></li>
        <li class="flex gap-3"><span class="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-aksen-lembut text-xs font-semibold text-aksen">4</span><span><b class="font-medium text-ink">Perhatikan biaya.</b> Biaya per tahun sudah dipotong dari hasil; cek juga biaya beli/jual/pindah di aplikasinya.</span></li>
        <li class="flex gap-3"><span class="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-aksen-lembut text-xs font-semibold text-aksen">5</span><span><b class="font-medium text-ink">"Teratas" bukan janji.</b> Produk teratas dipilih dari catatan masa lalu (lencana); belum terbukti tetap unggul. Sebar ke 2–3 produk dari manajer investasi berbeda.</span></li>
      </ol>
      <p class="m-0 mt-4 flex items-center gap-1.5 text-xs text-muted"><IkonInfo class="h-3.5 w-3.5" />Bukan nasihat keuangan. Sesuaikan dengan kondisi dan tujuanmu sendiri.</p>
    </Panel>
  </div>
</template>

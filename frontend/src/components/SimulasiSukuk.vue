<script setup>
import { ref, computed, watch } from "vue";
import { rupiah, persen, kelasPersen } from "../util.js";
import Panel from "./Panel.vue";

const props = defineProps({ x: Object });
const PAJAK = 0.1;
const FREK = { SR: 12, ST: 12, PBS: 2, "Negara lain": 2, Korporasi: 4, SPNS: 0 };
const NAMA_FREK = { 12: "bulanan", 4: "per kuartal", 2: "per semester", 1: "tahunan" };
const PILIHAN = [1e6, 1e7, 5e7, 1e8];

const nominal = ref(10000000);
const harga = ref(props.x?.harga ?? 100);
watch(() => props.x?.kode, () => (harga.value = props.x?.harga ?? 100));

const rp = (v) => `${v < 0 ? "-" : ""}Rp${rupiah(Math.round(Math.abs(v)))}`;
const tglPendek = (d) => d.toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });

function geserBulan(d, n) {
  const h = d.getDate();
  const t = new Date(d.getFullYear(), d.getMonth() + n, 1);
  t.setDate(Math.min(h, new Date(t.getFullYear(), t.getMonth() + 1, 0).getDate()));
  return t;
}

const hasil = computed(() => {
  const x = props.x;
  const N = Math.max(0, Number(nominal.value) || 0);
  const H = Math.max(0, Number(harga.value) || 0);
  if (!x?.jatuh_tempo || !N || !H) return null;
  const kini = new Date();
  kini.setHours(0, 0, 0, 0);
  const tempo = new Date(x.jatuh_tempo);
  tempo.setHours(0, 0, 0, 0);
  if (tempo <= kini) return null;
  const kupon = x.kupon || 0;
  const f = kupon > 0 ? FREK[x.jenis] ?? 2 : 0;
  const jadwal = [];
  let terakhir = null;
  if (f) {
    const langkah = 12 / f;
    for (let i = 0; ; i++) {
      const d = geserBulan(tempo, -langkah * i);
      if (d <= kini) {
        terakhir = d;
        break;
      }
      jadwal.unshift(d);
      if (i > 2000) break;
    }
  }
  const perBayar = (N * kupon) / (f || 1);
  const berjalan = f && terakhir ? (N * kupon * (kini - terakhir)) / 864e5 / 365 : 0;
  const beli = (N * H) / 100;
  const modal = beli + berjalan;
  const kuponKotor = perBayar * jadwal.length;
  const kuponPajak = kuponKotor * PAJAK;
  const selisih = N - beli;
  const selisihPajak = selisih > 0 ? selisih * PAJAK : 0;
  const akhir = N + kuponKotor - kuponPajak - selisihPajak;
  const untung = akhir - modal;
  const tahun = (tempo - kini) / 864e5 / 365.25;
  return {
    f, jadwal, perBayar, perBayarBersih: perBayar * (1 - PAJAK), berjalan, beli, modal, kuponKotor, kuponPajak, selisih, selisihPajak, akhir, untung, tahun,
    total: (untung / modal) * 100, tahunan: tahun > 0 ? (Math.pow(akhir / modal, 1 / tahun) - 1) * 100 : null, tempo,
  };
});

const daftarBayar = computed(() => {
  const h = hasil.value;
  if (!h?.jadwal.length) return [];
  const j = h.jadwal.map((d, i) => ({ d, nilai: h.perBayarBersih + (i === h.jadwal.length - 1 ? Number(nominal.value) : 0), akhir: i === h.jadwal.length - 1 }));
  return j.length <= 7 ? j : [...j.slice(0, 5), null, j.at(-1)];
});
</script>

<template>
  <Panel judul="Simulasi Investasi" :ket="`Ilustrasi apabila ${x.kode} dibeli hari ini dan dimiliki hingga jatuh tempo`">
    <div class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)]">
      <div class="space-y-4 rounded-2xl bg-surface-2 p-5">
        <label class="block">
          <span class="mb-1.5 block text-xs text-muted">Nilai nominal</span>
          <span class="flex items-center gap-2 text-[13px] text-ink-2">Rp <input v-model.number="nominal" type="number" min="1000000" step="1000000" class="!h-10 w-full !border !border-garis !bg-surface tabular-nums" /></span>
        </label>
        <div class="flex flex-wrap gap-2">
          <button v-for="v in PILIHAN" :key="v" type="button" class="h-7 rounded-full border px-3 text-xs transition"
            :class="Number(nominal) === v ? 'border-aksen bg-aksen-lembut text-aksen' : 'border-garis text-muted hover:text-ink'" @click="nominal = v">Rp{{ v >= 1e9 ? `${v / 1e9} M` : `${v / 1e6} jt` }}</button>
        </div>
        <label class="block">
          <span class="mb-1.5 block text-xs text-muted">Harga beli (% dari nominal)</span>
          <input v-model.number="harga" type="number" min="1" step="0.05" class="!h-10 w-full !border !border-garis !bg-surface tabular-nums" />
          <span class="mt-1 block text-[11px] text-muted">Harga pasar terakhir {{ x.harga == null ? "–" : x.harga.toLocaleString("id-ID", { maximumFractionDigits: 2 }) }}. Isi 100 untuk pembelian di pasar perdana.</span>
        </label>
        <div v-if="hasil" class="border-t border-garis pt-4 text-[13px]">
          <div class="flex justify-between gap-3"><span class="text-ink-2">Harga beli</span><span class="tabular-nums">{{ rp(hasil.beli) }}</span></div>
          <div v-if="hasil.berjalan" class="mt-1.5 flex justify-between gap-3"><span class="text-ink-2" title="Imbalan sejak tanggal kupon terakhir yang menjadi hak penjual">Imbalan berjalan</span><span class="tabular-nums">{{ rp(hasil.berjalan) }}</span></div>
          <div class="mt-2 flex justify-between gap-3 border-t border-garis pt-2 font-medium"><span>Dana dibutuhkan</span><span class="tabular-nums">{{ rp(hasil.modal) }}</span></div>
        </div>
      </div>

      <div v-if="hasil" class="min-w-0">
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div class="rounded-2xl border border-garis px-4 py-3">
            <div class="text-xs text-muted">Imbalan bersih {{ hasil.f ? NAMA_FREK[hasil.f] : "" }}</div>
            <div class="mt-0.5 text-[17px] font-medium tabular-nums">{{ hasil.f ? rp(hasil.perBayarBersih) : "–" }}</div>
            <div class="text-[11px] text-muted">{{ hasil.f ? "setelah pajak 10%" : "tanpa kupon (diskonto)" }}</div>
          </div>
          <div class="rounded-2xl border border-garis px-4 py-3">
            <div class="text-xs text-muted">Total imbalan bersih</div>
            <div class="mt-0.5 text-[17px] font-medium tabular-nums text-naik">{{ rp(hasil.kuponKotor - hasil.kuponPajak) }}</div>
            <div class="text-[11px] text-muted">{{ hasil.jadwal.length }} kali pembayaran</div>
          </div>
          <div class="rounded-2xl border border-garis px-4 py-3">
            <div class="text-xs text-muted">Keuntungan bersih</div>
            <div class="mt-0.5 text-[17px] font-medium tabular-nums" :class="kelasPersen(hasil.untung)">{{ rp(hasil.untung) }}</div>
            <div class="text-[11px]" :class="kelasPersen(hasil.total)">{{ persen(hasil.total, 2) }} total</div>
          </div>
          <div class="rounded-2xl border border-garis px-4 py-3">
            <div class="text-xs text-muted">Imbal hasil bersih per tahun</div>
            <div class="mt-0.5 text-[17px] font-medium tabular-nums" :class="kelasPersen(hasil.tahunan)">{{ persen(hasil.tahunan, 2) }}</div>
            <div class="text-[11px] text-muted">{{ hasil.tahun.toLocaleString("id-ID", { maximumFractionDigits: 1 }) }} tahun hingga jatuh tempo</div>
          </div>
        </div>

        <div class="mt-4 rounded-2xl border border-garis px-4 py-3 text-[13px]">
          <div class="mb-2 text-xs text-muted">Rincian hingga jatuh tempo {{ tglPendek(hasil.tempo) }}</div>
          <div class="flex justify-between gap-3"><span class="text-ink-2">Pokok kembali</span><span class="tabular-nums">{{ rp(Number(nominal)) }}</span></div>
          <div class="mt-1.5 flex justify-between gap-3"><span class="text-ink-2">Imbalan kotor</span><span class="tabular-nums">{{ rp(hasil.kuponKotor) }}</span></div>
          <div class="mt-1.5 flex justify-between gap-3"><span class="text-ink-2">Pajak imbalan 10%</span><span class="tabular-nums text-turun">{{ rp(-hasil.kuponPajak) }}</span></div>
          <div v-if="hasil.selisih" class="mt-1.5 flex justify-between gap-3"><span class="text-ink-2">{{ hasil.selisih > 0 ? "Keuntungan harga (beli di bawah 100)" : "Kerugian harga (beli di atas 100)" }}</span><span class="tabular-nums" :class="kelasPersen(hasil.selisih)">{{ rp(hasil.selisih) }}</span></div>
          <div v-if="hasil.selisihPajak" class="mt-1.5 flex justify-between gap-3"><span class="text-ink-2">Pajak keuntungan harga 10%</span><span class="tabular-nums text-turun">{{ rp(-hasil.selisihPajak) }}</span></div>
          <div class="mt-2 flex justify-between gap-3 border-t border-garis pt-2 font-medium"><span>Total diterima</span><span class="tabular-nums">{{ rp(hasil.akhir) }}</span></div>
        </div>

        <div v-if="daftarBayar.length" class="mt-4">
          <div class="mb-2 text-xs text-muted">Jadwal penerimaan</div>
          <div class="flex flex-wrap gap-2">
            <template v-for="(b, i) in daftarBayar" :key="i">
              <div v-if="!b" class="grid place-items-center px-1 text-muted">…</div>
              <div v-else class="min-w-[104px] rounded-xl px-3 py-2" :class="b.akhir ? 'bg-aksen-lembut' : 'bg-surface-2'">
                <div class="text-[11px] text-muted">{{ tglPendek(b.d) }}</div>
                <div class="text-[13px] font-medium tabular-nums" :class="b.akhir ? 'text-aksen' : ''">{{ rp(b.nilai) }}</div>
                <div v-if="b.akhir" class="text-[10px] text-muted">imbalan + pokok</div>
              </div>
            </template>
          </div>
        </div>
      </div>
      <p v-else class="m-0 self-center text-[13px] text-muted">Isi nilai nominal dan harga beli untuk melihat simulasi.</p>
    </div>
    <p class="m-0 mt-4 text-[11px] leading-relaxed text-muted">
      Asumsi: frekuensi imbalan {{ { SR: "bulanan (SR)", PBS: "per semester (PBS)", "Negara lain": "per semester", Korporasi: "per kuartal (umum untuk sukuk korporasi; cek prospektus)", SPNS: "tidak ada (SPNS diterbitkan dengan diskonto)" }[x.jenis] || "per semester" }},
      tanggal pembayaran mengikuti tanggal jatuh tempo, imbalan berjalan dihitung actual/365, pajak final 10% atas imbalan dan keuntungan harga.
      Belum termasuk biaya transaksi agen penjual atau broker. Imbalan sukuk negara dijamin negara; sukuk korporasi memiliki risiko gagal bayar. Bukan nasihat keuangan.
    </p>
  </Panel>
</template>

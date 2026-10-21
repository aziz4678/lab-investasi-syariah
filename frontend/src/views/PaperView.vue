<script setup>
import TeksWarna from "../components/TeksWarna.vue";
import KodeSaham from "../components/KodeSaham.vue";
import { ref, computed, inject, onMounted, onUnmounted } from "vue";
import { RefreshCw, RotateCcw, Lock, Radio, TriangleAlert } from "lucide-vue-next";
import {
  ambil,
  kirim,
  persen,
  rupiah,
  tanggal,
  infoAksi,
  kelasPersen,
} from "../util.js";
import { pakaiPekerjaan } from "../pekerjaan.js";
import KurvaPaper from "../components/KurvaPaper.vue";
import PanelPekerjaan from "../components/PanelPekerjaan.vue";
import Panel from "../components/Panel.vue";
import Stats from "../components/Stats.vue";
import ZonaPaper from "../components/ZonaPaper.vue";
import Kerangka from "../components/Kerangka.vue";

const muatStatus = inject("muatStatus");
const statusApp = inject("status");
const langsung = ref(null);
let detakLangsung = null;
async function muatLangsung() {
  langsung.value = await ambil("paper/langsung").catch(() => langsung.value);
}
onUnmounted(() => clearInterval(detakLangsung));
const adaLangsung = computed(() => langsung.value?.ada && r.value?.mulai && langsung.value.sesi > (r.value.tgl_terakhir || ""));
const kini = (t) => (adaLangsung.value ? langsung.value.posisi?.[t] : null);
const ekuitasKini = computed(() => (adaLangsung.value ? langsung.value.ekuitas : null));
const bawahStop = computed(() => (adaLangsung.value ? aktif.value.filter((p) => kini(p.ticker)?.di_bawah_stop) : []));
const r = ref(null);
const siap = ref(false);
const versiMuat = ref(0);
const ekuitas = ref([]);
const transaksi = ref([]);
const sinyal = ref([]);
const arsip = ref([]);
const galat = ref("");
const { kerja, galat: galatKerja, sibuk, mulai, lanjutkan } = pakaiPekerjaan();
const modal = ref(100_000_000);
const konfirmasi = ref("");
const tanyaReset = ref(false);
const pesan = ref("");

async function muat() {
  try {
    r.value = await ambil("paper/ringkasan");
    versiMuat.value += 1;
    arsip.value = await ambil("paper/arsip").catch(() => []);
    if (r.value.mulai) {
      [ekuitas.value, transaksi.value, sinyal.value] = await Promise.all([
        ambil("paper/ekuitas"),
        ambil("paper/transaksi"),
        ambil("paper/sinyal?batas=20"),
      ]);
    } else {
      ekuitas.value = [];
      transaksi.value = [];
      sinyal.value = [];
    }
    siap.value = true;
    await muatStatus();
  } catch (e) {
    galat.value = `API tidak bisa dihubungi: ${e.message}`;
  }
}

function mulaiPaper() {
  pesan.value = "";
  mulai("aksi/paper_mulai", { modal: Number(modal.value) }, muat);
}

function perbarui() {
  pesan.value = "";
  mulai("aksi/paper_harian", {}, muat);
}

async function reset() {
  try {
    const hasil = await kirim("aksi_paper_reset", {
      konfirmasi: konfirmasi.value,
    });
    tanyaReset.value = false;
    konfirmasi.value = "";
    kerja.value = null;
    pesan.value = `Paper trade direset. Data lama disimpan di arsip (sesi ${hasil.sesi}).`;
    await muat();
  } catch (e) {
    pesan.value = e.message;
  }
}

onMounted(async () => {
  await muat();
  await lanjutkan("paper_harian", muat);
});

const aksi = computed(() =>
  (r.value?.posisi || []).filter((p) => p.status !== "aktif"),
);
const aktif = computed(() =>
  (r.value?.posisi || []).filter((p) => p.status === "aktif"),
);
const dijual = computed(
  () => aksi.value.filter((p) => p.status === "jual_besok").length,
);
const LABEL_AKSI = {
  jual: "Jual",
  dividen: "Dividen",
  batal_ARA: "Batal · ARA terkunci",
  batal_kas: "Batal · kas kurang",
};

onMounted(() => {
  muatLangsung();
  detakLangsung = setInterval(() => statusApp?.value?.bursa_buka && muatLangsung(), 60000);
});

const stat = computed(() => {
  const x = r.value;
  if (!x?.mulai) return [];
  const terpakai = ((x.ekuitas - x.kas) / x.ekuitas) * 100;
  return [
    {
      label: "Ekuitas",
      nilai: `Rp${rupiah(Math.round(x.ekuitas))}`,
      ket: `modal Rp${rupiah(x.modal_awal)}`,
      info: "Kas + nilai posisi di harga penutupan terakhir yang sudah diproses.",
    },
    {
      label: "Return",
      nilai: persen(x.return_pct),
      nada: x.return_pct > 0 ? "naik" : x.return_pct < 0 ? "turun" : null,
      ket: `sejak ${tanggal(x.tgl_mulai)}`,
    },
    {
      label: "Posisi",
      nilai: `${aktif.value.length + dijual.value} / 10`,
      ket: `${persen(terpakai, 0, false)} modal terpakai`,
    },
    {
      label: "Trade selesai",
      nilai: String(x.trade_selesai),
      ket: x.trade_selesai
        ? `win rate ${persen(x.win_rate, 0, false)} · backtest ±34%`
        : "belum ada",
    },
    {
      label: "Menang / kalah",
      nilai: x.trade_selesai
        ? `${persen(x.rata_menang, 0)} / ${persen(x.rata_kalah, 0)}`
        : "–",
      ket: "backtest +35% / -10%",
      info: "Strategi ini wajar lebih sering kalah, asal rata-rata menang jauh lebih besar dari rata-rata kalah.",
    },
    {
      label: "Untung terealisasi",
      nilai: `Rp${rupiah(Math.round(x.untung_rp))}`,
      nada: x.untung_rp > 0 ? "naik" : x.untung_rp < 0 ? "turun" : null,
      ket: `dividen Rp${rupiah(Math.round(x.dividen_rp))}`,
    },
  ];
});
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <p class="m-0 min-w-0 flex-1 text-[13px] leading-relaxed text-ink-2">Aturan Follow Tren dijalankan ke depan dengan uang pura-pura, lalu dibandingkan dengan backtest.</p>
      <div v-if="r?.mulai" class="flex items-center gap-2">
        <button
          class="tombol"
          :disabled="sibuk"
          @click="tanyaReset = !tanyaReset"
        >
          <RotateCcw class="h-3.5 w-3.5" />Reset
        </button>
        <button class="tombol-utama" :disabled="sibuk" @click="perbarui">
          <RefreshCw
            class="h-3.5 w-3.5"
            :class="sibuk ? 'animate-spin' : ''"
          />{{ sibuk ? "Memperbarui..." : "Perbarui hari ini" }}
        </button>
      </div>
    </div>

    <div
      v-if="tanyaReset"
      class="panel flex flex-wrap items-center gap-3 px-5 py-3.5"
    >
      <span class="h-2.5 w-2.5 shrink-0 rounded-full bg-turun"></span
      ><span class="flex-1 text-ink-2"
        >Mulai ulang? Posisi dan riwayat dipindah ke arsip, tidak hilang. Ketik
        <b class="text-ink">RESET</b> untuk konfirmasi.</span
      >
      <input v-model="konfirmasi" placeholder="RESET" class="w-28" />
      <button
        class="tombol"
        @click="
          tanyaReset = false;
          konfirmasi = '';
        "
      >
        Batal
      </button>
      <button
        class="tombol !border-turun !text-turun"
        :disabled="konfirmasi !== 'RESET'"
        @click="reset"
      >
        Reset & arsipkan
      </button>
    </div>

    <div v-if="galat" class="panel px-5 py-3.5 text-turun">{{ galat }}</div>
    <PanelPekerjaan :kerja="kerja" :galat="galatKerja" />
    <div v-if="pesan" class="panel px-5 py-3.5 text-ink-2">{{ pesan }}</div>

    <template v-if="!siap && !galat">
      <Kerangka panel jenis="stat" :n="6" :judul="false" kolom="grid-cols-2 md:grid-cols-3 xl:grid-cols-6" />
      <Kerangka panel jenis="grafik" :tinggi="260" />
      <Kerangka panel jenis="tabel" :n="4" logo />
      <Kerangka panel jenis="grafik" :tinggi="300" />
    </template>

    <Panel
      v-if="siap && r && !r.mulai"
      judul="Mulai paper trade"
      ket="Mengunduh harga terbaru (±1 menit), lalu mengambil sinyal dari penutupan terakhir"
    >
      <div class="space-y-4">
        <ol class="m-0 list-decimal space-y-1 pl-5 text-ink-2">
          <li>Sinyal BELI dieksekusi di harga open hari bursa berikutnya.</li>
          <li>Tiap hari bursa setelah jam 17:00, tekan "Perbarui hari ini".</li>
          <li>Setelah 6-12 bulan, bandingkan hasilnya dengan backtest.</li>
        </ol>
        <div class="flex flex-wrap items-center gap-2">
          <span class="label">Modal paper (Rp)</span>
          <input
            v-model="modal"
            type="number"
            min="1000000"
            step="1000000"
            class="w-40 tabular-nums"
            :disabled="sibuk"
          />
          <span class="text-xs text-muted"
            >±Rp{{ rupiah(Math.round((Number(modal) || 0) / 10)) }} per
            posisi</span
          >
          <button
            class="tombol-utama"
            :disabled="sibuk || !(Number(modal) >= 1000000)"
            @click="mulaiPaper"
          >
            {{ sibuk ? "Berjalan..." : "Mulai paper trade" }}
          </button>
        </div>
        <p
          v-if="Number(modal) < 20000000"
          class="m-0 rounded-2xl bg-kuning-bg px-4 py-3 text-xs text-ink-2"
        >
          Modal kecil membuat banyak sinyal batal karena 1 lot melebihi jatah
          10% per posisi. Untuk hasil sebanding dengan backtest, pakai minimal
          Rp20-50 jt.
        </p>
      </div>
    </Panel>

    <template v-if="siap && r?.mulai">
      <Stats :items="stat" />

      <div v-if="adaLangsung" class="panel px-6 py-4">
        <div class="flex flex-wrap items-center gap-x-6 gap-y-3">
          <div class="flex items-center gap-2 text-[13px] font-medium"><Radio class="h-4 w-4 text-aksen" />Pantauan hari ini</div>
          <div v-if="ekuitasKini != null">
            <span class="text-xs text-muted">Ekuitas berjalan</span>
            <span class="ml-2 text-[17px] font-medium tabular-nums">Rp{{ rupiah(Math.round(ekuitasKini)) }}</span>
            <span class="ml-2 text-[13px] font-medium tabular-nums" :class="kelasPersen(ekuitasKini - r.ekuitas)">{{ persen((ekuitasKini / r.ekuitas - 1) * 100, 2) }}</span>
            <span class="ml-1 text-xs text-muted">hari ini</span>
          </div>
          <div class="text-xs text-muted">
            <span class="tabular-nums" :class="kelasPersen((ekuitasKini / r.modal_awal - 1) * 100)">{{ ekuitasKini != null ? persen((ekuitasKini / r.modal_awal - 1) * 100, 2) : "–" }}</span> sejak mulai
          </div>
          <span class="ml-auto text-xs text-muted">harga per menit Yahoo, pukul {{ langsung.jam }} · tertunda ±10 menit · resmi masuk paper setelah 17:00</span>
        </div>
        <p v-if="bawahStop.length" class="m-0 mt-3 flex items-start gap-2 rounded-2xl bg-turun-bg px-4 py-2.5 text-xs text-turun">
          <TriangleAlert class="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>{{ bawahStop.map((p) => p.ticker).join(", ") }} sedang di bawah stop. Kalau harga penutupan tetap di bawah stop, saham dijual di open besok.</span>
        </p>
      </div>

      <ZonaPaper :muat-ulang="versiMuat" />

      <Panel
        :judul="infoAksi(r.tgl_terakhir).judul"
        :ket="infoAksi(r.tgl_terakhir).ket"
        rapat
        info="Tidak perlu beli manual: sinyal dibeli otomatis di harga open dengan 10% ekuitas (aturan Follow Tren dikunci). Transaksinya baru muncul setelah Perbarui lewat jam 17:00, karena data hari itu baru final."
      >
        <p v-if="!aksi.length" class="m-0 px-6 pt-1 pb-4 text-muted">
          Tidak ada aksi. Pegang posisi yang ada.
        </p>
        <div v-else class="overflow-x-auto">
          <table class="tabel min-w-[640px]">
            <thead>
              <tr>
                <th class="w-20">Aksi</th>
                <th>Saham</th>
                <th>Alasan</th>
                <th class="!text-right">Lot</th>
                <th class="!text-right">Stop</th>
                <th class="!text-right">Hasil saat ini</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in aksi" :key="p.ticker">
                <td>
                  <span
                    class="chip"
                    :class="
                      p.status === 'jual_besok'
                        ? 'bg-turun-bg text-turun'
                        : 'bg-aksen-lembut text-aksen'
                    "
                    >{{ p.status === "jual_besok" ? "JUAL" : "BELI" }}</span
                  >
                </td>
                <td><KodeSaham :kode="p.ticker" /></td>
                <td class="text-ink-2">
                  {{
                    p.status === "jual_besok"
                      ? `close ${rupiah(p.close)} di bawah stop`
                      : `tembus tertinggi 52 minggu (close ${rupiah(p.close_sinyal)})`
                  }}
                </td>
                <td class="text-right">
                  {{ p.status === "jual_besok" ? p.lot : "–" }}
                </td>
                <td class="text-right">
                  <TeksWarna
                    :teks="
                      p.status === 'jual_besok'
                        ? rupiah(Math.round(p.stop))
                        : `${rupiah(Math.round(p.stop_awal_perkiraan))} (${persen(p.stop_awal_pct, 1)})`
                    "
                  />
                </td>
                <td
                  class="text-right font-medium"
                  :class="
                    p.status === 'jual_besok'
                      ? p.untung_pct >= 0
                        ? 'text-naik'
                        : 'text-turun'
                      : 'text-muted'
                  "
                >
                  {{ p.status === "jual_besok" ? persen(p.untung_pct) : "–" }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel
        judul="Posisi aktif"
        ket="Terkunci = hasil kalau kena stop sekarang · tidak ada target jual tetap"
        rapat
        info="Stop = close tertinggi sejak beli − 3×ATR. Stop ikut naik dan tidak pernah turun. Kalau close di bawah stop, jual di open besok."
      >
        <p v-if="!aktif.length" class="m-0 px-6 pt-1 pb-4 text-muted">
          Belum ada posisi aktif.
        </p>
        <div v-else class="overflow-x-auto">
          <table class="tabel min-w-[820px]">
            <thead>
              <tr>
                <th>Saham</th>
                <th>Tanggal masuk</th>
                <th class="!text-right">Harga masuk</th>
                <th class="!text-right">Close</th>
                <th v-if="adaLangsung" class="!text-right">Sekarang</th>
                <th class="!text-right">Untung</th>
                <th class="!text-right">Stop</th>
                <th class="!text-right">Terkunci</th>
                <th class="!text-right">Jarak ke stop</th>
                <th class="!text-right">Hari</th>
                <th class="!text-right">Nilai</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in aktif" :key="p.ticker">
                <td><KodeSaham :kode="p.ticker" /></td>
                <td class="text-ink-2">{{ tanggal(p.tgl_masuk) }}</td>
                <td class="text-right">{{ rupiah(p.harga_masuk) }}</td>
                <td class="text-right">{{ rupiah(p.close) }}</td>
                <td v-if="adaLangsung" class="text-right tabular-nums">
                  <template v-if="kini(p.ticker)">
                    <span :class="kini(p.ticker).di_bawah_stop ? 'font-medium text-turun' : ''">{{ rupiah(kini(p.ticker).harga) }}</span>
                    <span class="ml-1 text-xs" :class="kelasPersen(kini(p.ticker).ret)">{{ persen(kini(p.ticker).ret, 1) }}</span>
                  </template>
                  <span v-else class="text-muted">–</span>
                </td>
                <td
                  class="text-right font-medium"
                  :class="(kini(p.ticker)?.untung_pct ?? p.untung_pct) >= 0 ? 'text-naik' : 'text-turun'"
                >
                  {{ persen(kini(p.ticker)?.untung_pct ?? p.untung_pct) }}
                </td>
                <td class="text-right">{{ rupiah(Math.round(p.stop)) }}</td>
                <td
                  class="text-right"
                  :class="kelasPersen((p.stop / p.harga_masuk - 1) * 100)"
                >
                  <Lock
                    v-if="p.stop >= p.harga_masuk"
                    class="mr-1 inline h-3 w-3 align-[-1px]"
                  />{{ persen((p.stop / p.harga_masuk - 1) * 100, 1) }}
                </td>
                <td
                  class="text-right"
                  :class="
                    p.jarak_stop_pct < 3
                      ? 'font-medium text-turun'
                      : 'text-ink-2'
                  "
                >
                  {{ persen(kini(p.ticker)?.jarak_stop_pct ?? p.jarak_stop_pct, 1, false) }}
                </td>
                <td class="text-right text-ink-2">{{ p.hari }}</td>
                <td class="text-right">{{ rupiah(Math.round(p.nilai_rp)) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Panel>

      <KurvaPaper
        v-if="ekuitas.length > 1"
        :ekuitas="ekuitas"
        :modal="r.modal_awal"
      />

      <div class="grid gap-4 lg:grid-cols-2">
        <Panel
          judul="Riwayat transaksi"
          ket="Terbaru di atas · hasil jual sudah dipotong biaya + dividen"
          rapat
        >
          <p v-if="!transaksi.length" class="m-0 px-6 pt-1 pb-4 text-muted">
            Belum ada transaksi.
          </p>
          <div v-else class="max-h-[360px] overflow-auto">
            <table class="tabel">
              <tbody>
                <tr v-for="(t, i) in transaksi" :key="i">
                  <td class="text-muted">{{ tanggal(t.tgl) }}</td>
                  <td><KodeSaham :kode="t.ticker" /></td>
                  <td class="text-ink-2">{{ LABEL_AKSI[t.aksi] || t.aksi }}</td>
                  <td
                    class="text-right"
                    :class="
                      t.aksi === 'jual'
                        ? t.net_pct >= 0
                          ? 'text-naik'
                          : 'text-turun'
                        : 'text-ink-2'
                    "
                  >
                    <template v-if="t.aksi === 'jual'"
                      ><b class="font-medium" :class="kelasPersen(t.net_pct)">{{
                        persen(t.net_pct)
                      }}</b>
                      <span class="text-muted"
                        >· {{ t.hari }} hari</span
                      ></template
                    >
                    <template v-else-if="t.aksi === 'dividen'"
                      >Rp{{ rupiah(t.untung_rp) }}</template
                    >
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </Panel>
        <Panel
          judul="Sinyal harian"
          ket="Tembus harga tertinggi 52 minggu · tebal = dipilih"
          rapat
        >
          <div class="max-h-[360px] overflow-auto">
            <table class="tabel">
              <tbody>
                <tr v-for="s in sinyal" :key="s.tgl">
                  <td class="w-28 text-muted">{{ tanggal(s.tgl) }}</td>
                  <td class="!whitespace-normal">
                    <span v-if="!s.kandidat.length" class="text-muted"
                      >tidak ada sinyal</span
                    >
                    <span
                      v-for="k in s.kandidat"
                      :key="k"
                      class="mr-2"
                      :class="
                        s.terpilih.includes(k)
                          ? 'font-medium text-ink'
                          : 'text-muted'
                      "
                      >{{ k }}</span
                    >
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </Panel>
      </div>
    </template>

    <Panel v-if="arsip.length" judul="Arsip sesi sebelumnya" rapat>
      <div class="overflow-x-auto">
        <table class="tabel">
          <thead>
            <tr>
              <th>Sesi</th>
              <th>Periode</th>
              <th class="!text-right">Hari</th>
              <th class="!text-right">Modal</th>
              <th class="!text-right">Ekuitas akhir</th>
              <th class="!text-right">Trade</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="a in arsip" :key="a.sesi">
              <td class="text-muted">{{ a.sesi }}</td>
              <td class="text-ink-2">
                {{ tanggal(a.mulai) }} – {{ tanggal(a.akhir) }}
              </td>
              <td class="text-right">{{ a.hari }}</td>
              <td class="text-right">{{ rupiah(a.modal_awal) }}</td>
              <td class="text-right">{{ rupiah(a.ekuitas_akhir) }}</td>
              <td class="text-right">{{ a.trade }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </Panel>
  </div>
</template>

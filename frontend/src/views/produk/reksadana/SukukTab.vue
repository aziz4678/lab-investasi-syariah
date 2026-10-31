<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { ambil } from "@/api/client";
import { persen } from "@/utils/format";
import Panel from "@/components/common/Panel.vue";
import Segmen from "@/components/common/Segmen.vue";
import Kerangka from "@/components/common/Kerangka.vue";
import Logo from "@/components/common/Logo.vue";
import SukukDetail from "@/components/produk/SukukDetail.vue";

const KET_SUKUK = {
  SR: "Sukuk Ritel: sukuk negara untuk perorangan, dijual pada masa penawaran lewat bank/aplikasi mitra (termasuk Bibit, Ajaib, Bareksa). Imbalan tetap tiap bulan, dijamin negara. Bisa dijual di pasar sekunder setelah masa minimum kepemilikan.",
  PBS: "Project Based Sukuk: sukuk negara yang diperdagangkan di pasar sekunder lewat sekuritas atau bank. Harganya naik-turun mengikuti suku bunga.",
  SPNS: "Surat Perbendaharaan Negara Syariah: sukuk negara jangka pendek (maksimal 1 tahun).",
  Korporasi: "Sukuk yang diterbitkan perusahaan. Imbal hasil lebih tinggi, tapi ada risiko perusahaan gagal bayar; perhatikan peringkat (rating) penerbit.",
  "Negara lain": "Seri sukuk negara lainnya (misalnya seri valuta asing atau pembiayaan proyek).",
};
const JENIS_SUKUK = [["SR", "Sukuk ritel (SR)"], ["PBS", "Sukuk negara (PBS)"], ["SPNS", "SPN syariah"], ["Korporasi", "Korporasi"], ["Negara lain", "Lainnya"]];
const NEGARA = ["SR", "PBS", "SPNS", "Negara lain"];

const sukukData = ref(null);
const jenisSukuk = ref("SR");
const pilihSukuk = ref(location.hash.startsWith("#reksadana/sukuk/") ? decodeURIComponent(location.hash.split("/")[2]) : null);
onMounted(async () => {
  sukukData.value = await ambil("rd/sukuk").catch(() => ({ data: [], ringkas: [] }));
});
const sukukDipilih = computed(() => (sukukData.value?.data || []).find((x) => x.kode === pilihSukuk.value));
watch(pilihSukuk, (k) => {
  history.replaceState(null, "", k ? `#reksadana/sukuk/${encodeURIComponent(k)}` : "#reksadana/sukuk");
  window.scrollTo({ top: 0 });
});
watch(sukukDipilih, (x) => { if (x && x.jenis !== jenisSukuk.value) jenisSukuk.value = x.jenis; });
const sukukTampil = computed(() => (sukukData.value?.data || []).filter((x) => x.jenis === jenisSukuk.value).sort((a, b) => (a.jatuh_tempo || "").localeCompare(b.jatuh_tempo || "")));
const ringkasSukuk = computed(() => Object.fromEntries((sukukData.value?.ringkas || []).map((x) => [x.jenis, x])));
const sukukAktif = computed(() => ringkasSukuk.value[jenisSukuk.value]);
const tglPendek = (t) => (t ? new Date(t).toLocaleDateString("id-ID", { month: "short", year: "numeric" }) : "–");
</script>

<template>
  <SukukDetail v-if="sukukDipilih" :x="sukukDipilih" :ket="KET_SUKUK[sukukDipilih.jenis]" @kembali="pilihSukuk = null" />
  <div v-else class="space-y-5">
    <div class="panel px-6 py-5">
      <div class="mb-1 text-[15px] font-medium">Sukuk: "obligasi syariah" yang bisa dibeli langsung</div>
      <p class="m-0 mb-4 text-[13px] text-ink-2">Beda dengan reksa dana, sukuk dibeli langsung tanpa manajer investasi. Sukuk negara dijamin pemerintah; kamu menerima imbalan (kupon) rutin sampai jatuh tempo.</p>
      <Segmen v-model="jenisSukuk" :pilihan="JENIS_SUKUK" />
      <div class="mt-4 grid gap-4 rounded-2xl bg-surface-2 px-5 py-4 md:grid-cols-[1.4fr_1fr]">
        <p class="m-0 text-[13px] leading-relaxed text-ink-2">{{ KET_SUKUK[jenisSukuk] }}</p>
        <div class="grid grid-cols-3 gap-3 text-center">
          <div><div class="text-xs text-muted">Seri aktif</div><div class="mt-0.5 text-[17px] font-medium">{{ sukukAktif?.jumlah ?? 0 }}</div></div>
          <div><div class="text-xs text-muted">Kupon per tahun</div><div class="mt-0.5 text-[17px] font-medium">{{ sukukAktif?.kupon_median != null ? persen(sukukAktif.kupon_median, 2, false) : "–" }}</div><div class="text-[11px] text-muted">nilai tengah</div></div>
          <div><div class="text-xs text-muted" title="Perkiraan hasil per tahun kalau dibeli di harga sekarang dan dipegang sampai jatuh tempo (YTM)">Hasil kalau ditahan</div><div class="mt-0.5 text-[17px] font-medium">{{ sukukAktif?.ytm_median != null ? persen(sukukAktif.ytm_median, 2, false) : "–" }}</div><div class="text-[11px] text-muted">nilai tengah</div></div>
        </div>
      </div>
      <p class="m-0 mt-3 text-xs text-muted">Sukuk Tabungan (ST) tidak diperdagangkan di pasar sekunder sehingga tidak tercantum di daftar ini. Kupon sukuk negara kena pajak final 10%.</p>
    </div>
    <Panel :judul="JENIS_SUKUK.find((j) => j[0] === jenisSukuk)?.[1]" :ket="`${sukukTampil.length} seri · urut dari jatuh tempo terdekat · klik untuk detail dan grafik harga`" rapat>
      <Kerangka v-if="!sukukData" jenis="tabel" :n="8" logo />
      <div v-else class="overflow-x-auto">
        <table class="tabel min-w-[820px]">
          <thead><tr><th>Seri</th><th class="!text-right">Kupon/th</th><th>Jatuh tempo</th><th class="!text-right" title="Harga dalam persen dari nilai pokok; 100 = harga awal">Harga</th><th class="!text-right" title="Perkiraan hasil per tahun kalau dibeli di harga terakhir dan dipegang sampai jatuh tempo (YTM)">Hasil kalau ditahan</th><th>Penerbit / peringkat</th></tr></thead>
          <tbody>
            <tr v-for="x in sukukTampil" :key="x.kode" class="cursor-pointer hover:bg-surface-2/50" @click="pilihSukuk = x.kode">
              <td class="!h-auto max-w-[340px] py-2.5"><div class="flex items-center gap-3"><Logo :jenis="NEGARA.includes(x.jenis) ? 'negara' : 'emiten'" :kunci="NEGARA.includes(x.jenis) ? 'kemenkeu' : x.penerbit" :teks="x.penerbit" :ukuran="30" /><div class="min-w-0"><div class="font-medium">{{ x.kode }}</div><div class="truncate text-[11px] text-muted" :title="x.nama">{{ x.nama }}</div></div></div></td>
              <td class="text-right">{{ x.kupon == null ? "–" : persen(x.kupon * 100, 2, false) }}</td>
              <td class="tabular-nums">{{ tglPendek(x.jatuh_tempo) }} <span class="text-xs text-muted">· {{ x.sisa_tahun == null ? "–" : `sisa ${x.sisa_tahun.toLocaleString("id-ID", { maximumFractionDigits: 1 })} tahun` }}</span></td>
              <td class="text-right">{{ x.harga == null ? "–" : x.harga.toLocaleString("id-ID", { maximumFractionDigits: 2 }) }}</td>
              <td class="text-right font-medium">{{ x.ytm == null ? "–" : persen(x.ytm * 100, 2, false) }}</td>
              <td class="text-xs text-ink-2">{{ x.penerbit }}<template v-if="x.rating"> · {{ x.rating }}</template><template v-else-if="['SR', 'PBS', 'SPNS'].includes(x.jenis)"> · dijamin negara</template></td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="m-0 px-6 py-3 text-xs text-muted">Harga 100 = harga awal. Harga di bawah 100 (diskon) membuat hasil kalau ditahan lebih tinggi dari kupon.</p>
    </Panel>
  </div>
</template>

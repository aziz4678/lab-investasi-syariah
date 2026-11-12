<script setup>
import { ref, computed, inject, onMounted } from "vue";
import { TriangleAlert, ShieldAlert, ArrowRight, Info as IkonInfo } from "lucide-vue-next";
import { ambil } from "@/api/client";
import { tanggal } from "@/utils/format";

const props = defineProps({ bagian: { type: String, default: "h11a" } });
const pindahTab = inject("pindahTab");
const k = ref(null);

onMounted(async () => {
  k.value = await ambil("kualitas/paper").catch(() => null);
});

const sentuh = computed(() => k.value?.sentuh || []);
const sumber = computed(() => k.value?.sumber?.[props.bagian] || null);
const cadangan = computed(() => {
  const s = sumber.value;
  if (!s) return null;
  const y = s.sumber?.yahoo || 0;
  return y > 0 ? { tgl: s.tgl, jumlah: y } : null;
});
const idxGagal = computed(() => k.value?.jadwal && k.value.jadwal.idx_lengkap === false);
const umum = computed(() => k.value?.status === "ADA TEMUAN" && !sentuh.value.length);

function label(x) {
  const t = x.tgl ? ` ${x.tgl}` : "";
  return `${x.kode} (${x.peran}, ${x.kategori}${t})`;
}
</script>

<template>
  <div v-if="k && (sentuh.length || cadangan || idxGagal || umum)" class="space-y-2">
    <div v-if="sentuh.length" class="flex items-start gap-3 rounded-2xl border border-turun/40 bg-turun-bg px-4 py-3 text-[13px] text-turun">
      <ShieldAlert class="mt-0.5 h-4.5 w-4.5 shrink-0" />
      <div class="min-w-0 flex-1 leading-relaxed">
        <b class="font-medium">Kualitas data: ada temuan di saham yang dipegang atau kandidat paper.</b>
        Paper tetap jalan sesuai aturan, tapi harga saham ini perlu dicek: {{ sentuh.map(label).join(", ") }}.
      </div>
      <button class="tombol shrink-0" @click="pindahTab('kualitas')">Lihat <ArrowRight class="h-3.5 w-3.5" /></button>
    </div>
    <div v-if="cadangan || idxGagal" class="flex items-start gap-3 rounded-2xl bg-kuning-bg px-4 py-3 text-[13px] text-kuning">
      <TriangleAlert class="mt-0.5 h-4.5 w-4.5 shrink-0" />
      <div class="min-w-0 flex-1 leading-relaxed">
        <template v-if="cadangan">Data resmi IDX belum lengkap untuk {{ tanggal(cadangan.tgl) }}: {{ cadangan.jumlah }} saham memakai cadangan Yahoo.</template>
        <template v-else>Pengambilan data IDX di jadwal terakhir gagal; paper memakai cadangan Yahoo untuk hari yang belum ada.</template>
        Cek silang IDX akan menandai kalau ada selisih.
      </div>
    </div>
    <div v-if="umum" class="flex items-center gap-3 rounded-2xl px-4 py-2.5 text-xs text-ink-2" :class="k.jumlah_temuan > 0 ? 'bg-kuning-bg' : 'bg-surface-2'">
      <TriangleAlert v-if="k.jumlah_temuan > 0" class="h-4 w-4 shrink-0 text-kuning" />
      <IkonInfo v-else class="h-4 w-4 shrink-0 text-aksen" />
      <span class="min-w-0 flex-1">Cek kualitas data: {{ k.jumlah_temuan }} temuan baru<span v-if="k.jumlah_tahan">, {{ k.jumlah_tahan }} koreksi ditahan</span> (tidak menyentuh paper).</span>
      <button class="tombol shrink-0" @click="pindahTab('kualitas')">Lihat</button>
    </div>
  </div>
</template>

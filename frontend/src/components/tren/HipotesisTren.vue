<script setup>
import { inject, computed } from "vue";
import { ArrowRight } from "lucide-vue-next";
import Panel from "@/components/common/Panel.vue";

const props = defineProps({ h: Object, perjalanan: Array });
const pindahTab = inject("pindahTab");
const KOLOM = { 3: "md:grid-cols-3", 4: "md:grid-cols-4", 5: "md:grid-cols-5", 6: "md:grid-cols-6", 7: "md:grid-cols-7", 8: "md:grid-cols-8" };
const potongan = computed(() => (props.h?.kalimat || "").split("**").map((t, i) => ({ t, tebal: i % 2 === 1 })));
</script>

<template>
  <Panel :judul="h?.judul" :ket="h?.ket">
    <template #aksi><button class="tombol" @click="pindahTab('hipotesis', h?.kode)">Kriteria lengkap <ArrowRight class="h-3.5 w-3.5" /></button></template>
    <blockquote class="m-0 rounded-2xl border-l-4 border-aksen bg-surface-2 px-5 py-4 text-[14px] leading-relaxed">
      <template v-for="(p, i) in potongan" :key="i"><b v-if="p.tebal" class="font-medium">{{ p.t }}</b><template v-else>{{ p.t }}</template></template>
    </blockquote>
    <div class="mt-5 label">Perjalanan uji</div>
    <ol class="m-0 mt-3 grid list-none gap-0 p-0" :class="KOLOM[perjalanan?.length] || 'md:grid-cols-6'">
      <li v-for="(j, i) in perjalanan" :key="j.judul" class="relative flex gap-3 pb-4 md:block md:pr-3 md:pb-0">
        <div class="flex flex-col items-center md:flex-row">
          <span class="z-10 grid h-6 w-6 shrink-0 place-items-center rounded-full text-[11px] font-medium"
            :class="j.status === 'selesai' ? 'bg-aksen text-aksen-teks' : j.status === 'jalan' ? 'bg-aksen-lembut text-aksen ring-2 ring-aksen' : 'bg-surface-2 text-muted'">{{ i + 1 }}</span>
          <span v-if="i < perjalanan.length - 1" class="w-0.5 flex-1 md:h-0.5 md:w-auto" :class="j.status === 'selesai' ? 'bg-aksen' : 'bg-garis'" />
        </div>
        <div class="min-w-0 md:mt-2">
          <div class="text-[11px] text-muted">{{ j.waktu }}<span v-if="j.status === 'jalan'" class="ml-1.5 chip bg-aksen-lembut text-aksen">sekarang</span></div>
          <div class="text-[13px] font-medium">{{ j.judul }}</div>
          <div class="mt-0.5 text-xs leading-relaxed text-ink-2">{{ j.isi }}</div>
        </div>
      </li>
    </ol>
  </Panel>
</template>

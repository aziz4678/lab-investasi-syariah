<script setup>
import { computed } from "vue";
import { Award, TriangleAlert } from "lucide-vue-next";

const props = defineProps({ lencana: { type: Array, default: () => [] }, peringatan: { type: Array, default: () => [] }, kecil: Boolean, tanpaPeringatan: Boolean, maks: { type: Number, default: 0 } });
const semua = computed(() => {
  const l = props.lencana.map((x) => ({ ...x, jenis: "lencana" }));
  const p = props.tanpaPeringatan ? [] : props.peringatan.map((x) => ({ ...x, jenis: "peringatan" }));
  return [...l, ...p];
});
const tampil = computed(() => (props.maks ? semua.value.slice(0, props.maks) : semua.value));
const sisa = computed(() => semua.value.length - tampil.value.length);
</script>

<template>
  <div v-if="semua.length" class="flex flex-wrap gap-1">
    <span v-for="x in tampil" :key="x.jenis + x.kode" class="chip !gap-1" :class="[x.jenis === 'lencana' ? 'bg-naik-bg text-naik' : 'bg-kuning-bg text-kuning', kecil ? '!h-5 !px-2 !text-[10.5px]' : '']" :title="x.ket">
      <Award v-if="x.jenis === 'lencana'" :class="kecil ? 'h-3 w-3' : 'h-3.5 w-3.5'" />
      <TriangleAlert v-else :class="kecil ? 'h-3 w-3' : 'h-3.5 w-3.5'" />{{ x.label }}
    </span>
    <span v-if="sisa > 0" class="chip bg-surface-2 text-muted" :class="kecil ? '!h-5 !px-2 !text-[10.5px]' : ''" :title="semua.slice(tampil.length).map((x) => x.label).join(', ')">+{{ sisa }}</span>
  </div>
</template>

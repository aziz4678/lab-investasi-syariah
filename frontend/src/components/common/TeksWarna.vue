<script setup>
import { computed } from "vue";
const props = defineProps({ teks: [String, Number] });
const POLA = /([+-]\d[\d.,]*%)/;
const bagian = computed(() => String(props.teks ?? "").split(POLA).filter((x) => x !== "").map((x) => ({
  x, k: POLA.test(x) ? (x.startsWith("+") ? "text-naik" : /[1-9]/.test(x) ? "text-turun" : "") : "",
})));
</script>

<template><span><span v-for="(b, i) in bagian" :key="i" :class="b.k">{{ b.x }}</span></span></template>

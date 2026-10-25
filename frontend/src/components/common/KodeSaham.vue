<script setup>
import { inject } from "vue";
import Logo from "@/components/common/Logo.vue";
defineProps({ kode: String, logo: { type: Boolean, default: true } });
const buka = inject("bukaEmiten", null);
</script>

<template>
  <span class="inline-flex items-center gap-2 align-middle">
    <Logo v-if="logo" jenis="emiten" :kunci="kode" :teks="kode" :ukuran="22" />
    <button v-if="buka" type="button" class="font-medium text-ink underline decoration-garis decoration-2 underline-offset-4 transition hover:text-aksen hover:decoration-aksen"
      :title="`Lihat profil ${kode}`" @click="buka(kode)">{{ kode }}</button>
    <span v-else class="font-medium">{{ kode }}</span>
  </span>
</template>

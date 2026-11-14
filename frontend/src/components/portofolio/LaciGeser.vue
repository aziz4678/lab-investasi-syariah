<script setup>
import { watch, onBeforeUnmount } from "vue";
import { X } from "lucide-vue-next";

const props = defineProps({ modelValue: Boolean, judul: { type: String, default: "" } });
const emit = defineEmits(["update:modelValue"]);

const tutup = () => emit("update:modelValue", false);
const saatTombol = (e) => {
  if (e.key === "Escape") tutup();
};
watch(() => props.modelValue, (buka) => {
  if (buka) window.addEventListener("keydown", saatTombol);
  else window.removeEventListener("keydown", saatTombol);
});
onBeforeUnmount(() => window.removeEventListener("keydown", saatTombol));
</script>

<template>
  <Teleport to="body">
    <div v-if="modelValue" class="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" :aria-label="judul">
      <div class="absolute inset-0 bg-black/40" @click="tutup"></div>
      <div class="relative flex h-full w-full max-w-lg flex-col bg-surface shadow-2xl">
        <div class="flex items-center justify-between gap-3 border-b border-garis px-5 py-4">
          <div class="text-[15px] font-semibold">{{ judul }}</div>
          <button type="button" class="tombol !h-8 !w-8 !p-0" aria-label="Tutup" @click="tutup"><X class="h-4 w-4" /></button>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto px-5 py-5"><slot /></div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue";

const props = defineProps({ item: { type: Array, required: true }, tautan: { type: String, default: "" } });
const emit = defineEmits(["tautan"]);
const aktif = ref(props.item[0]?.[0] ?? "");
let pengamat = null;

const lompat = (id) => {
  aktif.value = id;
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
};

onMounted(() => {
  try {
    pengamat = new IntersectionObserver(
      (daftar) => {
        const terlihat = daftar.filter((x) => x.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
        if (terlihat) aktif.value = terlihat.target.id;
      },
      { rootMargin: "-20% 0px -65% 0px" },
    );
    props.item.forEach(([id]) => {
      const el = document.getElementById(id);
      if (el) pengamat.observe(el);
    });
  } catch {
    pengamat = null;
  }
});
onBeforeUnmount(() => pengamat?.disconnect());
</script>

<template>
  <nav class="sticky top-0 z-20 -mx-1 overflow-x-auto rounded-full bg-surface/90 px-1 py-1.5 backdrop-blur" aria-label="Bagian halaman">
    <div class="inline-flex min-w-full gap-1 rounded-full bg-surface-2 p-1">
      <button v-for="[id, label] in item" :key="id" type="button" class="h-8 shrink-0 rounded-full px-4 text-[13px] font-medium whitespace-nowrap transition"
        :class="aktif === id ? 'bg-aksen text-aksen-teks shadow-sm' : 'text-muted hover:text-ink'" @click="lompat(id)">{{ label }}</button>
      <button v-if="tautan" type="button" class="ml-auto h-8 shrink-0 rounded-full px-4 text-[13px] font-medium whitespace-nowrap text-aksen transition hover:bg-aksen-lembut" @click="emit('tautan')">{{ tautan }}</button>
    </div>
  </nav>
</template>

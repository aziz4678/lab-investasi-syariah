import { ref, computed, onBeforeUnmount } from "vue";
import { ambil, kirim } from "./util.js";

export function pakaiPekerjaan() {
  const kerja = ref(null);
  const galat = ref("");
  let timer = null;
  let aktif = true;

  async function pantau(id, setelah) {
    clearTimeout(timer);
    try {
      kerja.value = await ambil(`pekerjaan/${id}`);
    } catch (e) {
      galat.value = e.message;
      return;
    }
    if (kerja.value.status === "berjalan") {
      if (aktif) timer = setTimeout(() => pantau(id, setelah), 1500);
    } else if (kerja.value.status === "selesai" && setelah) {
      await setelah();
    }
  }

  async function mulai(jalur, body, setelah) {
    galat.value = "";
    try {
      const { id } = await kirim(jalur, body);
      await pantau(id, setelah);
    } catch (e) {
      galat.value = e.message;
    }
  }

  async function lanjutkan(jenis, setelah) {
    const daftar = await ambil("pekerjaan?batas=20").catch(() => []);
    const jalan = daftar.find((p) => p.jenis === jenis && p.status === "berjalan");
    if (jalan) await pantau(jalan._id, setelah);
  }

  onBeforeUnmount(() => {
    aktif = false;
    clearTimeout(timer);
  });

  const sibuk = computed(() => kerja.value?.status === "berjalan");
  return { kerja, galat, sibuk, mulai, lanjutkan };
}

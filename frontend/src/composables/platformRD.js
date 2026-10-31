import { ref } from "vue";
import { ambil } from "@/api/client";

const info = ref(null);
let janji = null;

export function pakaiPlatform() {
  if (!janji) {
    janji = ambil("rd/platform")
      .then((x) => (info.value = x))
      .catch(() => {
        info.value = { platform: [], pto: [] };
        janji = null;
      });
  }
  const nama = (k) => info.value?.platform?.find((p) => p.kode === k)?.nama || k;
  const izin = (k) => info.value?.platform?.find((p) => p.kode === k)?.izin_ojk?.[0] || null;
  return { info, nama, izin };
}

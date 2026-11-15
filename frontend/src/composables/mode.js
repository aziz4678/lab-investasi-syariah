import { ref } from "vue";

export const pemilik = ref(false);
export const modeSiap = ref(false);

let janji = null;
export function muatMode() {
  if (!janji) {
    janji = (async () => {
      try {
        const r = await fetch("/api/mode", { cache: "no-store" });
        pemilik.value = r.ok ? !!(await r.json()).pemilik : false;
      } catch {
        pemilik.value = false;
      }
      modeSiap.value = true;
    })();
  }
  return janji;
}

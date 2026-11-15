import { ref } from "vue";

export const pemilik = ref(false);
export const modeSiap = ref(false);

let sudah = false;
export async function muatMode() {
  if (sudah) return;
  sudah = true;
  try {
    const r = await fetch("/api/mode", { cache: "no-store" });
    pemilik.value = r.ok ? !!(await r.json()).pemilik : false;
  } catch {
    pemilik.value = false;
  }
  modeSiap.value = true;
}

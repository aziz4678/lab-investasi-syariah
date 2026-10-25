import { ref } from "vue";

const versiTema = ref(0);
export const modeTema = ref("sistem");
const mq = window.matchMedia("(prefers-color-scheme: dark)");

function terapkan() {
  const el = document.documentElement;
  if (modeTema.value === "sistem") delete el.dataset.theme;
  else el.dataset.theme = modeTema.value === "gelap" ? "dark" : "light";
  versiTema.value += 1;
}

export function setTema(mode) {
  modeTema.value = mode;
  try {
    localStorage.setItem("tema", mode);
  } catch {
    modeTema.value = mode;
  }
  terapkan();
}

export function temaGelap() {
  versiTema.value;
  return modeTema.value === "gelap" || (modeTema.value === "sistem" && mq.matches);
}

try {
  modeTema.value = localStorage.getItem("tema") || "sistem";
} catch {
  modeTema.value = "sistem";
}
terapkan();
mq.addEventListener("change", () => modeTema.value === "sistem" && terapkan());

export function pakaiTema() {
  return versiTema;
}

export async function ambil(jalur) {
  const r = await fetch(`/api/${jalur}`);
  if (!r.ok) throw new Error(`${jalur}: ${r.status}`);
  return r.json();
}

export async function kirim(jalur, body = {}) {
  const r = await fetch(`/api/${jalur}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || `${jalur}: ${r.status}`);
  return j;
}

export const JAM_CEK = 17.75;
export const MAKS_TELAT = 1;

function kunci(d) {
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

export function hariBursaTelat(waktuCek, sekarang, libur = []) {
  if (!waktuCek) return Infinity;
  const set = new Set(libur);
  const d = new Date(waktuCek);
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() + 1);
  const akhir = new Date(sekarang);
  akhir.setHours(0, 0, 0, 0);
  const sudahJam = sekarang.getHours() + sekarang.getMinutes() / 60 >= JAM_CEK;
  let n = 0;
  for (; d <= akhir; d.setDate(d.getDate() + 1)) {
    const hari = d.getDay();
    if (hari === 0 || hari === 6 || set.has(kunci(d))) continue;
    if (d.getTime() === akhir.getTime() && !sudahJam) continue;
    n++;
  }
  return n;
}

export function statusHeartbeat(waktuCek, sekarang, libur = []) {
  const telat = hariBursaTelat(waktuCek, sekarang, libur);
  const sejak = waktuCek ? kunci(new Date(waktuCek)) : null;
  const mati = telat > MAKS_TELAT;
  const pesan = !waktuCek
    ? "Pemeriksa belum pernah jalan — jadwal mungkin mati."
    : `Pemeriksa tidak jalan sejak ${sejak} — jadwal mungkin mati.`;
  return { mati, telat, sejak, pesan };
}

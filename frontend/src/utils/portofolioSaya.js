const BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
export const MAKS_BULAN_DEFAULT = 6;

export const labelBulan = (kunci) => {
  const [t, b] = String(kunci).split("-").map(Number);
  return `${BULAN[b - 1]} ${t}`;
};

export const kelompokPerBulan = (transaksi) => {
  const peta = new Map();
  for (const t of transaksi ?? []) {
    const kunci = String(t.tanggal).slice(0, 7);
    if (!peta.has(kunci)) peta.set(kunci, { kunci, label: labelBulan(kunci), jumlah: 0, total: 0, baris: [] });
    const g = peta.get(kunci);
    g.jumlah += 1;
    g.total += (t.jenis === "jual" ? -1 : 1) * (t.nominal ?? 0);
    g.baris.push(t);
  }
  const urut = [...peta.values()].sort((a, b) => (a.kunci < b.kunci ? 1 : -1));
  for (const g of urut) g.baris.sort((a, b) => (a.tanggal === b.tanggal ? String(b._id).localeCompare(String(a._id)) : a.tanggal < b.tanggal ? 1 : -1));
  return urut;
};

export const batasiBulan = (kelompok, semua = false, maks = MAKS_BULAN_DEFAULT) => (semua ? kelompok : kelompok.slice(0, maks));

const persenTeks = (v) => Math.abs(v * 100).toLocaleString("id-ID", { maximumFractionDigits: 1 });

export const kalimatKonteks = (ringkasan) => {
  if (!ringkasan || ringkasan.untung == null || ringkasan.untung_persen == null || ringkasan.untung === 0) return null;
  if (ringkasan.untung > 0) return { jenis: "naik", teks: `Naik ${persenTeks(ringkasan.untung_persen)}% — tetap ikuti rencana, jangan menambah porsi di luar jadwal.` };
  return { jenis: "turun", teks: `Turun ${persenTeks(ringkasan.untung_persen)}% — wajar untuk saham; yang menentukan adalah tetap setor rutin.` };
};

export const buatPemuat = (ambilData, terapkan) => {
  let nomor = 0;
  return async (...args) => {
    const saya = ++nomor;
    let hasil;
    try {
      hasil = await ambilData(...args);
    } catch {
      hasil = null;
    }
    if (saya !== nomor) return false;
    terapkan(hasil);
    return true;
  };
};

export const kunciHasil = (modeContoh, skenario, pid) => (modeContoh ? `contoh-${skenario}` : `porto-${pid}`);

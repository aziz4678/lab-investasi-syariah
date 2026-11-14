import test from "node:test";
import assert from "node:assert/strict";
import { labelBulan, kelompokPerBulan, batasiBulan, kalimatKonteks, buatPemuat, kunciHasil } from "../src/utils/portofolioSaya.js";

const tx = (tanggal, nominal, jenis = "beli", id = tanggal) => ({ _id: id, tanggal, nominal, jenis });

test("label bulan memakai singkatan Indonesia", () => {
  assert.equal(labelBulan("2021-12"), "Des 2021");
  assert.equal(labelBulan("2020-05"), "Mei 2020");
});

test("transaksi dikelompokkan per bulan, bulan terbaru di atas, ringkas jumlah dan total", () => {
  const g = kelompokPerBulan([tx("2021-12-03", 250000, "beli", "a"), tx("2021-12-03", 250000, "beli", "b"), tx("2021-11-30", 500000, "beli", "c"), tx("2021-12-20", 100000, "jual", "d")]);
  assert.deepEqual(g.map((x) => x.kunci), ["2021-12", "2021-11"]);
  assert.equal(g[0].label, "Des 2021");
  assert.equal(g[0].jumlah, 3);
  assert.equal(g[0].total, 400000);
  assert.equal(g[1].total, 500000);
  assert.equal(g[0].baris[0]._id, "d");
});

test("default tampil 6 bulan terakhir, tombol semua menampilkan seluruhnya", () => {
  const data = [];
  for (let b = 1; b <= 12; b++) data.push(tx(`2021-${String(b).padStart(2, "0")}-05`, 1000000));
  const g = kelompokPerBulan(data);
  assert.equal(g.length, 12);
  assert.equal(batasiBulan(g).length, 6);
  assert.equal(batasiBulan(g)[0].kunci, "2021-12");
  assert.equal(batasiBulan(g, true).length, 12);
  assert.equal(batasiBulan(g.slice(0, 3)).length, 3);
});

test("kalimat konteks untuk untung dan rugi", () => {
  const naik = kalimatKonteks({ untung: 2000000, untung_persen: 0.0967 });
  assert.equal(naik.jenis, "naik");
  assert.match(naik.teks, /^Naik 9,7% — tetap ikuti rencana, jangan menambah porsi di luar jadwal\.$/);
  const turun = kalimatKonteks({ untung: -3500000, untung_persen: -0.1309 });
  assert.equal(turun.jenis, "turun");
  assert.match(turun.teks, /^Turun 13,1% — wajar untuk saham; yang menentukan adalah tetap setor rutin\.$/);
  assert.equal(kalimatKonteks({ untung: 0, untung_persen: 0 }), null);
  assert.equal(kalimatKonteks(null), null);
  assert.equal(kalimatKonteks({ untung: 10, untung_persen: null }), null);
});

test("pemuat: respons lama yang telat tidak menimpa respons terbaru", async () => {
  const terapkan = [];
  const tunggu = (ms, v) => new Promise((r) => setTimeout(() => r(v), ms));
  const muat = buatPemuat((nama, ms) => tunggu(ms, nama), (x) => terapkan.push(x));
  const lama = muat("lama", 40);
  const baru = muat("baru", 5);
  assert.equal(await baru, true);
  assert.equal(await lama, false);
  assert.deepEqual(terapkan, ["baru"]);
});

test("ganti skenario 5x bolak-balik: state selalu diganti, bukan ditumpuk, dan yang tampil hanya yang terakhir", async () => {
  let state = null;
  let diterapkan = 0;
  const data = { bagus: { bagian: ["alokasi", "produk", "pembanding", "grafik", "riwayat"], isi: "bagus" }, jelek: { bagian: ["alokasi", "produk", "pembanding", "grafik", "riwayat"], isi: "jelek" } };
  const muat = buatPemuat(async (k) => structuredClone(data[k]), (x) => { state = x; diterapkan += 1; });
  const urutan = ["bagus", "jelek", "bagus", "jelek", "bagus", "jelek", "bagus", "jelek", "bagus", "jelek"];
  for (const k of urutan) await muat(k);
  assert.equal(diterapkan, 10);
  assert.equal(state.isi, "jelek");
  for (const nama of ["alokasi", "produk", "pembanding", "grafik", "riwayat"]) assert.equal(state.bagian.filter((x) => x === nama).length, 1);
  assert.equal(state.bagian.length, 5);
});

test("pemuat: klik beruntun cepat hanya menerapkan hasil terakhir", async () => {
  const diterapkan = [];
  const muat = buatPemuat((k) => new Promise((r) => setTimeout(() => r(k), Math.random() * 20)), (x) => diterapkan.push(x));
  const semua = ["a", "b", "c", "d", "e"].map((k) => muat(k));
  await Promise.all(semua);
  assert.deepEqual(diterapkan, ["e"]);
});

test("kunci hasil berubah tiap ganti skenario atau portofolio supaya tampilan dibuat ulang", () => {
  assert.equal(kunciHasil(true, "bagus", "p1"), "contoh-bagus");
  assert.equal(kunciHasil(true, "jelek", "p1"), "contoh-jelek");
  assert.equal(kunciHasil(false, "", "p1"), "porto-p1");
  assert.notEqual(kunciHasil(true, "bagus", "p1"), kunciHasil(false, "", "p1"));
});

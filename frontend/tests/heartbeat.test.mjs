import test from "node:test";
import assert from "node:assert/strict";
import { hariBursaTelat, statusHeartbeat, jadwalPertama } from "../src/utils/heartbeat.js";

const libur = ["2026-12-24", "2026-12-25", "2026-12-31"];
const w = (s) => new Date(s);

test("cek hari ini setelah jam jadwal: tidak telat", () => {
  assert.equal(hariBursaTelat("2026-11-16T17:45:00", w("2026-11-16T20:00:00"), libur), 0);
});

test("cek Senin, sekarang Selasa sore: telat 1 hari bursa, belum mati", () => {
  const s = statusHeartbeat("2026-11-16T17:45:00", w("2026-11-17T18:30:00"), libur);
  assert.equal(s.telat, 1);
  assert.equal(s.mati, false);
});

test("cek Senin, sekarang Rabu sore: telat 2 hari bursa, mati", () => {
  const s = statusHeartbeat("2026-11-16T17:45:00", w("2026-11-18T18:30:00"), libur);
  assert.equal(s.telat, 2);
  assert.equal(s.mati, true);
  assert.equal(s.pesan, "Pemeriksa tidak jalan sejak 2026-11-16 — jadwal mungkin mati.");
});

test("hari ini sebelum jam jadwal tidak dihitung", () => {
  assert.equal(hariBursaTelat("2026-11-16T17:45:00", w("2026-11-18T10:00:00"), libur), 1);
});

test("akhir pekan tidak dihitung: cek Jumat, sekarang Minggu", () => {
  const s = statusHeartbeat("2026-11-13T17:45:00", w("2026-11-15T12:00:00"), libur);
  assert.equal(s.telat, 0);
  assert.equal(s.mati, false);
});

test("cek Jumat, Senin sore masih normal, Selasa sore mati", () => {
  assert.equal(statusHeartbeat("2026-11-13T17:45:00", w("2026-11-16T18:30:00"), libur).mati, false);
  assert.equal(statusHeartbeat("2026-11-13T17:45:00", w("2026-11-17T18:30:00"), libur).mati, true);
});

test("hari libur bursa tidak dihitung", () => {
  const s = statusHeartbeat("2026-12-23T17:45:00", w("2026-12-28T18:30:00"), libur);
  assert.equal(s.telat, 1);
  assert.equal(s.mati, false);
});

test("belum pernah jalan, jadwal pertama belum lewat = info", () => {
  const s = statusHeartbeat(null, w("2026-11-16T10:00:00"), libur, w("2026-11-14T12:00:00"));
  assert.equal(s.mati, false);
  assert.equal(s.belum, true);
  assert.match(s.pesan, /^Pemeriksa otomatis belum pernah jalan\. Jadwal pertama: .*16.*, 17:30\.$/);
});

test("pemasangan Jumat setelah jam jadwal: jadwal pertama Senin", () => {
  assert.equal(jadwalPertama(w("2026-11-13T19:00:00"), libur).getDate(), 16);
});

test("belum pernah jalan, jadwal pertama sudah lewat = gagal", () => {
  const s = statusHeartbeat(null, w("2026-11-16T18:30:00"), libur, w("2026-11-14T12:00:00"));
  assert.equal(s.mati, true);
  assert.equal(s.belum, false);
});

test("jadwal pertama melewati hari libur", () => {
  assert.equal(jadwalPertama(w("2026-12-23T19:00:00"), libur).getDate(), 28);
});

test("belum pernah jalan = mati", () => {
  const s = statusHeartbeat(null, w("2026-11-16T18:30:00"), libur);
  assert.equal(s.mati, true);
  assert.match(s.pesan, /belum pernah jalan/);
});

from fastapi import APIRouter, Body, HTTPException

from backend.app.services import belanja as bl
from backend.app.services import portofolio_contoh as pc
from backend.app.services import portofolio_saya as ps
from backend.app.services.reksadana import bersih

router = APIRouter(prefix="/api/portofolio-saya")


def _jalan(f, *a, **k):
    try:
        return f(*a, **k)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except KeyError as e:
        raise HTTPException(404, str(e).strip("'\""))


@router.get("")
def daftar():
    repo = ps.Repo()
    return bersih({"portofolio": repo.pastikan_default(), "target": ps.NAMA_TARGET, "aplikasi": list(ps.APLIKASI), "fee_default": ps.FEE_DEFAULT})


@router.post("/portofolio")
def simpan_portofolio(data: dict = Body(...)):
    repo = ps.Repo()
    pid = data.get("id")
    return bersih(_jalan(repo.simpan_portofolio, data, pid))


@router.post("/portofolio/{pid}/hapus")
def hapus_portofolio(pid: str):
    return bersih(_jalan(ps.Repo().hapus_portofolio, pid))


@router.get("/produk")
def produk(q: str = ""):
    return ps.cari_produk(q)


@router.get("/contoh")
def daftar_contoh():
    return {"skenario": pc.daftar_skenario()}


@router.get("/contoh/{skenario}")
def contoh(skenario: str):
    return _jalan(lambda: bl.dari_cache("contoh", (skenario,), lambda: pc.analisis_contoh(skenario)))


@router.get("/{pid}/analisis")
def analisis(pid: str):
    return _jalan(ps.analisis, pid)


@router.get("/{pid}/isi-belanja")
def isi_belanja(pid: str, apps: str = "bibit,ajaib,makmur,stockbit", setoran: float = 0):
    return _jalan(ps.isi_dari_belanja, pid, apps, setoran=setoran)


@router.post("/transaksi")
def tambah(data: dict = Body(...)):
    return bersih(_jalan(ps.Repo().tambah, data))


@router.post("/transaksi/{tid}/ubah")
def ubah(tid: str, data: dict = Body(...)):
    return bersih(_jalan(ps.Repo().ubah, tid, data))


@router.post("/transaksi/{tid}/hapus")
def hapus(tid: str):
    return bersih(_jalan(ps.Repo().hapus, tid))


@router.get("/transaksi/{tid}/riwayat")
def riwayat(tid: str):
    return bersih(ps.Repo().riwayat(tid))

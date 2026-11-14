import pandas as pd
from backend.research import uji_h21_h22 as m
for periode in ["dev"]:
    S = m.susun(periode)
    eb = m.pembanding_sama(S)
    for nama, kw in [("dasar", {}), ("S2 Rp20M", {"min_nilai": 20e9})]:
        for k in [0.0, 0.25, 0.5, 1.0]:
            base = m.simulasi(S, "h22", tick=k, **kw)
            e = base["ekuitas"]; ebj = eb.reindex(e.index)
            ej = m.pembanding_jii(S, base["mulai"])
            ebx = m.pembanding_sama(S, **kw).reindex(e.index) if kw else ebj
            kr, s, b, j = m.nilai_h22(S, base, ebx, ej)
            lulus = [x[2] for x in kr]
            print(periode, nama, "biaya", {0.0:"0,4",0.25:"0,6",0.5:"0,8",1.0:"1,2"}[k], "| CAGR", s["cagr"], "DD", s["dd"], "| bobot sama", b["cagr"], "| kriteria", "".join("V" if v else "x" for v in lulus), sum(lulus), "/6", flush=True)

(async () => {
  const SEMUA = ["tw1", "tw2", "tw3", "audit"];
  const TAHUN = new Date().getFullYear();
  const TUGAS = [[TAHUN - 1, ["audit"]], [TAHUN, SEMUA]];
  const JEDA_TOLAK = [30, 60, 120, 240, 480];
  const BATAS_PER_TAHUN = 0;
  const JEDA = 1500;
  const KODE = new Set(["AADI", "AALI", "ABBA", "ABMM", "ACES", "ACRO", "ACST", "ADCP", "ADHI", "ADMG", "ADMR", "ADRO", "AGAR", "AGII", "AISA", "AKRA", "AKSI", "ALDO", "AMAN", "AMMN", "AMMS", "ANDI", "ANJT", "ANTM", "APEX", "APLN", "ARCI", "AREA", "ARNA", "ASGR", "ASHA", "ASII", "ASLC", "ASLI", "ASPI", "ASPR", "ASRI", "ASSA", "ATAP", "ATLA", "AUTO", "AVIA", "AWAN", "AXIO", "AYAM", "AYLS", "BABY", "BAIK", "BALI", "BANK", "BAPA", "BATR", "BAUT", "BBRM", "BBSS", "BCIP", "BDKR", "BEBS", "BEEF", "BELI", "BELL", "BESS", "BEST", "BIKE", "BIMA", "BINO", "BIPP", "BIRD", "BISI", "BKDP", "BKSL", "BLES", "BLOG", "BLTA", "BLUE", "BMHS", "BMTR", "BNBR", "BOAT", "BOBA", "BOGA", "BOLA", "BOSS", "BRIS", "BRMS", "BRPT", "BRRC", "BSBK", "BSDE", "BSML", "BSSR", "BTEK", "BTPS", "BUAH", "BUDI", "BUKA", "BULL", "BUMI", "BUVA", "BWPT", "BYAN", "CAKK", "CAMP", "CARE", "CASH", "CASS", "CBDK", "CBMF", "CBPE", "CBRE", "CBUT", "CCSI", "CENT", "CGAS", "CHEK", "CHEM", "CHIP", "CITA", "CITY", "CLEO", "CMNP", "CMPP", "CMRY", "CNKO", "CNMA", "COAL", "COCO", "CPIN", "CPRO", "CRAB", "CRSN", "CSIS", "CSMI", "CSRA", "CTRA", "CTTH", "CUAN", "CYBR", "DAAZ", "DADA", "DATA", "DEAL", "DEFI", "DEPO", "DEWA", "DEWI", "DGIK", "DGNS", "DGWG", "DIGI", "DILD", "DIVA", "DKFT", "DKHH", "DMAS", "DMMX", "DOOH", "DOSS", "DPUM", "DRMA", "DSFI", "DSNG", "DSSA", "DUCK", "DWGL", "DYAN", "ECII", "EDGE", "EKAD", "ELIT", "ELPI", "ELSA", "ELTY", "EMTK", "ENAK", "ENRG", "ENVY", "ENZO", "EPAC", "ERAA", "ERAL", "ERTX", "ESIP", "ESSA", "ESTA", "ESTI", "EURO", "EXCL", "FAST", "FILM", "FIRE", "FITT", "FOLK", "FORE", "FORU", "FPNI", "FREN", "FUTR", "FWCT", "GDST", "GEMA", "GEMS", "GIAA", "GJTL", "GMFI", "GOLF", "GOOD", "GOTO", "GPRA", "GPSO", "GRIA", "GRPH", "GRPM", "GTBO", "GTRA", "GTSI", "GULA", "GUNA", "GZCO", "HAIS", "HAJJ", "HALO", "HATM", "HDIT", "HEAL", "HELI", "HEXA", "HGII", "HILL", "HITS", "HKMU", "HOKI", "HOMI", "HOPE", "HRME", "HRTA", "HRUM", "HUMI", "HYGN", "IATA", "IBOS", "ICBP", "ICON", "IDPR", "IKAN", "IKPM", "IMPC", "INAF", "INCO", "INDF", "INDO", "INDR", "INDS", "INDX", "INDY", "INET", "INKP", "INPS", "INTP", "IOTF", "IPCC", "IPCM", "IPOL", "IPPE", "IPTV", "IRRA", "IRSX", "ISAP", "ISAT", "ISSP", "ITMA", "ITMG", "JARR", "JAST", "JATI", "JAWA", "JAYA", "JGLE", "JIHD", "JKON", "JMAS", "JPFA", "JSKY", "JSMR", "JTPE", "KAEF", "KAQI", "KARW", "KAYU", "KBAG", "KBLM", "KBLV", "KDTN", "KEEN", "KEJU", "KETR", "KICI", "KIJA", "KING", "KINO", "KIOS", "KJEN", "KKES", "KKGI", "KLAS", "KLBF", "KOBX", "KOCI", "KOKA", "KOPI", "KOTA", "KPIG", "KREN", "KRYA", "KSIX", "KUAS", "LABA", "LABS", "LAJU", "LAND", "LAPD", "LCKM", "LINK", "LIVE", "LMAS", "LMAX", "LPCK", "LPIN", "LPKR", "LPPF", "LSIP", "LUCK", "MAHA", "MAIN", "MANG", "MAPA", "MAPI", "MARK", "MAXI", "MBAP", "MBMA", "MBSS", "MBTO", "MCAS", "MCOL", "MDIA", "MDIY", "MDKA", "MDLA", "MDLN", "MEDC", "MEDS", "MEJA", "MENN", "MERI", "META", "MGLV", "MGNA", "MGRO", "MHKI", "MIDI", "MIKA", "MINA", "MINE", "MITI", "MKAP", "MKPI", "MKTR", "MLIA", "MLPL", "MLPT", "MMIX", "MMLP", "MNCN", "MORA", "MPIX", "MPMX", "MPOW", "MPPA", "MPXL", "MRAT", "MSIE", "MSIN", "MSJA", "MSKY", "MSTI", "MTDL", "MTEL", "MTFN", "MTMH", "MTPS", "MUTU", "MYOR", "NAIK", "NANO", "NASA", "NASI", "NATO", "NAYZ", "NCKL", "NELY", "NEST", "NETV", "NFCX", "NICE", "NICL", "NIKL", "NINE", "NIRO", "NPGF", "NRCA", "NSSS", "NTBK", "NZIA", "OASA", "OBAT", "OBMD", "OILS", "OKAS", "OLIV", "OMED", "OPMS", "PACK", "PADA", "PALM", "PAMG", "PANI", "PANR", "PART", "PBSA", "PCAR", "PDPP", "PEHA", "PEVE", "PGAS", "PGEO", "PGUN", "PICO", "PIPA", "PJHB", "PKPK", "PMUI", "PNBS", "POLL", "POWR", "PPRE", "PPRI", "PPRO", "PRAY", "PRDA", "PRIM", "PSAB", "PSAT", "PSDN", "PSGO", "PSKT", "PSSI", "PTBA", "PTDU", "PTMP", "PTMR", "PTPP", "PTPS", "PTPW", "PTRO", "PTSN", "PURA", "PURE", "PURI", "PWON", "PYFA", "RAAM", "RAFI", "RAJA", "RALS", "RANC", "RATU", "RBMS", "REAL", "RELF", "RGAS", "RICY", "RIGS", "RISE", "RMKE", "RMKO", "RODA", "ROTI", "RSCH", "RSGK", "RUIS", "RUNS", "SAGE", "SAME", "SAMF", "SAPX", "SATU", "SBMA", "SCMA", "SCNP", "SDMU", "SDPC", "SEMA", "SGER", "SGRO", "SHID", "SHIP", "SICO", "SIDO", "SILO", "SIMP", "SINI", "SKRN", "SLIS", "SMBR", "SMCB", "SMDM", "SMDR", "SMGA", "SMGR", "SMIL", "SMKL", "SMKM", "SMLE", "SMMT", "SMRA", "SMSM", "SNLK", "SOCI", "SOFA", "SOLA", "SOTS", "SPRE", "SQMI", "SRAJ", "SRSN", "SRTG", "SSIA", "SSMS", "STAA", "SULI", "SUNI", "SURI", "SWAT", "SWID", "TAMA", "TAPG", "TAYS", "TCPI", "TDPM", "TEBE", "TECH", "TELE", "TFAS", "TGRA", "TGUK", "TINS", "TIRT", "TKIM", "TLDN", "TLKM", "TMAS", "TMPO", "TNCA", "TOBA", "TOOL", "TOPS", "TOSK", "TOTL", "TOYS", "TPIA", "TPMA", "TRIN", "TRIS", "TRJA", "TRON", "TRUE", "TRUK", "TSPC", "TYRE", "UANG", "UCID", "UDNG", "UFOE", "ULTJ", "UNIQ", "UNTD", "UNTR", "UNVR", "UVCR", "VAST", "VERN", "VICI", "VISI", "VIVA", "VKTR", "WAPO", "WBSA", "WEGE", "WEHA", "WGSH", "WIDI", "WIFI", "WIKA", "WINR", "WINS", "WIRG", "WMPP", "WMUU", "WOOD", "WOWS", "WSBP", "WTON", "YELO", "YUPI", "ZATA", "ZBRA", "ZINC", "ZYRX", "ADMF", "AGRO", "AGRS", "AHAP", "ALII", "AMAR", "AMOR", "AMRT", "APIC", "ARKA", "ARKO", "ARTO", "ASMI", "BABP", "BACA", "BACH", "BAJA", "BBCA", "BBHI", "BBKP", "BBNI", "BBRI", "BBTN", "BBYB", "BCAP", "BCIC", "BDMN", "BEER", "BEKS", "BFIN", "BGTG", "BHAT", "BHIT", "BINA", "BIPI", "BJBR", "BJTM", "BKSW", "BMRI", "BNBA", "BNGA", "BNII", "BNLI", "BPII", "BPTR", "BREN", "BSIM", "BVIC", "CARS", "CASA", "CDIA", "CFIN", "CMNT", "COIN", "DFAM", "DNAR", "DOID", "EMAS", "EMMI", "FUJI", "GGRM", "GSMF", "HMSP", "IMAS", "IMJS", "INCF", "INOV", "INPC", "ISEA", "ITIC", "JECX", "JELI", "KRAS", "LEAD", "LPPS", "LUCY", "MARI", "MASB", "MAYA", "MCOR", "MFIN", "MOLI", "MTWI", "NISP", "NOBU", "PADI", "PANS", "PBRX", "PEGE", "PMMP", "PNBN", "PNIN", "PNLF", "POLA", "POLY", "PRAS", "PRDL", "RANS", "RLCO", "SBAT", "SMMA", "SRIL", "STRK", "SUPA", "TBIG", "TBLA", "TOWR", "TRGU", "TRIM", "TUGU", "UNSP", "VICO", "VTNY", "WIIM", "WINE", "WSKT", "YOII", "YULE"]);
  const TAG = ["ProfitLoss", "ProfitLossAttributableToParentEntity", "ProfitLossBeforeIncomeTax", "SalesAndRevenue", "GrossProfit",
    "NetCashFlowsReceivedFromUsedInOperatingActivities", "BasicEarningsLossPerShareFromContinuingOperations", "BasicEarningsLossPerShare",
    "Assets", "Liabilities", "Equity", "EquityAttributableToEquityOwnersOfParentEntity", "CashAndCashEquivalents",
    "CurrentAssets", "CurrentLiabilities", "InterestIncome", "InterestAndShariaIncome", "IncomeFromSharia"];
  const KONTEKS = ["CurrentYearDuration", "PriorYearDuration", "CurrentYearInstant", "PriorEndYearInstant"];
  const tunggu = ms => new Promise(r => setTimeout(r, ms));
  const u16 = (b, i) => b[i] | (b[i + 1] << 8);
  const u32 = (b, i) => (b[i] | (b[i + 1] << 8) | (b[i + 2] << 16) | (b[i + 3] << 24)) >>> 0;
  const inflate = async data => new Uint8Array(await new Response(new Blob([data]).stream().pipeThrough(new DecompressionStream("deflate-raw"))).arrayBuffer());
  async function bacaZip(buf) {
    const b = new Uint8Array(buf);
    let e = b.length - 22;
    while (e >= 0 && u32(b, e) !== 0x06054b50) e--;
    if (e < 0) throw new Error("bukan zip");
    let p = u32(b, e + 16);
    const n = u16(b, e + 10);
    const hasil = [];
    for (let i = 0; i < n; i++) {
      const metode = u16(b, p + 10), ukuran = u32(b, p + 20), ln = u16(b, p + 28), le = u16(b, p + 30), lk = u16(b, p + 32), off = u32(b, p + 42);
      const nama = new TextDecoder().decode(b.slice(p + 46, p + 46 + ln));
      p += 46 + ln + le + lk;
      if (!/\.(x?html?|xml|xbrl)$/i.test(nama)) continue;
      const mulai = off + 30 + u16(b, off + 26) + u16(b, off + 28);
      const isi = b.slice(mulai, mulai + ukuran);
      hasil.push(new TextDecoder().decode(metode === 8 ? await inflate(isi) : isi));
    }
    return hasil;
  }
  function angka(teks, skala, tanda) {
    let s = teks.replace(/<[^>]+>/g, "").trim();
    const kurung = /^\(.*\)$/.test(s);
    s = s.replace(/[(),\s]/g, "");
    if (s === "" || s === "-") return null;
    let v = parseFloat(s) * Math.pow(10, parseInt(skala || "0"));
    if (kurung || tanda === "-") v = -v;
    return isFinite(v) ? v : null;
  }
  function ambilFakta(teksList) {
    const f = {};
    const pola1 = /<ix:nonfraction((?:[^>"]|"[^"]*")*?)(?<!\/)>((?:(?!<ix:nonfraction)[\s\S])*?)<\/ix:nonfraction>/gi;
    const pola2 = /<idx-cor:(\w+)([^>]*)>([^<]*)<\/idx-cor:\1>/gi;
    for (const t of teksList) {
      for (const m of t.matchAll(pola1)) {
        const at = Object.fromEntries([...m[1].matchAll(/([\w:]+)="([^"]*)"/g)].map(x => [x[1].toLowerCase(), x[2]]));
        const nama = (at.name || "").split(":").pop();
        if (!TAG.includes(nama) || !KONTEKS.includes(at.contextref)) continue;
        const v = angka(m[2], at.scale, at.sign);
        if (at.unitref && !f._unit && /idr|usd|sgd|eur|jpy/i.test(at.unitref)) f._unit = at.unitref;
        if (v !== null && f[nama + "@" + at.contextref] === undefined) f[nama + "@" + at.contextref] = v;
      }
      for (const m of t.matchAll(pola2)) {
        const ctx = (m[2].match(/contextRef="([^"]*)"/i) || [])[1];
        const un = (m[2].match(/unitRef="([^"]*)"/i) || [])[1];
        if (un && !f._unit && /idr|usd|sgd|eur|jpy/i.test(un)) f._unit = un;
        if (!TAG.includes(m[1]) || !KONTEKS.includes(ctx)) continue;
        const v = angka(m[3], "0", null);
        if (v !== null && f[m[1] + "@" + ctx] === undefined) f[m[1] + "@" + ctx] = v;
      }
    }
    return f;
  }
  const simpan = (isi, nama) => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(isi)], { type: "application/json" }));
    a.download = nama;
    a.click();
  };
  async function ambilSopan(url, jenis) {
    for (let i = 0; i <= JEDA_TOLAK.length; i++) {
      let r = null;
      try { r = await fetch(url, { credentials: "include" }); } catch (e) { r = null; }
      if (r && r.ok) return r;
      if (r && r.status === 404) throw new Error("status 404");
      if (i === JEDA_TOLAK.length) break;
      console.log(`  ${jenis} ditolak (${r ? r.status : "jaringan"}), tunggu ${JEDA_TOLAK[i]} detik lalu coba lagi`);
      await tunggu(JEDA_TOLAK[i] * 1000);
    }
    throw new Error("BERHENTI");
  }
  let total = 0;
  for (const [th, periode] of TUGAS) {
    const hasil = [];
    let diTahun = 0;
    const nama = periode.length === SEMUA.length ? `idx_fundamental_${th}.json` : `idx_fundamental_${th}_${periode.join("_")}.json`;
    try {
      for (const per of periode) {
        const daftar = [];
        const unik = new Set();
        let hal = 0, tanpaBaru = 0, jumlah = null;
        while (jumlah === null || unik.size < jumlah) {
          const r = await ambilSopan(`/primary/ListedCompany/GetFinancialReport?indexFrom=${hal}&pageSize=100&year=${th}&reportType=rdf&EmitenType=s&periode=${per}&kodeEmiten=&SortColumn=KodeEmiten&SortOrder=asc`, "daftar");
          const j = await r.json();
          jumlah = j.ResultCount || 0;
          const sebelum = unik.size;
          for (const a of j.Results || []) {
            if (unik.has(a.KodeEmiten)) continue;
            unik.add(a.KodeEmiten);
            if (KODE.has(a.KodeEmiten)) daftar.push(a);
          }
          tanpaBaru = unik.size === sebelum ? tanpaBaru + 1 : 0;
          hal += 1;
          if (!(j.Results || []).length || tanpaBaru >= 2) break;
          await tunggu(JEDA);
        }
        console.log(th, per, "laporan semua", unik.size, "| target", daftar.length);
        for (const a of daftar) {
          if (BATAS_PER_TAHUN && diTahun >= BATAS_PER_TAHUN) break;
          const lamp = a.Attachments || [];
          const zip = lamp.find(x => /inlinexbrl\.zip$/i.test(x.File_Name)) || lamp.find(x => /\.zip$/i.test(x.File_Name));
          const rec = { kode: a.KodeEmiten, tahun: a.Report_Year, periode: a.Report_Period, file_modified: a.File_Modified, sumber: zip ? zip.File_Name : null };
          if (zip) {
            try {
              const r = await ambilSopan(zip.File_Path, "file " + a.KodeEmiten);
              rec.fakta = ambilFakta(await bacaZip(await r.arrayBuffer()));
            } catch (e) {
              if (e.message === "BERHENTI") throw e;
              rec.error = e.message;
            }
            await tunggu(JEDA);
          }
          hasil.push(rec);
          total += 1;
          diTahun += 1;
          if (BATAS_PER_TAHUN) console.log("  TES", rec.kode, rec.tahun, rec.periode, rec.sumber, rec.fakta ? Object.keys(rec.fakta).length + " angka" : (rec.error || "tanpa zip"));
          if (total % 10 === 0) console.log("  diproses", total, "| terakhir", rec.kode, rec.tahun, rec.periode, rec.fakta ? Object.keys(rec.fakta).length + " angka" : (rec.error || "tanpa zip"));
        }
        if (BATAS_PER_TAHUN && diTahun >= BATAS_PER_TAHUN) break;
      }
    } catch (e) {
      if (e.message !== "BERHENTI") throw e;
      if (hasil.length) simpan(hasil, nama.replace(".json", "_sebagian.json"));
      console.log(`IDX MASIH MENOLAK setelah menunggu ~15 menit. Disimpan ${hasil.length} laporan ${th} sebagai *_sebagian.json. BERHENTI. Coba lagi nanti mulai tahun ${th}.`);
      return;
    }
    if (!BATAS_PER_TAHUN) simpan(hasil, nama);
    console.log(`TAHUN ${th} (${periode.join(",")}) SELESAI: ${hasil.length} laporan, ${hasil.filter(x => x.fakta && Object.keys(x.fakta).length).length} berisi angka`);
  }
  console.log("SEMUA SELESAI");
})();

import csv,sys,glob
LC={"PCM3168APAPR":"C529289","INA217AIDWR":"C1849416","BQ24074RGTR":"C54313","TPS63060DSCR":"C48567","OPA1678IDR":"C192421",
    "TCA9555PWR":"C465732","TLV75533PDBVR":"C404027","TPS2051CDBVR":"C129581","TPS2552DBVR":"C46506","TPS61230DRCR":"C139626","NCP163ASN500T1G":"C603657","TUSB321RWBR":"C139392","PESD5V0L1BA":"C85380","SMF15CA":"C2890424","XAL4020-102MEC":"C4555951","RT0603BRD0720KL":"C723637","RT0603BRD074K99L":"C723532"}
for fn in glob.glob(sys.argv[1]+"/*_BOM_*.csv"):
    rows=list(csv.reader(open(fn))); h=rows[0]
    vi=h.index("Comment") if "Comment" in h else h.index("Value"); li=h.index("LCSC Part #") if "LCSC Part #" in h else h.index("LCSC")
    for r in rows[1:]:
        if r[vi] in LC: r[li]=LC[r[vi]]
    csv.writer(open(fn,"w",newline="")).writerows(rows)
    print(fn, sum(1 for r in rows[1:] if r[li] in ("","choose")),"rows without LCSC")

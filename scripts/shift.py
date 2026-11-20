# shift.py REF:dx:dy ... : move parts by a small amount and drag the track ends that sit on their pads
import sys, json, pcbnew
D = "/home/claude/radio/out_revc1/radio_carrier"
b = pcbnew.LoadBoard(f"{D}/carrier_placed.kicad_pcb"); pl = json.load(open(f"{D}/placement.json"))
r = json.load(open(f"{D}/routes.json"))
F = {f.GetReference(): f for f in b.GetFootprints()}
for arg in sys.argv[1:]:
    ref, dx, dy = arg.split(":"); dx, dy = float(dx), float(dy); f = F[ref]
    pads = [(pcbnew.ToMM(p.GetPosition().x) - 100, pcbnew.ToMM(p.GetPosition().y) - 50, p.GetNetname()) for p in f.Pads()]
    f.SetPosition(pcbnew.VECTOR2I_MM(pcbnew.ToMM(f.GetPosition().x) + dx, pcbnew.ToMM(f.GetPosition().y) + dy))
    pl[ref][0] = round(pl[ref][0] + dx, 3); pl[ref][1] = round(pl[ref][1] + dy, 3)
    k = 0
    for t in r["tracks"]:
        for e in ((2, 3), (4, 5)):
            for px, py, n in pads:
                if t[0] == n and abs(t[e[0]] - px) < 1e-3 and abs(t[e[1]] - py) < 1e-3:
                    t[e[0]] += dx; t[e[1]] += dy; k += 1
    print(ref, "moved; track ends dragged", k)
b.Save(f"{D}/carrier_placed.kicad_pcb"); json.dump(pl, open(f"{D}/placement.json", "w")); json.dump(r, open(f"{D}/routes.json", "w"), default=float)

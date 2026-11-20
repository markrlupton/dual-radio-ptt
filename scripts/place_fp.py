#!/usr/bin/python3
"""Carrier PCB placement: hand-placed ICs/connectors, then a greedy placer for passives that puts each one
as close as possible to the pins it connects to, inside its functional zone. Writes <out>/fp_placed.kicad_pcb."""
import pcbnew, re, json, sys, math
import numpy as np
from pcbnew import VECTOR2I_MM as P, FromMM, ToMM
sys.path.insert(0, "/home/claude/radio")
from fpinfo import crt

OUT = sys.argv[1]
PROJ = "radio_frontpanel"
NET = f"{OUT}/{PROJ}.net"
LIBDIR = "/usr/share/kicad/footprints"
OX, OY = 100.0, 50.0
W, L = 124.0, 38.0

net_txt = open(NET).read()
comps = dict(re.findall(r'\(comp \(ref "([^"]+)"\)\s*\(value "[^"]*"\)\s*\(footprint "([^"]+)"\)', net_txt))
values = dict(re.findall(r'\(comp \(ref "([^"]+)"\)\s*\(value "([^"]*)"\)', net_txt))
tstamp = {b[0]: b[2] for b in re.findall(r'\(comp \(ref "([^"]+)"\)(.*?)\(tstamps "([0-9a-f-]{36})"\)\)', net_txt, re.S)}
exp = json.load(open(f"{OUT}/expected_nets.json"))
pin_net = {}
for k, n in exp.items():
    r, p = k.split("."); pin_net.setdefault(r, {})[p] = n

# ------------------------------------------------------------------ fixed placement (x, y, rot)
EY = 13.0
def enc(cx): return (cx - 7.5, EY - 2.5, 0)
def sw12(cx, cy): return (cx - 6.25, cy - 2.5, 0)
def sw6(cx, cy): return (cx - 3.25, cy - 2.25, 0)
FIXED = {
 "ENC1": enc(11.0), "ENC2": enc(29.5), "ENC3": enc(94.0), "ENC4": enc(112.5),
 "SW1": sw12(48.5, EY), "SW2": sw12(75.5, EY), "SW3": sw6(62.0, 9.0), "SW4": sw6(62.0, 18.5),
 "D1": (48.5, 3.2, 0), "D2": (75.5, 3.2, 0), "D3": (62.0, 2.6, 0),
 "J1": (61.4, 29.0, 90), "U1": (46.0, 31.0, 90),
 "H1": (3.2, 34.8, 0), "H2": (120.8, 34.8, 0), "H3": (3.2, 3.2, 0), "H4": (120.8, 3.2, 0),
}
ZONES = {
 "iox": ((36.0, 21.5, 88.0, 37.0), ["C1", "C2"] + [f"R{1+i}" for i in range(8)]),
 "encA": ((1.0, 20.5, 40.0, 37.0), [f"R{10+i}" for i in range(8)] + [f"C{10+i}" for i in range(4)]),
 "encB": ((84.0, 20.5, 123.0, 37.0), [f"R{18+i}" for i in range(8)] + [f"C{14+i}" for i in range(4)]),
 "led": ((40.0, 0.8, 84.0, 8.0), ["R30", "R31", "R32"]),
}
HUG = {"C1": "U1.24", "C2": "U1.24", "R30": "D1.2", "R31": "D2.2", "R32": "D3.2"}
TP_HUG = {}
IGNORE_NETS = {"GND", "+3V3"}
board = pcbnew.CreateEmptyBoard()
board.SetCopperLayerCount(4)
ds = board.GetDesignSettings(); ds.SetCopperLayerCount(4)
nc = ds.m_NetSettings.m_DefaultNetClass
nc.SetTrackWidth(FromMM(0.2)); nc.SetClearance(FromMM(0.15)); nc.SetViaDiameter(FromMM(0.5)); nc.SetViaDrill(FromMM(0.25))
ds.m_TrackMinWidth = FromMM(0.127); ds.m_MinClearance = FromMM(0.127); ds.m_ViasMinSize = FromMM(0.45)
ds.m_MinThroughDrill = FromMM(0.2); ds.m_HoleToHoleMin = FromMM(0.25); ds.m_CopperEdgeClearance = FromMM(0.3)
nets = {}
for n in sorted(set(exp.values())):
    ni = pcbnew.NETINFO_ITEM(board, n); board.Add(ni); nets[n] = ni

FPS = {}
for ref, fpid in comps.items():
    lib, name = fpid.split(":")
    fp = pcbnew.FootprintLoad(f"{LIBDIR}/{lib}.pretty", name)
    fp.SetReference(ref); fp.SetValue(values.get(ref, "")); fp.SetFPID(pcbnew.LIB_ID(lib, name))
    if ref in tstamp: fp.SetPath(pcbnew.KIID_PATH("/" + tstamp[ref]))
    FPS[ref] = fp

# --- occupancy at 0.25 mm
GS = 0.25
NXo, NYo = int(W / GS) + 1, int(L / GS) + 1
occ = np.zeros((NYo, NXo), np.uint8)
def rot_pt(x, y, r):
    a = math.radians(r); c, s = round(math.cos(a)), round(math.sin(a))
    return (x * c + y * s, -x * s + y * c)          # KiCad: positive angle = CCW on screen (y down)
def rbox(b, r):
    pts = [rot_pt(x, y, r) for x in (b[0], b[2]) for y in (b[1], b[3])]
    return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))
CRT = {ref: crt(fp) for ref, fp in FPS.items()}
PADL = {ref: [(p.GetNumber(), ToMM(p.GetPosition().x), ToMM(p.GetPosition().y)) for p in fp.Pads() if p.GetNumber()] for ref, fp in FPS.items()}
POS = {}
def mark(ref, x, y, r, pad=0.2):
    b = rbox(CRT[ref], r)
    i0, i1 = int((x + b[0] - pad) / GS), int(math.ceil((x + b[2] + pad) / GS))
    j0, j1 = int((y + b[1] - pad) / GS), int(math.ceil((y + b[3] + pad) / GS))
    occ[max(0, j0):j1, max(0, i0):i1] = 1
    POS[ref] = (x, y, r)
def pad_xy(ref, num):
    x, y, r = POS[ref]
    for (n, px, py) in PADL[ref]:
        if n == num:
            dx, dy = rot_pt(px, py, r); return (x + dx, y + dy)
    raise KeyError((ref, num))

for ref, (x, y, r) in FIXED.items(): mark(ref, x, y, r, 0.3)
# the Teensy body sits over the sockets; parts under it are fine (socket height), so only sockets are marked
# keep the codec pin ring free for fan-out: inflate the codec
# routing channels kept clear
# board edge margin
occ[:, :int(0.8 / GS)] = 1; occ[:, -int(0.8 / GS):] = 1; occ[:int(0.8 / GS), :] = 1; occ[-int(0.8 / GS):, :] = 1

def anchors(ref):
    """per pin: target point (pad of the same net already placed, nearest IC first)"""
    out = {}
    for pnum, n in pin_net.get(ref, {}).items():
        if n is None: continue
        if ref in HUG and n not in ("GND",):
            hr, hp = HUG[ref].split(".")
            if pin_net[hr][hp] == n and hr in POS: out[pnum] = [pad_xy(hr, hp)]; continue
        if ref in TP_HUG and TP_HUG[ref]:
            hr, hp = TP_HUG[ref].split(".")
            if hr in POS: out[pnum] = [pad_xy(hr, hp)]; continue
        if n in IGNORE_NETS: continue
        pts = []
        for r2, pins in pin_net.items():
            if r2 == ref or r2 not in POS: continue
            for p2, n2 in pins.items():
                if n2 == n:
                    try: pts.append(pad_xy(r2, p2))
                    except KeyError: pass
        if pts: out[pnum] = pts
    return out

def place(ref, zone):
    an = anchors(ref)
    if not an: return False
    x0, y0, x1, y1 = zone
    best = None
    for r in (0, 90, 180, 270):
        b = rbox(CRT[ref], r)
        wi, hi = int(math.ceil((b[2] - b[0] + 0.4) / GS)), int(math.ceil((b[3] - b[1] + 0.4) / GS))
        # free-window test via summed area table
        S = np.pad(occ.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
        win = S[hi:, wi:] - S[:-hi, wi:] - S[hi:, :-wi] + S[:-hi, :-wi]       # [j,i]: window starting at (j,i)
        free = win == 0
        J, I = np.nonzero(free)
        if len(J) == 0: continue
        # centre of the part for window start (i,j)
        cx = I * GS - (b[0] - 0.2); cy = J * GS - (b[1] - 0.2)
        ok = (cx + b[0] >= x0) & (cx + b[2] <= x1) & (cy + b[1] >= y0) & (cy + b[3] <= y1)
        cx, cy = cx[ok], cy[ok]
        if len(cx) == 0: continue
        cost = np.zeros(len(cx))
        for (pn, px, py) in PADL[ref]:
            if pn not in an: continue
            dx, dy = rot_pt(px, py, r)
            pts = np.array(an[pn])
            d = np.min(np.hypot((cx + dx)[:, None] - pts[None, :, 0], (cy + dy)[:, None] - pts[None, :, 1]), axis=1)
            cost += d * (3.0 if ref in HUG else 1.0)
        k = int(np.argmin(cost))
        if best is None or cost[k] < best[0]: best = (cost[k], cx[k], cy[k], r)
    if best is None:
        print("NO ROOM", ref, zone); return None
    _, cx, cy, r = best
    mark(ref, round(cx / 0.05) * 0.05, round(cy / 0.05) * 0.05, r)
    return True

pending = [(z, ref) for z, (zone, refs) in ZONES.items() for ref in refs]
# hugging caps first, then the rest in rounds as anchors appear
pending.sort(key=lambda t: (t[1] not in HUG, t[0] == "tp"))
for rnd in range(6):
    left = []
    for z, ref in pending:
        res = place(ref, ZONES[z][0])
        if res is False: left.append((z, ref))
    pending = left
    if not pending: break
for z, ref in pending:            # no anchor at all: drop into the zone anywhere
    print("unanchored", ref); HUG.pop(ref, None)
    x0, y0, x1, y1 = ZONES[z][0]; PADL_ref = PADL[ref]
    # use zone centre as a fake anchor
    an_c = ((x0 + x1) / 2, (y0 + y1) / 2)
    pin_net.setdefault(ref, {})
    POS["__c"] = (an_c[0], an_c[1], 0); PADL["__c"] = [("1", 0, 0)]
    HUG[ref] = "__c.1"; pin_net["__c"] = {"1": pin_net[ref].get("1")}
    place(ref, ZONES[z][0]); del POS["__c"]

missing = [r for r in FPS if r not in POS]
print("unplaced:", missing)

for ref, fp in FPS.items():
    if ref not in POS: continue
    x, y, r = POS[ref]
    fp.SetPosition(P(OX + x, OY + y)); fp.SetOrientationDegrees(r)
    board.Add(fp)
    for pad in fp.Pads():
        n = exp.get(f"{ref}.{pad.GetNumber()}")
        if n: pad.SetNet(nets[n])
        if n == "GND" and pad.GetNumber() in ("65", "11", "13", "17") and ref in ("U1", "U4", "U11", "U12", "U10"):
            pad.SetZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    if ref == "U4":
        for pad in fp.Pads():
            if pad.GetNumber() == "11": pad.SetZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    fp.Reference().SetTextSize(P(0.7, 0.7)); fp.Reference().SetTextThickness(FromMM(0.1)); fp.Value().SetVisible(False)

s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_RECT); s.SetStart(P(OX, OY)); s.SetEnd(P(OX + W, OY + L))
s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(FromMM(0.1)); board.Add(s)
for lay in (pcbnew.In1_Cu, pcbnew.In2_Cu):
    z = pcbnew.ZONE(board); z.SetLayer(lay); z.SetNetCode(nets["GND"].GetNetCode())
    z.SetLocalClearance(FromMM(0.2)); z.SetMinThickness(FromMM(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL); z.SetThermalReliefGap(FromMM(0.2)); z.SetThermalReliefSpokeWidth(FromMM(0.3))
    o = z.Outline(); o.NewOutline()
    for (x, y) in [(0.2, 0.2), (W - 0.2, 0.2), (W - 0.2, L - 0.2), (0.2, L - 0.2)]: o.Append(P(OX + x, OY + y))
    board.Add(z)
board.Save(f"{OUT}/fp_placed.kicad_pcb")
json.dump({k: v for k, v in POS.items()}, open(f"{OUT}/placement.json", "w"), indent=0)
print("placed", len(POS))

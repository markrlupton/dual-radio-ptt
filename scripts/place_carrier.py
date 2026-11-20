#!/usr/bin/python3
"""Carrier PCB placement: hand-placed ICs/connectors, then a greedy placer for passives that puts each one
as close as possible to the pins it connects to, inside its functional zone. Writes <out>/carrier_placed.kicad_pcb."""
import pcbnew, re, json, sys, math
import numpy as np
from pcbnew import VECTOR2I_MM as P, FromMM, ToMM
sys.path.insert(0, "/home/claude/radio")
from fpinfo import crt

OUT = sys.argv[1]
PROJ = "radio_carrier"
NET = f"{OUT}/{PROJ}.net"
LIBDIR = "/usr/share/kicad/footprints"
OX, OY = 100.0, 50.0
W, L = 65.0, 95.0

net_txt = open(NET).read()
comps = dict(re.findall(r'\(comp \(ref "([^"]+)"\)\s*\(value "[^"]*"\)\s*\(footprint "([^"]+)"\)', net_txt))
values = dict(re.findall(r'\(comp \(ref "([^"]+)"\)\s*\(value "([^"]*)"\)', net_txt))
tstamp = {b[0]: b[2] for b in re.findall(r'\(comp \(ref "([^"]+)"\)(.*?)\(tstamps "([0-9a-f-]{36})"\)\)', net_txt, re.S)}
exp = json.load(open(f"{OUT}/expected_nets.json"))
pin_net = {}
for k, n in exp.items():
    r, p = k.split("."); pin_net.setdefault(r, {})[p] = n

# ------------------------------------------------------------------ fixed placement (x, y, rot)
J1X, J2X, TY = 24.88, 40.12, 5.0
FIXED_EXTRA0 = {"J1": (J1X, TY, 0), "J2": (J2X, TY, 0)}
FIXED_EXTRA = {
 "J3": (38.4, 71.2, 0),
 "J13": (8.6, 2.6, 0), "J14": (3.0, 18.0, 0),
 "U1": (32.5, 53.0, 90),
 "J12": (3.6, 52.0, 270),
 "U2": (13.5, 50.0, 0),
 "U4": (49.0, 47.0, 0),
 "U3": (44.5, 62.0, 0),
 "J10": (14.0, 91.6, 180), "J11": (51.0, 91.6, 180),
 "K1": (7.0, 75.0, 90), "Q1": (11.5, 74.0, 0),
 "K2": (58.0, 75.0, 90), "Q2": (53.5, 74.0, 0),
 "U5": (32.5, 76.0, 0), "Y1": (26.8, 73.5, 90),
 "J15": (57.0, 3.4, 180), "SW1": (46.6, 2.8, 180), "J16": (61.3, 15.0, 90),
 "U10": (55.5, 11.5, 0),
 # TPS61230 boost: inductor across the top (VIN right, SW left), input caps right, output caps left (TI layout)
 "U11": (52.0, 22.0, 0), "L1": (52.0, 17.3, 180),
 "C103": (55.7, 19.4, 0), "C104": (55.7, 17.0, 0),
 "C105": (48.4, 22.25, 180), "C106": (48.4, 24.45, 180), "C107": (48.4, 26.65, 180), "C109": (48.6, 28.6, 180),
 "U12": (49.0, 33.5, 0), "U13": (57.0, 33.0, 0), "U14": (57.0, 38.5, 0),
 "C111": (52.05, 33.5, 270), "C113": (52.7, 30.45, 0), "R131": (52.7, 35.95, 180),
 "H1": (3.2, 3.2, 0), "H2": (61.8, 49.0, 0), "H3": (3.2, 83.6, 0), "H4": (61.8, 83.6, 0),
}
FIXED = dict(FIXED_EXTRA0)
FIXED.update(FIXED_EXTRA)
# zones for the greedy placer (x0, y0, x1, y1); parts listed by group
ZONES = {
 "teensy": ((26.8, 3.5, 38.2, 39.5), ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10", "C1", "D1"]),
 "codec": ((21.5, 41.0, 44.0, 66.0), ["C10", "C11", "C12", "C13", "C14", "C15", "C16", "C17", "C18", "C19", "C20", "C21", "C22", "C23"]),
 "mic": ((7.0, 40.0, 24.5, 62.0), ["R20", "R21", "R22", "R23", "C24", "R24", "R25", "D2", "D3", "C25", "C26", "C27", "R26", "R27", "C28", "R28", "C29", "R81"]),
 "hp": ((40.0, 40.0, 63.5, 58.0), [f"R{b+i}" for b in (70, 75) for i in range(5)] + ["C60", "C61", "C62", "C63", "R80", "C65", "C66", "C67", "C68"]),
 "aux": ((7.0, 12.0, 24.5, 46.0), ["C70", "C71", "C72"] + [f"R{90+i}" for i in range(4)]),
 "auxdac": ((40.0, 50.0, 63.5, 68.0), ["R102", "R103"]),
 "usbA": ((10.0, 78.0, 29.0, 89.6), ["U8", "U6", "C90", "C91"]),
 "usbB": ((38.0, 78.0, 57.0, 89.6), ["U9", "U7", "C93", "C94"]),
 "txamp": ((35.5, 54.0, 55.0, 72.0), ['R35', 'R36', 'R37', 'R38', 'C33', 'C34', 'R55', 'R56', 'R57', 'R58', 'C43', 'C44']),
 "radioA": ((1.0, 60.0, 30.0, 89.0), [r for r in [f"R{30+i}" for i in range(15)] + [f"C{30+i}" for i in range(6)] + ["D10", "D11", "D12", "D13", "R45"] if r not in ['R35', 'R36', 'R37', 'R38', 'C33', 'C34', 'R55', 'R56', 'R57', 'R58', 'C43', 'C44']]),
 "radioB": ((36.0, 60.0, 64.0, 89.0), [r for r in [f"R{50+i}" for i in range(15)] + [f"C{40+i}" for i in range(6)] + ["D20", "D21", "D22", "D23", "R65", "C50", "C51"] if r not in ['R35', 'R36', 'R37', 'R38', 'C33', 'C34', 'R55', 'R56', 'R57', 'R58', 'C43', 'C44']]),
 "hub": ((22.0, 64.0, 43.0, 94.0), ["C80", "C81", "R110", "R111", "C82", "R112", "R113", "R114", "R115", "C83", "C84", "C85", "C86", "C87", "C88"]),
 "power": ((42.5, 0.5, 64.5, 29.5), ["U15", "Q3", "R120", "R121", "R134", "C119", "D30", "R122", "R123", "R124", "D31", "R125", "C100", "C101", "C102", "R126",
                                     "C108", "R127", "R128", "C120"]),
 "rails": ((42.5, 26.0, 64.5, 44.0), ["R129", "R130", "R132", "C110", "C112", "C114", "C115", "C116", "C117", "C118", "D32", "R133"]),
 "tp": ((1.0, 1.0, 64.0, 94.0), ["TP1", "TP2", "TP3", "TP4", "TP5", "TP6", "TP7", "TP8", "TP9", "TP10", "TP11", "TP12", "TP13", "TP14", "TP15", "TP16", "TP17"]),
}
# decoupling: cap -> pad it must hug
HUG = {"C10": "U1.49", "C11": "U1.3", "C12": "U1.14", "C13": "U1.34", "C14": "U1.46", "C15": "U1.12",
       "C16": "U1.49", "C17": "U1.34", "C18": "U1.46", "C19": "U1.1", "C20": "U1.15", "C21": "U1.59", "C22": "U1.60",
       "C25": "U2.13", "C26": "U2.7", "C65": "U4.2", "C66": "U4.4", "C67": "U4.2", "C68": "U4.4",
       "C50": "U3.8", "C51": "U3.4", "C83": "U5.20", "C84": "U5.20", "C85": "U5.21", "C86": "U5.13", "C87": "U5.12", "C88": "U5.28",
       "C90": "U6.5", "C93": "U7.5", "C100": "U10.13", "C101": "U10.10", "C102": "U10.2",
       "C108": "U11.6", "R127": "U11.7", "R128": "U11.7", "C120": "U11.7",
       "U8": "J10.7", "U9": "J11.7", "U6": "J10.9", "U7": "J11.9", "C91": "J10.9", "C94": "J11.9",
       "C110": "U12.3", "C115": "U13.1", "C116": "U13.5", "C119": "U15.12",
       "C117": "U14.1", "C114": "U12.6", "R133": "U12.3", "C118": "U14.5", "C1": "R10.1"}
TP_HUG = {"TP1": "R1.2", "TP2": "R2.2", "TP3": "R3.2", "TP4": "R4.2", "TP5": "R5.1", "TP6": "U1.4", "TP7": "C105.1", "TP8": "C118.1",
          "TP9": "C116.1", "TP10": "C113.1", "TP13": "C114.1", "TP14": "C101.1", "TP15": "C102.1", "TP16": "J1.1", "TP17": "U5.1",
          "TP11": "R42.1", "TP12": "R62.1"}
IGNORE_NETS = {"GND", "+5V2", "+3V3", "+5VP", "-5VP", "+5VA", "SYS", "VBAT", "VCOMAD"}

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
x, y, r = FIXED["U1"]; occ[int((y - 9.0) / GS):int((y + 9.0) / GS), int((x - 9.2) / GS):int((x + 9.2) / GS)] = 1
# routing channels kept clear
occ[int(38.8 / GS):int(41.5 / GS), int(26 / GS):int(39 / GS)] = 1     # Teensy -> codec bus
# hand-drawn power copper (TPS61230 loop) stays clear of other parts
exec(open("/home/claude/radio/power_zones.py").read())
for (_n, _poly) in LOCAL_ZONES:
    xs_ = [p[0] for p in _poly]; ys_ = [p[1] for p in _poly]
    occ[int(min(ys_) / GS):int(math.ceil(max(ys_) / GS)), int(min(xs_) / GS):int(math.ceil(max(xs_) / GS))] = 1
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
board.Save(f"{OUT}/carrier_placed.kicad_pcb")
json.dump({k: v for k, v in POS.items()}, open(f"{OUT}/placement.json", "w"), indent=0)
print("placed", len(POS))

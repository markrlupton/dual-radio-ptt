# erclite.py dir/proj : the power / driver part of KiCad's ERC, computed from the exported netlist + the schematic's power symbols
import re, sys, collections
d = sys.argv[1]; proj = d.rstrip("/").split("/")[-1]
net = open(f"{d}/{proj}.net").read(); sch = open(f"{d}/{proj}.kicad_sch").read()
nets = {}
for m in re.finditer(r'\(net \(code "\d+"\) \(name "([^"]*)"\)(.*?)\n\s*\)\)?(?=\s*\(net |\s*\)\s*\)\s*$)', net, re.S):
    pass
# simpler tokeniser: split on "(net (code"
for blk in net.split("(net (code")[1:]:
    name = re.search(r'\(name "([^"]*)"\)', blk).group(1)
    nodes = re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)(?: \(pinfunction "[^"]*"\))? \(pintype "([^"]+)"\)', blk)
    nets[name.lstrip("/")] = nodes
psyms = set(re.findall(r'\(symbol \(lib_id "lib:([^"]+)"\) \(at [^)]*\) \(unit 1\)', sch)) & set(re.findall(r'\(symbol "lib:([^"]+)" \(power\)', sch))
flags = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else set()
DRV = {"output", "bidirectional", "tri_state", "passive", "power_out", "open_collector", "open_emitter"}
err, warn = [], []
for n, nodes in sorted(nets.items()):
    T = collections.Counter(t.split("+")[0] for _, _, t in nodes)
    haspsym = n in psyms
    if n in flags and T["power_out"]: err.append(f"PWR_FLAG on a net already driven by power_out (power_out-power_out): {n}")
    if (T["power_in"] or haspsym) and not T["power_out"] and n not in flags:
        err.append(f"power input not driven: {n} ({T['power_in']} power_in pins{', power symbol' if haspsym else ''})")
    if T["input"] and not (set(T) & DRV) and n not in flags and not n.startswith("unconnected-"):
        err.append(f"input pin not driven: {n}")
    if T["output"] > 1: err.append(f"output-output conflict: {n}")
    if T["power_out"] > 1: err.append(f"power_out-power_out conflict: {n}")
    if T["output"] and T["power_out"]: err.append(f"output-power_out conflict: {n}")
    if T["output"] and T["open_collector"]: err.append(f"output-open_collector conflict: {n}")
    if len(nodes) == 1 and not n.startswith("unconnected"): warn.append(f"single-pin net: {n} ({nodes[0][0]}.{nodes[0][1]})")
print(f"{proj}: {len(nets)} nets, power symbols on {len(psyms)} nets, PWR_FLAG on {sorted(flags)}")
for e in err: print("  ERROR", e)
for w in warn: print("  warn ", w)
print(f"  {len(err)} errors, {len(warn)} warnings")

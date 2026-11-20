"""relink.py <sch> <pcb>: set each PCB footprint's (path "/<uuid>") to its schematic symbol's uuid, matched by
reference, so KiCad's Update-PCB-from-Schematic sees one linked design (no 'relink by reference' needed)."""
import re, sys
sch = open(sys.argv[1]).read(); pcb = open(sys.argv[2]).read()
ref2u = {}
for m in re.finditer(r'^\(symbol \(lib_id "[^"]+"\)[^\n]*\(uuid ([0-9a-f-]+)\)\n  \(property "Reference" "([^"]+)"', sch, re.M):
    if not m.group(2).startswith("#"): ref2u[m.group(2)] = m.group(1)
out, n, miss = [], 0, []
pos = 0
for m in re.finditer(r'\(footprint "[^"]+"', pcb):
    i = m.start(); j = pcb.find("(fp_text reference", i); k = pcb.find("(footprint ", i + 10)
    ref = re.match(r'\(fp_text reference "([^"]+)"', pcb[j:]).group(1)
    pm = re.compile(r'\(path "/[0-9a-f-]+"\)').search(pcb, i, j)
    if ref in ref2u and pm:
        out.append(pcb[pos:pm.start()] + f'(path "/{ref2u[ref]}")'); pos = pm.end(); n += 1
    else: miss.append(ref)
out.append(pcb[pos:]); open(sys.argv[2], "w").write("".join(out))
print(f"relinked {n}; not in schematic: {miss}")

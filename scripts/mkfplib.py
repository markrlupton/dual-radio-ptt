"""mkfplib.py <board_dir> <pcb>... : build <board_dir>/radio.pretty from the footprints the boards use,
write fp-lib-table, and repoint every footprint FPID in the given .kicad_pcb files to radio:<name>.
Footprints are copied from the KiCad stock library this design was laid out against, so pad geometry is
identical to what is on the board (checked below), and the project no longer depends on the installed
library version (KiCad 8/9/10 renamed or revised several of these)."""
import re, sys, os, shutil
STOCK = "/usr/share/kicad/footprints"
d = sys.argv[1]; pcbs = sys.argv[2:]
os.makedirs(f"{d}/radio.pretty", exist_ok=True)
ids = set()
for p in pcbs: ids |= set(re.findall(r'\(footprint "([^":]+:[^"]+)"', open(p).read()))
names = {}
for fid in sorted(ids):
    lib, name = fid.split(":")
    if lib == "radio": continue
    assert name not in names or names[name] == lib, f"name clash {name}"
    names[name] = lib
    shutil.copy(f"{STOCK}/{lib}.pretty/{name}.kicad_mod", f"{d}/radio.pretty/{name}.kicad_mod")
open(f"{d}/fp-lib-table", "w").write('(fp_lib_table\n  (lib (name "radio")(type "KiCad")(uri "${KIPRJMOD}/radio.pretty")(options "")(descr "Project footprints (rev C.2): every footprint used on this board"))\n)\n')
pad = re.compile(r'\(pad "?(\w*)"? (\w+) (\w+) \(at ([-\d.]+) ([-\d.]+)(?: [-\d.]+)?\) \(size ([\d.]+) ([\d.]+)\)')
def block(s, i):
    n = 0
    for j in range(i, len(s)):
        if s[j] == "(": n += 1
        elif s[j] == ")":
            n -= 1
            if n == 0: return s[i:j + 1]
for p in pcbs:
    s = open(p).read()
    # geometry check: every placed footprint's pads equal the library copy's pads (pad-local coordinates)
    for m in re.finditer(r'\(footprint "([^":]+):([^"]+)"', s):
        lib, name = m.group(1), m.group(2)
        if lib == "radio": continue
        b = block(s, m.start())
        libpads = sorted(set(pad.findall(open(f"{d}/radio.pretty/{name}.kicad_mod").read())))
        brdpads = sorted(set(pad.findall(b)))
        # board pads carry footprint rotation in the (at) angle only; x/y are local, so they must match
        assert brdpads == libpads, (p, name, set(brdpads) ^ set(libpads))
    s = re.sub(r'\(footprint "[^":]+:([^"]+)"', r'(footprint "radio:\1"', s)
    open(p, "w").write(s)
print(len(names), "footprints ->", f"{d}/radio.pretty")

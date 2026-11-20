# Dual-Radio PTT Audio Board (Teensy 4.0): rev C.2

A carrier for a Teensy 4.0 that bridges a headset to two tactical radios. A front-panel daughterboard carries four encoders, the PTT buttons and the LEDs.

Rev C.2 is the manufacturing close-out after the fourth outside review (of rev C.1). That review found no new electrical problem, so **the copper and the circuit are unchanged from C.1** apart from the courtyard fix. This revision covers parts selection, the project footprint library and the fab and assembly files. The full spec is at https://claude.ai/artifact/69VW2KktqLnx2tKRjk1YQv ; its "Rev C", "Rev C.1" and "Rev C.2" sections list every change.

| Board | Size | Stack | Parts | Status |
|---|---|---|---|---|
| `radio_carrier` | 65 × 95 mm | F sig + GND / In1 solid GND / In2 +5.2 V plane (low-current rails and a few codec-area signals) / B sig + GND | 240 | Fully routed. DRC (KiCad 7.0.11): **0 copper, 0 courtyard, 0 unconnected, 0 footprint/library** issues. Only silkscreen warnings are left (silk clipped by mask or overlapping, which JLC clips anyway). ERC: 0 errors, 0 warnings. |
| `radio_frontpanel` | 124 × 38 mm | 4 layers (both inner layers GND) | 54 | Layout unchanged from rev B. DRC: same result as the carrier (silkscreen warnings only). ERC: 0 errors, 0 warnings. |

Vias are 0.45 mm with a 0.2 mm drill on the carrier and 0.5 / 0.25 mm on the front panel. Order the carrier with the **JLC04161H-7628** stack-up and **impedance control** (see below).

## What changed in rev C.2 (fourth review)
| Review item | Rev C.2 |
|---|---|
| **LCSC selections must keep the specified tolerances** (selecting by value and package alone is not enough) | Every SMT row on both boards now has a specific MPN **and** LCSC number, chosen together, in the schematic (`MPN` and `LCSC` fields), both BOMs and the JLC BOM. Precision parts: **15 kΩ 0.1 % 25 ppm** Yageo RT0603BRD0715KL **C326733**; **11 kΩ 0.1 % 25 ppm** FH TD03G1102BT **C667038** (alt Yageo RT0603BRD0711KL); 20 kΩ / 4.99 kΩ 0.1 % unchanged (C723637 / C723532). Rev C.1's note that LCSC lacked 0.1 % 15 k / 11 k was wrong. The JLC BOM's Comment column is now the MPN, so JLC matches on part number, not value. See the selection table below. |
| **A real dielectric error turned up** | The generic 1 nF entry pointed at **C21122, an X7R part**, while C24, C32–C34 and C42–C44 are specified C0G (mic and ADC RF filters, TX low-pass). They are now FH 0603CG102J500NT **C1636** (C0G 50 V 5 %). The generator now refuses to emit a C0G capacitor without a C0G part selected, so this can't recur. |
| **Five power-stage courtyard overlaps** | Fixed: C103 / C104 moved 0.45 mm and C105 / C106 0.3 mm with their tracks. DRC now reports no courtyard overlaps. Switching-loop geometry is effectively unchanged. |
| **Footprint-library warning (codec footprint)** | Every footprint on both boards is now in a **project library** `radio.pretty` with its own `fp-lib-table`. That is 33 footprints on the carrier and 10 on the front panel, U1's HTQFP-64 thermal-via footprint included. All FPIDs in the PCB and all schematic `Footprint` fields point to `radio:<name>`. The library copies were checked pad-for-pad against what is placed on the boards (`mkfplib.py` asserts it). The project no longer depends on the installed KiCad library version; KiCad 8–10 renamed or revised several of these footprints. 3D models still reference the KiCad stock model path, which affects only the 3D view. |
| PCB ↔ schematic link | The PCB footprints now carry their schematic symbols' UUIDs (`relink.py`), so Update-PCB-from-Schematic sees a linked design without "re-link by reference". |
| **Controlled impedance** | Confirmed what we can confirm here: all three pairs are 0.30 mm / 0.20 mm gap on F.Cu only, no vias, over solid In1 GND. Lengths 39.9 / 39.7, 41.5 / 41.3 and 13.5 / 10.1 mm. Computed **89.3 Ω differential with mask** (εr 4.4), 95.9 Ω bare. **Order "Impedance control: yes" with JLC04161H-7628** and put in the order remark: *USB D+/D− pairs (nets USB_A_*, USB_B_*, USBH_*): 90 Ω ±10 % differential, L1 referenced to L2, 0.30 mm trace / 0.20 mm gap.* JLC may adjust width by a few µm to hit target; accept that. Only JLC's coupon measurement confirms the number. |
| **Host cable arrangement** | Stated explicitly under "Things you must do" (item 2) with J3's pinout. The pigtail is the one uncontrolled-impedance section of the high-speed path. |
| **Fab and assembly review** | Gerbers (4 Cu, paste, mask, silk, edge), separate PTH / NPTH Excellon and the job file were regenerated from the C.2 boards. **CPL rotations:** the JLC corrections for KiCad stock footprints are applied: SOT-23/-5/-6 +180°, SOIC / SOP / TSSOP +270°, VQFN-16 +270°. **`*_rotation_check.csv` lists every polarized part** with its KiCad angle, offset, final CPL angle and what to look at for pin 1. Packages the table doesn't cover are left at KiCad's angle and flagged: U1 HTQFP-64, U4 / U11 PVSON-10, U5 SSOP-28, U12 WSON-12, U15 X2QFN-12, Y1, the LEDs, the SOD diodes, J10–J12, J15, SW1. **Check every flagged part in JLC's placement preview before releasing the order**; their preview is the authority because it uses their own footprint for each LCSC part. All parts are top-side. |
| Substitutions | Leave JLC's automatic substitution off. If a part goes out of stock, pick a replacement from the alternates in the MPN field or one of the same tolerance / TCR / dielectric. Never substitute a 0.1 % resistor with a 1 % one, or a C0G with an X7R. |

### Parts chosen in rev C.2 (previously unselected or generic)
| Ref | Value / spec | MPN | LCSC |
|---|---|---|---|
| R70 R72 R75 R77 | 15 kΩ 0.1 % 25 ppm | Yageo RT0603BRD0715KL | C326733 |
| R71 R73 R76 R78 | 11 kΩ 0.1 % 25 ppm | FH TD03G1102BT (alt Yageo RT0603BRD0711KL) | C667038 |
| R116 R117 | 45.3 kΩ 1 % (current limit) | Viking ARG03FTC4532 (thin film, 25 ppm; alt Bourns CR0603-FX-4532ELF C49675646) | C218038 |
| R24 | 169 Ω 1 % (INA217 gain) | Panasonic ERJ-3EKF1690V | C403019 |
| R120 | 910 kΩ 1 % (TUSB321 VBUS_DET) | Bourns CR0603-FX-9103ELF (alt RESI AECR0603F910KK9 C352285) | C203887 |
| R122 | 1.24 kΩ 1 % (BQ24074 ILIM) | Vishay CRCW06031K24FKEA (alt FH RS-03K1241FT C321702) | C843923 |
| R127 | 422 kΩ 1 % (boost FB) | RALEC RTT034223FTP | C103627 |
| R129 | 294 kΩ 1 % (charge-pump FB+) | RALEC RTT032943FTP (alt Vishay CRCW0603294KFKEA C2092132) | C13177 |
| R131 | 287 kΩ 1 % (charge-pump FB−) | LIZ CR0603FA2873G | C100934 |
| C24 C32–C34 C42–C44 | 1 nF C0G | FH 0603CG102J500NT (alt Samsung CL10C102JB8NNNC C163508) | C1636 |
| C29 | 2.7 nF C0G | Walsin 0603N272J500CT | C388043 |
| C60–C63 | 330 pF C0G | Samsung CL10C331JB8NNNC | C1664 |
| C120 | 18 pF C0G | Samsung CL10C180JB8NNNC | C1647 |
| C80 C81 (DNP) | 10 pF C0G | Samsung CL10C100JB8NNNC | C1634 |
| Y1 | 12 MHz 3225, 20 pF, ±10 ppm | YXC X322512MSB4SI | C9002 |
| Front panel D3 | amber / orange 0805 | NationStar NCD0805O1 (605 nm) | C84262 |
| J10 J11 / J12 | JST GH 10 / 6 | BM10B-GHS-TBT / BM06B-GHS-TBT | C2983879 / C189892 |
| J15, SW1, ENC1–4 | USB-C, slide switch, encoders | GCT USB4125-GF-A-0190, C&K PCM12SMTR, Bourns PEC12R-4217F-S0024 | C5246813, C221841, C49671241 |

Rows still without an LCSC number are hand-soldered commodity mechanicals: 1×14 sockets, 1×3 / 2×8 headers, Micro-Fit 43650-0315 and the tactile switches. They are in the JLC BOM so you can mark them DNP. Stock moves; re-check availability in JLC's BOM tool when you order.

## What changed in rev C.1 (third review)
| Review item | Rev C.1 |
|---|---|
| **Battery current path had a 0.2 mm via and a 0.15 mm section feeding U10's BAT pins** | U10 (BQ24074) is turned 180° so its BAT pins face J16 and its OUT pins face the boost stage. **Both high-current paths are now single F.Cu copper pours with no vias:** J16 pin 1 → U10 BAT (narrowest about 1.55 mm along the run, about 1.05 mm only where the copper meets the 0.5 mm-pitch QFN pins) and U10 OUT → L1 / C103 / C104 / U11 VIN (narrowest about 1.1 mm, about 0.95 mm at the pin row). Other nets are kept out of both pours by the router, and no via of any net may sit within about 0.5 mm of their edges. C102 (battery cap) now sits on the battery pour under J16; C100 (IN cap) sits right under U10's IN pin; C101 moved near SW1. |
| USB-C input path | VBUS_IN (≤1.3 A) runs 0.5 mm (one 0.25 mm neck at the A9 pin between the CC pins). Each layer change uses two vias in parallel: two 0.6/0.3 mm vias going down, one 0.6/0.3 mm plus one 0.5/0.25 mm via coming up at U10's IN pin. Power-net vias are 0.6/0.3 mm wherever they fit. |
| **J16 pin 2 (battery −) thermal relief: 1 spoke where 2 are required** | J16, U10, C101 and C102 ground pads now connect solidly to the pours (no thermal relief). |
| **Current limit did not guarantee 500 mA with a 1 % resistor** | R116 / R117 → **45.3 kΩ 1 %**. TI's equations with the resistor tolerance included give **0.519 A minimum (R +1 %)** and **0.644 A maximum (R −1 %)** per port. 47.5 kΩ gave 0.494–0.616 A. |
| Host USB pair had 0.15 mm segments | Those were pad-entry stubs inside J3's 1.7 mm pads; they are now 0.30 mm like the rest of the pair. The pair's breakout into J3 is still uncoupled over the 2.54 mm pin pitch. |
| **"About 93 Ω under mask" was not what the solver modelled** | `zdiff.py --mask` now models the solder mask with JLCPCB's figures (1.2 mil on laminate and between traces, 0.6 mil on copper, εr 3.8) and 1.6 mil finished outer copper. 0.30 / 0.20 mm on the 0.2104 mm 7628 prepreg: **95.9 Ω bare, 89.3 Ω with mask** (εr 4.4), 94.3 / 87.9 Ω at εr 4.6. Rectangular trace cross-section; trapezoidal etching raises it slightly. Have JLC confirm with impedance control ordered. |
| **ERC not clean** | KiCad's own ERC (7.0.11, run in the schematic editor) now reports **0 errors and 0 warnings on both boards**. Fixes: PWR_FLAGs only on nets nothing else drives (GND, VBUS_IN, +5V_TEENSY), U11's second VOUT pin made passive, LM27762 PGOOD tied to GND as its datasheet says for unused (pin typed passive), PCM3168A pin 44 typed as the input it is in I²C mode, no stray no-connect flags, a project symbol library (`lib.kicad_sym` + `sym-lib-table`) so no library warnings. Reports: `*-erc.rpt`. Newer KiCad versions add checks; I could not run KiCad 10 here. |
| LCSC numbers | Added: TPS61230DRCR C139626, NCP163ASN500T1G C603657, TUSB321RWBR C139392, PESD5V0L1BA C85380, SMF15CA C2890424, L1 → XAL4020-102MEC C4555951 (current version of the -MEB), RT0603BRD0720KL C723637, RT0603BRD074K99L C723532. |

## What changed from rev B (rev C)
| Review item | Rev C |
|---|---|
| **U6 / U7 enable polarity wrong** (TPS2051B is active-high; the hub's PWRJ is active-low) | Replaced with **TPS2552DBVR**: active-low EN, open-drain FAULT, adjustable current limit. EN ← HUB_PWRJ, FAULT → HUB_OVC (wired-OR). |
| Port current limit 0.75–1.25 A per port (TPS2051B) | R116 / R117 on ILIM set the limit (rev C.1: 45.3 kΩ, **0.519–0.644 A per port** including the 1 % tolerance). Two shorted ports can't pull more than about 1.3 A from +5V2. |
| **J16 JST-PH (2 A) on a 2.6 A battery path** | **Molex Micro-Fit 3.0 43650-0315** vertical (5 A per contact): 1 +, 2 −, 3 NTC. Mating housing 43645-0300 with 43030 crimps. |
| Battery / SYS copper | Superseded in rev C.1 by the battery and SYS pours above. |
| **USB pairs not coupled / not single-layer** | All three pairs re-routed **on F.Cu only, no vias, one width**: 0.30 mm traces, 0.20 mm gap (0.50 mm pitch) over the solid In1 GND, routed as a true pair (one centreline, both conductors offset from it). Impedance: see the rev C.1 table (89 Ω with mask modelled, target 90 Ω). Measured lengths: radio A 39.9 / 39.7 mm, radio B 41.5 / 41.3 mm (0.2 mm skew); host link 13.5 / 10.1 mm (set by J3's 2.54 mm pin spacing). |
| Pair topology | To route both radio pairs without crossing, the hub ports were swapped (radio A now on FE1.1s port 2, pins 8 / 9; radio B on port 1, pins 10 / 11) and U8 / U9 were turned 180° so each pair flows straight through its USBLC6 (pins 1→6 and 3→4) before dropping into the connector. The ESD ground pin gets its own via under the part. |
| Continuous load vs. 1.3 A USB input | Operating-mode table below. At full load on USB the battery supplements; this is intentional and stated. |
| PTT TVS (SMF15CA, 15 V standoff) | Maximum radio PTT keying voltage is now a stated limit: **≤ 15 V open-circuit**. |
| Port power cycling | Documented: the hub's power switching is ganged, so a power-cycle drops **both** radio ports. |

## Operating modes and power budget
Loads at the +5.2 V boost output: board ≈ 350 mA (1.8 W); each radio port 0–500 mA nominal, current-limited at 0.519 A min / 0.644 A max.

| Mode | Input available | Full load (board + 2 × 500 mA ≈ 7 W out, ≈ 7.8 W in) | Board only (≈ 2 W in) |
|---|---|---|---|
| Battery only | 18650, 3.0–4.2 V | ≈ 2.2 A from the cell at 3.6 V, ≈ 2.6 A at 3.0 V. Use a cell rated ≥ 5 A continuous. | ≈ 0.6 A from the cell |
| USB-C, source offers ≥ 1.5 A (TUSB321 → 1.3 A input limit) | ≈ 6 W | Input covers most of it; the battery supplies the rest (BQ24074 supplement mode). The cell slowly discharges. | Fully covered; battery charges |
| USB-C, default 500 mA source | ≈ 2.5 W | Battery supplies ≈ 5 W; net discharge | Covered, little or no charge current |
| Fault: both ports shorted | — | ≤ 2 × 0.644 A ≈ 6.7 W + board ≈ 8.5 W out, ≈ 9.7 W in → ≤ 3.2 A from the cell at 3.0 V (2.7 A at 3.6 V). Within the TPS61230 (4 A valley), BQ24074 battery FET (4.5 A) and Micro-Fit (5 A) ratings, and carried by the no-via battery/SYS pours. The TPS2552s thermally cycle into a hard short and report FAULT to the hub. | — |

**Without a battery fitted, full radio-port load on USB alone is not supported.**

## Things you must do
1. **Cut the Teensy VUSB–VIN pad.**
2. **USB host pigtail (J3).** J3 pin 1 = D+ (USBH_DP), pin 2 = D− (USBH_DM), pin 3 = GND. Wire the Teensy 4.0's underside USB-host D+ / D− pads to J3 pins 1 / 2, and a Teensy GND pin to J3 pin 3. Use a twisted pair (about 1 twist per cm, **60 mm or less**, 28–30 AWG), with the GND wire twisted along with it or run right beside it. This hop carries the hub's high-speed upstream link (480 Mb/s). It is the only part of that path without controlled impedance, so keep it as short as the stack-up allows and don't route it past the boost inductor L1. If the hub shows enumeration errors, shorten the pigtail first.
3. **Firmware is not written yet.** Everything below is a requirement on firmware you still need to write:
   - Codec rate: set PCM3168A **SRAD = SRDA = 01 (single rate)**; auto mode reads 256 fs MCLK as dual rate. Set FMTAD / FMTDA to match the Teensy's TDM slot layout.
   - PTT safety: watchdog, transmit timeout, release PTT if I²C to the buttons stalls. The gate pull-downs only cover reset.
   - Headphone mute: HP_EN high only after the codec and rails are running; low before shutdown.
   - Port power: a stuck radio is recovered by the USB host toggling hub port power, which cycles both ports together.
4. **Battery.** Protected 18650 with a 10 kΩ NTC on J16 pin 3 (or fit R124, which disables temperature protection).
5. **Radios.** PTT line must be ≤ 15 V open-circuit and switched to ground. RX ≤ 2 Vrms differential line level (fit R34 / R54 for speaker level). TX is mic level; R40 / R60 (100 Ω) set the drive level and may need changing per radio. Compatibility with a specific radio is conditional on these until checked against its pinout.

## Codec channel map (TDM slots)
| Channel | Use |
|---|---|
| ADC1 | Aux in (J14 pins 9 / 10) |
| ADC2, ADC6 | Unused (terminated) |
| ADC3 | Headset mic (INA217, G ≈ 60) |
| ADC4 / ADC5 | Radio A / Radio B RX |
| DAC1 / DAC2 | Headset L / R (OPA1622) |
| DAC3 / DAC4 | Radio A / Radio B TX (OPA1678) |
| DAC5 | Aux out (J14 pins 13 / 14) |

## Teensy 4.0 pin map
| Pin | Signal | | Pin | Signal |
|---|---|---|---|---|
| 0 | EXP_0 (aux) | | 23 | MCLK |
| 1 | EXP_1 (aux) | | 22 | VBAT_SENSE (A8, ½ divider) |
| 2 | PTT_A drive | | 21 | BCLK |
| 3 | PTT_B drive | | 20 | FSYNC |
| 4 | IOX_INT (TCA9555) | | 19 / 18 | I²C SCL / SDA |
| 5 | CODEC_RST | | 17 / 16 | ENC Radio-A channel B / A |
| 6 | HP_EN | | 15 / 14 | ENC Radio-A volume B / A |
| 7 / 8 | TDM TX / RX | | 13 | EXP_13 (aux) |
| 9 / 10 | ENC Radio-B volume A / B | | VIN | +5 V via B5819W |
| 11 / 12 | ENC Radio-B channel A / B | | 3V3 | not used |

## Connectors
| Ref | Part | Pins |
|---|---|---|
| J10 / J11 | JST-GH 10 | 1 RX, 2 RX_RTN, 3 TX, 4 TX_RTN, 5 PTT (≤ 15 V), 6 PTT_RTN, 7 D+, 8 D−, 9 VBUS (switched, 0.519–0.644 A limit), 10 GND |
| J12 | JST-GH 6 | 1 MIC+, 2 MIC−, 3 SPK_L, 4 SPK_R, 5 GND, 6 shield |
| J13 | 2×8 1.27 mm | front-panel ribbon |
| J14 | 2×8 2.54 mm aux | +3V3, +5V2, EXP_0/1/13, ADC1±, DAC5±, GND |
| J15 | USB-C | power in (TUSB321 detects the source's current) |
| J16 | Molex Micro-Fit 3.0 43650-0315 | 1 +, 2 −, 3 NTC |
| J3 | 1×3 | USB host D+, D−, GND pigtail |

## Known limits
- **Ground isolation:** none. The radio ports share ground through J10 / J11 pin 10 and USB.
- **CPL rotations** for packages not in the standard correction table are KiCad's own angle; confirm them in JLC's placement preview (`*_rotation_check.csv`).
- **Moved parts:** C80 (DNP crystal load cap) moved 5 mm from the crystal to clear the USB corridor. Leave it unfitted (the FE1.1s has internal load capacitors). C94 (radio B VBUS bulk) moved next to U7.
- **USB impedance:** computed, not measured. Order impedance control and let JLC confirm.
- **Charge-status LED feed:** R125's VBUS_IN branch and the battery-voltage sense branch (VBAT to R9 / TP15) are thin tracks with single vias; they carry milliamps.

## Files
- `radio_carrier/` and `radio_frontpanel/`: KiCad 7 projects (open with KiCad 7 or newer) with their project symbol library (`lib.kicad_sym`, `sym-lib-table`), project footprint library (`radio.pretty`, `fp-lib-table`), and ERC / DRC reports.
- `*/fab/`: Gerbers and drill (zip), `*_BOM_JLC.csv`, `*_CPL_JLC.csv` (JLC rotation corrections applied), `*_rotation_check.csv`, `*_BOM_full.csv` (MPN, LCSC, fitted, SMT / hand-solder), schematic PDF.
- `img/`: renders.
- `scripts/`: generators, router and finishing scripts, `zdiff.py` impedance solver (`--mask`), `pourcheck.py` (narrowest copper on the power paths), `erc_gui.sh` (runs KiCad's ERC headless), `mkfplib.py` (builds the project footprint library and checks it against the boards), `relink.py` (PCB ↔ schematic UUID link).
- `img/carrier_power_paths.png`, `img/carrier_usb_pairs.png`: the power pours and the USB pairs.

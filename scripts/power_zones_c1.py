# F.Cu power copper (board-local mm). Shared by router (keep-out for other nets) and finish (zones).
# rev C.1: U10 turned 180 deg so the battery and SYS paths are each one same-layer pour with no vias.
LOCAL_ZONES = [
 ("BB_SW", [(49.95, 15.5), (51.45, 15.5), (51.45, 20.5), (50.6, 21.75), (49.95, 21.75)]),
 # SYS: U10 OUT pins 10/11 -> left corridor -> L1.1 / C104 / C103 / U11 VIN
 ("SYS",   [(50.6, 11.0), (54.55, 11.0), (54.55, 11.95), (52.6, 11.95), (52.6, 15.4), (55.3, 15.4), (55.3, 20.3), (54.15, 20.3),
            (54.15, 21.25), (52.95, 21.25), (52.95, 20.3), (51.7, 20.3), (51.7, 15.1), (50.6, 14.6)], 6),
 # VBAT: J16 pin 1 -> corridor beside the connector pins -> U10 BAT pins 2/3, and down to C102
 ("VBAT",  [(56.6, 11.0), (61.75, 11.0), (61.75, 19.4), (61.05, 20.1), (61.05, 23.3), (59.8, 23.3), (59.8, 19.3), (57.95, 19.3), (57.95, 13.95), (58.4, 13.5),
            (58.4, 12.0), (56.6, 12.0)], 6),
 ("+5V2",  [(48.85, 21.8), (50.5, 21.8), (50.5, 22.7), (49.85, 22.7), (49.85, 29.4), (48.85, 29.4)]),
]

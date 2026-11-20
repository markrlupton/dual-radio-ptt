import numpy as np
OUTD = "/home/claude/radio/out_revc/radio_frontpanel"
BOARD = OUTD + "/fp_placed.kicad_pcb"
OUTJSON = OUTD + "/routes.json"
W, L, OX, OY = 124.0, 38.0, 100.0, 50.0
WIDTH = {"+3V3": 0.3}
def cost(n, l, X, Y): return np.ones(X.shape, np.float32)
ORDER_FIRST = ["+3V3"]
ATTEMPTS = 4
SILK = [("DUAL-RADIO PTT FRONT PANEL rev C", 70, 36.6, 1.0)]

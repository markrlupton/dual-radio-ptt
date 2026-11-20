import numpy as np
OUTD = "/home/claude/radio/out_revc1/radio_carrier"
BOARD = OUTD + "/carrier_placed.kicad_pcb"
OUTJSON = OUTD + "/routes.json"
W, L, OX, OY = 65.0, 95.0, 100.0, 50.0
WIDTH = {}
WIDTH["SYS"] = 0.5; WIDTH["VBAT"] = 0.5   # main current carried by the LOCAL_ZONES pours
WIDTH["BB_SW"] = 0.5
WIDTH["VBUS_IN"] = 0.5
for n in ["USBH_DP", "USBH_DM", "USB_A_DP", "USB_A_DM", "USB_B_DP", "USB_B_DM"]: WIDTH[n] = 0.3
HALVES = (0.075, 0.15, 0.25, 0.4, 0.45)
PAIRS = [("USBH_DP", "USBH_DM"), ("USB_A_DM", "USB_A_DP"), ("USB_B_DP", "USB_B_DM")]
PAIR_PITCH = 0.5
GUIDE_K = 4.0
WIDTH["+5V2"] = 0.3
INNER2 = "+5V2"
for n in ["+5V_TEENSY", "+3V3", "+5VA", "+5VP", "-5VP", "RA_VBUS", "RB_VBUS", "CP_C1P", "CP_C1N", "CP_OUT", "HUB_3V3", "HUB_1V8", "PWR_EN"]: WIDTH[n] = 0.3
MIC = {"HS_MIC_P", "HS_MIC_N", "MIC_P_F", "MIC_N_F", "INA_RG1", "INA_RG2", "MIC_PRE", "ADC3_P", "ADC3_N", "+5VP", "-5VP", "HS_SHLD", "VCOMAD"}
SOFT = {"HS_SPK_L", "HS_SPK_R", "ADC1_P", "ADC1_N", "ADC2", "ADC4_P", "ADC4_N", "ADC5_P", "ADC5_N", "ADC6"}
def fast(n):
    return n.startswith(("TDM_", "I2C_", "USB", "HUB_X", "BB_", "CP_C1", "ENC_", "IOX", "EXP_", "PTT_", "CODEC_RST"))
def analog(n):
    return n.startswith(("ADC", "DAC", "AUX_", "RA_RX", "RB_RX", "RA_TX", "RB_TX", "HP", "HS_", "MIC", "INA", "VCOM", "VREF"))
def cost(n, l, X, Y):
    c = np.ones(X.shape, np.float32)
    mic = (X < 21.5) & (Y > 41) & (Y < 61)
    if n not in MIC:
        c[mic] += 2.0 if n in SOFT else 10.0
    if fast(n):
        c[mic] += 10.0
        if l == 0: c[(X < 46) & (Y > 40) & (Y < 68)] += 3.0
    if analog(n) and l == 1: c += 1.5
    if n in POWER and l in (0, 1): c += 2.0
    if n.startswith("USB"):
        c[(X < 47.5) & (Y > 40) & (Y < 68)] += 15.0       # keep the pairs out of the codec's escape area
    if n.startswith("USB") and l == 1: c += 3.0      # keep USB pairs on F.Cu over the solid GND layer
    if l == 2:
        if n in POWER: c[:] = 1.0
        else:
            box = ((X > 20) & (X < 46) & (Y > 41) & (Y < 69)) | ((X > 35) & (X < 56) & (Y > 54) & (Y < 72))   # under the codec the +5V2 plane is voided: local 3rd signal layer
            c[:] = np.where(box, 1.5, 300.0)
            if n.startswith("CHG_"): c[(X > 52) & (X < 64.5) & (Y > 8) & (Y < 30)] = 4.0   # charger program/status lines may dip to In2 locally
    return c
NLAYERS = 3
POWER = {"+5V2", "+3V3", "+5VA", "+5VP", "-5VP", "+5V_TEENSY", "RA_VBUS", "RB_VBUS", "HUB_3V3", "VCOMAD", "VCOMDA", "VREFAD1", "VREFAD2"}
F_ONLY = {"BB_SW"}
def layers(n): return (0, 1) if n in ("VBUS_IN", "SYS", "VBAT") else (0,) if n in F_ONLY else (0,) if n.startswith("USB") else (0, 1, 2)
exec(open("/home/claude/radio/power_zones_c1.py").read())
ORDER_FIRST = ["VBUS_IN", "VBAT", "SYS", "BB_SW", "SYS", "PWR_EN", "BB_FB", "BB_SS", "VBAT", "VBUS_IN", "CP_C1P", "CP_C1N", "MIC_P_F", "MIC_N_F", "INA_RG1", "INA_RG2", "HS_MIC_P", "HS_MIC_N", "MIC_PRE", "MIC_AC", "ADC3_P", "ADC3_N", "USBH_DP", "USBH_DM", "USB_A_DP", "USB_A_DM", "USB_B_DP", "USB_B_DM"]
ATTEMPTS = 2
RESUME = True

FANOUT_LAST = False
STITCH_FINE = (2.0, 41.0, 21.5, 61.0)
SILK = [("DUAL-RADIO PTT CARRIER rev C", 32.5, 44.0, 1.2), ("Teensy 4.0 - USB this end", 32.5, 2.5, 1.0), ("RADIO A", 14.0, 86.5, 1.2), ("RADIO B", 51.0, 86.5, 1.2), ("HEADSET", 6.0, 44.0, 1.0), ("FRONT PANEL", 9.0, 14.5, 1.0), ("AUX", 5.0, 39.5, 1.0), ("CUT TEENSY VUSB-VIN PAD", 32.5, 62.0, 1.0)]

ESCAPE = {"U1": (1.3, 2.1)}
VIA = (0.45, 0.2)
PAIR_P_CLASSES = [0.45, 0.25, 0.15]
GND_FULL = ("U10", "J16", "C102", "C101")
BIG_VIA = (0.6, 0.3)
BIG_VIA_NETS = ("VBUS_IN", "VBAT", "SYS", "+5V2", "RA_VBUS", "RB_VBUS", "BB_SW")
MID_VIA = (0.5, 0.25)

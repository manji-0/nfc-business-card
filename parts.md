# Locked BOM — NFC Business Card

Verified 2026-07-14 against LCSC / JLCPCB Parts Library.

## NFC IC (required)

| Field | Value |
|-------|-------|
| MFR | NXP |
| MPN | **NT3H2111W0FHKH** |
| LCSC / JLCPCB | **C710403** |
| Package | XQFN-8 (1.6 × 1.6 mm), SOT902-3 |
| Type | NFC Forum **Type 2** Tag (NTAG I²C plus, 1 kB) |
| Cin | 50 pF |
| Assembly | JLCPCB SMT (Extended), Economic & Standard |
| LCSC stock (check) | ~10,000+ at lock time |

### Why this part

- Type 2 NDEF → iPhone background URL open works well
- Rewritable from NFC Tools / Core NFC (do not OTP-lock)
- Real SMT package (not wafer / MOA8)
- In stock and listed for JLCPCB assembly

### Pin use (NFC-only business card)

| Pin | Symbol | Connection |
|-----|--------|------------|
| 1 | LA | Antenna |
| 2 | VSS | Local GND island left of U1 (component strip only; no copper under antenna) |
| 3 | SCL | NC (test pad optional) |
| 4 | FD | NC (test pad optional) |
| 5 | SDA | NC (test pad optional) |
| 6 | VCC | NC (passive RF-powered) |
| 7 | VOUT | NC |
| 8 | LB | Antenna |
| EP | center | **Do not solder** (per datasheet) |

## Tuning capacitor (DNP — pads only)

| Field | Value |
|-------|-------|
| Ref | C1 |
| Footprint | C_0402_1005Metric |
| Default | **Do Not Place** |
| Candidate if needed | **10–18 pF** NP0/C0G 0402 only (never X7R). See table below. |
| Notes | Parallel across LA–LB. With L≈1.9 µH, Cin=50 pF alone is ~16 MHz; C1 pulls toward 13.56–14.5 MHz. Populate only after first-article phone tests. Run `scripts/tune_antenna.py` for estimates. |

### C1 LCSC parts (verified 2026-08-02)

NP0/C0G **only** — X7R capacitance drifts with voltage/temperature and will not tune reliably at 13.56 MHz.

| Nominal | LCSC | MPN | f_res est. (5T, +3 pF parasitic) | Role |
|---------|------|-----|----------------------------------|------|
| **10 pF** | **C301961** | Walsin 0402N100J500CT | **14.6 MHz** | **Primary** — AN11276 single-tag band (~14.5 MHz) |
| 12 pF | C106201 | YAGEO CC0402JRNPO9BN120 | 14.4 MHz | First SMT populate alternative |
| 15 pF | C106997 | YAGEO CC0402JRNPO9BN150 | 14.0 MHz | If reads still “high” with 10 pF |
| 18 pF | C106202 | YAGEO CC0402JRNPO9BN180 | 13.7 MHz | Toward ISO 13.56 MHz center |
| 22 pF | C1555 | FH 0402CG220J500NT (C0G) | 13.4 MHz | Only if still undertuned after 18 pF |

**BOM default (when populated):** C301961 (10 pF NP0). **First article:** leave DNP; hand-solder 10 pF if range is short.

> **Obsolete/wrong IDs (do not use):** C158992 (681 Ω resistor), C1525 (100 nF X7R), C1528 (160 pF X7R).

## NC pin terminators (DNP — B.Cu pads only)

| Field | Value |
|-------|-------|
| Ref | R2–R6 |
| Footprint | R_0402_1005Metric (**B.Cu**) |
| Value | **100 kΩ** → VSS (SCL, SDA, FD, VCC, VOUT) |
| MPN | **RC0402FR-07100KL** (YAGEO) |
| LCSC | **C60491** (100 kΩ 0402 ±1%, 62.5 mW) |
| Verified | 2026-08-02 against JLCPCB / LCSC |
| Default | **Do Not Place** |
| Notes | Weak pull-down defines floating NC pins; no RF tuning impact. Populate if field reliability needs margin. |

> **Obsolete/wrong ID (do not use):** C25744 — Uni-Royal 0402WGF1002TCE is **10 kΩ**, not 100 kΩ.

## Alternates (if C710403 unavailable at order time)

1. **ST25TN01K-AFH5** — LCSC C3303589 — Type 2, UFDFN-5 (low stock historically)
2. **ST25TA02K-DC6C5** — LCSC C2654880 — Type 4, UFDFPN-8 (recheck stock)

Do **not** switch to ST25DV / ISO15693 for this card if iPhone tap-to-Safari is required.

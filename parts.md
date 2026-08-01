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
| Candidate if needed | **10–22 pF** NP0 0402 (start ~15 pF). e.g. 10 pF LCSC **C158992**, 15 pF **C1525**, 22 pF **C1528** |
| Notes | Parallel across LA–LB. With L≈1.9 µH, Cin=50 pF alone is ~16 MHz; C1 pulls toward 13.56 MHz. Populate only after first-article phone tests. |

## Alternates (if C710403 unavailable at order time)

1. **ST25TN01K-AFH5** — LCSC C3303589 — Type 2, UFDFN-5 (low stock historically)
2. **ST25TA02K-DC6C5** — LCSC C2654880 — Type 4, UFDFPN-8 (recheck stock)

Do **not** switch to ST25DV / ISO15693 for this card if iPhone tap-to-Safari is required.

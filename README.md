# NFC Business Card (KiCad → JLCPCB)

Passive NFC PCB business card: **89 × 51 mm**, URL NDEF, rewritable from iPhone.

| Item | Value |
|------|-------|
| IC | NXP **NT3H2111W0FHKH** (Type 2 / NTAG I²C plus) |
| LCSC | **C710403** (JLCPCB Extended, SMT) |
| Board | 2-layer, **0.8 mm**, **black** mask, white silk, ENIG |
| Antenna | Right zone ~29.5 × 46 mm, **6 turns**, 0.25 / 0.25 mm |
| Text zone | Left **50 mm** — name as **ENIG copper**; roles / QR / contacts in silk |
| Components | 7 mm strip between text and antenna (U1 + C1 DNP) |

## Repo layout

```
nfc-business-card.kicad_*   KiCad project
lib/                        Symbols & footprints
antenna/                    Design notes + spiral points
fab/                        Gerber zip, BOM, CPL, checklist
scripts/                    Regenerate project / fab
parts.md                    Locked BOM
```

## Regenerate design

```bash
.venv/bin/python scripts/make_nfc_logo.py
.venv/bin/python scripts/make_back_logos.py
.venv/bin/python scripts/make_qr_silk.py
.venv/bin/python scripts/make_text_silk.py
.venv/bin/python scripts/generate_kicad_project.py
.venv/bin/python scripts/render_preview.py
python3 scripts/export_fab.py
```

Open `nfc-business-card.kicad_pro` in KiCad 8+ to edit silk text, tweak antenna, or re-export with **JLCPCB Fabrication Toolkit**.

Photoreal mockup (front + back):

```bash
.venv/bin/python scripts/make_nfc_logo.py      # NFC icon silk from assets/nfc-symbol.svg
.venv/bin/python scripts/make_back_logos.py    # back 2x2 logo silk
.venv/bin/python scripts/make_qr_silk.py       # inverted QR -> assets/qr-silk.png
.venv/bin/python scripts/make_text_silk.py    # roles + contacts silk PNGs
.venv/bin/python scripts/render_preview.py     # fab/preview.png
```

Front NFC icon: `assets/nfc-symbol.svg` (from SVG Repo). Check license/terms if you ship commercially.

## Order on JLCPCB

Follow [`fab/ORDER_CHECKLIST.md`](fab/ORDER_CHECKLIST.md).

1. Upload `fab/nfc-business-card-gerbers.zip` (or KiCad Toolkit output).
2. Enable SMT Assembly; upload `fab/bom.csv` + `fab/positions.csv`.
3. Confirm U1 = C710403 and rotation in the preview.
4. First run: **5 boards**.

## Write / rewrite URL (iPhone & Android)

1. Install **NFC Tools** (or NXP TagWriter).
2. Write → Add record → **URL / URI** → your `https://…` page → Write.
3. Tap the card (iPhone: near the top/camera area on modern models).

### Rules for rewritability

- **Do not** use “Lock”, “Make read-only”, or OTP lock. That is permanent.
- Optional: enable **write password only** (PROT = write protect). Reads still open the URL; rewriting needs the password in the same app session.
- After a successful write, lock the phone and tap again to confirm Safari/Chrome opens without an app.

## Design notes

See [`antenna/NOTES.md`](antenna/NOTES.md) and [`parts.md`](parts.md).

- Left **text zone**: name on **F.Cu** (mask opening + ENIG); roles, QR, contacts in silk.
- NFC antenna + chip sit on the **right** (reference-card style).
- If read range is weak, try C1 ≈ 5–15 pF NP0 0402 (e.g. C158992).

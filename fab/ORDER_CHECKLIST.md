# JLCPCB order checklist

## PCB

- Layers: 2
- Dimensions: 89 × 51 mm
- Thickness: **0.8 mm**
- Surface finish: **ENIG**
- Solder mask: **Black**
- Silkscreen: **White**
- Layout: left text zone (ENIG name), right NFC antenna + chip at feed
- **Upload Gerbers from KiCad** (mask / silk / paste / ENIG name) — not the placeholder layers in `fab/gerber/`
- Optional copper preview: `fab/nfc-business-card-gerbers.zip` (F.Cu + outline only)

## SMT Assembly

- Qty: start with **5**
- Side: Top
- BOM: `fab/bom.csv` (U1 = C710403)
- CPL: `fab/positions.csv` (synced to U1 feed position)
- C1 is DNP

## JLCPCB options

- Copper: 1 oz (default)
- Board outline tolerance: **Precision** (±0.1 mm) recommended for card size
- Run online DFM before checkout

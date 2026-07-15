# NFC antenna design notes

Board outline: **89.0 × 51.0 mm** (Edge.Cuts).
Chip: **NT3H2111W0FHKH**, Cin = **50 pF** (datasheet).

## Target inductance

Resonance: \( f = 1 / (2\pi\sqrt{L C}) \)

With \( f = 13.56\,\mathrm{MHz} \), \( C = 50\,\mathrm{pF} \):

\[
L = \frac{1}{(2\pi f)^2 C} \approx 2.76\,\mu\mathrm{H}
\]

Design target: **L ≈ 2.0–2.4 µH** (5 turns) for **~14–14.5 MHz** nominal with 50 pF + parasitics.
If the finished card reads poorly, populate C1 (start ~5–15 pF NP0) to pull frequency down.

References:

- NXP AN11276 — NFC antenna design
- NXP AN11786 — Antenna design guide for NTAG I²C
- NT3H2111_2211 product data sheet (50 pF input capacitance)

## Geometry used on this card

| Parameter | Value |
|-----------|-------|
| Text zone (left) | **50 mm** — artwork copper-free except ENIG name |
| Component strip | **7 mm** — U1 + C1 at antenna feed |
| Antenna (right) | **~29.5 × 46 mm**, **5 turns**, 0.25 / 0.30 mm |
| Feed | U1/C1 at spiral left edge; LA/LB buses 0.40 mm pitch, 0.18 mm traces |
| Copper under coil | **None** |

Reference-style segregation: electronics at the feed gap, artwork freedom on the left.

Rough L ≈ **2.2 µH** (nominal ~14.5 MHz). First-article phone tests decide whether C1 is needed.

## Layout rules

1. Keep ≥ 3 mm clearance from Edge.Cuts to outer turn.
2. Do not place ground pour under the spiral.
3. Place U1 and C1 pads at the feed gap; short LA/LB traces.
4. VSS may have a tiny local pad / pour at the chip only — do not flood the antenna area.
5. Center EP of XQFN-8: **no solder paste / no net** (datasheet).

## Verification after PCBA

1. Write a short HTTPS URL with NFC Tools.
2. Tap with iPhone (rear camera area) and Android.
3. Note max reliable distance.
4. If < ~5 mm and flaky, try C1 = 10 pF; iterate ±5 pF.

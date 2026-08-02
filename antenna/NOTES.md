# NFC antenna design notes

Board outline: **89.0 × 51.0 mm** (Edge.Cuts).
Chip: **NT3H2111W0FHKH**, Cin = **50 pF** (datasheet).

## Target inductance

Resonance: \( f = 1 / (2\pi\sqrt{L C}) \)

With \( f = 13.56\,\mathrm{MHz} \), \( C = 50\,\mathrm{pF} \):

\[
L = \frac{1}{(2\pi f)^2 C} \approx 2.76\,\mu\mathrm{H}
\]

Design target: **L ≈ 2.0–2.4 µH** (5 turns). With Cin=50 pF alone this is often **~15–16 MHz**;
parasitics and a DNP C1 (**10–22 pF** NP0) pull toward 13.56 MHz on first article.
If range is still poor after C1, consider 6 turns (L≈2.6 µH).

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

Rough L ≈ **1.9 µH** → f_res ≈ **16 MHz** with Cin=50 pF alone. First-article phone tests + C1 decide trim.

## Layout rules

1. Keep ≥ 3 mm clearance from Edge.Cuts to outer turn.
2. Do not place ground **pour** under the spiral. A single thin B.Cu underpass for LB
   (inner end → component strip) is required so F.Cu feed does not cross the outer turn;
   keep it ≤ feed trace width and well clear of any GND island.
3. Place U1 and C1 pads at the feed gap; short LA/LB traces.
4. VSS has a tiny local copper island left of U1 in the component strip — do not flood the antenna area.
5. Center EP of XQFN-8: **no solder paste / no net** (datasheet).
6. The spiral is **netted F.Cu tracks (net LA)**; the antenna footprint is only a
   **net-tie junction** at the coil inner end (`net_tie_pad_groups "1,2"`). The physical
   bridge copper lives in the footprint as two overlapping connect pads: pad 1 (LA)
   spans from the coil end to the take-off, pad 2 (LB) runs from the take-off down to
   via_in. Overlapping pads in a tie group are exempt from the DRC short test, so the
   coil closes to LB with real copper but no cross-net track touch. Do **not** use a
   track to bridge the pads (KiCad 10 DRC reports an LA/LB short) and do not put the
   pads far apart with no overlap (the board stays open). No un-netted copper may
   exist — un-netted spiral `fp_line` copper makes DRC shorting results **UUID-dependent**
   (0/1/2 errors across regenerations). Keep every copper item netted.

## Verification after PCBA

1. Write a short HTTPS URL with NFC Tools.
2. Tap with iPhone (rear camera area) and Android.
3. Note max reliable distance.
4. If < ~5 mm and flaky, try C1 = 10 pF; iterate ±5 pF.

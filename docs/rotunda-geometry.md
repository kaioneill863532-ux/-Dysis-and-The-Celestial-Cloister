# Rotunda geometry seed — 2026-09-27

This is a sampled geometry seed for the new prototype, not a complete collision or playability proof. Units are metres; positions are `[east, up, south]`. Position angles use `atan2(z, x)` in radians. Celestial phase `H` is the original hour angle in degrees, not an independently chosen solar altitude.

## Shared geometry and phase rules

- Outer diameter 40; facade radius 19; floors 0 / 6 / 12 / 18; roof 24.
- Main gallery radii 11.2–14.8. Twelve column centres at radius 10.5 and angles `15 + 30*k` degrees. The numerical clearance checks currently assume column radius 0.45 and player horizontal radius 0.35.
- A complete blocked architectural bay around angle 0 separates the accessible arc 15–345 degrees. Do not let inner passages, roof bridges or jump assistance bypass this seam.
- Departure-floor phase fields are linear over the **unwrapped** arc 15–345 degrees: L0 `H=0..8`, L1 `H=8..24`, L2 `H=24..44`. These are stored in `core/layout.js`.
- A beam traversal keeps the departure field, irrespective of its current height. No automatic floor switch by `y` and no horizontal platform carry.
- The player may climb while moving toward a smaller angle. D2 therefore gently reverses the sun while ascending; this is a consequence of a position field, not a discontinuity.

## Day ramps

Each ramp is sampled at 101 positions along the straight line from its solved foot to its top. At every sample, the source phase is recalculated from that sample's XZ position; the actual optical strip is recomputed. The player follows its support height, without being moved sideways. The test suite additionally uses 201 samples for support and phase continuity.

| Ramp | Foot / mirror | Top | Phase along ascent |
|---|---|---|---|
| D1 | `[8.513368, 0, 3.228065]` | `[8.488931, 6, 12.123450]` | 0.139770 → 0.969697 |
| D2 | `[-11.130671, 6, -5.372496]` | `[-14.295702, 12, 3.830522]` | 17.249233 → 15.272727 |
| D3 | `[-8.356239, 14.5, -9.958578]` | `[0, 18, -15]` | 37.030303 → 39.454545 |
| Roof | `[7.127507, 18, -10.566964]` | `[-4.305397, 24, 1.309028]` | constant 44.273200 |

All proposed light strips have nominal width 2.8. Values below describe the nominal centre path before architectural shadow clipping.

| Ramp | Maximum lateral error | Maximum height adjustment from straight interpolation | Maximum sampled walking slope | Nearest column-axis distance |
|---|---:|---:|---:|---:|
| D1 | 0.0458 | 0.0006 | 34.01° | 1.0773 |
| D2 | 0.0970 | 0.0324 | 32.14° | 1.7982 |
| D3 | 0.0108 | 0.1011 | 21.96° | 2.6998 |
| Roof | numerical zero | numerical zero | 20.00001° | 2.3934 |

D1's foot is at radius 9.1048, inside the main gallery. It requires a real, short stone approach from the gallery. Do not leave the foot floating over the courtyard. D3 begins on a real mirror-side platform at height 14.5, reached by the planned 14-riser stone stair from L2 height 12; the reflected strip then starts at the physical mirror height.

D1 and D2 do **not** have 2.8 metres of completely column-free light throughout. Their centre paths clear the assumed player capsule, but columns can clip the outside of the beam. Render and collide the clipped optical shape consistently; do not draw light through stone. D3 and the offset roof route have more clearance. Column capitals, bases, rails and decorations have not been included in these cylinder checks.

## D3 mirror and its incoming light well

The mirror must be calibrated at the phase when the player reaches its top landing, `H=39.454545`, rather than at the original sketch value `H=30`.

With the mirror centre raised to height 14.5, its fixed normal is approximately:

`[-0.271024055, -0.920559438, -0.281276167]`

The plane normal may be negated without changing reflection. It is a tilted plane; a vertical mirror rotating only in yaw cannot produce this rising branch.

At that phase, tracing toward the sun from the mirror reaches the facade radius 19 at:

`[-18.831437, 21.296727, 2.525265]`

Crucially, this incoming ray crosses the L3 floor plane at:

`[-13.750481, 18, -3.529976]`, radius `14.196354`, angle `194.397861°`.

**L3 needs an actual light well or double-height opening here.** A solid annular floor will shade the mirror even though the outgoing reflected ramp is mathematically correct. The final opening must include the full incoming bundle and its phase sweep, not only this one centreline.

## Roof ascent and the initially closed iris

`H=44.2732` produces altitude approximately 20° on the preserved orbit. The roof aperture radius remains 4.5, with a fixed rim at height 24. Moving iris leaves remain below at maximum height 23.3 and initially retain the same 9m central opening.

The originally proposed radial route pointed through the 315° column: its centreline approached that column axis to about 0.20m. The configuration therefore uses a **slightly offset chord** from angle 304°, radius 12.746061, to another point on the same central aperture rim. It still enters through the centre opening, never the tower exterior. Its full nominal 2.8m strip clears the assumed columns with a small additional margin.

The ray passes the leaf plane inside the initial aperture, so ascending does not trigger opening. The fixed rim/platform and fixed radial connection bridge carry the player. Only movement on the later outer rooftop route opens the lower iris leaves.

The roof chord must use its constant connection phase. Its position angle changes substantially during ascent even though the ray stays straight; a raw floor-angle field would rotate it out from under the player. The fixed roof phase is spatially authored, not a player-operated freeze control.

## Phase handoffs on real stone

The candidate floor ranges are intentionally simple, but they do not automatically agree at inter-floor endpoints:

| Arrival | Departing beam phase | Next floor's phase at the same angle |
|---|---:|---:|
| D1 at 55° | 0.969697 | 9.939394 |
| D2 at 165° | 15.272727 | 33.090909 |

These differences must **not** be applied as an instantaneous trigger. Reserve real stone transition paths, parameterize their phase by path progress, and match the old value at entry and the new field at exit. The transition should finish before the next optical puzzle. A fixed-phase vestibule by itself does not solve a mismatch; it still needs a continuous handoff or a change to the layer field endpoints. Length and pacing of these transitions remain an integration decision.

L3 can use a short linear field from the D3 landing (`theta=270°, H=39.454545`) to the roof foot (`theta=304°, H=44.2732`). It then enters the constant roof connection. At the roof rim, keep that same phase until the fixed connection bridge reaches the next authored rooftop phase field.

## N2 moon-reflection candidate

Mirror centre: `polar(19, 280°, 14.5)`.

The old sketch—calibrate a horizontal radial rail at `H=125`, then advance to 135/140/145—does tilt downward, but too little. Its intersections with height 6 lie at radii approximately 155.2 / 92.7 / 62.3, outside the building.

A usable revealing-light alternative is:

- Initial phase `H=105`.
- Initial horizontal outgoing heading 108°, eight degrees from the exact inward radial heading of 100°.
- Fixed mirror normal `[-0.553112335, -0.365319990, -0.748737638]`.
- Reveal phase `H=145`.
- Reflected direction `[0.258537079, -0.299969654, 0.918246582]`.
- L1 reveal target `[10.625274, 6, 7.308271]`: radius 12.896018, angle 34.520955°.

This is a **thin revealing beam, not a walkable bridge**. The closest column axis is about 0.7792m away; with 0.45m-radius columns, keep its optical half-width at or below 0.2m before accounting for capitals and ornament.

The beam crosses the L2 floor at `[5.454009, 12, -11.058518]`. That point needs a physical light well; otherwise the upper floor blocks revelation of the lower landing. Incoming moonlight and the outside bay's ceiling also need the full-scene occlusion check. If changing N2 to `H=105..145` conflicts with the final night sequence, retain the original phase range and reveal a higher stair entrance instead; let real stairs cover the remaining descent.

## Verified and still open

Verified by `node --test tests/layout.test.mjs`: sampled support width and continuity, endpoint heights, slopes below 35°, conservative centre-path column clearance, the offset roof aperture/leaf intersection, and the revised moon target inside the gallery.

Not yet verified: finite aperture and mirror size, incoming beam clipping over the complete phase range, floor and railing collision meshes, continuous swept collision between samples, jump assistance, final phase-transition pacing, or human playability. This configuration should seed the greybox, not bypass those checks.

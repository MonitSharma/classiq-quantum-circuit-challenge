# The arithmetic route's missing number: the y-side fold costs 95

> Audit: see [POST190_Y_FOLD_AUDIT.md](POST190_Y_FOLD_AUDIT.md). The 95/71 measurement reproduces, but the interval length, raw descriptor widths and universal arithmetic-obstruction claims below are incorrect. A disk-only y5-band fold measures 74/56/9; this is not a full-oracle gain.

Protected best unchanged: **190 depth / 857 CX / 18 qubits**, `artifacts/190/`.

The open question in the arithmetic plan was preparing radius and mode
information cheaply. It is now measured rather than estimated, and the answer is
negative for a specific arithmetic reason.

## Measurement

`src/post190_y_fold.py` builds `y -> (band, sign, magnitude)` with the band split
at 28, each band centred on its own disk centre, and a sign-controlled one's
complement. The mapping is checked on all 64 coordinates by direct simulation.

| component | depth | CX |
|---|---:|---:|
| band bit `[y >= 28] = y5 or (y4 y3 y2)` | 23 | 15 |
| subtract 19 (centre the D2 band) | 41 | 26 |
| conditional add 10 (centre the other band) | 40 | 26 |
| sign-controlled one's complement | 4 | 4 |
| **whole fold, after merging** | **95** | **71** |

For comparison the x-side fold is **10 / 10** on all 128 inputs, and the
six-address lookup this was meant to replace is **77**.

**The y fold alone costs more than the entire lookup it would replace**, before
any radius lookup, comparator or rectangle work is added.

## Why, and why it is not an implementation artefact

The x side is cheap by numerical coincidence. `40 + 55 = 95`, so a controlled XOR
of the low five bits maps the disk centred at 55 onto the one centred at 40; and
the shared centre's low-five value is **8**, a power of two, so "subtract 8 mod
32" is two gates.

The y centres are 19 and 41, with low-five values 19 and 9.

* `19 + 9 = 28`, not 31, so no XOR reflection aligns them.
* Both are **odd**, so their sum is even, while XOR alignment needs it to be 31 --
  odd. No unconditional shift can repair that, because shifting both by `s`
  changes the sum by `2s`, which is even. So the parity obstruction is exact.

Each band therefore needs its own centring constant. Because 19 is odd, the
constant adder must set bit 0, which forces the full carry chain up the register
-- a four-control gate and a three-control gate -- and that single term is the
41-layer row above. No choice of representation avoids it: any constant congruent
to `-19` mod 32 is odd.

## It also fails the descriptor requirement

Even paying 95, the fold does not produce a four-bit descriptor. Checking which
outputs determine the row class:

| descriptor | class collisions |
|---|---:|
| `(band, magnitude)` | 13 |
| `(band, sign, magnitude)` | 3 |
| `(band, sign, magnitude, y5)` | 0 |

Only the last works, and it is five bits per side, which puts the kernel on ten
wires -- the regime measured at 711 terms and 382 layers. The mod-32 fold aliases
across the `y5` boundary because the square band spans 29..53, thirty-five values,
more than one 32-block, so no single-block fold can be injective on it.

## Consequence

The arithmetic/phase construction is costed and it does not compete: the y-side
preparation is 95 against the 77 it replaces, and the descriptor it yields is
wider, not narrower. The x-side components remain genuinely good -- the 10-layer
fold and the 25/36-layer prefix comparator are verified and reusable -- but they
are the half of the problem that was already cheap.

This does not close every arithmetic formulation. It closes the one with a
concrete resource schedule: fold both coordinates, look the radius up from the
folded distance, compare. The obstruction is that the two y centres are both odd
and do not sum to 31, which is a property of the logo's geometry, not of the
circuit.

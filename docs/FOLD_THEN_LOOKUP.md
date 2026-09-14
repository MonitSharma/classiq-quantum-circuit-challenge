# Lookup address width: the right lever, and why this predicate resists it

**Outcome: the route is closed, but for a sharp reason.** The measurement below
is real and is the most useful thing found this round; the route built on it does
not survive contact with the predicate's class structure. Read the closure
section before the arithmetic.

Protected best unchanged: **196 / 858 / 18**, `artifacts/196/`. Nothing here is a
new oracle; this records measurements that make one route worth building.

## The measurement that matters

The loader's cost is dominated by the *number of address bits*, not by anything
I had been optimising. Compiling a three-output lookup with the beam scheduler,
Rx-conjugated, guarded so every parity carries one output variable:

| address bits | Walsh terms | depth | CX |
|---:|---:|---:|---:|
| 6 (current) | 174 | **77** | 193 |
| 5 | 70 | **48** | 91 |
| 4 | 42-48 | **33** | ~52 |

Roughly a factor 1.5 per address bit. Every previous search in this repository
moved terms around inside a *six*-address lookup, where 77 is provably the frame
design's floor. Removing address bits is a different lever entirely, and it was
never pulled.

## Why the address can be four bits

The row classes are two nested staircases: on the D2 band the class is a bucket
of `|y - 19|`, and on the square/D1 band a bucket of `|y - 41|`. So fold the
coordinate first -- destroy it, since the oracle's `C^dagger K C` sandwich
restores it -- and look the level up from the folded distance instead of from y.

The two bands need different level profiles:

* D2, by `|y - 19|`: `5 5 5 4 4 3 3 2 1 0 ...`
* square/D1, by `|y - 41|`: `4 4 4 3 3 2 1 6 6 6 6 6 6 0 ...`

but their **boundaries union to just seven cuts** -- at 3, 5, 6, 7, 8, 9 and 13 --
so **one eight-bucket map of the folded distance serves both bands**. That is
three bits, and the branch bit comes free on a coordinate wire, giving a
four-wire descriptor: the same kernel width as today.

## Why the address cannot be narrowed here

For the lookup to read five wires instead of six while the descriptor stays four
bits, one code partition of the 32 addresses -- at most **eight** blocks, because
three loaded bits -- must refine the class partition of *both* raw fibres. The
block count is the number of distinct `(class in fibre 0, class in fibre 1)`
pairs, and which address of one fibre faces which of the other is set by a
reversible pre-map that the oracle's own inverse undoes.

| alignment | row side | column side |
|---|---:|---:|
| identity, best raw wire | 16 | 14 |
| best invertible affine, 120k samples | 12 | 11 |
| best short uncontrolled circuit, up to 9 gates, 180k samples | > 10 | 10 (four CX) |
| transportation floor (7 row classes, 6 column classes) | 7 | 7 |

Eight blocks *is* achievable by some permutation -- an explicit eight-cell
transportation plan exists for the row side, matching `c5<->c10`, `c3<->c9`,
`c1<->c7`, `c2<->c8`, `c4` and `c6` into `c6`, and `c0` across `c6` and `c0`.
But no cheap reversible map realises one: affine maps stop at 12, and short
gate circuits do not reach 10 on the row side at all.

The four-address variant is worse. It needs each raw fibre's classes to be unions
of blocks from one common size profile; exhaustively checking every way to split
16 into four parts, the row class sizes `[22,12,5,5,4,4,4,2,2,2,2]` admit **no**
profile, while the column sizes admit exactly one, `(2,4,5,5)`. Both sides must
improve together, since the loaders run in parallel, so the row side decides it.
Widening the descriptor to two raw wires plus a four-address lookup fails the
same way: the common refinement over all wire pairs is 12 (row) and 11 (column),
against the eight that three loaded bits allow.

So the address width is the right lever and it is measurably large -- but this
predicate's two raw fibres simply do not share a coarse enough code partition.

## Route arithmetic, had the alignment existed

Per side the encoder becomes `fold + lookup`, and the kernel keeps its width:

| fold depth | lookup | kernel | oracle |
|---:|---:|---:|---:|
| 10 | 33 | 43 | **129** |
| 15 | 33 | 43 | **139** |
| 10 | 33 | 36 | **122** |
| 15 | 48 | 43 | 169 |
| 10 | 48 | 36 | 152 |

The 48-column is what you get if the folded distance needs five address bits --
it ranges to 19 on one band and 22 on the other, so the "far" region has to be
folded into the top bucket rather than carried as extra address bits. That is
the single open question, and it decides whether this route lands near 130 or
near 160.

The x side is easier: `40 + 55 = 95`, so a controlled XOR of the low five bits
maps the disk centred at 55 onto the one centred at 40, and the earlier probe
measured that reflection-plus-fold at **10 depth / 10 CX** on all 128 inputs.
The y centres are 19 and 41, which admit no XOR reflection (`41 XOR 58 = 19` but
`42 XOR 58 = 16`, not 18 or 20), so the y fold needs a small controlled constant
subtraction and is the piece to build and measure first.

## What was ruled out getting here

* **Destructive classifier, free garbage.** Correctly outside the 77-layer bound,
  which only governs lookups. Beam search over CX and relative-phase Toffoli,
  scored by whether any four wires separate the classes, starts at 40 unseparated
  pairs on the raw coordinate and stalls at 25 by depth 25. Retargeted at a fixed
  class-determining descriptor the objective is smooth -- Hamming distance 96 to
  29 -- but reaching 0 took 70 gates and depth 84-142 across six affine targets.
  Open, not excluded; my synthesis is what failed.
* **Reflect-folds of the existing code.** All 64 shifts of "shift then reflect the
  low five bits about 32" leave the Walsh support at 170-175 and the frame floor
  at 77, because a single fold cannot align two centres.

## What is worth keeping

The address-width measurement. Every search in this repository had been moving
Walsh terms around inside a *six*-address lookup, where 77 layers is provably the
frame design's floor. Dropping one address bit is worth 29 layers per side and
two bits 44 -- far more than any scheduling gain available -- so any future idea
should be judged first on whether it narrows the address, and only then on its
own cost.

The blocker is now stated precisely enough to test other ideas against: a route
narrows the address only if it makes the raw fibres' class partitions share a
code partition of at most eight blocks. The eight-bucket observation earlier in
this file (the two band profiles' boundaries union to seven cuts) is the one
structure found that does satisfy it -- but it applies to the *folded distance*,
and folding both bands to a common distance needs the two centres 19 and 41
aligned, which no XOR reflection does and which a controlled constant
subtraction pays for in exactly the layers it saves.

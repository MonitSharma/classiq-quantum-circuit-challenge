# Reassessment: why 524 is stuck, and what 197 must look like

Qualification from the [subsequent research review](RESEARCH_REVIEW_2026-09-09.md): this document's deductions about the leader's architecture, CX as a binding scoring constraint, and the necessity of a particular sweep structure are hypotheses or overstatements, not proofs. Depth is the primary score. The new review supplies exact scope for the UCR and feature-coding obstructions, including a 405-layer bound for reordering the current fixed gate multiset. Read that review before treating the conclusions below as exclusions of other architectures.

Written September 9, 2026. Nothing in this document supersedes a verified
artifact. The protected best remains
`artifacts/524/full_mux_feature_linear_tket_524.qasm` at **524 depth / 950 CX /
18 qubits**, SHA `7736b6dab26dd757575acab7135751e8d31f10da563cd96a9cc273135b8e6147`
(re-measured today).

## 1. The leaderboard moved; the docs were stale

`docs/HANDOFF.md` records rank 1 as Mateusz P. at 291 / 655. The live challenge
page now shows:

| Rank | Participant | Depth | CX |
|---|---|---:|---:|
| 1 | Daksh S. | **197** | **475** |
| 2 | Gabriele M. | 246 | 462 |
| 3 | Pablo C. | 262 | 582 |
| 4 | Tushar P. | 281 | 510 |
| 5 | Amit S. | 286 | 763 |

Scoring is unchanged: u3/cx depth after transpilation, all-to-all connectivity,
CX count as tiebreak, width capped at 18 and informational only. Deadline
September 30, 2026. Resubmission once per hour.

## 2. Measured stage budget of the current design

Each stage of `src/full_mux.py` compiled independently to exact `u3`/`cx`:

| Stage | Depth | CX |
|---|---:|---:|
| `lookup` (6-output, 6-control UCR over y) | 128 | 352 |
| `left` x-phase (3-output, 6-control UCR over x) | 128 | 186 |
| fold + comparator + phase cube (+ inverses) | 86 | 60 |
| `lookup.inverse()` | 128 | 352 |
| `pair_circuit` (radius-8 tail correction) | 71 | 66 |
| **total** | **541** | **1016** |

which matches the measured 536/1020 raw and 524/950 after the affine-feature
recoding plus pytket. So the entire circuit is three 128-layer UCR stages plus
157 layers of glue. There is no hidden slack.

## 3. The binding constraint is CX count, not depth

A 6-control UCR costs exactly 64 CX **per output** and 128 layers regardless of
how many outputs share the sweep. Therefore:

- our y-load alone is 6 x 64 = 384 CX; load + unload is **768 CX**;
- the rank-1 entry's *entire circuit* is **475 CX**.

The leader's whole oracle is cheaper than our load/unload pair. This is a hard
statement, independent of any cleverness in the glue: **rank 1 does not use
6-control UCR loads.** Any continuation that keeps the
load / phase / unload skeleton with 6-control sweeps is capped around 470-520
depth and cannot approach 197.

The numbers do fit a different skeleton almost exactly. Three stages of
**5-control** UCRs (32 Gray steps, 64 layers, 32 CX per output) with ~5 outputs
each give 3 x 64 = 192 layers and 3 x 5 x 32 = 480 CX. Compare 197 / 475. That
is the shape to aim for.

## 4. New structural facts about the logo predicate

All computed from the authoritative `logo` predicate in `src/search.py`.

### 4.1 Only 11 distinct rows and 11 distinct columns

The 64x64 mask has exactly **11 distinct rows** (as functions of x) and
**11 distinct columns**. GF(2) rank is 10, as previously recorded, but the
class count is much smaller than the rank suggests. Rows:

```
empty                    y in 22 values
[38,42]                  y in {11,27}
[36,44]                  y in {12,26}
[34,46]                  y in {13,14,24,25}
[33,47]                  y in {15,16,22,23}
[32,48]                  y in {17..21}
[2,26]                   y in {29..34, 48..53}
[2,26] u [53,57]         y in {35,47}
[2,26] u [51,59]         y in {36,46}
[2,26] u [50,60]         y in {37,38,44,45}
[2,61]                   y in {39..43}
```

Every row is a union of at most two x-intervals.

### 4.2 The two disks merge into one nested chain

Peel off the two disjoint rectangles
`Square = [2,26] x [29,53]` and `Bar = [27,48] x [39,43]`. What remains is the
two disks, and the y5-conditional reflection `x' = x XOR 31` (which is exactly
the reflection the current `fold` already performs, in a different bit pattern)
maps the upper disk's rows onto the lower disk's coordinate frame:

```
[53,57] -> [38,42]      [51,59] -> [36,44]
[50,60] -> [35,45]      [49,61] -> [34,46]
```

Together with the lower disk's rows this is a *single* totally ordered chain

```
[38,42] c [36,44] c [35,45] c [34,46] c [33,47] c [32,48]
```

so

```
f = Square XOR Bar XOR [ lambda(x XOR 31*y5) <= ell(y) ]
```

with `lambda` in {1..6, infinity} and `ell` in {0..6}, both 3-bit. This is a
cleaner statement of what `full_mux` already implements, and it shows the
71-layer `pair_circuit` is an artefact of the encoding, not of the geometry:
the current design stores the radius `r` in {0,2,4,5,6,7} in three bits, so
`r = 8` has no codeword and its 10 points need a separate tail circuit. In the
level encoding `ell` in {0..6} that case disappears.

The reason this cannot simply be swapped in: the three-table x-phase identity
needs a third target holding a *known constant*, which is what `V` provides
today. Encoding the level in 4 bits frees no wire (4 + A + B = 6), and using a
level bit as the third target injects a spurious rank-1 term
`[x not in [2,48]] * [y in [15,23]]` (153 points) that costs more to repair than
the 71 layers saved. Any attempt here must solve the third-target problem first.

### 4.3 Two impossibility results that close cheap routes

**No coordinate can be dropped from the y-loader.** A feature set can be loaded
by a 5-control UCR only if some fixed-point-free involution preserves it. The
row-class sizes include 5 (y in {17..21}) and 5 (y in {39..43}); with the square
and bar peeled off the level function `ell` has fibre sizes 34, 4, 4, 4, **9**,
4, **5**. Odd fibres mean no such involution exists. The y-load therefore needs
all six controls in *any* linear or nonlinear coordinate frame. The same holds
for the x-side square table (`[2,26]` has fibres 25/39).

**The full predicate has no linear symmetry.** Over all 4095 nonzero
`(vx, vy)`, the best agreement of `f(x,y)` with `f(x^vx, y^vy)` is 4006/4096
(at `vx=1, vy=0`); nothing is exact. So no CNOT-only change of basis reduces the
control count of any stage.

### 4.4 Reversible logic loses to the UCR for these predicates

Measured in exact `u3`/`cx`, one 6-bit interval predicate computed into a clean
ancilla:

| construction | depth | CX |
|---|---:|---:|
| ESOP + `MCXGate`, `[2,26]` | 179 | 103 |
| ESOP + `MCXGate`, `[27,48]` | 211 | 116 |
| Qiskit `IntegerComparator`, `x >= 27` (5 ancillas) | 88 | 56 |
| MCX with 2 clean ancillas, 6 controls | 54 | 30 |
| Toffoli (`MCX`, 2 controls) | 11 | 6 |

A single interval needs two thresholds, so ~180 layers, and the two x-side
predicates serialise on the x register. The 128-layer 3-output UCR that replaces
both is strictly better. Merging the tail correction into MCZ cubes over
`{x} u {y}` measured 112/82, worse than the existing 71/66 `pair_circuit`. All
three of these were tested today and are negative.

## 5. What the next attempt has to do

The skeleton must change so that no stage is a 64-step sweep. Two concrete
mechanisms, in priority order.

1. **Duplicated phase targets.** A *phase* (Rz) multiplexer is additive over its
   Walsh terms, so its 64 terms can be split into two 32-term chains driven onto
   two wires that hold the *same* bit; with rotated control orders the two
   chains run in the same layers, giving 64 layers instead of 128 at identical
   CX. (A *Boolean* Ry load cannot be split this way - partial angle sums are
   not computational-basis states. `src/shell_mux.py` tried the Boolean version
   and ran its three sweeps serially, which is why it scored 969.) The blocker
   is arithmetic: halving the x-phase needs clean duplicates of all three of its
   targets, i.e. three spare wires, and all six ancillas are live. **The real
   research question is therefore: find a decomposition whose live y-feature
   count is 3, not 6.**

2. **Shannon split with duplicated wires on the load side.** `F(y) =
   F0(z) XOR y5*(F0 XOR F1)(z)`: load `F0` and the delta with two 5-control
   sweeps that share the same 32 layers (64 layers total), then one Toffoli on
   y5. Costs 2 wires per feature and the same 64 CX per feature, but 75 layers
   instead of 128. Again: viable only at 3 live features.

Both reduce to the same requirement. Everything else measured here says the
current 6-live-feature skeleton is at its floor.

## 6. Explicitly closed by this pass

- Making any UCR stage 5-control by change of coordinates (impossible, 4.3).
- Replacing either x-side interval predicate with reversible logic (4.4).
- Replacing `pair_circuit` with MCZ cubes (112/82 vs 71/66).
- Reordering stages to overlap the y-unload with the x-phase or the comparator:
  the unload would have to be split into two sweeps, and two sweeps cost 256
  layers where one costs 128, so every such schedule loses.

### 5.3 Why "just use two smaller load phases" does not work either

Worked through today, so it does not get re-tried: splitting the y work into a
disk phase (live features `ell`, 3 wires) and a rectangle phase (live features
`Sy`, `By`, constant, 3 wires) does make each phase fit in 3 wires, but it costs
two load sweeps and two unload sweeps instead of one of each. Concretely, with
the Shannon-split loader at 64 layers per sweep plus ~33 layers of Toffoli
combine:

```
disk:       64 + 33 + 86 (fold/compare/phase) + 33 + 64  = 280
rectangles: 64 + 22 + 128 (x-phase) + 22 + 64            = 300
total                                                     ~580
```

worse than the present 541. The sweep count, not the sweep width, dominates.
Any winning schedule has to keep the total number of sweeps at three (or fewer)
*and* make each sweep 32 steps. Nothing measured so far does both.

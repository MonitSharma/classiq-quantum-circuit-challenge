# Joint five-output y-feature loader

## Scope

This experiment targets the reversible loading primitive

```text
y -> (R0(y), R1(y), R2(y), A(y), B(y))
```

where `R0..R2` are the three radius bits from `src/radius.py`, `A` is
`29 <= y <= 53`, and `B` is `39 <= y <= 43`. It uses the six coordinate bits
only and does not modify the protected complete logo oracle.

All truth-table artifacts use the repository convention that `y0` is the
least-significant bit. The intended physical outputs are `q12..q16`, with
`q17` as the only extra clean scratch wire.

## Exact Boolean inventory

The generated 64-row truth table is in
`artifacts/vector_feature_truth_table.json`. It contains **10 distinct
five-bit output codewords**. The GF(2) ANF inventory is in
`artifacts/vector_feature_algebra.json`:

| output | ANF terms | algebraic degree |
|---|---:|---:|
| `R0` | 16 | 6 |
| `R1` | 20 | 5 |
| `R2` | 12 | 5 |
| `A` | 8 | 6 |
| `B` | 8 | 6 |

There are 64 scalar ANF term occurrences but only 36 unique monomials. Fourteen
monomials occur in at least two outputs, including one shared by all five
outputs. This confirms real cross-output algebraic sharing; it does not yet
prove that the sharing survives reversible pebbling.

## Irreversible joint synthesis

`src/vector_feature_logic_inventory.py` emitted a proper six-input,
five-output PLA and ran three Berkeley ABC multi-output flows. The best natural
basis result used **56 AIG AND nodes at logic depth 8**. The output is recorded
in `artifacts/vector_feature_logic_inventory.json` and the generated ABC
networks are retained as `.bench` files under `artifacts/`.

`src/vector_feature_basis_search.py` scored **8,192 affine output encodings**
from 256 invertible matrices and all 32 affine offsets per matrix, then
compiled 64 distinct encodings through ABC. The best ABC screening result was
**46 AND nodes at logic depth 7**. This is a valid output-basis improvement in
node count, but the best y-input basis below remains better on the depth proxy
(48/6). The basis search is recorded in
`artifacts/vector_feature_basis_search.json`.

These are irreversible network metrics. They are not quantum depth or CX
claims and must not be substituted for a serialized U3/CX score.

## Reversible reference

`src/vector_loader_baseline.py` constructs each output exactly using
six-controlled minterm toggles, with no assumptions about clean input wires.
The serialized loader is `artifacts/vector_loader_best.qasm` and its metrics
are in `artifacts/vector_loader_metrics.json`:

| loader | depth | CX | width | status |
|---|---:|---:|---:|---|
| exact minterm reference | 7463 | 3822 | 18 | exact loader-only reference |

This is deliberately noncompetitive. It establishes a correctness-preserving
upper baseline and shows why the work must focus on shared reversible
pebbling, not merely finding a smaller irreversible AIG.

## Current decision

The vector function has enough sharing to justify implementing a reversible
pebbling compiler. The next experiment should convert the natural-basis ABC
network (and then the valid basis candidates) into affine-plus-AND nodes,
schedule them over `q12..q17`, and preserve exact output bits while clearing
the scratch. A loader-only serialized score below roughly 128 depth would be
interesting; the complete oracle must still be integrated and exhaustively
verified before it can affect the protected 531 result.

The protected complete-oracle result remains **531 depth / 1,020 CX / 18
qubits** at `artifacts/531/full_mux_531.qasm`. No leaderboard submission or
QMOD upload was performed by this experiment.

## Clean-pebble feasibility result

The ABC network was parsed into 56 affine-plus-AND product nodes by
`src/vector_reversible_pebble.py`, and its output truth tables were reproduced
exactly. A bounded reversible planner was then run on the natural network and
all 64 screened affine output bases. The planner permits at most six live
product nodes. Reserving one clean output accumulator leaves at most five
product pebbles.

No screened basis allowed all five outputs to fit with five or fewer live
product pebbles. In the natural basis, `A` alone requires all six live pebbles
under this schedule, while `R0`, `R1`, `R2`, and `B` do not close within the
bounded six-pebble search. The complete scan is recorded in
`artifacts/vector_feature_reversible_schedule.json`.

This closes the naive clean-output schedule, not the entire vector-loader
direction. The next compiler must use dirty output wires, output-frame
transforms, recomputation, or a different shared representation; simply
reserving one clean target per output cannot exploit the ABC sharing.

## Dirty-frame span probe

`src/vector_dirty_frame_search.py` performs an optimistic abstract search in
which all six ancilla wires may hold arbitrary Boolean frame values. It asks
whether toggled shared product nodes can make the five feature functions lie in
the final six-wire linear span. The best bounded run covered only **3 of 5**
outputs after 12 abstract toggles. It did not produce a gate circuit, and its
control-span checks were relaxed to expose possible endgame dependencies, so
the result is not a reversible score or an impossibility proof.

The artifact is `artifacts/vector_dirty_frame_search.json`. The next serious
implementation must restore disjoint physical controls and synthesize the
dirty affine frame explicitly; the current probe is useful only as a search
diagnostic.

## Local-coordinate fallback

The fallback in `src/local_y_distance.py` normalizes the low five y bits by
subtracting 19 when `y5=0` and 9 when `y5=1`, modulo 32, while preserving
`y5`. The transform was independently replayed on all 64 y inputs. With
three clean scratch ancillas and v-chain MCX synthesis, the exact serialized
transform measured **274 depth / 151 CX / width 18**. The no-ancilla reference
was 425/247.

This is not competitive as a complete disk architecture: the coordinate
transform must be inverted after phase marking, so the transform pair alone is
approximately 548 depth before radius loading or x-phase logic. The result is
therefore closed as a standalone fallback. Artifacts are
`artifacts/local_y_distance.qasm` and
`artifacts/local_y_distance_metrics.json`.

## Shared vector-ESOP fallback

The ANF monomials were also compiled as a shared multi-output ESOP in
`src/vector_esop_loader.py`. Each of the 36 unique monomials is computed into
q17, fanned out to its output mask, and uncomputed. The raw construction was
independently replayed on all 64 y inputs, checking exact output bits and
`q17=0`.

Because q15 and q16 are output wires, they are not used as clean scratch. All
degree-3-and-higher monomials therefore use exact no-ancilla MCX synthesis.
The serialized result is **2505 depth / 1453 CX / width 18**, recorded in
`artifacts/vector_esop_loader.qasm` and
`artifacts/vector_esop_loader_metrics.json`. An earlier 1354/840 measurement
was rejected because it illegally reused output wires as scratch.

This loader-only result is far above the protected complete-oracle depth 531,
so the naive shared-ESOP fallback is closed and was not integrated.

## Affine y-input basis search

An additional search changed the six y input coordinates before loading. The
best sampled map is represented by rows `(1, 2, 4, 40, 16, 48)` with affine
offset `16`; its pre/post linear cost is four CNOTs by the matrix proxy. Scoring
16,384 affine input encodings found a joint ABC network of **48 AND nodes at
logic depth 6**, improving the natural 56/8 network.

The corresponding exact shared-ESOP loader uses 26 unique monomials and
includes the reversible input-basis transform. It passed all 64 input replays
and serialized to **1973 depth / 1136 CX / width 18**. This is a genuine
loader improvement over 2505/1453, but remains far above the complete 531
oracle and was not integrated.

Artifacts:

- `artifacts/vector_input_basis_search.json`
- `artifacts/vector_input_basis_esop_loader.qasm`
- `artifacts/vector_input_basis_esop_metrics.json`

## Relative-phase dirty-output continuation

The input-basis loader was also rebuilt with exact dirty-ancilla MCX
synthesis, using the five feature output wires as restored dirty work space.
The ordinary exact version measured 1996 depth / 1130 CX / width 18, so it did
not improve the 1973/1136 clean-output loader. A relative-phase
compute/fanout/uncompute version measured **1560 depth / 874 CX / width 18** at
`artifacts/vector_input_basis_dirty_rp_loader.qasm`.

All 64 y basis inputs were independently simulated: the y register and q17
returned to their inputs/zero, the five feature outputs were exact, and every
case had the same global phase. This remains a loader-only diagnostic and is
not a replacement for the verified complete 531-depth oracle.

## Direct output-accumulator continuation

The strongest loader diagnostic so far toggles output accumulators directly
for each shared ANF cube, using the other output wires as restored dirty
ancillas for relative-phase MCX synthesis. It measures **1478 depth / 823 CX /
18 qubits** at `artifacts/vector_input_basis_direct_target_loader.qasm`.
All 64 y inputs were checked for exact feature bits, restored y and q17, and
single-basis-state output. Four relative-phase classes remain, so the
construction is intended only for exact inverse pairing around a diagonal
phase operation; it is not itself a complete logo oracle.
The serialized loader followed by its exact inverse reduced to identity under
U3/CX transpilation (depth 0 / CX 0), confirming the intended phase
cancellation.

## Complete integration result

The direct loader was integrated into the original phase/correction skeleton
by deriving `V = R1 OR R2` in q17 and reversing the loader afterward. Eight
routing seeds were measured; the best serialized complete candidate was
**3243 depth / 1965 CX / width 18** and passed exhaustive verification on all
4096 inputs. This is a negative result: dirty direct-target loading is not a
useful replacement for the six-output UCR stage in the complete oracle.

## Persistent output-frame loader

The output-frame scheduler maintains `f = M p` on the five feature wires and
changes M between shared ANF cubes so each cube uses one physical target when
possible. With deterministic seed 1234 and 2,000 frame completions sampled per
cube, the serialized loader measured **871 depth / 553 CX / width 18** and
passed all 64 y-input checks.

The complete integration measured **2032 depth / 1425 CX / width 18** over
eight routing seeds; seed 1 was best and exhaustive verification covered all
4096 inputs with zero ancilla leakage. This is an improvement over the direct
loader integration but not over the protected 531 oracle.

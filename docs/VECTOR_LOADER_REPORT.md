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
**48 AND nodes at logic depth 10**. The natural basis remains preferable on
logic depth (8 versus 10), while the 48-node result may still be useful if a
reversible schedule can exploit its sharing. The basis search is recorded in
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
network (and then the 48-node basis candidate) into affine-plus-AND nodes,
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

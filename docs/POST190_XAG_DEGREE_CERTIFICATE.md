# Fixed protected labels: a stronger AND bound and a smaller witness compiler

The protected full logo oracle remains 190/857/18. This work improves the
witness compiler and establishes bounds on a precisely specified Boolean
synthesis task; it does not produce an improved logo oracle.

## At least six AND gates per side, without waiting for SAT

All six truth tables in the running experiments' scratchpad `funcs.json` were
compared with the labels from `artifacts/190/class_codes.json` and match exactly.
For each side, transform its three output truth tables into algebraic normal
form (ANF) over GF(2), then keep only monomials of degree five or six. Those
three projected coefficient vectors have rank THREE on both sides.
Equivalently, every nonzero XOR of the three outputs has degree at least five.

The standard Boolean degree bound states that a function of algebraic degree d
needs at least d-1 AND gates in an XOR/AND/NOT circuit. See the research paper
[The Multiplicative Complexity of 6-variable Boolean Functions](https://pmc.ncbi.nlm.nih.gov/articles/PMC7802510/).
Apply this bound to each prefix of a topologically ordered XAG. The first
three AND results have degree at most four. In a five-AND circuit, all degree
five/six terms of its affine outputs must therefore come from the last TWO
AND results. Their projected span has dimension at most two, contradicting
the measured rank three. Thus **k >= 6 on both sides** for the protected labels.

More generally, if output coefficient rank after projection to degree >=d is
r>0, k >= d-2+r. `src/post190_degree_rank_bound.py` implements this check and
saves all ANF coefficients, monomial masks, projected vectors, and ranks in
`artifacts/post190_inplace_xag_lower/degree_rank_certificate.json`.
The strongest unrestricted result here is six, not a claim that six suffices.
This bound survives changes of internal DAG or XOR basis, but does not close
other nonlinear output encodings or direct quantum oracle constructions.

## Depth-three restriction actually requires at least seven ANDs

The outputs include degree-six terms. In an XAG of AND-depth at most three,
every node of degree >=5 must be at level three: levels one and two have
maximum degrees two and four. Such nodes cannot be ancestors of one another.
At least three such nodes are needed to supply the rank-three projected output
space. At least one has degree six, so its ancestor subcircuit contains at
least five AND nodes by the degree bound: itself and at least four ancestors.
Those ancestors are not among the level-three high-degree nodes. Consequently
**k >= 4+3 = 7** under the AND-depth-three restriction.

It is therefore pointless to seek a k=5 witness for these fixed labels, or a
k=6 witness with AND-depth <=3. Feasibility at k=6 without that depth cap, or
at k>=7 with it, remains unresolved. Runtime extrapolations from two UNSAT
instances do not establish that k=6 is computationally out of reach.

## Compiler improvement measured on the supplied synthetic witness

The scratchpad `build_xag.py` allocated two affine temporaries plus separate
output wires. Its k=3 example measured 41 encoder layers / 42 CX / 14 wires.
`src/post190_xag_inplace_lower.py` implements affine operands in place, uses
relative-phase Toffolis into clean node wires, and applies an invertible output
basis change on those node wires instead of allocating a second output bank.

For that SAME synthetic k=3 example:

| quantity | new result |
|---|---:|
| encoder depth | 24 |
| encoder CX | 22 |
| width | 9 |
| complete synthetic phase/uncompute depth | 33 |
| complete synthetic phase/uncompute CX | 31 |

All 64 arbitrary primary-input basis states were simulated through both the
encoder and the complete C/Z-parity/C.inverse construction. Code outputs are
correct, coordinates are preserved, ancillas clean up, and shared-global-phase
error is 1.25e-15. Two focused tests pass.
This is NOT a protected-label witness or a logo oracle. It establishes that
11+k wires and the corresponding old timings are properties of the naive
compiler, not mandatory costs of a witness.

The new compiler still needs k clean node wires, and only accepts output rows
that are independent modulo the original inputs. It therefore does not solve
the k>=6 register/pebbling problem. Dirty coordinate reuse and pebbling remain
separate synthesis questions. AND-depth alone does not certify a small live set.

## Running searches and next action

At inspection, saved files contained `y4: UNSAT` and `x4: UNSAT`, without a k=5
result. Process inspection was blocked by the environment, so liveness was not
confirmed. No external running process or scratchpad source was changed.
The repository solver accepts a timeout parameter but calls blocking solve()
without implementing it. Use `src/run_bounded.py` for new native solver runs.

Recommended redirection: retire the now-analytically-impossible k=5 targets;
try k=6 with greater AND-depth or k>=7 with depth <=3, with explicit reversible
storage/scheduling checks. Search for a usable witness rather than extrapolating
how long a proof will take. Keep the 190 submission protected.

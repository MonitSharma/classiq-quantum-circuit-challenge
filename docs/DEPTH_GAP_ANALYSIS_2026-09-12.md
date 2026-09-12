# Why the current circuit misses 183 depth

**Later same-day construction supersedes this audit's best-circuit status:**
[DISTRIBUTED_LOOKUP_258.md](DISTRIBUTED_LOOKUP_258.md) documents a verified
258/1188/18 circuit. The new implementation distributes lookup phases onto
coordinate wires and uses a 13-layer kernel. The bounds on the old fixed gate
placement and the restricted affine/diagonal model remain valid, but this
earlier report's statement that no improvement was found is now historical.

September 12, 2026. This is a code and evidence audit, with a bounded native
component experiment and a restricted-family depth bound. **No new best oracle
was found.** The exact 456/1140 QASM remains the best documented local result.

## Feasibility and the actual problem

The notebook asks for an operator on arbitrary coordinate inputs, not an image
state preparation. Its action is

`|x,y,0^a> -> exp(i phi) (-1)^logo(x,y) |x,y,0^a>`.

There are 12 input bits, at most six clean ancillas, 1,097 marked coordinates,
and 2,999 unmarked coordinates. Coordinates and ancillas must be restored;
only one common global phase is allowed. The notebook's 18 disjoint rectangles
implement the union correctly but repeat substantial predicate computation.
The notebook is the baseline; most subsequent research is in `src/` and `docs/`.

Safari's challenge page inspected during this audit displays 183/789/18,
188/451/18, 190/389/18, 191/374/18, and 195/432/18 as its leading entries.
It displays Monit S. at rank 24 with 524/950/18. These are observed public
scores, not privately inspected winning circuits or a newly submitted result.
[Official challenge](https://www.classiq.io/challenge#leaderboard).

Accepting the verified entries under the stated rules, a depth-183 circuit is
possible. That does not establish that 182 is possible, identify an algorithm
for finding 183, or guarantee rank one at the deadline. Nothing in this
repository establishes a general depth lower bound anywhere near 183.

The 456 result is already approximately 91.4% below the recorded notebook depth
5329. Reaching 183 requires a further 59.9% reduction. This is a substantial
remaining synthesis problem, not evidence of a mistake in the target function.

## What was independently checked now

`src/september12_depth_audit.py` extracts the notebook's pure predicate and QASM
metric functions without running SDK, synthesis, authentication, or upload
cells. Its report is `artifacts/september12_depth_audit_final.json`.

* The notebook predicate agrees with `search.MASK` on all 4,096 coordinates.
* The two-level-comparison identity in `level_oracle.py` has zero mismatches.
* Both protected QASM hashes match their existing exhaustive reports.
* The notebook's own metric parser agrees with Qiskit's metrics for both files.
* Twelve serialized seven-qubit alternative loader components were checked on
  all 128 basis inputs each, including both initial values of the target bit.

This audit did not rerun the full baseline simulations: their exact bytes match
the previously successful exhaustive reports. It did not edit the notebook or
either protected circuit. There is no new full-oracle candidate requiring
promotion or submission.

| Exact artifact | Depth | CX | U3 | Largest number of gates touching one wire |
|---|---:|---:|---:|---:|
| `artifacts/456/level_merged_456.qasm` | 456 | 1140 | 1061 | 389, q16 |
| `artifacts/524/full_mux_feature_linear_tket_524.qasm` | 524 | 950 | 823 | 405, q16 |

## The bottleneck is materializing labels

The strongest current structural identity is

`logo(x,y) = [u1(y)+v1(x)>=6] XOR [u2(y)+v2(x)>=6]`,

where each level is in 0 through 5. It absorbs the square, trimmed bar, and
one disk into a single staircase comparison. This is useful compression: the
central phase is small. But constructing its inputs is expensive.

`build_merged` loads codes for the first comparison, changes to codes for the
second comparison, then erases them. The two sides run in parallel. Ry
rotation composition merges the middle erase/load pair, saving a whole stage.
Each surviving dense six-control ladder nevertheless has 64 rotations and
64 CX positions on a target. Sparse-angle and ordering experiments did not
remove this cost sufficiently.

The current artifact provides a stronger, less assumption-dependent diagnostic
than assigning an exact fraction of total depth to abstract stages. Its six
ancilla touch counts are **387, 370, 385, 386, 389, 334**. A circuit retaining
those operations on those wires has depth at least 389, whatever legal
reordering is chosen. To reach 183, q16 alone must lose or redistribute at least
206 operations. Redistribution changes the implementation and has its own cost.

The total occupied wire slots are 1061 + 2*1140 = 3341. Even perfect use of all
18 wires would require 186 layers without gate reduction. More significantly,
the actual per-wire imbalance raises that floor to 389. The task is to change
how the computation uses wires, not just to ask the scheduler to work harder.
These are bounds on this fixed implementation, not on equivalent circuits.

## Why so many different methods failed similarly

The method names differ more than their eventual circuits. Many searches
minimize a classical representation and then lower it into temporary Boolean
values, phase gates, and cleanup. The same resource constraints recur.

| Family | What the recorded experiments establish | What they do not establish |
|---|---|---|
| Rectangle and geometric factoring | Repeated comparisons and corrections are expensive after lowering | Geometry cannot support a shallow hand construction |
| XAG, ESOP, BDD, LUT | Low classical node count or AND depth does not include wire lifetimes, affine transport, and reversal | Every nonlinear reversible circuit is too deep |
| Coordinate/level codes | Small codebooks and cheap kernels exist; tested encoders/decoders are costly | Every choice of code, garbage, transition, and kernel is expensive |
| Destructive and phase-history searches | Bounded searches stalled; exact residual correction became costly | No exact shallow circuit exists outside the searched neighborhoods |
| MPO and variational synthesis | Compressed representations exist; tested optimizers remain approximate | Compression supplies a cheap exact unitary implementation |
| Compiler cleanup | Existing local passes do not bridge the measured gap | A mathematically different global rewrite is impossible |

A classical function can discard input distinctions. A unitary must retain
enough information to reverse its computation. Merely counting three output
code bits therefore misses the garbage wires and the work needed to recover
the original coordinates. Allowing a data wire to change temporarily is legal,
but the construction must still be injective on reachable inputs and restore
that wire at the end.

The recent v2 result is especially specific: the implemented split-code/ESOP
encoder costs 301 depth. It does not implement the hoped-for product-factored
native encoder. Its failure cannot be generalized to every possible encoder.

## A genuine restricted-family exclusion: depth at least 682

The history already records the odd-population Walsh argument. Here is its
extension into a gate/depth bound, including arbitrary integer phase lifts and
the six clean ancillas.

**Model:** X, CX, and diagonal one-qubit gates, with ancillas initially in
computational-basis states. No intermediate Hadamards or other basis-changing
rotations. Anti-diagonal one-qubit gates may also be allowed: each is a bit
flip times a diagonal phase and does not alter the argument.

Let z be the twelve-bit input. Every wire in this model carries an affine
Boolean function of z. Consequently each phase gate contributes a constant
plus a multiple of one Walsh character `chi_s(z)=(-1)^(s dot z)`.

For the correct oracle, its accumulated real phase must be

`P(z) = phi + pi*f(z) + 2*pi*k(z)`, with integer k(z).

For every nonzero mask s, the Fourier coefficient is

`P_hat(s) = pi/4096 * sum_z (f(z)+2*k(z))*chi_s(z)`.

The numerator is odd: modulo two it equals the marked population 1097.
Therefore it cannot vanish for any of the 4,095 nonconstant masks, for any
integer lift k. A global phase affects only the constant mask.

Every nonconstant mask must therefore occur on a wire receiving a phase gate:
at least **4,095 one-qubit phase-bearing gates**. Initially only the twelve
individual input masks occur; clean ancillas add only the zero mask. Each CX
can introduce at most one new mask. X only changes an affine constant. Thus
at least **4,083 CX gates** are required as well.

At width 18, a layer has at most eighteen occupied wire slots. It follows that

`depth >= ceil((4095 + 2*4083)/18) = 682`.

This excludes direct affine parity/diagonal synthesis as an explanation of the
183-depth leader, even with the allowed ancillas. It does **not** exclude
Toffoli constructions, Ry lookup, or general U3/CX synthesis: their native
circuits use intermediate basis-changing gates. The current 456 circuit is
outside this restricted family and is fully consistent with the bound.
The proof is analytic; the audit's random integer-lift checks are regressions,
not an exhaustive proof substitute.

## Bounded experiment: omit multiplexer diagonal corrections

I tested Qiskit's `UCGate(..., up_to_diagonal=True)` on the twelve bit functions
from the four level encoders using `TRIPLE_DEFAULT`. This permits extra
diagonal phases. In a complete encoder/inverse sandwich around a diagonal
kernel those phases can cancel. This is a legitimate opportunity to measure,
not permission to discard arbitrary phases between unrelated transitions.
[IBM UCGate documentation](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.UCGate).

Every tested component compiled to **127 depth, 63 CX, 64 U3**. All preserved
the controls and performed the expected target toggle up to phase on all 128
inputs; maximum monomial error was approximately 2.96e-13. The test includes
serialization and uses `qubits_initially_zero=False`.

This is a negative result for these default codes, this decomposition, and
this ordering. It is not a search over all code assignments. It saves roughly
one layer on a lookup rather than the hundreds required globally; I did not
integrate it or start another scheduling campaign. Published phase-tolerant
logic synthesis is relevant, but its reported savings cannot simply be applied
again to the already phase-tolerant Ry construction.
[Seidel et al.](https://doi.org/10.1088/2058-9565/acaf9d).

## Corrections to earlier conclusions

Several passages in `LEVEL_COMPARATOR.md` should be read as historical claims,
not theorems:

* “456 is the floor” is not established. The concrete fixed-wire bound is 389;
  even the document's own abstract arithmetic gives 438 in one passage.
* A sample of 40,000 affine twists does not prove that the natural split is
  optimal over all relevant changes of representation.
* Failure to find a kernel below 27 is not proof of kernel optimality.
* “Only AND-network encoders can go lower” has not been proved.
* `4E+2K` is a budget for a symmetric, staged two-pass construction. It is not
  a universal cost law; shared prefixes, unequal costs, and direct transitions
  change it. With K=27 and that staging, E<=32 suffices for depth <=183 before
  other overhead; E<=31 is the stricter sub-180 checkpoint.
* Degree-three v2 codes are excluded by the newer exhaustive model screen.
  Older suggestions that this route merely needs finishing are superseded.
* “Ancillas are mathematically required” does not follow from Fourier density.
  Ancilla-free general quantum implementations exist; the density argument
  concerns a restricted phase-polynomial representation and its cost.

The attached notebook's suggestions and old research stop decisions are source
material. The current request authorizes renewed analysis; those older remarks
were not treated as a new instruction to refuse work or submit anything.

## What would justify the next substantial search

The missing deliverable is an exact, shallow native construction. Another
representation by itself is not that deliverable. Two useful sources of new
evidence would be a public explanation of a leading architecture, or a concrete
native component that invalidates the current cost assumptions. The public
metrics alone do not identify the winning algorithm: 183/789 and 191/374 could
reflect different decompositions, scheduling tradeoffs, or other choices.

An internally testable remaining specification is **joint reachable-state
encoder/transition/kernel synthesis**, rather than another independent ESOP
encoder. It would search actual native wire operations, allow reversible data
scrambling, choose code labels and garbage together, and charge the transition
between the two phase applications and final restoration. It must track phases
as well as Boolean labels. This overlaps earlier research ideas; it is not
claimed as a newly discovered winning method. Existing bounded searches do not
exhaust this space, but neither do they supply evidence that a new broad search
will converge.

Before allocating another long run, require a replayable native component and
an explicit full-circuit depth budget that could reach the target. A lower AND
count, a low residual, or an approximate fidelity is insufficient. An eventual
full candidate must pass `src/exhaustive_verify.py` on its exact new QASM and
retain a matching hash. Submission also needs a matching description/QMOD.

**Assessment:** the leaderboard level is feasible under the stated verified
benchmark. Your current implementations do not reach it, and the tested
compiler/loader substitutions cannot bridge the gap. This audit explains and
narrows that gap, but it has not solved the missing synthesis problem or
established a guaranteed path to rank one.

## Reproduce this audit

From the workspace root, choosing a new output filename:

```sh
.venv/bin/python src/september12_depth_audit.py --out /tmp/classiq_depth_audit_replay.json
```

The script refuses to overwrite an existing output report. It does not call
historical search entry points, alter protected artifacts, or contact the SDK.

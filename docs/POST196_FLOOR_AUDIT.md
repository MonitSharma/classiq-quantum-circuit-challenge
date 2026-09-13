# Audit of the claimed 150-depth architecture floor

The protected best remains **196 / 858 / 18**. This audit finds errors in the
claimed exclusion of 142. It does not establish a circuit below 142 or 100.
Reproduction: `.venv/bin/python src/post196_floor_audit.py`; measurements are
in `artifacts/post196_floor_audit/report.json`.

## The code frontier was not exhaustive

`post196_code_frontier.py` restricts the first two subsets to a pool (default
300), keeps one code per loader-term total, restricts the paired shortlists,
and computes one kernel ANF completion. Different codes with the same loader
cost can have different kernel costs. Different integer phase lifts of the
same kernel can also have different costs, as the protected 196 already shows.
Consequently neither the predicted frontier nor its selected native builds
establish a universal lower bound.

There was an additional implementation error: `complete()` returns both
component orientations and free cells, but the caller never varied the free
cells. The unused `extra` expression considered only the empty subset.

A counterexample on the actual row classes, raw parity 32:

- First two subset masks: 6385 and 4710, supports 23 and 31.
- Free cells: 3, 9, 12.
- Old minimum third-bit support: 43; complete minimum: 40 (mask 4540).
- Total support: **94 instead of 97** for this pair.

`completion_subsets()` now includes all free assignments. Its regression test
also verifies that every returned completion separates every required pair.
The overall search is still bounded and is now labeled accordingly. The
94-term point is consistent with earlier spectral-code work in the repository;
it is not a new verified oracle or a reason to repeat that entire search.

## The stated floors mix bounds with construction overhead

The source/host argument assumes a fixed partition and restricted transitions.
A general parity network can change those roles; two hosts with the same
output component can XOR to form a source. Intermediate parities can also
contain multiple output variables even when no rotation is applied to them.
Adding approximately 13 layers from the existing frame skeleton is not a
proof that every allowed construction must pay that overhead sequentially.

The claimed general kernel floor `3*T/8` is false. Eight independent singleton
parities take eight parallel Rz gates, depth 1, whereas that formula gives 3.
For a fixed diagonal phase-polynomial representation with T distinct nonzero
parities on n wires, a valid simple gate-occupancy bound is
`ceil((T + 2*max(0,T-n))/n)`: up to n parities can be present initially and each
CX creates at most one new wire parity. For T=69 and n=8 this is 24, not 26.
This remains a bound on that representation, not all equivalent phase lifts
or general quantum circuits. Combining selected representations' counts does
not yield an all-code lower bound.

Class-constant degree calculations likewise do not close class-*separating*
encoders. A class can use several codes, including codes that differ between
raw-parity fibers. Degree is also distinct from the number and depth of shared
nonlinear operations needed to compute several outputs.

## Packing arithmetic and what it actually implies

The serialized QASM has **858 CX and 789 U3**, hence **2,505 wire-slots**.
Available slots are 18*196 = 3,528; occupancy is **71.0034%**, not 65%.
The occupancy lower bound is `ceil(2505/18) = 140`.

A lower bound is not a schedulable construction: dependencies and incompatible
wire usage can prevent perfect packing. The proximity of 140 to the leader's
142 does not reveal the leader's method. Nor does it show that all 18 wires
must be continuously occupied in a winning circuit; reducing the gate count
can also lower depth.

At depth 99, capacity is only 1,782 wire-slots. Therefore the existing gate
multiset needs **at least 723 fewer wire-slots (28.9%)** to reach sub-100,
regardless of scheduling. This is a useful necessary target for a replacement
construction, not a proof of its feasibility.

## Consequence for the next search

The measured failure to beat 196 is real; the asserted architectural
impossibility proof is not. Continue to preserve the 196 artifact and avoid
another unmotivated seed sweep. The substantial open direction remains shared
reversible computation of class-separating features, allowing temporary
coordinate modification and using the exact inverse to restore it. Existing
partial Boolean witnesses and bounded negative searches do not settle this.
No new full circuit or submission was produced by this audit.

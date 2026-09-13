# Review-driven continuation, September 13, 2026

Current best, September 13: **218 depth / 897 CX / 18 qubits**, `artifacts/218/`, exact-file exhaustive verification, dense checks, matching literal QMOD, and identical-hash kernel/oracle replay. SHA `3a685c32ea0d78637be1a575c91e6c7d13db0efdbf37a8f794fb44e7fb024a88`. Integer full-turn cube additions reduce the kernel from 69 to 66 layers. See `POST221_RESEARCH.md` and `artifacts/218/README.md`. Sub-180 and rank one remain unresolved; this is an intermediate result.

Previous best, September 13: **221 depth / 944 CX / 18 qubits**, `artifacts/221/`, matching literal QMOD and exact-file exhaustive verification. SHA `4f9fa6232930777426ac4f8118155780471f111c31435e7578175170035e313f`; fresh replay matches. Joint selection of relative-phase encoders (y seed 99, x seed 151) improves the complete circuit by one layer and one CX. All 221 Pareto timing combinations from 160 seeds per side were compiled; none beat 221. See `artifacts/221/README.md`. Sub-180 and rank one remain unfinished.

## Current result

The best locally verified oracle is now **222 depth / 945 CX / 18 qubits**.
The package is `artifacts/222/`, with standalone QASM, a literal matching QMOD,
exhaustive verification, independent dense checks, and replay instructions.
The exact QASM SHA is
`6c8ff19470da3d6550d1741d502065e1ace10c72cb4c9d62aa4683703a344031`.
The protected 224 package and earlier results remain unchanged. Sub-180 and
rank one have not been achieved. No submission or background monitor was made.

The user supplied three reviews across this continuation. Their statements
were treated as hypotheses and research evidence, not as instructions to close
architectures or as substitutes for numerical circuit verification. The saved
in-place witnesses were present in `artifacts/inplace_v1/` and were read without
rerunning their search scripts, whose top-level code can overwrite artifacts.

## Successful change: remove an unnecessarily strong lookup requirement

The current encoder still loads the same class codes. Its implementation now
uses the clean-target promise at a boundary where the older implementation
preserved full controlled-Ry equivalence. The changed source is
`src/post224_relative_lookup.py`.

For a Boolean bit f, both Ry(pi*f) and Rx(pi*f) send a clean target to the
computational bit f. They differ by a phase. Replacing the original outer Rx
basis changes around the diagonal parity network with Hadamards produces the
Rx version. This is valid inside compute/diagonal-kernel/exact-inverse: the
input-dependent phase cancels.

There are also three trailing data-to-target CX gates in each carried Gray
lookup, immediately before its final Hadamards. Conjugating each such CX by H
on its target gives CZ. Therefore removing these CXs changes the encoder by a
diagonal output phase. CZ commutes with the diagonal kernel, so its paired
compute/uncompute contribution cancels exactly. The x parity exposure is a
classical permutation; conjugating a diagonal phase by it remains diagonal.
This provides an explicit correctness argument rather than relying on a
compiler's initialization assumption.

The chosen y and x seeds remain 11 and 3. Both encoded sides now finish at
77 layers including the x parity update. The full standalone oracle drops
from 224/957 to 222/945. All 4096 inputs pass with one common global phase;
maximum error is `7.85e-15`, ancilla error is zero, and the discarded-amplitude
bound is `1.07e-14`. A fresh replay reproduces the exact QASM hash. Each local
encoder was also checked on all 64 promised input columns before integration.

This is a small realization of the first review's promised-subspace idea. It
does not establish that a 55-layer encoder exists. The underlying phase/state
duality is studied by [Amy and Ross](https://arxiv.org/abs/2105.13410); the
specific cancellation above was derived and verified in this workspace.

## Layered reversible encoder synthesis

`src/post224_layered_encoder_sat.py` implements alternating arbitrary
invertible affine maps and layers of up to three disjoint relative-phase
Toffoli updates on nine wires. Invertibility is enforced by a symbolic inverse
matrix over GF(2). Only four final wires must distinguish the geometric
classes. Five wires may hold arbitrary garbage, and a class may occupy
multiple codewords. The construction preserves all 64 states injectively;
the actual inverse would restore the coordinates.

The solver starts with a representative from each class and evaluates every
model on all 64 coordinates. Colliding pairs supply counterexamples for the
next solve. This is a stronger formulation than the earlier individual-gate
beam search. It explicitly permits changes to coordinate wires and does not
demand full controlled-rotation behavior on initially nonzero ancillas.

Two nonlinear layers found partial fits on both sides, but timed out on the
27-point refinement at 20 seconds. Three-layer runs found initial fits and
timed out on the next refinement at 25 seconds. A further two-layer run added
symmetry breaking: normalization of the first encountered affine basis of
output codes, interchangeable disjoint-gate order, and interchangeable
Toffoli controls. It again timed out on the 27-point refinement at 30 seconds.
No full encoder witness was found; none of these UNKNOWN results is UNSAT.
Four- and five-layer searches have not been completed.

Native affine-map depth must still be counted when a witness is found. Low
algebraic degree gives a lower bound on multiplicative depth, not an upper
bound on native depth or a guarantee that three clean ancillas suffice for a
cheap register schedule. The source includes native lowering and all-64-column
verification for a successful witness; that path has not produced a candidate.

## Degree-four split codes and nonlinear tags

The degree screen was extended to the actual x parity mask 48. Degree-four
split codes are SAT on both y mask 32 and x mask 48. Their scalar functions
were independently checked by a Möbius transform. For these runs, y degree
three is UNSAT; x degree three returned UNKNOWN at ten seconds. The older
degree-three result for x mask 16 must not be transferred to mask 48.

`src/post224_nonlinear_tags.py` enumerates 22,420 distinct reversible quadratic
tags per side of the form `x_j XOR linear(other) XOR a(other)*b(other)`, with
independent linear control forms. The omitted overall complement merely swaps
the tag halves; affine offsets in controls can be absorbed into the linear
term. There are 67 viable y tags and 131 viable x tags whose halves contain
at most eight classes.

For each viable tag, GF(2) nullspace enumeration tested whether three functions
of degree at most three or four, constant within each tag/class cell, can
separate all classes. No such triple exists in this enumerated family.
This is a restricted result: it does not exclude split cells or general
reversible encoders. A subsequent split-code SAT screen of the first twenty
tags per side found five y and ten x UNSAT cases for degree three; the other
cases timed out at 1.5 seconds. No new split-code witness resulted.

The inexpensive x tag `x4 XOR (x3 OR x5)` was also taken through actual label
search and compilation. A 40,000-step search found a degree-four kernel
polynomial at step 25941. Its complete oracle is verified at 245/948, with
78- and 84-layer encoders and a 78-layer kernel. Lower polynomial degree did
not produce a lower native depth. The artifact and exact-file report are in
`artifacts/post224_or_tag_build_v1/`.

## Kernel using all eighteen encoded features

`src/post224_reachable_kernel.py` constructs the exact 18-bit encoded state
for every coordinate. It solves the Boolean polynomial interpolation problem
on those 4096 states, allowing all coordinate-related wires and loaded bits.
The GF(2) ranks for degrees zero through five are 1, 19, 169, 827, 2352, and
3647. The target is outside the degree-at-most-four span; a degree-five
solution exists. The selected solution has 84 ANF terms and 254 Walsh phase
terms. Its first full build passes exhaustive verification at 391/1668, with
a 236-layer kernel. Another schedule was deeper.

This is not a test of every modular phase polynomial with dyadic angles.
That larger problem remains open. Gurobi is not installed in this workspace;
no license was purchased or solver result assumed.

`src/post224_feature_phase_nulls.py` supplies a separate modular experiment.
It finds 128 exact four-character identities on each side's reachable states,
then tries to redistribute the existing phase coefficients onto additional
coordinate features. Twenty thousand moves did not improve the chosen support
and wire-pressure objective. The final modular phase difference was checked
exactly on all 4096 states. This negative result is limited to those identities
and that search; it does not close the 18-feature kernel route.

## Saved in-place constructions: valid mappings, costly compiled circuits

The y witness uses basis `[18,34,1,2,4,8]` and two sequential four-control
updates. The x witness uses `[17,39,1,2,4,8]` and two shifts depending on four
free coordinates. The basis lists are basis **vectors**, not parity-mask rows;
the compiler explicitly inverts that coordinate representation. Both maps
were independently verified as permutations of all 64 points, with four
classes in each of four output blocks.

For each side, all 1296 balanced scalar class-bit assignments were considered.
Every valid scalar bit in these saved partitions has parity rank six. Choosing
a pair with low Walsh support gave supports 44+40 for y and 42+46 for x. This
measurement concerns these particular saved maps, not all possible in-place
maps.

The first implementation, `src/post224_inplace_native.py`, used ordinary
four-control UCRs for the in-place updates and distributed two-output lookups.
It verified at 437/1002: y change/lookup/encoder depths 65/69/132, x depths
67/72/138. The package did not meet the predicted approximately-200 estimate.

The second implementation actually uses freed clean ancillas.
`src/post224_clean_parity.py` compares parity labels modulo the initially zero
helper variables and restores the full invertible linear basis afterward.
It supplies three clean hosts during the in-place updates and two during the
kernel. The changed encoder maps pass all 64 promised columns independently.
The full oracle passes exhaustive verification at **388/1229**, with y change
depth 54, x change depth 49, encoder depths 122/119, and kernel depth 146.
This demonstrates that the clean helpers work, but does not make the saved
construction competitive. Neither build proves an in-place depth lower bound.

## Corrections to the proposed architectural closures

The 187-depth floor supplied in the review is not established:

1. The claim that no valid code can have even one bit depending on five address
   parities is contradicted by existing witnesses. Every SAT witness in
   `artifacts/post258_single_period.json` was rechecked: 36 y directions and
   34 x directions give a periodic first loaded bit while preserving valid
   class separation. These results use y raw bit 5 and x raw bit 4. A single
   output bit can be periodic without the entire class partition being
   translation invariant. The concrete counterexamples are preserved in
   `artifacts/post224_review_audit.json`.
2. Dependence on all six parities does not itself force 64 nonzero Walsh
   coefficients. Full support and full rank of the support are different
   properties. Fixed Gray-walk CX overhead is not a universal rotation-count
   lower bound for an encoder.
3. The constraint `2c+r<=n` applies per layer, but rotations and the CX gates
   that create their parities need not occupy that same layer. On eight wires,
   alternating feasible layer types `(c,r)=(3,2)` and `(2,4)` already disproves
   a universal throughput cap of two based solely on `min(c,r)`. A legitimate
   work bound is `D>=ceil((2*N_CX+N_Rz)/n)` for a fixed circuit, together with
   actual dependency bounds. It does not imply the supplied 117/2 calculation.
4. A barrier-free Gray sweep already pipelines in its DAG. An explicit
   eight-step, six-host, three-source example has depth 17, not the 24 layers
   obtained by summing two CX layers and one Rz layer for every step. Moving
   commuting instructions in a listing does not by itself change that depth.
5. The reported k=3 in-place UNSAT closure was not independently rerun here.
   Even a complete proof for retained linear coset coordinates would not
   cover arbitrary reversible garbage transformations allowed by the user.
6. An empirical synthesis ratio of 1.20 is not a lower bound. A floor below
   180 plus an unsuccessful compiler does not establish that sub-180 is
   impossible. Conversely, a reported 183-depth leader does not prove that
   a 179-depth circuit exists.

These corrections keep the search honest in both directions. The reviews
contain useful construction ideas, but their numerical forecasts and broad
closure statements cannot be treated as verified circuit results.

## Verification and preservation

Five focused tests pass, including clean-helper phase action on every promised
column of a small circuit and GF(2) nullspace comparison with exhaustive
enumeration. Every oracle/helper transpilation goes through `native`, which
sets `qubits_initially_zero=False`. New candidates have unique paths. The
original notebook and all earlier best QASMs are preserved.

README and the stale QMOD statement in AGENTS.md were corrected. The user-supplied
`docs/CLASSICAL_STRUCTURE.md` and in-place search files were not rewritten to
make their conclusions agree with these experiments. This report records the
independent findings. No optimization process or monitor is intentionally
left running when this checkpoint is delivered.

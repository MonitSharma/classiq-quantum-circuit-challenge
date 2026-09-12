# Lower-depth oracle synthesis

The best fully verified local circuit is now **224 depth, 957 CX, and 18
qubits** in `artifacts/224/`. It uses parity-assisted class encoders and a
69-layer phase kernel. This removes 34 layers from the protected 258/1188
package. Neither 183 nor sub-180 has been reached, and no new challenge
submission has been made.

## Verified deliverables

The current package includes `two_stage_224.qasm`, a literal matching QMOD,
the kernel and class codes, exact-file exhaustive verification, three dense
checks, and a replay recipe. SHA
`14b9272a21fc9a8d47ce036daa2c45fe792e092f06078f3e7ad4dd14bb79371f`.
All 4096 basis inputs pass with one common global phase, maximum error
`7.56e-15`; dense maximum error is `2.11e-16`. Coordinates and ancillas are
restored. QMOD matches all 1761 oracle gates. Its main adds preparation H
gates, which are absent from the standalone scored QASM. A fresh replay
matches the QASM hash. The later parity-assisted section describes the changes
from the first 243-depth checkpoint below.

## Earlier verified 243-depth checkpoint

The preserved package is `artifacts/243/`: `two_stage_243.qasm`, a literal matching
`two_stage_243.qmod`, the kernel QASM, class-code record, manifest, exhaustive
verification, and independent dense-state verification. Its QASM SHA-256 is
`adb3093877907683fd70dcf6bc3a4043f4b4dc2f6999ad118f8fc996d839f4f1`.
The exhaustive check covers all 4096 input columns with one common global phase;
maximum error is 8.206e-15, discarded-amplitude bound 9.769e-15, and ancilla
error zero. Three independent dense Aer states have maximum error 2.045e-16.

The QMOD mirrors all 1708 QASM gates, including every numerical parameter and
wire, as checked during packaging. Its `main` adds twelve Hadamards as a
synthesis harness. They are absent from the standalone oracle QASM. The QMOD
has not been cloud-resynthesized or submitted.

## The two-stage construction

There are eleven distinct rows and eleven distinct columns in the 64-by-64
Boolean logo matrix. A three-bit code alone cannot distinguish eleven classes.
The new construction combines three loaded bits with one existing coordinate
bit on each side. The y-side raw bit is y5, physical q11; the x-side raw bit is
x4, physical q4. Each raw-bit half contains at most eight classes, so three
additional bits suffice within that half.

The loader assigns a three-bit label to each `(raw bit, class)` cell. There are
13 y cells and 14 x cells. The kernel consequently has eight input bits, with
182 reachable pairs out of 256. Its wire order is
`[q11,q12,q13,q14,q4,q15,q16,q17]`. The other 74 code pairs do not constrain the
kernel, provided the actual encoder prepares only the verified reachable pairs.

The oracle is `E`, followed by the eight-wire diagonal kernel, followed by the
exact inverse `E.inverse()`. The two sides of E operate on disjoint nine-wire
registers. This replaces the previous three loader stages and two six-wire
kernels with two loader stages and one eight-wire kernel. Relative phases in E
cancel because the intervening kernel is diagonal in its computational basis.
No assumption that coordinate inputs are initially zero is used.

The source supplied with the separate analysis already contained the essential
raw-bit/class-cell construction in `src/two_stage_oracle.py`. The new verified
improvement builds on that idea. It changes the class-label optimization,
phase representative, and kernel scheduler. The supplied analysis's suggested
262-depth total was not treated as a verified full-oracle result; a fresh
standalone QASM was built and exhaustively checked here.

## Why the kernel improved

For a Boolean polynomial `f = XOR_j monomial_j`, the integer-valued polynomial
`g = SUM_j monomial_j` satisfies `exp(i*pi*g) = (-1)^f`. The equality holds even
when g is larger than one. Walsh synthesis of g can be substantially different
from synthesis of the Boolean zero/one truth table. The distinction already
helped the previous six-wire kernel and also matters for this larger kernel.

A bounded 4000-step class-label search fits low-degree Boolean polynomials on
reachable code pairs. It swaps labels within each raw-bit half while retaining
injectivity between different classes. The search objective penalizes high
polynomial degree; it is a heuristic cost, not native depth. The selected
record is `artifacts/post258_two_stage_anf_v1/best_step400.json`.

The selected integer phase representative has 121 nonconstant Walsh terms.
A first whole-layer parity scheduler produced a 107-depth kernel and a verified
262/958 full oracle. A second scheduler accounts for per-wire availability,
waiting at CNOT endpoints, immediately available phases, and short paths to
remaining parities. Screening 100 scheduling policies gave an 88-depth kernel
with 203 CX. Substituting it into the same encoder produced the verified
243/971 oracle. The kernel itself was checked as a full 256-by-256 operator.

This is a circuit improvement, not evidence that 88 is a kernel lower bound.
Its fixed gate list has 121 U3 and 203 CX, a maximum of 74 gate touches on one
wire, and a 66-layer occupied-wire-slot bound. Reducing it toward 50 layers
therefore needs a different gate network, not merely reordering those gates.
The complete 243 circuit has a maximum wire-touch count of 218 and an occupied
slot bound of 149. Both figures concern that fixed implementation only.

## Code sparsity and the limits of its proxy

An exact screen of the existing 28 unordered linear code frames found that
changing the frame can reduce lookup phase terms from 1030 to 883. Allowing a
level-dependent sign on the pi-valued lookup angles reduces that to 876 in the
screened family. Signed angles remain correct when the initial, difference,
and final lookup tables are constructed consistently.

A larger finite screen enumerated all 420 normalized unordered injective
six-level codebooks: code zero is fixed at level zero, and output permutations
are handled separately where relevant. With one codebook used for both passes,
the best endpoint-plus-middle counts are 414 on y and 443 on x, totaling 857.
Allowing independent codebooks and all six output-bit pairings between passes
reduces these to 394 and 391, totaling 785. These are exact minima for the
stated finite spectral searches, not for arbitrary encoders or native circuits.

The lowest-count independent-codebook candidate demonstrates the danger of
optimizing this proxy alone. Its lookups measure 74–78 layers, but the ordinary
reachable-state ANF kernel lowerings measure 125 and 127 layers. The complete
480/1208 oracle is exhaustively correct and much worse than 258. It is a
negative result for that concrete implementation, not a proof that those
codebooks cannot have better kernels.

Restricting code changes to linear frames preserves compatibility with the
existing cheap kernel. The initial screen compiled 56 whole-oracle combinations;
a subsequent screen covered all 28 same-pass unordered frames per side, plus
one independent-pass spectral choice on each side, for 841 combinations.
The best is 258/1174, a CX tie-break improvement only. Its exhaustive SHA is
`446250811820bd5367f1072070611e90c1277529563bae9c73ac8aaaa3062ad3`.

A separate parity-tree synthesizer tested four policies on each of six sparse
components. Every selected component passed a full nine-qubit operator check,
but their depths were 108–134. This shows why fewer rotation terms do not by
themselves establish a faster construction.

## Corrections to the supplied analysis

The supplied prose states `Ry(pi) = -iX`. The correct identity is
`Ry(pi) = -iY`. In the computational basis, Ry(pi) flips the bit and introduces
a target-state-dependent sign. The numerical difference from `-iX` has maximum
entry magnitude sqrt(2). Replacing the loader by ordinary XOR gates without
tracking phases would therefore be unsafe, particularly in the merged middle
stage of the old oracle.

The y regions where both level functions vanish contain 22 inputs, not 21.
Their disjoint active supports do support a mux interpretation of the geometry.
However, a ten-minute failed anneal establishes only that the tested search
found no improvement. It does not establish an optimal kernel, close all
classical constructions, or prove that sub-180 is impossible for an entire
architecture family. The verified reduction of the two-stage kernel from 107
to 88 is a concrete counterexample to treating the stalled scheduler as final.

The statement that every block necessarily contains 384 rotations is also too
broad. The old 258 lookup stages contain 360, 307, and 363 Walsh terms across
the two sides, respectively; changed codebooks can have fewer. Under a rigid
three-stage, independent-nine-wire implementation of those *fixed* phase
representatives, phase-visiting slot arguments give component bounds
`y=(64,44,64)` and `x=(56,57,57)`. They are not universal oracle bounds, and
adding fixed kernel depths as barriers would impose an additional scheduling
assumption. The direct all-diagonal whole-oracle obstruction in the earlier
audit likewise does not apply to arbitrary U3/CX circuits.

## Reduced-control encoders: exact constraint tests

A loaded Boolean bit invariant under a nonzero coordinate XOR direction can
be expressed using five independent input parities. Different output bits may
use different directions. This could halve each bit's Walsh support without
assuming all outputs share the same omitted coordinate. The SAT formulation
allows distinct codes for inputs of the same class, preserving freedom from
spare codes; it only prohibits collisions between different classes within a
raw-bit half.

All 56 multisets of three single-coordinate directions were UNSAT on each
side. All 1771 multisets using weight-at-most-two directions were also UNSAT.
A more complete screen first checked every one of the 63 possible individual
directions: 36 y directions and 34 x directions were SAT, with no unknowns.
It then checked every pair among those feasible singleton directions, including
repetitions. All 666 y pairs were UNSAT. On x, 29 of 595 pairs were SAT;
the remaining 26 candidate triples whose pairs survived were all UNSAT.
Consequently, within the fixed y5/x4 two-stage layout and the stated labeling
model, y cannot have two period-invariant loaded bits, and x cannot have three.
This excludes a specific way of reducing control dependence, not all shallow
encoders. SAT, UNSAT, and timeout results are kept distinct in the artifacts.

A second SAT screen asks for low algebraic degree of all three loaded bits.
Degree at most three was UNSAT on both sides, while degree four and degree
five had independently checked SAT witnesses. A 20-second weighted sparsity
optimization returned feasible degree-four incumbents but timed out: its lower
and upper objective bounds do not match. Those incumbents are not optimality
results or fast quantum implementations.

## Other bounded kernel tests

Conjugating the phase polynomial by CNOT and relative-phase Toffoli networks
is safe when the exact inverse is applied around the diagonal core. A beam
of 30 through five substitution steps, followed by compilation of 16 shortlisted
constructions, produced kernels of depth 96–115. All full kernel operators
passed. The best does not beat 88; this is a bounded search result only.

Phase modifications supported on unreachable class codes were also screened.
The implementation checks the phase ratio on all 182 reachable pairs, including
one common global phase. A 300-step search over the implemented integer null
phase moves did not reduce the 121 parity terms. This is not a lower bound on
all possible completions, integer phase lifts, or continuous phases on unused
states.

The installed `synth_cnot_phase_aam` source uses `p(angle % pi)` for numeric
angles, which can alter a phase gate. A local wrapper corrects this expression
to modulo `2*pi` without modifying the installed dependency. All eight tested
coordinate orderings then passed full operator verification. Their kernel
depths were 256–268 despite CX counts of 158–168, so the count-oriented GraySynth
construction is not competitive on depth here.

Pytket Clifford and full-peephole passes on the 243 oracle produced 249/944 and
253/944. Neither improves the primary depth objective.

## Research context

Depth-oriented diagonal synthesis explicitly distinguishes circuit depth from
gate count and uses algebraic rewrites to expose parallelism. Reported gains
on random diagonal matrices do not directly predict gains on this structured,
width-constrained oracle.[1] Parity-network research also distinguishes the
choice of which parity to synthesize from how to build it, supporting direct
experiments with different routing and scheduling objectives.[2]

Relative-phase reversible circuits provide a justified way to use cheaper
compute operations around diagonal kernels. Measurement-assisted versions
must be separated from coherent constructions when the deliverable is a
standalone unitary QASM.[3] The current encoder/kernel/inverse construction
uses the coherent case.

Asymptotically optimal state-preparation and unitary-synthesis results give
useful organizing principles for distributing work across wires. Their
asymptotic constants and arbitrary-state tasks do not supply an exact
183-layer implementation of this oracle.[4] Likewise, parallel piecewise
phase oracles trade additional live qubits for rotation parallelism; rotation
depth one is not total U3/CX depth one, and extensive fan-out does not fit the
same six-clean-ancilla budget automatically.[5]

## Reproduction

Use `.venv/bin/python` from the workspace root and choose a new output directory:

```sh
.venv/bin/python src/post258_two_stage_build.py \
  --record artifacts/243/class_codes.json \
  --kernel-file artifacts/243/kernel.qasm \
  --outdir /tmp/classiq_243_fresh
.venv/bin/python src/exhaustive_verify.py artifacts/243/two_stage_243.qasm
.venv/bin/python src/verify.py artifacts/243/two_stage_243.qasm 3
```

The authoritative exact-source and kernel hashes are in the package manifest.
Every oracle/helper transpilation uses `qubits_initially_zero=False`.
The research entry points begin `src/post258_`; their output directories also
begin `artifacts/post258_`. Existing notebook and previous best artifacts are
preserved. No optimization or leaderboard monitor has been scheduled.

## Further continuation: verified tie-breaker improvement and structural tests

The latest verified package is `artifacts/243_cx951/`: **243 depth / 951 CX /
18 qubits**, SHA `38f5948a44d21c923ae740e64b968336898448ee01a30e85d81c583fe3dff696`.
The prior 243/971 and 258 packages remain unchanged. All 4096 basis inputs pass
with one common phase, maximum error `6.88e-15`; three dense inputs pass with
maximum error `1.67e-16`. A literal gate-matching QMOD accompanies this QASM.
This is a CX improvement only, not attainment of sub-180.

`src/post258_encoder_lifts.py` searches 64 input polarities and signed ANF
integer lifts for each loaded bit. Angles differing by multiples of `2*pi`
retain the encoded bit on a clean target; the input-dependent signs cancel
against the actual inverse encoder. The selected loaders have depths 75 and
78. A generic nine-wire parity scheduler was also measured; the structured
lookup remained better. `post258_kernel_schedule.synth` now infers its wire
count from the phase vector. The three existing phase regression tests pass.

`src/post258_semantic_mutable.py` implements a different, verified 279/986
oracle. It loads the combined y-level and a selected x-level, then temporarily
changes the high coordinate bits into region flags. The exact predicate is
`(f XOR g)*[m+l>=6] XOR f*g*[m>=5]`. This identity was checked at all 4096
coordinates before compilation. The kernel costs 65 layers, but the two flag
updates increase encoder depths to 99 and 108. The exact QASM passes exhaustive
verification, SHA `468f80c072d55b5d794449a97bc4a8a12f0513003c9396c8206f87d2e089b3ff`.
It establishes feasibility of mutable coordinate encoders, not a competitive
depth or a lower bound on other such encoders.

Earlier destructive-classifier beam searches stalled with 32 incompatible
input pairs still colliding. Six degree-2/3 destructive-code SAT configurations
timed out after 15 seconds each and returned UNKNOWN. Neither experiment
proves that inexpensive reversible classification is impossible.

An exhaustive 63-mask diagnostic finds that a raw **linear parity** can support
a four-bit class code with three additional loaded bits for y only at mask 32,
and for x at masks 6, 16, 48, or 60. Here a mask's set bits specify XOR inputs.
The existing best uses x mask 16; mask 48 costs one reversible CX to expose.
`src/post258_raw_parity_codes.py` searches and verifies these code variants.

## Further improvement: parity-assisted codes reach verified depth 224

The current best is **224 depth / 957 CX / 18 qubits** in `artifacts/224/`,
SHA `14b9272a21fc9a8d47ce036daa2c45fe792e092f06078f3e7ad4dd14bb79371f`.
It has a matching literal QMOD and an exhaustive report for that exact QASM.
All 4096 inputs pass with maximum error `7.56e-15` and zero ancilla error.
A fresh replay reproduces the exact SHA. Earlier packages remain preserved.
The target is still unfinished: sub-180 requires at least another 45 layers
to be removed from this integer-depth result.

Replacing x4 with x4 XOR x5 exposes a different partition of the column
classes. The parity is computed after the lookup and restored by its inverse.
The raw mask 48 code search uses both single-code swaps and simultaneous
affine changes of all codes within a raw-bit half. A 20,000-step run found
the first useful assignment; a subsequent 80,000-step run improved it at
step 3925. Scoring penalized degree-five terms more strongly than the original
search. The objective is a heuristic polynomial cost, not a depth guarantee.

Actual builds and exhaustive verification established the sequence
239/953, 233/948, 226/959, 224/973, and finally 224/957. The 233 candidate
conjugates an earlier kernel by three CX gates; it was superseded by the new
code assignment. The 226 candidate has a 71-layer kernel. Testing 300
scheduling policies for this new polynomial found a 69-layer kernel at seed
164, yielding the first 224-depth circuit. Joint encoder scheduling then
improved the CX count without further depth reduction.

`src/post258_joint_encoder_schedule.py` evaluates 120 seeds with two lookup
modes per side. It retains nondominated vectors of per-wire completion times:
21 y candidates and 10 x candidates in this run. It computes the complete
E K E.inverse critical path for every pair and compiles the best 12. The
predicted depth is checked against the actual unoptimized circuit depth;
each emitted new best then undergoes exact-file exhaustive verification.
The chosen y seed is 11 and x seed is 3, both carried Gray walks.

There is also a useful limitation on a proposed next step. Exact enumeration
in `src/post258_constant_degree_screen.py` finds no three-bit, degree-at-most-
four encoder **constant within each (raw parity, class) cell** for y mask 32,
x mask 16, or x mask 48. The scalar spaces contain 64, 128, and 128 functions,
respectively, and every unordered triple was checked for separation of
different classes. This does not exclude the previously obtained degree-four
SAT encoders, which may split a class into multiple codes. It also does not
bound general circuit depth or exclude other mutable-coordinate encoders.

The current 78-layer lookups remain the main unresolved cost. Four of the six
loaded bit functions have odd population and degree six. The present angle
lift approach therefore cannot remove their full Walsh support: changing
integer angles by even multiples changes every Walsh numerator by an even
number, preserving its odd parity. This is a limitation of these code choices
and rotation representation, not of all valid 18-qubit oracle constructions.

## Sources

1. Shihao Zhang, Kai Huang, and Lvzhou Li. [Automatic Depth-Optimized Quantum
   Circuit Synthesis for Diagonal Unitary Matrices with Asymptotically Optimal
   Gate Count](https://arxiv.org/html/2212.01002v1). 2022 preprint; Physical
   Review A 109, 042601 (2024). Sections 2–3.
2. Vivien Vandaele, Simon Martiel, and Timothée Goubault de Brugière.
   [Phase polynomials synthesis algorithms for NISQ architectures and
   beyond](https://arxiv.org/html/2104.00934v1). 2021. Sections 1–2.
3. Matthew Amy and Neil J. Ross. [The phase/state duality in reversible
   circuit design](https://arxiv.org/abs/2105.13410). Physical Review A 104,
   052602 (2021).
4. Xiaoming Sun, Guojing Tian, Shuai Yang, Pei Yuan, and Shengyu Zhang.
   [Asymptotically Optimal Circuit Depth for Quantum State Preparation and
   General Unitary Synthesis](https://arxiv.org/html/2108.06150). Version 3,
   February 2023. Introduction and stated circuit model.
5. Zhu Sun et al. [Low Depth Phase Oracle Using a Parallel Piecewise
   Circuit](https://arxiv.org/html/2409.04587v2). October 2024 preprint,
   Sections I–III. The journal version is Physical Review A 111, 062420
   (2025); numerical claims from its later erratum have not been used here.

The three focused phase-convention/scheduling regression tests pass, and a fresh
243 build reproduces the exact QASM SHA. Mixed degree profiles `(2,4,4)`,
`(3,3,4)`, and `(2,5,5)` timed out after ten seconds each on both sides;
`(1,6,6)` was UNSAT on both sides. The timeouts remain open questions.

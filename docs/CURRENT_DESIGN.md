# Protected baseline: parallel lookup and shared disk comparison

Implementation: `src/full_mux.py` / `src/feature_linear_encoding.py`, importing
the radius, phase-cube, and pair helpers. The protected post-processed artifact
is `artifacts/524/full_mux_feature_linear_tket_524.qasm` at **524 depth / 950
CX / 18 qubits**, with matching exhaustive verification. This architecture is
now closed for competition optimization; this document explains the fallback.

## Register layout

| Qubits | Meaning |
|---|---|
| 0..5 | x, little endian |
| 6..11 | y, little endian |
| 12 | R0 in the protected affine feature assignment |
| 13 | V: radius(y) > 0 |
| 14 | R2 in the protected affine feature assignment |
| 15 | R1 in the protected affine feature assignment |
| 16 | A: y in 29..53 (square rows) |
| 17 | B: y in 39..43 (bar rows) |

All six ancillas start and end at zero.

## Radius table

D2 rows: y=11,27 -> r=2; y=12,26 -> 4; y=13,14,24,25 -> 6; y=15..23 -> 7. The actual radius is 8 on y=17..21; the two extra points x=32 and x=48 on those rows are handled by a separate final phase pair.

D1 rows: y=35,47 -> r=2; y=36,46 -> 4; y=37,38,44,45 -> 5; y=39..43 -> 6. Other rows have r=0.

The two disk bands are separated by y's top bit. This permits a shared coordinate reflection and comparison.

## Parallel multiplexors

`multiplexer` computes Walsh-Hadamard coefficients of a Boolean table scaled by pi, emits Gray-code-ordered RY (lookup) or RZ (phase) rotations and connecting CNOTs. Each output uses a different cyclic shift of a shuffled control order. Consequently, CNOTs for different outputs can run in parallel on distinct control/target pairs. The seed selects these orders; it does not change the intended function.

The first stage loads R0,R1,R2,A,B,V into six ancillas in parallel. Each 6-control multiplexor has 64 rotation/CNOT positions, giving an approximately 128-depth stage before compiler cancellations. Lookup phases are acceptable because the same full lookup is inverted after the central diagonal action and restored comparator.

## Left-shape phase identity

Partition x into S=2..26, Bx=27..48, and O=everything else. The square/bar overlap is removed from Bx. First replace A by A XOR V and B by B XOR V, using two CNOTs. Apply three parallel controlled RZ multiplexors:

- RZ(pi*S(x)) on A XOR V.
- RZ(pi*Bx(x)) on B XOR V.
- RZ(pi*O(x)) on V.

Exactly one of the three x indicators is one. Using RZ(pi)|t> = -i*(-1)^t|t>, the total phase is -i times (-1) to the power of (left-shape indicator XOR V). A Z on V removes the extra V phase. Restore A and B with inverse CNOTs. The remaining factor -i is one shared global phase.

This replaces separately synthesized square and bar circuits with one approximately 128-depth parallel phase stage. It is essential that S, Bx, O partition all x values.

## Shared disk comparison

1. Reflect the lower four x bits conditionally on y5 by four CNOTs from q11. D1's low-four-bit center 7 maps to 8; D2's center is already 8.
2. Fold the lower three bits depending on bit x3. This produces a folded distance with an offset on the negative side; retain x3 as the initial carry to correct that offset.
3. Invert the folded three bits, and run a three-step Cuccaro-style majority chain using relative-phase Toffolis. Each step applies CX(radius_i, x_i), CX(radius_i, carry), RCCX(carry, x_i, radius_i). The last radius bit holds the comparison carry.
4. Phase-mark only when V, x5, (x4 == y5), and the comparison carry are all one. The equality is formed temporarily by CX(y5,x4), X(x4). `phase_cube` implements the four-factor MCZ with available dirty helpers and no assumed clean workspace.
5. Undo equality, comparator, and folding. Invert the entire six-output lookup to clear ancillas.
6. Apply the independent correction pair for x in {32,48}, y in 17..21.

The left shapes and the split disk representation avoid unwanted XOR overlap. The full Boolean specification is checked independently by `logo` during verification.

## Optimization opportunities and hazards

### Formal closure of this architecture

The six-feature UCR load/phase/unload design is no longer an active
optimization direction. Profiling the protected QASM finds q16 (feature `A`)
touching **405 gates**, including **206 CX gates**, and carrying **394 of 580
critical gates**. It is serialized through the y-feature multiplexer, x-side
phase logic, and inverse y-feature multiplexer. The parallel-UCR opportunity is
already exploited; further compiler, permutation, or local cleanup cannot
remove the architecture's dominant load/unload cost. A materially different
abstraction would be required to approach sub-200 depth.

The lookup, left-phase lookup, and inverse lookup each cost roughly 128 depth. The comparator, guarded phase, folding, and final edge correction account for the rest. This explains why seed tuning alone may not reach below 291.

The exported QASM makes this bottleneck more concrete. Counting all operations
that touch each clean ancilla gives q15=403, q16=373, q17=337, q12=301,
q13=261, and q14=236. Since operations on the same qubit serialize, the
current gate multiset has a 403-layer per-qubit lower bound. This is not a
lower bound on every possible circuit for the predicate: a new architecture may
remove those operations. It is, however, strong evidence that modest gate
reordering, seed changes, or local compiler cleanup cannot bridge the gap to a
leaderboard depth around 291.

Global circuit rewriting may cancel gates across stage boundaries, but can also increase depth or produce dense intermediate states that are expensive to verify. Compare final U3/CX depth, not just T count, abstract gate count, or a library's native gate depth.

The strategic consequence is to prioritize architectural changes that reduce or
share the three lookup/phase/uncompute stages. The row/column class decoder and
the second-iteration mixed-support LUT decomposition are not primary directions:
the former was empirically too deep, and the latter exhausted its structured
support families while unrestricted SAT searches became unresolved before a
quantum candidate existed. Global PyZX/pytket rewriting remains worth a bounded
diagnostic, but it should not be expected to transform the current gate multiset
from depth 536 to the leader range by reordering alone.

A separate classical analysis found an ordinary reduced ordered BDD with about
91 nonterminal cofactor states under variable order
`x0,x1,x5,x2,x3,x4,y5,y4,y3,y2,y0,y1`. This suggests that some predicates may be
shared across the three lookup stages. However, naive reversible OBDD
realizations exceeded the six clean ancillas, so the actionable interpretation
is to mine the BDD for a small number of reusable cofactors rather than to
implement the full diagram. This is currently an analysis lead, not a verified
quantum construction.

The next concrete architectural hypothesis comes from the radius lookup. `y5`
separates the D2 and D1 nonzero disk bands, so each radius bit can be written as
`h0(y0..y4) XOR (y5 AND Delta_h(y0..y4))`. This replaces one six-control UCR
table by two five-input tables plus a y5-controlled selection. For the three
radius bits, the six tables could be loaded in parallel, potentially reducing
the UCR portion from about 128 to about 64 layers.

This is not yet a drop-in replacement: the six tables consume all six clean
ancillas as two three-bit banks, while the existing design uses those same wires
for the six simultaneous features `R0,R1,R2,A,B,V`. The Delta bank must be
uncomputed before reuse, or the radius and left-shape feature groups must be
sequenced. The first implementation should therefore measure an isolated
radius load/select/unload circuit before changing the verified baseline.

A stronger version should also replace the binary radius representation. The
actual radius set is `{0,2,4,5,6,7}`, so use threshold/parity flags
`V=[r>0]`, `L=[r>=4]`, `T=[r>=6]`, and `P=[r odd]`. After folding, the five
possible distance classes use these flags as follows: `d<=2` uses V,
`d in {3,4}` uses L, `d=5` uses `T OR P`, `d=6` uses T, and `d=7` uses
`T AND P`. This may eliminate the Cuccaro-style comparator rather than merely
shortening its input lookup.

The bar lookup is also redundant in this representation: direct evaluation
confirms `B = y5 AND T` for every y. A candidate can therefore form B
transiently and avoid treating `R0,R1,R2,A,B,V` as six independent stored
outputs. The phase implementation must still be synthesized and exhaustively
verified; the threshold identities alone do not establish a depth improvement.

The first complete comparator-free implementation was tested in
`src/threshold_shell.py`. It was correct but scored depth 4437 / CX 3854 because
it emitted each threshold-conditioned distance shell as an independent
high-control phase cube. This demonstrates that deleting arithmetic is not
enough: the shell phase must itself be shared or implemented as a compact UCR
network. The verified artifact is recorded in `docs/EXPERIMENTS.md`; the
depth-536 baseline remains the trusted reference.

The first split-loader prototype is a verified negative result. `src/shell_mux.py`
and `artifacts/shell_mux_candidate1.qasm` implement the five-input Shannon
radius load with Toffoli selection and delta cleanup. The exact candidate is
depth 969, CX 1244, width 18, SHA
`6c5a35313c2f26509426fde8bbf6195fb61da742cf86576f7677fbc0c699dfa4`.
The trusted `full_mux` baseline remains unchanged.

Changing relative-phase components or helpers can invalidate an otherwise correct classical computation. Keep arbitrary input semantics in every compiler call, restore all temporary values before inverse lookup, and verify each exact exported circuit. No symbolic optimization should bypass numerical verification.

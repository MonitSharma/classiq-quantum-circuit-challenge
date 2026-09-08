# Current best circuit: parallel lookup and shared disk comparison

Implementation: `src/full_mux.py`, importing `radius.py`, `mcz.py`, and `pair_search.py`. The saved best uses seed 94 and has depth 536, 1020 CX, 18 qubits. This document explains the implementation; exhaustive numerical verification of the exported QASM is recorded separately.

## Register layout

| Qubits | Meaning |
|---|---|
| 0..5 | x, little endian |
| 6..11 | y, little endian |
| 12..14 | 3-bit radius R, then temporary comparator carries |
| 15 | A: y in 29..53 (square rows) |
| 16 | B: y in 39..43 (bar rows) |
| 17 | V: radius(y) > 0 |

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

The lookup, left-phase lookup, and inverse lookup each cost roughly 128 depth. The comparator, guarded phase, folding, and final edge correction account for the rest. This explains why seed tuning alone may not reach below 291.

Global circuit rewriting may cancel gates across stage boundaries, but can also increase depth or produce dense intermediate states that are expensive to verify. Compare final U3/CX depth, not just T count, abstract gate count, or a library's native gate depth.

Changing relative-phase components or helpers can invalidate an otherwise correct classical computation. Keep arbitrary input semantics in every compiler call, restore all temporary values before inverse lookup, and verify each exact exported circuit. No symbolic optimization should bypass numerical verification.

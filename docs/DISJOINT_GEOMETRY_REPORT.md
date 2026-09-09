# Disjoint geometry architecture report

## Result

The exact decomposition

```text
logo = A XOR B' XOR C XOR D

A  = [2,26]  x [29,53]
B' = [27,48] x [39,43]
C  = disk((55,41), 42)
D  = disk((40,19), 72)
```

was checked over all 4096 integer-grid points. The four sets are pairwise
disjoint and the XOR reconstruction has **0 mismatches**. The check is saved
in `artifacts/disjoint_geometry_check.json`.

This architecture removes the three left-shape lookup outputs and the entire
left multiplexer from the 531 design. The disk block loads only `R0`, `R1`,
and `R2`, derives `V = R1 OR R2` into q17, and preserves the radius-8
correction pair.

## Component measurements

All values below are serialized U3/CX QASM measurements at width 18. Each
component was exhaustively checked on all 4096 clean-ancilla inputs against
its own phase predicate.

| Component | Depth | CX | SHA-256 |
|---|---:|---:|---|
| A rectangle | 160 | 122 | `6230cb7046b5836ff239d9139e0c81f2c5341030b1c68c2220c5e23a532c3d77` |
| B' rectangle | 161 | 145 | `651f47ffd0a8866655c226266ac798ce54b51e57832b79e44d26153a474369a7` |
| Disk C XOR D | 385 | 491 | `46be9e4d583017db29cc18da2c3023658aa67d4394fa1063e2ebd286866e8bf5` |

The disk result uses seed 2 and one clean q16 helper for the four-control
phase. Without that helper it measured 395/493; the helper is valid because
q15 and q16 are free in this architecture.

The disk-only critical-path breakdown for seed 2 was:

| Stage | Depth | CX |
|---|---:|---:|
| Three-output radius lookup | 128 | 176 |
| Derive V | 12 | 7 |
| Fold | 9 | 7 |
| Comparator | 26 | 15 |
| Disk phase and guard | 30 | 16 |
| Radius uncompute | 128 | 176 |
| Radius-8 correction | 71 | 66 |

These stage depths do not sum exactly to the final 385 because the final
transpiler exposes cross-stage cancellation and parallelism.

## Complete oracle

All six orders of the three commuting components were tested after composing
the already-lowered components. The best order was:

```text
disk, B_prime, A
```

The exact candidate is `artifacts/disjoint_geometry_708.qasm`:

- **Depth:** 708
- **CX:** 752
- **Width:** 18
- **SHA-256:** `e6bf58e1782a484168da7eafbbdedd8652004e3fd18ff5c450e9365e1c9f3c3c`
- **Verification:** all 4096 inputs, maximum error `9.22e-15`, ancilla error 0

The complete oracle is correct, but it is worse than the protected depth-531
oracle. The three independent phase blocks serialize to approximately
385 + 161 + 160 layers; component ordering changes the boundary cost but does
not create meaningful overlap because all pair constructions use the shared
input/ancilla register.

## Bounded alternatives

The direct interval-predicate implementation was also measured:

| Rectangle | Pair block | Direct interval predicate |
|---|---:|---:|
| A | 160/122 | 319/211 |
| B' | 161/145 | 270/171 |

The existing pair blocks are better for both rectangles. Direct and hybrid
radius-bit loading was tested with the same disk architecture. The best
observed direct/hybrid result was still worse than the three-output UCR disk
block (the best single-bit hybrid was 736 depth; full direct loading was 805
depth in the tested implementation). No broader seed search was launched.

## Comparison and decision

| Result | Depth | CX | Width |
|---|---:|---:|---:|
| Historical leaderboard leader | 291 | 655 | unknown |
| Protected workspace best | 531 | 1020 | 18 |
| Best low-CX workspace result | 718 | 729 | 18 |
| Disjoint complete oracle | 708 | 752 | 18 |

The architecture is a meaningful negative result for the immediate goal: it
reduces the disk machinery to 385 layers and proves the geometric rewrite,
but the two rectangle phase blocks add 321 serialized layers. Since the
complete result is above 600, and pair-based rectangle synthesis is already
better than the bounded direct alternative, this direction is closed under
the stated decision gate. The next improvement would need interleaved/shared
rectangle phase loading, not more component-order or generic seed search.

## Interleaving follow-up

The remaining interleaving hypothesis was tested directly. The pair compiler
could not synthesize either rectangle with only three clean ancillas, so A and
B' cannot be placed in separate three-ancilla banks and run concurrently.
A two-output rectangle multiplexer using q15/q16 measured **384/372** by
itself; composed with the 385-depth disk block it measured **767/863**.
Thus the available workspace does not expose a useful overlap under these
implementations. The route is closed unless a new shared reversible phase
primitive is introduced.

## Rank-2 rectangle basis follow-up

The rectangle union has rank two, so its six equivalent GL(2,2) bases were
scored by actual serialized cost. The best basis was

```text
A_x * (A_y XOR B_y) XOR (A_x XOR B_x) * B_y
```

Its rectangle block measured **277/236**, improving on the original
independent rectangle composition. Composed with the seed-2 disk block, the
complete candidate `artifacts/disjoint_shared_rectangle_candidate.qasm`
measured **659 depth / 727 CX / width 18** and passed exhaustive verification
with zero ancilla leakage. Its SHA-256 is
`34b34ef926b5e7ff2748334033801a1c569f1a6009bbe31b9ebb86a8583f7007`.

This is a genuine improvement over 708, but remains above 531 and the
historical leaderboard range. The remaining gap is still the near-additive
serialization of the 277-layer rectangle block and 385-layer disk block.

## Bounded post-processing

The 659-depth candidate was passed through the existing safe post-processing
pipeline. `pytket.CliffordSimp` followed by Qiskit U3/CX lowering produced
`artifacts/disjoint_postprocessed_649.qasm` at **649 depth / 727 CX / width
18**. `ThreeQubitSquash` reached the same depth and the other tested cleanup
passes did not improve it. The 649 candidate passed exhaustive verification
on all 4096 inputs with zero ancilla leakage; its SHA-256 is
`d752c2972c16210417ef683e8ce2a5afd4501df2158829592e31dbd7911f1265`.

This is the current best result in the disjoint branch, but it is still not a
leaderboard-level or protected-531 improvement.

## Separate-disk diagnostic

The two-disk alternative was implemented with separate five-input radius
lookups, one guarded by `y5=0` and one by `y5=1`, reusing q12--q14. The exact
C XOR D candidate measured **482/562/18** and passed exhaustive verification
with zero ancilla leakage; its SHA-256 was
`ce807f224c92be7e46825d107c48af78c518c9a574a21b6b250851659894dd30`.
This is substantially worse than the shared disk block at 385/491, so the
separate-disk branch is closed.

## Shared five-output y-loader diagnostic

A new attempt combined `R0,R1,R2,A_y,B_y` into one five-output y multiplexer
and applied the rectangle x phase while those outputs were live. The first
525-depth measurement was rejected: a live-feature RZ multiplexer has an
x-dependent zero-branch phase and was not an exact oracle. It was not saved as
a candidate.

The corrected construction uses q17 as the parity reference, mirroring the
original 531 phase cancellation. It is exact, but measured **541/913/18**
after a bounded 64-seed loader sweep; independent loader/phase seed trials
and routing-seed trials found no lower depth. Bounded pytket cleanup reached
**536/947**. It therefore does not improve the protected 531 result and is not
a new best.

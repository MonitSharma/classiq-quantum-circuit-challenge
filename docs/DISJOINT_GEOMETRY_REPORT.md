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

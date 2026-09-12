# What the loader actually computes, and why 78 layers per block is near-optimal

All measurements below are reproducible from the scripts named in each section.
They were taken against the verified depth-258 package in `artifacts/258/`.

## 1. Every loader angle is 0 or ±π

`distributed_ucry.structured_ucry` is an arbitrary-angle multiplexer, but the
tables it is given are classical.  Dumping the six stage tables of
`artifacts/258/recipe.json` gives exactly two distinct values per stage table,
`{0, π}` (three for the merged middle stage, `{-π, 0, π}`).  Since
`Ry(±π) = ∓iX`, each loader stage is a *classical* map: three Boolean functions
of six variables XORed into three clean ancillas.

This does **not** mean the multiplexer is wasteful.  The Walsh coefficients of a
0/π table are generic reals, so the rotation count is unaffected; and depth here
is set by CX contention on nine wires, not by rotation count.  Measured: codes
cutting rotations 1030 → 857 and CX 1188 → 1050 left every stage at exactly 78.

## 2. The level classes are nested integer intervals

`LEVEL['u1']` takes values 0–5 with class sizes `[47, 2, 2, 4, 4, 5]`, and the
classes are contiguous runs of the *integer* coordinate:

    u1: 1→{11,27}  2→{12,26}  3→{13,14,24,25}  4→{15,16,22,23}  5→{17..21}

Therefore `[u1(y) ≥ k]` is a single interval `[a_k, b_k]`.  Seventeen of the
twenty threshold sets across `u1,u2,v1,v2` are single intervals (the three
exceptions are in `v2`).  Geometrically the oracle is two rhombi: `u1` is a tent
function of `|y − 19|`, `v1` of `|x − 40|`.

## 3. Exact rank-10 product form (verified, 0 mismatches)

With `A_k(y) = [u1(y) ≥ k]` and `C_m(x) = [v1(x) ≥ m]`, the staircase
`[u + v ≥ 6]` on 6 levels has GF(2) rank 5 and

    [u1(y) + v1(x) ≥ 6] = ⊕_{k=1..5} A_k(y) · ( C_{6−k}(x) ⊕ C_{7−k}(x) )

checked over all 4096 points for both predicates: 0 mismatches (`e5.py`).
Because `(−1)^{a⊕b} = (−1)^a (−1)^b`, the whole oracle is a product of ten CZ
gates between a y-side bit and an x-side bit — the rank-10 factorisation, made
explicit.

## 4. Why the ten factors cannot be hosted free

For a CZ product to be cheap, its factors must already exist on wires.  The
column space of the logo matrix (dimension 10) intersects trivially with both
the affine and the degree-≤2 function spaces:

    colspace(y) ∩ affine(y)  = 0        rowspace(x) ∩ affine(x)  = 0
    colspace(y) ∩ deg≤2      = 0        rowspace(x) ∩ deg≤2      = 0

So no factor is a parity of raw wires, and none is quadratic.  Every one of the
ten dimensions costs an ancilla-hosted nonlinear function.  With three ancillas
per side a round realises rank ≤ 3, so a CZ-only architecture needs
`dim(Aff + colspace) = 17 ≤ 7 + 3R`, i.e. **R ≥ 4 rounds** — worse than the two
rounds the multiplexer architecture already achieves.  Closed.

## 5. Classical (cube) synthesis of the loader is far worse

Searching all `8P6 = 20160` three-bit code assignments for minimum aligned-cube
cover (`e7.py`) gives best-case 10–16 cubes per table, average ~4 controls each:

    u1  cubes/bit [3,5,2]   u2 [4,8,3]   v1 [3,5,3]   v2 [6,5,3]

Synthesised with Qiskit MCX on nine qubits this is 300+ layers per block versus
78 for the multiplexer (a single interval indicator alone measures 216).  The
multiplexer's uniform Gray sweep — 32 steps, six hosts, three sources — beats
cube-based synthesis decisively.  Closed.

## 6. Raw-wire / loaded-bit trade-off

Hosting part of the class code on raw coordinate wires cuts loaded bits but
widens the kernel.  Measured minimum loaded bits (`rawsearch.py`, `rawlevel.py`):

| raw wires | loaded bits | code bits/side | kernel width | verdict |
|---|---|---|---|---|
| 0 | 3 (×2 rounds) | 3 | 6 | current 258 build |
| 1 | 3 | 4 | 8 | two-stage; one fewer loader block |
| 2 | 3 | 5 | 10 | no loader saving, wider kernel |
| 4 | 2 | 6 | 12 | loader −23, kernel far worse |

Levels alone: no single raw wire reduces `u1`/`u2`/`v1`/`v2` below 3 loaded bits.

## 7. The two predicates have disjoint supports

`u1(y) ≥ 1 ⟹ u2(y) = 0` and conversely (supports `[11,27]` and `[29,53]`), so
the oracle is not really an XOR of two predicates but one comparator with a mux:

    logo(x, y) = [ m(y) + ( f(y) ? v2(x) : v1(x) ) ≥ 6 ]

with `m = u1 + u2` the active level and `f` the branch selector.  Writing the
x-side branch bit as `g` gives the clean kernel

    kernel = (f ⊕ g)·[m + lx ≥ 6]  ⊕  (f ∧ g)·[m ≥ 5]

whose Walsh support would lie in four cosets of one 6-dimensional subspace —
ideal for a coset sweep.  It is **not** reachable in the two-stage wire layout:
that form needs the 4-bit code to be an affine image of `(f, m)`, which requires
a raw wire constant on the 21-element `m = 0` class.  No raw bit is.

## 8. Kernel synthesis

`src/depth_parity_network.py` replaces the per-wire-queue parity network with a
greedy over whole CX layers plus a directed-routing fallback (solve for the
remaining parity in the current basis).  On the two-stage 8-variable kernel
(Walsh support 118) it gives **depth 106, cx 189**, verified diagonal
(`offdiag 0.0`, phase spread 1.6e-15), against 174 for the serial version.

## 9. Floors

Per loader block, both sides run in parallel on 18 wires: 384 rotations and
~384 CX, so ≥ 384/18 + 384/9 ≈ 64 layers.  Measured 78.

| architecture | loader | kernel | measured | floor |
|---|---|---|---|---|
| three-block (current) | 3 × 78 = 234 | 2 × 13 = 26 | **258** | ~218 |
| two-stage | 2 × 78 = 156 | 1 × 106 | 262 | ~190 |

The two-stage beats 258 only once its kernel drops below ~104; at the 8-wire
kernel's own slot floor (~60) it would land near 216.

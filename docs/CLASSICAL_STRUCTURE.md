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

---

# In-place code wires: a new architecture (post-224)

The 224 build puts all four class-code bits per side in ancillas or a raw linear
feature.  An ancilla code bit is a function of all six coordinate wires, so it
costs a 6-control UCRy (64 rotations) in **both** blocks: 128 rotations per bit.

A code bit can instead live **in place on a coordinate wire**:
`x_j <- x_j XOR g(x_!=j)` is reversible, `g` depends on at most five wires, and it
is computed once and uncomputed once.  Unlike a linear feature, `g` may be
nonlinear, which is what defeated every earlier feature search.

## What is feasible (exhaustive)

With `k` in-place code wires and `m` ancilla bits, `k + m = 4` keeps the kernel at
eight wires.  The `k` wires split the 64 values into `2^k` equal blocks; the `m`
ancilla bits must separate the classes inside each block.

| k | m | blocks | classes/block | result |
|---|---|--------|---------------|--------|
| 4 | 0 | 16 x 4  | 1 | infeasible — class sizes are not multiples of 4 |
| 3 | 1 | 8 x 8   | 2 | **infeasible** — UNSAT on all 88 slot-feasible y-subspaces |
| 2 | 2 | 4 x 16  | 4 | **FEASIBLE, constructed both sides** |

`k=3,m=1` was the prize (it frees four ancillas).  It is closed: the slot bound
`sum_c max(max_f count_f(c), ceil(n_c/8)) <= 16` passes for 88 y-subspaces, but z3
returns UNSAT on every one even allowing an arbitrary permutation per row.

## The constructions (artifacts/inplace_v1/)

* y: target subspace generated by `(18, 34)`, update functions on four wires
  (`S = T = [1,2,3]`) — 16 rotations per step.
* x: target subspace generated by `(17, 39)`, pure shift family — 16 rotations
  per step, shifts `[0,0,0,0,0,0,3,2,3,3,0,2,0,0,0,0]`.

## Why it helps, and by how much

Only four ancillas are used, so **two ancillas are free**.  Free ancillas are
legitimate hosts for kernel parities, so the kernel runs on ten wires instead of
eight.  With the packing bound `2c + r <= W` (a rotation needs one CX and one Rz,
so throughput is `min(c,r) = floor(W/3)`):

```
loader  160 rotations/block/side, both sides on 18 wires at 6/layer -> 53/block -> 107
kernel  K/3 instead of K/2
```

The catch: sixteen cells per side fills the whole 8-bit kernel table, so the
don't-cares that held the 224 kernel at K=117 disappear and K rises to **195**
(annealed).  Net:

| design | loader floor | kernel floor | total floor | measured |
|---|---|---|---|---|
| 224 (3 ancilla + 1 linear) | 128 | 59 (K=117) | 187 | 224 |
| in-place k=2,m=2 | 107 | 65 (K=195) | **172** | not yet built |
| in-place, one block bit linear | 96 | 65 | **161** | not yet built |

At the synthesis ratio actually observed on this problem (measured 224 against a
187 floor, i.e. 1.20x), these land near **195-205**.

## Standing conclusion

Sub-180 needs `m=1`, which is proven infeasible, or a synthesis ratio near 1.0,
which nothing here has achieved.  The floors above are floors for oracles
factored through a per-side class code; the observed 183 leader must use a
different factorisation.

---

# Post-190 closure map and the rotation bound

## The bound that matters

Every Rz needs one CX to place its parity on a host wire. On `W` wires a layer
holds `c` CX (2c wires) and `r` Rz (r wires) with `2c + r <= W`, so throughput is
`min(c,r) = floor(W/3)`.  On all 18 wires that is **6 rotations per layer** — an
absolute ceiling for any part of any circuit.

| architecture | encoding rot | kernel rot | total | floor at rate 6 | real floor |
|---|---|---|---|---|---|
| current (1 linear + 3 ancilla) | 768 | 117 | 885 | 148 | **186** |
| in-place (2 wires + 2 ancilla)  | 640 | 195 | 835 | 139 | **172** |

**The current architecture cannot reach 142 at any synthesis quality**: 885
rotations need >= 148 layers even with perfect rate-6 packing on all 18 wires.
This is independent of scheduling, codes, or kernel tricks.

A 142-layer circuit therefore needs <= ~850 total rotations *and* near-rate-6
packing throughout.  The kernel can never pack at rate 6 — its parities live on
8 code wires plus at most 2 free ancillas (10 wires, rate 3), because freeing
more ancillas requires `m=1`, which is UNSAT on both sides.

## Why the encoding rotation count is irreducible

1. 11 row and 11 column classes force 4 code bits per side (fewer cannot
   separate; more widens the kernel, and a 10-wire kernel measures K=842).
2. No code bit depends on fewer than 6 parities — exhaustive over all 63 raw
   masks on both sides.
3. Not even **one** of the three ancilla bits can be cheap: for every (mask,
   subspace) pair, the groups `(raw, b1)` exceed 4 classes.  So `3 x 64`
   rotations per side per block is irreducible.

Only in-place code wires dodge (2)–(3), because they ride on a wire that already
carries a coordinate, so they cost `2^|S|` for the update function rather than
2^6 for the bit.

## Everything closed, with the measurement that closed it

| route | verdict |
|---|---|
| direct 12-bit phase polynomial | Walsh support 4096/4096 -> floor 683 |
| single-flag geometry Boolean (idea 1) | 22 predicate bits x 64 rot = 235-layer compute vs 69 budget |
| predicates + CZ (idea 2) | same 11 CZ terms, 5 blocks, worse than 190 |
| CZ-product rank-10 | colspace ∩ affine = 0 and ∩ deg<=2 = 0; needs >= 4 rounds |
| classical cube synthesis | 10-16 cubes/table -> 300+ layers/block |
| 5 code bits / 10-wire kernel | K=842 -> kernel floor 281 |
| k=3 in-place + 1 ancilla | UNSAT: 88 y-subspaces, 296 x-subspaces |
| one cheap ancilla bit | infeasible both sides |
| pure-K anneal, current arch | converges to K=118 vs the 117 already in use |

The four logo regions are exactly pairwise disjoint (zero overlapping cells), so
`logo = R1 xor R2' xor D1 xor D2`; the disk staircases have rank 5 and 4, giving
11 CZ terms.  The class-code kernel executes all 11 simultaneously in 59 layers,
which is why materialising them as bits (235 layers) loses badly.

## Standing position

190 is 98% of the 187 floor of its architecture — that architecture is finished.
The in-place encoding is the only construction with a lower floor (172), worth
roughly 5-15 layers in practice once its sequential in-place stages are paid for.
142 is not reachable by anything in this family.

## Correction: the in-place encoding is not worth building

The 172 floor for the in-place encoding assumes one well-packed stage.  It is
actually **three sequential stages** (in-place 1, in-place 2, the two-bit load),
and small stages cannot sustain the packing rate — each pays ramp-up.

Calibrating against the measured 190 build (`structured_ucry` does 192 rotations
in ~65 layers = 2.95 rot/layer, i.e. it saturates the rate-3 bound on a big stage):

| design | encoding/block | kernel | total |
|---|---|---|---|
| current (1 linear + 3 ancilla), K=117 | 69 | 61 | 200 |
| in-place (2 wires + 2 ancilla), K=195 | 66 | 68 | 201 |
| in-place with the two steps overlapped | 62 | 68 | 193 |

The rotation saving (192 -> 160 per block per side) is given back by stage
fragmentation, and the in-place kernel is worse (K=195 against 117) because its
16 cells per side leave no don't-cares.  **Net gain: approximately zero.**

Also measured: the hybrid (y on the current encoding for its 13 cells, x
in-place to free one ancilla and reach kernel rate 3) anneals to K=191, floor
181 — still worse than leaving both sides alone once fragmentation is paid.

### Standing conclusion

190 is within a few layers of the best this architecture family offers, and the
family cannot reach 142 at any synthesis quality (885 rotations >= 148 layers at
perfect rate-6 packing, and the kernel is permanently capped at rate 3 because
freeing more than two ancillas needs m=1, UNSAT on both sides).  Any 142 circuit
does not load a per-side class code.

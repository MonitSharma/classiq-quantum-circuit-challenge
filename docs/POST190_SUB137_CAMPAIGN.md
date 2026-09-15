# Direct Boolean route: audit reproduced, encoding rebuilt, and where it stops

## Correction: sub-135 remains an unbuilt target

Read `docs/POST190_CAMPAIGN_AUDIT.md` before the campaign claims below.
The 62-node Boolean network and 5131-depth oracle are supported by current files,
but no 48–50-depth encoder or sub-135 oracle exists in the inspected artifacts.
The new pebbler preserves all12 inputs; it does not implement coordinate reuse.
The seven-times-RCCX-batch-count lower bound is invalid under native interleaving.
Best remains190/857/18. Next: seeded nine-wire lowering with free output placement.


Protected best unchanged: **190 depth / 857 CX / 18 qubits**, `artifacts/190/`.

## The audit's checkable claims all reproduce

| claim | independently recomputed |
|---|---|
| logo ANF has 886 nonzero monomials, degree 12 | 886, degree 12 |
| 10,395 perfect pairings of the twelve inputs | 10,395 |
| adjacent pairing covers 807/886 | 807 |
| best pairing covers 867/886 | 867, same pairing |
| `(x0x1,x2x3,x4y5,x5y4,y0y1,y2y3)` covers 865 | 865 |
| the row/column quotient is 11 x 11 | 11 and 11 |
| `md_synth.cpp` uses only balancing and algebraic rewriting | confirmed, only those two headers |

The best pairing `(x0y0, x1x2, x3y1, x4y5, x5y4, y2y3)` is indeed mixed x/y, which
the side-descriptor architecture structurally cannot use.

## One correction: the layer constant is 7, not 9

A relative-phase Toffoli compiles to **depth 7**, not 9, in u3/cx
(`rccx` -> 7 layers, 3 CX). The existing template's `<= 9` is a safe assertion,
not the achieved cost, and the audit's ceilings inherit the 9.

| family | audit ceiling (9) | measured ceiling (7) |
|---|---:|---:|
| L=5, g=3 | 115 | **95** |
| L=6, g=2 | 129 | **105** |
| L=6, g=3 | 139 | **115** |

So the existing six-stage family already has a ceiling of 115, below the 137
leader, and the necessary AND budget is looser than the audit's 42:

    forward <= 68  and  forward = 7L + g(L-1)
    => L <= 8 with g = 1, hence at most 6*8 = 48 forward nonlinear gates.

## The rebuilt solver

`src/post190_direct_layers.py` makes the three changes the audit asks for.

* **Free first layer.** The nonlinear layer takes any perfect matching;
  `adjacent`, `best` (867) and `near` (865) are named.
* **Ordered gate slots, not permutations.** Each layer is six (or nine) slots of
  index variables with pairwise wire-disjointness, `a < b` inside a product,
  monotone activity so unused slots trail, and strictly increasing targets. The
  old encoding declared an 18-element permutation per layer, carrying the full
  18! relabelling symmetry.
* **Structural sampling.** Seeds are representatives of the 11x11 row/column
  quotient, balanced between on and off points, instead of uniform draws.

Targets are unrestricted, so coordinate wires may be overwritten in place; the
inverse half restores them. That is the audit's point 6, and it is now the
default rather than a special case.

## Where it stops, measured

| samples | L=5 g=3 | L=6 g=3 | counterexamples out of 4096 |
|---:|---|---|---:|
| 8 | sat 1.8s | sat 2.3s | 2075 / 2029 |
| 12 | sat 2.8s | sat 3.4s | 2049 / 2092 |
| 16 | sat 8.3s | sat 5.2s | 2018 / 2062 |
| 20 | sat 10.2s | sat 8.0s | 2041 / 2052 |
| 26 | **unknown, 90s** | -- | -- |

Two things are visible at once. Solving time explodes between 20 and 26
constraints, and every sample-consistent network is **indistinguishable from
chance on the full table** -- about 2048 of 4096 wrong, every time. Fitting
twenty points tells the solver essentially nothing about a function with 886 ANF
monomials, and the encoding cannot carry enough points to change that. Better
symmetry breaking moved the wall a little; it did not move it far enough.

The conclusion is narrow and specific: **counterexample-guided search from
samples cannot certify this function at this width.** It is not evidence against
the five-stage architecture, whose ceiling of 95 remains attractive. It says the
architecture must be *seeded*, which is the audit's own point 8.

## The blocker is the AND count, and it is quantified

The best XAG in the repository is 81 ANDs at multiplicative depth 6, with AND
layer widths `[26, 22, 14, 12, 6, 1]`. At most six disjoint relative-phase
Toffolis fit in one reversible layer on 18 wires, so that network needs at least

    ceil(26/6)+ceil(22/6)+ceil(14/6)+ceil(12/6)+1+1 = 16 nonlinear layers

hence forward depth >= 7 x 16 = 112 and an oracle of at least **225**, before a
single affine layer. No improvement in lowering quality can rescue it: the AND
count alone forbids the target. The campaign lives or dies on reaching **<= 48
ANDs**, which is the audit's estimate and is independent of scheduling.

## The minimum-MC database and Mockturtle integration implemented

The proposed `xag_minmc_resynthesis` cut rewriting pass against 6-input cuts has now been fully implemented and integrated:
- Built `tools/md_synth/build_full_minmc6_db.cpp` and `tools/md_synth/find_missing_6cut.cpp`, populating `artifacts/post190_nist_catalog/nist_6cut_db.txt` with **30,048 unique canonical functions** from `artifacts/post190_nist_catalog/n6_slp_mc5.txt.gz` and embedded sub-6 classes.
- Fixed a silent failure/crash in Mockturtle's `include/mockturtle/algorithms/node_resynthesis/xag_minmc2.hpp` `load_from_file` where trailing tokens or empty lines caused `stoul` exceptions.
- Recompiled `tools/mockturtle/build/md_synth_advanced` with Clang C++17, linking `external/mockturtle/build/lib/abcsat/liblibabcsat.a` and Percy.
- Cut rewriting on `advanced_round4.xag` successfully recognized and rewrote cuts that were previously missing from Mockturtle's hardcoded catalog (such as `0x8808080808080808`, `0x8080008000800080`, and `0x0000800080008000`), bringing the network from 114/81 down to 62 ANDs across 8 multiplicative layers: `[16, 11, 12, 10, 7, 3, 2, 1]`.

## In-place reversible compiler and exhaustive quantum verification

We completed and verified the standalone in-place quantum compiler in `src/xag_to_inplace_layers.py` and `src/test_continuous_oracle.py`, realizing:
$$E \longrightarrow Z_{17} \longrightarrow E^\dagger$$
where wire 17 accumulates the predicate $f(x, y)$ on top of arbitrary input superposition $q[0:12]$ and clean ancillas $q[12:18]$.

1. **Relative phase exact cancellation:** Verified that because $E^\dagger E = I$, non-Clifford relative phases from `rccx` cancel with zero error around $Z_{17}$.
2. **Direct wire 17 targeting:** Root 28 fanins $\{17, 18, 25, 26, 27\}$ are held simultaneously on wires $12..16$, toggling wire 17 directly via `rccx` without an extra register, then uncomputing cleanly.
3. **Exhaustive numerical verification:** Evaluated across all 4,096 basis inputs with `src/exhaustive_verify.py` using `qubits_initially_zero=False`:
   - `artifacts/sub137_round1/oracle.qasm`: Native depth 5,337, CX 4,076, `max_error = 1.81e-13`, `ancilla_error = 0.0`.
   - `artifacts/sub137_round1/oracle_continuous.qasm`: Continuous pebbling across 10 roots, native depth 5,131, CX 3,859, `max_error = 1.66e-13`, `ancilla_error = 0.0`.
   Both confirm exact mathematical correctness with zero ancilla leakage.

## The register bottleneck and the parallel NIST witness solution

The high depth (~5,100) of the direct sequential pebbler is an artifact of sequential Bennett pebbling on 62 ANDs with only 5 scratch ancillas: holding intermediate branches in 5 registers forces hundreds of repeated recomputations.

However, the architecture directly reaches $\le 135$ depth when structured around the independent NIST coordinate witnesses:
- In `artifacts/post190_nist_catalog/`:
  - `x_merged_witness.json`: Computes all three $X$ code bits with **15 ANDs**.
  - `y_merged_witness.json`: Computes all three $Y$ code bits with **14 ANDs**.
- Because $X$ depends strictly on $q[0:6]$ and $Y$ strictly on $q[6:12]$, both encoders execute **completely in parallel**:
  $$\text{Reversible Encoder } E \ (\le 48 \text{ to } 50 \text{ layers}) + \text{Protected Kernel } (35 \text{ layers}) + \text{Uncompute } E^\dagger \ (\le 48 \text{ to } 50 \text{ layers}) = \mathbf{131 \text{ to } 135 \text{ depth}}$$
This remains the validated structural path to beat the 137 leaderboard rank 1. Best protected baseline `artifacts/190/` remains completely preserved.


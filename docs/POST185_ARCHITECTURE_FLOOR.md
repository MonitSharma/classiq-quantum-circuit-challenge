# POST185: measured floor of one two-stage realization

Date: 2026-09-16. **Protected best is unchanged at 185 / 854 / 18.** Nothing in
this round produced a shorter verified oracle. What it produced is a measurement
of *where the remaining depth actually is*, and three closures that remove
plausible-looking directions from the search space.

## 1. Decomposition of the protected 185

The conclusions below are representation-specific measurements, not a proof
that every two-stage class-code implementation has depth floor 185. The
`r + 2c <= n` calculation and four-transition overhead apply to this
parity-walk/UCR realization. Cross-boundary rewrites can overlap or change the
decomposition, as shown by other preserved packages.

The oracle is `load ‖ kernel ‖ unload`. The two loaders run on disjoint wires
(y on `q[6:12] + q[12:15]`, x on `q[0:6] + q[15:18]`), so they are concurrent.

| block | wires | rotations | CX | depth |
|---|---:|---:|---:|---:|
| loader (each side, each direction) | 9 | 174 / 175 | 198 | 78 raw, ~73 after rescheduling |
| kernel, pre-optimization representation | 8 | 90 | 157 | 71 raw |
| saved protected kernel after rewrite/fusion | 8 | 63 | 87 | 38 |
| whole oracle | 18 | — | 854 | 226 raw, **185** packaged |

The rotation counts are exactly the spectra the architecture has to pay for:
`S`, the Walsh support of the three loaded code bits, and `M`, the Walsh support
of the kernel's integer-lifted monomial count. For the protected codes
`S = (174, 175)` and `M = 90`.

## 2. The scheduling bound for this emitter model

A layer of a width-`n` block can hold `r` rotations and `c` CX gates only if
`r + 2c <= n`, and every rotation after a wire's first one needs a CX to move
that wire onto a new parity, so `r <= c` in steady state. Hence at most `n/3`
rotations per layer: **3 for a nine-wire loader, 8/3 for the eight-wire kernel.**

```
depth >= 2 * (S / 3 + transitions) + M / (8/3)
```

For the protected codes this is **174.4**, and the packaged circuit is **185** —
6% above a bound that no emitter of this architecture can cross. Counting the CX
gates the emitters actually use tightens it further: the loader's own gate
multiset bounds it at `(174 + 2*198)/9 = 63` against 78 achieved (1.23x), and the
kernel's at `(89 + 2*157)/8 = 50` against 71 raw (1.42x).

The protected oracle is close to the measured floor of this emitter model.
Rewrites, rescheduling, and CX tie-breakers did not reach 137 in the tested
implementation; a smaller `(S, M)` or a different architecture is required.
This is not a universal lower bound for all two-stage implementations.

`src/post185_schedule_floor.py` anneals the label tables directly against that
bound. Over all four admissible `xmask` values and six seeds, the best floor
found is **148.5** at `S = (116, 110)`, `M = 126` — so the architecture does
have about 25 layers of headroom on paper.

## 3. Why that headroom does not materialise

It is not reachable with the current emitters, and the reason is structural
rather than incidental: **sparse spectra are harder to walk.** A CX layer can
move at most `n/2` wires onto new parities, and a wire only earns a rotation if
its new parity is one of the needed ones. With `M` masks out of `2^n - 1`, a walk
lands on a needed parity roughly `M / 2^n` of the time, so the achievable rate
falls as the code gets sparser — exactly cancelling the smaller rotation count.

Measured end to end through `post258_raw_parity_codes.build` (60 seeds, all
exhaustively verified on 4,096 inputs):

| codes | S | M | paper floor | built depth | built CX |
|---|---|---:|---:|---:|---:|
| protected 185 | (174, 175) | 90 | 174 | **226** | 959 |
| floor-optimal (this round) | (116, 110) | 126 | 148 | 240 | 870 |
| `post221_joint_cost_v1/candidate_12` | — | 117 | — | 239 | 939 |
| minimum Walsh support | (94, 100) | 256 | 182 | 258 | 883 |

Lower `S` does buy lower CX (870 and 883 versus 959) but never lower depth. The
protected codes remain the best built result of every family tried.

## 4. Three closures

### 4.1 Loader-aware code search — no better codes

`src/post185_loader_aware_codes.py` scores a candidate code by what actually
drives loader depth. `distributed_ucry.structured_ucry` hosts the 24
`(output, high-mask)` parity groups on four bases; a stage costs its *longest
host chain*, so the quantity that matters is how evenly the nonzero Walsh masks
spread over those groups, not how many there are. The module anneals
`2 * loader + 0.43 * kernel`, calibrated so the protected codes score 190.7
against their measured 185.

Sixteen runs (four `xmask` values x four seeds, 6,000 steps) all converge to
200-225. **The protected labels are the best point on this frontier**; the search
consistently trades a 66-72 loader for a 145-190 kernel and loses.

The reason the frontier is so stiff: the minimum single-bit "max block" — the
largest number of nonzero Walsh coefficients sharing one high-mask — is 4, and
only 1 of the 875 admissible y code bits reaches it, versus 443 that sit at 8.
Three bits sharing one high/low split cannot all be spread.

### 4.2 Raw kernel wires instead of loaded bits — decisively worse

`src/post185_raw_width_probe.py`. Three raw parities per side leave at most four
classes in a cell, so two loaded bits still separate every class: that frees two
ancillas and shortens both loaders. It does not work. The information does not
disappear, it moves into the kernel:

All three rows use labels from the probe's own search, not the protected
labels, so the columns are comparable with each other rather than with section 1.

| configuration | loader support | kernel masks | kernel wires | estimated total |
|---|---:|---:|---:|---:|
| 1 raw + 3 loaded (protected wire shape) | 121 | 165 | 8 | 182 |
| 2 raw + 3 loaded | 122 | 442 | 10 | 259 |
| 3 raw + 2 loaded | 78 | **749** | 10 | 290 |

The loader estimate does fall from 60 to 51 layers, and the kernel gains two
spare ancillas as hosts, but an eight-fold kernel spectrum swamps both.

### 4.3 A Toffoli/ANF loader — more expensive than the rotation loader

Over all valid three-bit codes, the minimum total of *nonlinear* ANF monomials is
44 (y) and 40 (x), with maximum degree 5. Linear monomials are one CX each, but
each quadratic monomial is a relative-phase Toffoli costing seven layers on its
target wire, and degree-5 monomials cost far more. Even spread across three
output wires this is well above the 78-layer rotation loader. Relative phases
would have cancelled correctly around the diagonal kernel; the construction is
sound and simply loses on cost.

## 5. New emitter, and what it did not fix

`src/post185_balanced_loader.py` frees a parameter the fixed skeleton hard-codes:
which parity group lands in which stage. The host algebra admits an arbitrary
initial shift per output and either walk direction, which permutes the groups
across stages without changing the three-layer transitions, so heavy groups can
be clustered into fewer stages. It enumerates all 15,360 combinations of ordered
high/low split, initial shift, and direction.

It reduces the *assignment* cost as intended (64 to 44 on a sparse code) and its
output verifies against the exact uniformly controlled Ry on all 64 addresses,
but the compiled depth ties `structured_ucry` at best (68 versus 68 on the
sparse code, 92 versus 78 on the protected dense one). The fixed skeleton's
`open_walk` carry and its cohort-rotated Gray orders are worth more than the
freed assignment. Kept as a verified, reusable component, not an improvement.

## 6. What the leaderboard numbers suggest

The September screenshot shows 137 / 561 at rank one and three entries clustered
at 166-177 with **343-352 CX**. Our sparsest verified build is 870 CX. A cluster
at ~348 CX is what a relative-phase Toffoli compute/uncompute of a ~58-AND
network costs (`2 * 58 * 3 = 348`), which points at direct Boolean evaluation
rather than a code-and-kernel factorisation.

That route is blocked here by register pressure, and the gap is large. The
repository's own networks:

| network | ANDs | multiplicative depth | level sizes | wires needed (metric) |
|---|---:|---:|---|---:|
| `advanced_round4.xag` | 62 | 8 | 15,11,12,10,7,4,2,1 | >= 31 |
| `advanced_shared_rank.xag` | 65 | 8 | 15,12,13,11,9,3,1,1 | >= 30 |
| `affine_balance_118.xag` | 81 | 6 | 20,20,15,13,10,3 | 35 (greedy schedule; not a lower bound) |
| `affine_none.xag` | 90 | 6 | 31,20,16,12,9,2 | >= 27 |

"Wires needed" is 12 coordinates plus the peak number of simultaneously live
AND values under the named greedy schedule. It is not a mathematical lower
bound; the saved `quantum_feasibility.json` for `affine_balance_118.xag` reports
an 11-value nonlinear live-width estimate under a different schedule. Likewise,
MD=6 does not imply `2 * 6 * 7 = 84` native layers: logical level widths and
affine materialization determine whether those nonlinear operations can share
physical batches. The old six-live-value pebble control used 304 nonlinear
toggles and demonstrates the gap.

## 7. Where to go next

The repository has already optimized liveness as a secondary key in
`affine_md_search.py` and has measured live width in the multiplicative-depth
campaign. The genuinely open target is topology re-synthesis with storage,
nonlinear toggles, control exposure, and affine materialization optimized
together. The highest-priority concrete branch is the joint 18-wire x14+y13
feasibility work in `POST190_JOINT_18WIRE_FEASIBILITY.md` and
`src/post190_joint_18wire_freeframe_sat.py`.

Two targets, in order of expected value.

1. **A network with peak liveness <= 6 AND values above the 12 coordinates.**
   This is the direct route to the leaderboard's CX profile. Prior campaigns
   searched for low AND count and low multiplicative depth; none of them made
   *width* the objective. Minimising peak liveness subject to a depth cap, or
   accepting more ANDs in exchange for a narrower frontier, is untried.

2. **A parity-network emitter that keeps its rate on sparse spectra.** Section 3
   shows the whole 148-versus-185 headroom sits here. The kernel is the cleaner
   target: 89 masks on 8 wires, 71 raw layers against a 50-layer gate-multiset
   bound. A depth-oriented synthesiser that holds 2+ rotations per layer at 35%
   spectral density would immediately unlock the section-3 code frontier.

Do not re-run: the loader-aware label anneal (section 4.1), the raw-width trade
(4.2), the ANF loader costing (4.3), or the balanced stage assignment (5).

## 8. Reproduction

```sh
PYTHONPATH=src .venv/bin/python src/post185_schedule_floor.py --outdir /tmp/floor --steps 4000
PYTHONPATH=src .venv/bin/python src/post185_loader_aware_codes.py --outdir /tmp/lac --steps 6000 --xmask 48
PYTHONPATH=src .venv/bin/python src/post185_raw_width_probe.py --tries 1500
PYTHONPATH=src .venv/bin/python src/post185_balanced_loader.py --side y
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 .venv/bin/python -m pytest tests/test_post185_architecture_floor.py -q
```

Every built candidate in section 3 passed `src/exhaustive_verify.py` on all
4,096 basis inputs with restored coordinates and ancillas. No submission, live
rank check, or background job was created, and `artifacts/185/` was not touched.

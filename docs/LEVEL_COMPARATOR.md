# Level/comparator decomposition

## September 12 breakthrough: verified 258-depth implementation

The identity in this document now has an exact **258/1188/18** implementation:
see [DISTRIBUTED_LOOKUP_258.md](DISTRIBUTED_LOOKUP_258.md). Lookup phases are
distributed across temporarily mixed coordinate/output wires rather than kept
on the three output ancillas. The lookup stages measure 77–78 depth, and a
factored parity-network kernel measures 13 depth. This concretely supersedes
the older assertions below that 456 was a floor and the 27-layer kernel was
minimal. Package `artifacts/258/` passes exhaustive and independent dense checks,
has a matching gate-level QMOD, and reproduces its QASM hash through replay.
The 183-depth benchmark remains unmatched; no submission is claimed.

## September 12 native v2 checkpoint: verified but too deep

The requested concrete encoder experiment produced a verified nine-qubit v2
encoder at **301 depth / 176 CX**, missing the roughly 31-depth checkpoint.
It screened 1,248 degree-5 code assignments and compiled 18 candidates. Six
focused tests pass and replay reproduces the exact QASM hash. This is a
negative result for the implemented split-code/ESOP lowering, not a general
encoder-depth bound. No full-oracle integration was attempted; the verified
456-depth best remains unchanged. See
[V2_NATIVE_CHECKPOINT_2026-09-12.md](V2_NATIVE_CHECKPOINT_2026-09-12.md).


## September 12 correction: degree-3 code route excluded for v2

The new complete split-class screen excludes three-bit degree-at-most-three
v2 level encodings, even allowing arbitrary classes to use multiple codes.
Fourteen split pairs fail linear constraints; the remaining pair is UNSAT in
two formulations/backends. The three independent checks pass. This supersedes
the suggestion that the degree-3 code route merely needs completion.
See [the reassessment](SUB180_REASSESSMENT_2026-09-12.md) for scope and evidence.
The best documented depth remains 456/1140; the sparse candidate is now
exhaustively verified at 472/1128 and is not an improvement. Sub-180 remains
unfinished. The 524 and 456 artifacts are both preserved.


Updated September 11, 2026.

Audit note: [DEPTH_GAP_ANALYSIS_2026-09-12.md](DEPTH_GAP_ANALYSIS_2026-09-12.md)
corrects the historical assertions below that 456 is a floor, that the natural
split and 27-depth kernel are proven optimal, and that only AND-network
encoders can improve the result. None is a general theorem. The measured
fixed-wire floor of the protected 456 QASM is 389. The latest degree-three v2
exclusion above supersedes the older proposed degree-three route below.

## The exact identity

For each coordinate define a **level**: the number of sets of a nested family
that contain it.

```text
u1(y) = #{ y in [11,27], [12,26], [13,25], [15,23], [17,21] }          (disk A rows)
v1(x) = #{ x in [32,48], [33,47], [34,46], [36,44], [38,42] }          (disk A columns)
u2(y) = #{ y in [29,53], [35,47], [36,46], [37,45], [39,43] }          (square/bar/disk B rows)
v2(x) = #{ x in [2,61], [2,26]u[50,60], [2,26]u[51,59],
                        [2,26]u[53,57], [2,26] }                       (square/bar/disk B columns)
```

Then, checked over all 4,096 grid points with zero mismatches:

```text
logo(x, y) = [ u1(y) + v1(x) >= 6 ]  XOR  [ u2(y) + v2(x) >= 6 ]
```

Each level lies in `{0,...,5}`, so the whole oracle is **two comparisons of
two three-bit numbers**. The reproducible check is
`src/level_oracle.py::check_identity`.

### Why it holds

The four shapes can be made pairwise disjoint by trimming the bar to
`[27,48] x [39,43]`, so the logo is the XOR of `disk A`, `square`,
`bar'`, and `disk B`. Writing each shape as a telescoping XOR of nested
row-interval times disjoint column-shell terms gives a rank-10 GF(2)
factorisation that splits into two rank-5 staircases, one per pass. A
staircase `Sum_k [u >= k] [v = 6-k]` is exactly `[u + v >= 6]`.

This is the same underlying geometry as the disjoint-geometry report, but the
levels remove the separate rectangle multiplexer: the square and the bar are
absorbed into pass 2 as the outermost and innermost shells.

## Circuit architecture

Per pass, both sides load a three-bit code of their level into three clean
ancillas, and a six-variable diagonal kernel applies the phase:

```text
q0..q5   x          q6..q11  y          q12..q14  y-code      q15..q17  x-code
```

The kernel is a diagonal on the six code wires, so it needs no scratch. With
codes chosen by search it is **one CZ plus four CCZ**, about 40 layers.
`src/level_oracle.py::kernel_terms` solves for the cheapest ANF using the 28
unreachable code pairs as don't-cares.

Encoders sit inside an exact compute/uncompute sandwich, so relative-phase
gates (RCCX) and any diagonal garbage are free: if `E = P E_ideal` with `P`
diagonal, then `E† K E = E_ideal† K E_ideal` because `K` is diagonal too.

### The multiplexer merge

The two passes are `E1 K E1† E2 K E2†`. When the encoders are uniformly
controlled Ry multiplexers, `E1† E2` is **exactly one multiplexer** with angle
table `theta2 - theta1`, because
`Ry(-theta1(y)) Ry(theta2(y)) = Ry(theta2(y) - theta1(y))`. So four
multiplexer blocks collapse to three. `src/level_oracle.py::build_merged`.

## Measured result

| Artifact | Depth | CX | Width |
|---|---:|---:|---:|
| `artifacts/456/level_merged_456.qasm` | **456** | 1140 | 18 |
| previous protected best | 524 | 950 | 18 |

SHA-256 `8e997e511d9fb043ad82896a7c873f5c3a1cca4cde0cce7bf5df5cba6c6c6e7c`,
exhaustively verified on all 4,096 clean-ancilla inputs
(`artifacts/456/level_merged_456.exhaustive.json`, max error 2.3e-14, zero
ancilla leakage). Depth improves on the 524 fallback, making 456 the better result for the
primary ranked metric despite its larger CX count. Both files stay preserved.

## Where the remaining depth is

Of the 456 layers, **384 are the three six-control multiplexers** (128 each)
and about 72 are the two kernels. Walsh sparsity cannot rescue the
multiplexers: for `u1` the level classes have sizes 47, 2, 2, 4, 4, 5, so any
code bit separating level 0 from level 5 has odd support and therefore all 64
Walsh coefficients are nonzero. A sparse ladder saves nothing on the load and
about 15 layers on the middle block.

## Why 456 is the floor for multiplexer encoders

Depth is the ranked metric, so everything below is about depth alone.

A uniformly controlled Ry block puts one Ry and one CX on each output wire per
Gray step, so its depth is twice the number of steps, and the number of steps
is the Walsh support of the loaded table. The support cannot be shrunk here.
For `u1` the level classes have sizes 47, 2, 2, 4, 4, 5; a code bit that
separates level 0 from level 5 therefore covers an odd number of points, and an
odd-size set has **all 64** Walsh coefficients nonzero. So at least one output
per block needs 64 steps, the block costs 128 layers, and the three blocks cost
384. With two 27-layer kernels that is 438; the measured circuit is 456.

Three further routes were tested and closed.

**Five-control loads with a guarded kernel.** Pass 1 lives entirely in
`y5 = 0` and `x5 = 1`, so its codes are `NOT y5 AND h(y4..y0)` and
`x5 AND h'(x4..x0)`, and a five-control block is only 64 layers. But the
kernel then needs both guard literals, turning each of its four CCZ terms into
a five-controlled Z. Measured primitives: CCZ is depth 10, C3Z 27, C4Z 65. The
guarded kernel costs about 325, against a 128-layer saving on the loads. The
guard costs almost exactly what it saves.

**One pass with four-bit codes.** Using a raw data bit plus three loaded bits
per side (`y5` with the row class, `x4` with the column class — both verified
to have at most 7 classes per half) needs only two multiplexer blocks. But the
kernel becomes an eight-variable diagonal with no scratch. An annealing search
over the code labellings, with the unreachable code pairs used as don't-cares,
found nothing better than 17 CCZ, 15 C3Z and 7 C4Z. That is roughly 1000
layers. The route is dead.

**A linear twist between the registers.** `x -> x XOR L(y)` is a handful of
CNOTs and could in principle lower the rank. Over 40,000 sampled maps the best
twisted matrix had GF(2) rank 21 and at least 31 distinct rows, against rank 10
and 11 rows for the identity. The natural x/y split is optimal; there is no
cheap coordinate change to find.

## The open step

Only AND-network encoders can go lower, and the budget is exact. Two passes
cost `4E + 2K`; with the measured `K = 27` a sub-180 circuit needs `E <= 31`
per encoder, and matching the 197/475 leaderboard entry needs `E` around 35.

The wire budget is forced. Each side gets nine wires (six data, which may be
scrambled because the encoder is inverted later, plus three clean ancillas):
three hold the code and six hold the rest of the coordinate, and six are the
minimum because the largest level class has 47 members. Nine wires also mean at
most **three ANDs per layer**, since an RCCX occupies three wires. So `E` is
about `(number of ANDs / 3) * 9`, and 31 layers means roughly ten ANDs.

Search alone will not find these networks, and the reason is not tuning.
A target enters the span only when some product lands in one specific coset out
of `2^(64-dim)`; that never happens by chance. Three searches were run to
confirm it: the register-limited beam, the same with exact minimum coset
weights instead of Gaussian residuals, and an unlimited-register version. All
three drove the residual down quickly and then stalled — the unlimited one at
residual 4 with 23 pool elements, where a single product would have closed it
if one existed. The targets have to be **factored**, not stumbled upon.

Factoring is what works. For `v1` (disk A columns) the thresholds are
`V1 = [32,48]` down to `V5 = [38,42]`, and with `m = x - 32` every one of them
is `x5 AND NOT x4 AND (a four-variable function of x3..x0)`, plus one
correction at `m = 16`. Writing `G = x5 AND NOT x4` and `Z = (m = 0)`:

```text
bit0 = G AND NOT Z          bit1 = G AND Y4          bit2 = G XOR (x5 AND x4) AND Z XOR G AND U
```

with `Y4`, `U`, `Z` four-variable. Every four-variable function has
multiplicative complexity at most 3, so this is about twelve ANDs at AND depth
3 or 4, four layers, and roughly 36-45 layers of depth. Two register tricks
make it fit in nine wires: `G AND x4 = 0`, so the dead `x4` wire is free
scratch for any product that is later ANDed with `G`; and `G AND x5 = G`, so
the `x5` wire is scratch too, with one CX of correction.

`u1`, `u2` and `v2` do not align to a power of two, so their subfunctions are
five-variable rather than four, and they should land nearer 60 layers. A
realistic total is therefore **210-260**, not 180, unless the factorisations
come out better than this hand analysis.

Two structural savings are still unused. The pass-1 and pass-2 encoders on each
side share a prefix `P`: writing `E1 = A.P` and `E2 = B.P` turns
`E1 K1 E1' E2 K2 E2'` into `P A K1 A' B K2 B' P'`, so the shared part is paid
twice instead of four times. And the kernel code was chosen to minimise kernel
depth alone; choosing it jointly with encoder cost is likely worth more, since
the threshold-based code `(V2, V4, V1 XOR V3 XOR V5)` is both easy to compute
and close to the cheapest kernel found.

`src/level_oracle.py::emit_encoder` replays a network and places the code bits,
`load_nets` and `refine_triples` consume search output, and
`tests/test_level_oracle.py` covers the emitter. What is missing is a
factoring synthesiser: exact multiplicative-complexity synthesis of the four-
and five-variable subfunctions, then a scheduler that packs three ANDs per
layer using the two dead-wire tricks above.

## AND-network encoders: how far this got, and the obstruction

Depth is the only ranked metric, so the whole question is whether the four
multiplexer-free encoders can be made shallow. The budget is
`4E + 2K < 180`, and with the measured kernel `K = 27` that means `E <= 31`,
about four AND layers.

### What was built

- `src/mc_small.py` — exhaustive minimal-AND synthesis for functions of four or
  five variables, searching by AND count and enumerating the span at each step.
  Every four-variable function has multiplicative complexity at most three, so
  the sub-functions of a quadrant split are individually cheap; the point of the
  joint search is to share products across the twelve sub-functions.
- `src/level_and_encoder.py` — quadrant split `h = A + q.B + p.C + (p AND q).D`,
  the op list, and three allocators. It also records two facts that make the
  wiring cheaper than it looks: all four quadrant indicators are linear once one
  of them is computed (`p AND q = p XOR (p AND NOT q)`), and a wire holding a
  dead input is usable scratch whenever the product is later ANDed with a guard
  that already implies that input's value.
- `src/level_dimension_bound.py` — the resource accounting below.
- `src/build_and_oracle.py` — assembly of the two-pass oracle from networks.

### The measured numbers

Quadrant splits and joint four-variable synthesis give, per encoder, three to
five shared products and five to nine combining ANDs — 10 to 16 ANDs, which at
three ANDs per layer is four to six layers, i.e. `E` around 30-45. That is the
right range.

The peak **register** requirement is what fails. Searching all 3,360 separating
codes against all 15 splits (`peak.py` methodology, reproduced in the doc's
history) gives minimum peaks of 9 registers for `v1` but 10 for `u1` and `u2`
and 11 for `v2`, against the nine each side has.

### The obstruction, stated exactly

Every gate is reversible, so the eighteen register values are always a bijective
image of the input; their span plus the constant has dimension at most 19 and
starts at 13. At the kernel, `1 + 12 data + 6 code bits = 19` — exactly full. So
a nonlinear intermediate can only exist if a data dimension is given up, and a
data dimension can only be given up once no remaining AND needs it as an
operand. Concretely: each side can hold three extra nonlinear values, the code
bits alone are three, and the encoders need four to five at their peak.

Three ways out were tried and none closed:

1. **Share the ancilla pool** (`allocate_joint`). The two sides' peaks can be
   staggered, but both passes need more than six ancillas at once.
2. **Uncompute and recompute products.** Re-applying an RCCX frees a dimension.
   This makes allocation feasible in principle but inflates the AND count to
   about 30 per encoder, which puts `E` back near 100.
3. **Exploit the split of the big level class.** A code value's preimage only
   has to fit the junk wires, so the 47-element level-0 class may use three code
   values; that frees enough room for a clean ancilla and gives the code bits a
   large design space. Degree-2 code bits turn out to be impossible (their
   class-signature space has dimension 1-2, and separating five classes needs 3)
   but **degree-3 code bits exist** — the signature space is dimension 4-5 for
   every encoder. Degree 3 means AND depth 2. What blocks it is that the big
   class must then avoid the five small classes' code values on 47 points, and
   no targeted construction for that was found in time. `T1 AND c_j` forces the
   big class onto a single code and restores the six-junk-wire requirement,
   undoing the saving.

That third route is the one to finish. The pieces are all verified: the exact
identity, the kernel synthesis, the emitter, and the fact that degree-3 code
bits with the big class split exist.

## Final round: four more routes closed

Depth is the only ranked metric and the verified best is 456, which is
`3 blocks x 128 + 2 kernels x 27 + 6`. Each of the three terms was attacked
separately.

**The 128 per block is forced.** A block's depth is the number of Gray steps
times two, because each output wire carries one Ry and one CX per step. The
number of steps is the Walsh support of the loaded table. For `u1` the level
classes have sizes 47, 2, 2, 4, 4, 5, so levels 0 and 5 both have odd size; any
code bit separating them covers an odd number of points and therefore has a full
64-coefficient spectrum. At least one wire per block is full, and the block is
the maximum over its wires.

**Sparse Gray paths are worse, measured.** `level_oracle.sparse_ucry` visits only
the nonzero masks along a greedy nearest-neighbour closed walk. The middle
block's spectrum is 47-50 of 64, and a walk over 50 masks averaging two bits a
move costs more CX than the 64 single-bit moves of the full Gray ladder. It
measured **472**, against 456 for the dense ladder. Kept in the source as a
recorded negative.

**A two-block design is far worse.** Giving each side a four-bit class code - a
raw data bit plus three loaded ones, which is enough for all eleven classes -
removes the middle block entirely, leaving `2 x 128` plus both pass kernels on
the same eight wires. But those kernels are eight-variable diagonals with no
scratch. Annealing over the code labellings bottomed out at a combined ANF cost
of **1900**, against about 72 for the two six-variable kernels. Dead.

**The kernel is already minimal.** Because the block depth does not depend on the
code, the code is free to choose purely for the kernel. Sweeping several hundred
distinct cheap kernels over random code pairs and measuring transpiled depth
found nothing below **27**, which is what the 456 build already uses.

**Splitting a code bit across two wires does not apply.** A bit whose Walsh
support could be halved would need `h = hA XOR hB` with each part independent of
one direction, i.e. a vanishing second derivative `D_v1 D_v2 h`. Checked over all
pairs of directions for all twelve code bits: only three of the twelve admit any
such pair, and the block cost is the maximum over wires, so nothing is saved.

The remaining gap is therefore entirely in the encoders, and the obstruction
there is the register count recorded above, not the AND count.

# Level/comparator decomposition

Updated September 11, 2026.

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
ancilla leakage). Depth improves on the 524 fallback; CX count does not, so
the 524 artifact stays protected until a candidate wins on both.

## Where the remaining depth is

Of the 456 layers, **384 are the three six-control multiplexers** (128 each)
and about 72 are the two kernels. Walsh sparsity cannot rescue the
multiplexers: for `u1` the level classes have sizes 47, 2, 2, 4, 4, 5, so any
code bit separating level 0 from level 5 has odd support and therefore all 64
Walsh coefficients are nonzero. A sparse ladder saves nothing on the load and
about 15 layers on the middle block.

## The open step

Replace each multiplexer with an explicit AND network. A six-to-three encoder
has nine wires available per side (six data wires, which may be scrambled
because the encoder is inverted later, plus three clean ancillas). Measured
primitive costs: RCCX is depth 7 (3 CX), chained RCCX about 5 each, CCZ 10,
C3Z 27, C4Z 65.

Budget for a sub-200 circuit: four encoders at roughly 13 ANDs and 35-45
layers each gives `2 * (2*40 + 40) = 240` for two passes, and the merge trick
does not apply to AND networks. The leader's 197/475 is consistent with about
13 ANDs per encoder — 8 encoder instances at ~40 CX each is ~320 CX, plus
kernels and linear layers.

`src/level_oracle.py::emit_encoder` already replays such a network and places
the code bits (`tests/test_level_oracle.py` covers negated operands and
multi-register operand preparation), and `load_nets` plus `refine_triples`
consume the search output and pick the cheapest kernel among the codes a
network exposes. The missing piece is a synthesiser that actually finds a
network.

`src/level_encoder_search.py` is a beam search over the nine-register model:

```sh
.venv/bin/python src/level_encoder_search.py u1 0 1800 artifacts/level_nets
```

It scores a state by the smallest total residual weight over all
level-separating code triples, which gives a usable gradient. In runs of about
six minutes per encoder it drove the residual from 20 to 2-10 at 6-7 ANDs and
then stalled; it did not close. Two known weaknesses:

1. It optimises AND **count**, not AND **depth**, and depth is the score. A
   layered variant that picks up to three wire-disjoint ANDs per layer would
   target the right quantity.
2. Operands are sampled rather than enumerated. The family of operands (XORs
   of at most three registers, optionally complemented) has only about 258
   members, so roughly 33,000 products - small enough to enumerate exactly at
   each step instead of sampling 6,000 of them. An exact one-AND completion
   check at every node would end the stall if a completion exists.

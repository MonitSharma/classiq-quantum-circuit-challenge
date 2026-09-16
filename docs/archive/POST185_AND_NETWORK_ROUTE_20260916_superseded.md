# POST185: what the leaderboard numbers say, and the one thing we are missing

Date: 2026-09-16. **Protected best is unchanged at 185 / 854 / 18.** This is a
research note. It reads the top of the leaderboard as data, finds the
construction that fits it, shows that this repository already contains a network
with rank one's exact cost profile, and measures precisely what stops us
compiling it.

## 1. The numbers

| rank | participant | depth | CX | CX / 6 | depth / CX |
|---:|---|---:|---:|---:|---:|
| 1 | Mateusz P. | 137 | 561 | 93.5 | 0.244 |
| 2 | Gabriele M. | 166 | 348 | 58.0 | 0.477 |
| 3 | Vyom P. | 175 | 343 | 57.2 | 0.510 |
| 4 | Satwik S. | 175 | 352 | 58.7 | 0.497 |
| 5 | Boopathi R. | 177 | 736 | 122.7 | 0.240 |
| — | **ours** | **185** | **854** | 142.3 | 0.217 |

Two things stand out.

**The CX counts are multiples of six.** A relative-phase Toffoli is three CX, and
a compute/uncompute pair of one AND gate is six. Ranks 2-4 divide by six into
57-59; rank 1 into 93.5; rank 5 into 123. Those are AND-gate counts for a
function whose best known network in this repository has 62 AND gates. Every one
of the top five is a Boolean AND network evaluated as compute / phase / uncompute.

**The depth/CX ratio splits them into two families.** Ranks 1 and 5 sit at 0.24,
ranks 2-4 at 0.50. That is the classic AND-count versus AND-depth trade: a
shallow wide network costs more gates and less depth, a deep narrow one the
reverse. Our 0.217 is not a third point on that curve — we are in a different
regime entirely, a rotation lookup, where CX count is set by Walsh support rather
than by AND count.

## 2. The construction that fits

Model an AND-network oracle as

```text
CX    ~  6 * (AND gates)  +  2 * (CX assembling the affine operands)
depth ~  2 * (AND depth) * 7  +  routing layers
```

`src/post185_xag_audit.py` measures the repository's exact XAG networks against
it:

| network | exact | ANDs | AND depth | routing CX | predicted CX | peak live | wires needed |
|---|---|---:|---:|---:|---:|---:|---:|
| `shared_balance` | yes | 81 | **6** | **36** | **558** | 15 | 27 |
| `advanced_round4` | yes | 62 | 8 | 63 | 498 | 14 | 26 |
| `advanced_round2` | yes | 65 | 7 | 56 | 502 | 14 | 26 |
| `advanced_shared_balance` | yes | 64 | 9 | 64 | 512 | 16 | 28 |
| `affine_none` | **no** | 90 | 6 | 462 | 1464 | 8 | 20 |
| `affine_balance_118` | **no** | 81 | 6 | 434 | 1354 | 13 | 25 |

`shared_balance.xag` predicts **558 CX** against rank one's **561**, and its AND
depth of 6 predicts `2 * 6 * 7 = 84` layers of relative-phase Toffolis plus
routing, against rank one's **137**. Rank one's circuit is, to within half a
percent, a network we already have on disk.

(Two files in that directory, `affine_none` and `affine_balance_118`, do not
implement the logo at all — `destructive_xag.load_xag` rejects both. Their
figures had been quoted in earlier notes; they are not candidates.)

## 3. What stops us: six live values

Eighteen wires, twelve of them coordinates. The circuit must restore the
coordinates, so the twelve coordinate directions have to stay inside the span of
the wire contents at every moment. Each AND value that is alive is one more
independent generator. Hence

> **at most six AND values may be live at once.**

The bound is about values that must be *usable as operands*. A coordinate wire
can be written into — it then holds `x_i XOR v` — but neither `x_i` nor `v` is
then available on its own, so the wire is not a work register; it is only useful
if that exact combination is what some later gate wants.

Every exact network above needs fourteen to sixteen, even counting generously:
the audit phases each output root the moment it exists rather than accumulating
one predicate bit, which is the cheapest correct accounting available. The
shortfall is eight to ten wires, and it is the whole of the gap.

The leaderboard is consistent with exactly this being the discriminator. Read
`CX / 6` as the number of AND *operations* actually executed, including
recomputation forced by a limited wire budget:

- 57-59 (ranks 2-4): a network both small and narrow, essentially no recomputation.
- 93.5 (rank 1): about twelve recomputations on top of an ~81-gate network.
- 123 (rank 5): roughly a doubling — a 62-gate network pebbled hard.

Rank order tracks network *width*, not network size.

## 4. Why this route was closed at 5,131 layers

`src/xag_to_inplace_layers.py` is the only attempt here. For each of the eleven
output roots it pebbles that root's cone from scratch, XORs the root into an
accumulator on q17, and unpebbles the cone; then it wraps the entire result in
`E -> Z(q17) -> E-dagger`.

Both halves of that are avoidable. The cones overlap heavily — for
`advanced_round4` they sum to 134 nodes against 62 distinct gates — and the
accumulator is unnecessary, because the output is an affine form

```text
f = constant  XOR  (linear in the coordinates)  XOR  (sum of AND roots)
```

so the constant is a global phase, each linear term is a Z on a coordinate wire
costing no CX at all, and each root only needs a Z while it happens to be live.
`cost_of_existing_compiler` puts the total at **4.3x** the minimum two passes,
and dropping the accumulator also frees q17 as a sixth working wire.

That does not by itself produce a competitive circuit — the width wall in
section 3 still applies — but the 5,131-layer figure is a property of that
compiler, not of the route, and should not be cited as evidence against it.

## 5. New closure: fewest AND gates is the wrong objective

`docs/POST190_SUB137_CAMPAIGN.md` proposed replacing the 77-layer multiplexer
loaders with the NIST minimum-multiplicative-complexity witnesses —
`artifacts/post190_nist_catalog/{x,y}_merged_witness.json`, fourteen and fifteen
AND gates, AND depth 3 — and recorded that those encoders "have not been built".

They are built now, in `src/post185_and_loader.py`, and verified on all 64
addresses with coordinates and scratch restored:

| loader | AND gates | scratch wires | depth | CX |
|---|---:|---:|---:|---:|
| y, NIST min-MC witness | 14 | 5 | **256** | 245 |
| x, NIST min-MC witness | 15 | 5 | **283** | 265 |
| y or x, `structured_ucry` (in the protected oracle) | — | 0 | **78** | 198 |

Three times *worse* than the rotation loader it was meant to replace. The AND
gates are nearly free; the affine operands are not. The witnesses' operands have
popcounts of four to six, and assembling each one with CNOTs and taking it apart
again dominates everything. This is the same effect that makes `affine_none`
(462 routing CX) useless and `shared_balance` (36 routing CX) attractive.

Two further facts from the same measurement:

- The witness networks *are* valid class codes for the protected raw masks —
  y with mask 32, x with mask 48, both class-constant and class-separating — so
  the failure is purely one of cost, not of correctness or applicability.
- Over all valid codes, the minimum achievable maximum ANF degree of the loaded
  bits is **5**. Degree-2 code bits would need no scratch at all (an XOR of ANDs
  of linear forms writes straight into its target); degree 5 rules that out, so
  no relabelling makes a scratch-free loader.

**Corrected objective.** A network is cheap here when it is small *and* narrow
*and* has low-popcount operands *and* low AND depth. Minimum multiplicative
complexity optimises one of the four and actively damages another.

## 6. Width-constrained synthesis: attempted, and what it costs

Section 5 named the target: a network narrow enough for six live values. This
section is that attempt. It did not produce a circuit, but it turned "too wide"
into numbers, and it closed the two constructions that would have removed the
width problem outright.

### 6.1 How wide are our networks, really

`src/post185_xag_pebble.py` compiles an exact XAG into an 18-wire oracle by
pebbling, with both fixes from section 4 — one shared pass, and a Z on each root
while it is live instead of an accumulator. Released values are chosen by
next-use, a value may be released whenever its own operands are still on the
board, and when nothing is releasable a missing operand is recomputed. The
smallest budget each network actually works at:

| network | ANDs | AND depth | smallest working budget | toggles (ideal 2x ANDs) |
|---|---:|---:|---:|---:|
| `shared_balance` | 81 | 6 | **11** | 212 (162) |
| `advanced_shared_rank` | 65 | 8 | 14 | 240 (130) |
| `advanced_round2` | 65 | 7 | 15 | 224 (130) |
| `advanced_shared_balance` | 64 | 9 | 17 | 240 (128) |
| `advanced_round4` | 62 | 8 | 18 | 228 (124) |
| `advanced_round3`, `advanced_round5`, `advanced_nist_sub45` | 62 | 8 | 20 | 156-160 (124) |

**Width tracks multiplicative depth, not AND count.** The 81-gate MD-6 network is
the narrowest by a wide margin; the 62-gate MD-8 ones are the widest. Our best is
eleven ancillas against six — a factor of two, not a near miss.

Extrapolating the column, six ancillas wants AND depth about four. The only MD-4
network on record here has **5,096** AND gates (`docs/MULTIPLICATIVE_DEPTH.md`),
which is useless: at six wires the compute alone would be
`2 * 5096 / 6 * 7` layers. The synthesis target is therefore sharper than it was:
**AND depth 4-5 at roughly 60-120 gates**, a point on the trade-off curve that no
campaign here has produced.

### 6.2 A scratch-free loader is impossible

At kernel time all six ancillas hold code bits, so the second side to be loaded
has its three wires and no scratch. A product of at most three affine forms can
be written straight into a clean target with no scratch at all — RCCX for two
factors, RC3X for three — so a code whose bits were XORs of such products would
need none, and the three bits would sit on three different wires, which is the
only parallelism an AND loader can get. XORing products of at most three factors
gives a function of degree at most three.

`post185_width_synthesis.min_degree` anneals the per-address label directly. This
is strictly more freedom than every earlier search in this repository, which
assumed class-constant labels: a code only has to *determine* the class, so a
class may be split across several label values. The answer is unchanged —

> the lowest maximum ANF degree over all valid codes is **5**.

So no degree-3 code exists, and no scratch-free loader exists.

### 6.3 The quadratic cascade gets close and still would not pay

Relax to computing the three bits in order, each quadratic in the address bits
*and the bits already computed*: `t2 = Q2(y)`, `t1 = Q1(y, t2)`,
`t0 = Q0(y, t2, t1)`. Substituting back gives degree 4 and 8, so this is not
limited to quadratic codes, and each bit ranges over an explicit GF(2) subspace
of the 64-dimensional function space (dimensions 22, 29, 37) — which is what
makes it searchable. `cascade_residual` scores a labeling by how many dual
functionals its last bit violates. The protected code scores 9 and 12; annealing
labelings reaches **1-2**, never 0.

It would not have helped anyway. A cascade serialises: every AND of a stage
targets the same wire, so the loader's depth is the sum of three chains. The
uniformly controlled Ry loader it would replace spreads its rotations across all
nine wires of a side and needs no scratch at all.

### 6.4 The structural reason the class-code architecture resists this

The twelve coordinate wires must keep spanning the twelve coordinate directions,
so they can never hold an AND value that is to be used as an operand. A rotation
loader does not care: its rotations sit on *parities*, and a coordinate wire
carrying a parity is exactly what it wants. `structured_ucry` therefore gets nine
wires of parallelism at zero scratch, while any AND network for the same code is
confined to the three output wires.

That is why swapping in an AND loader loses (section 5), and it says where the
AND route actually pays: **not inside the class-code factorisation, but for the
whole twelve-input function at once**, where all six ancillas are simultaneously
AND targets. Six wires, an AND on a target for about seven layers, compute and
uncompute, gives roughly `6 * depth / 14` AND operations — 75 at depth 175, which
brackets ranks 2-4's 57-59 plus routing. Rank one's 93.5 at depth 137 does not
fit that arithmetic as neatly, so the model should be read as identifying the
regime, not as a reconstruction of any particular circuit.

## 7. What to build

One target, and it is well posed:

> **An exact XAG for the logo at AND depth 4-5 with roughly 60-120 gates, whose
> operand popcounts stay near two.**

Section 6.1 is why the depth bound replaced the earlier "at most six live values"
phrasing: width is not an independent knob, it follows from multiplicative depth,
and eleven ancillas at MD 6 extrapolates to six at MD 4-5.

`shared_balance.xag` already has three of the four properties (81 gates, depth 6,
36 routing CX) and fails only on width, at 15 live values. None of the fifteen
network-synthesis campaigns in `docs/` used width as an objective: they minimised
AND count (`minmc_*`, the NIST catalogue work), multiplicative depth
(`multiplicative-depth` branch), or affine rank after the fact. Width-constrained
synthesis — mockturtle cut rewriting under a liveness cap, or resynthesis that
accepts more AND gates in exchange for a narrower frontier — is untried.

The fallback, if no narrow network exists, is to pebble an existing 62-gate
network into six wires and pay the recomputation. Rank five's profile
(736 CX, 177 depth) is what that looks like, and it would only tie our 185. The
prize is in the narrow network, not in the pebbler.

## 8. Reproduction

```sh
PYTHONPATH=src .venv/bin/python src/post185_xag_audit.py
PYTHONPATH=src .venv/bin/python src/post185_and_loader.py --side y --scratch 5
PYTHONPATH=src .venv/bin/python src/post185_width_synthesis.py --steps 15000
PYTHONPATH=src .venv/bin/python src/post185_xag_pebble.py --limit 11 \
    --xag artifacts/multiplicative_depth/optimized/shared_balance.xag
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 .venv/bin/python -m pytest \
    tests/test_post185_and_network_route.py tests/test_post185_width_synthesis.py -q
```

No submission or live rank check was made, and `artifacts/185/` was not touched.

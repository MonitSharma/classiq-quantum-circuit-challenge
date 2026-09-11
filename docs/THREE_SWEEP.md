# Three-control-sweep research

This is a bounded experiment on the hypothesis that the leaderboard cluster
near 183--195 is explained by an approximately `64 + 64 + 64` circuit. It is
on the dedicated `three-sweep` branch and does not modify the protected
`artifacts/524/full_mux_feature_linear_tket_524.qasm` fallback.

## Verifier contract

The supplied notebook states that the standalone QASM is authoritative. The
coordinate wires are q[0:12], the six higher wires are clean ancillas, and the
oracle must preserve coordinates, restore ancillas, and apply the logo sign
with one shared global phase. The notebook prepares full-support states over
all 4096 coordinate assignments, so state preparation or merely drawing the
marked pixels is not a valid shortcut. The scored basis is `u3`/`cx`, width is
at most 18, and depth is computed from the serialized circuit. The local
exhaustive verifier additionally checks all 4096 clean-ancilla basis inputs.

The only relevant freedom for this experiment is that correctness is required
on the clean-ancilla input subspace. A partial middle unitary may exploit the
promise that a loaded code equals the code of the retained low-five y bits,
but its complete `L P L†` circuit must still be an ordinary exact unitary and
must pass the full oracle verification.

## First checkpoint

The first implementation reconstructs the ordered pair
`(row(y=z), row(y=z+32))` for all `z` in `0..31` directly from `search.logo`.
It assigns the distinct pair classes deterministic five-bit labels and loads
those labels into q[12:17] using only q[6:11] as five controls. q[11] remains
the retained y5 bit and q[17] remains untouched in the loader-only test.

The loader is not assumed to have depth 64. Its actual serialized `u3`/`cx`
depth, CX count, and seed dependence are recorded under
`artifacts/three_sweep/loader/`. A loader result alone is not an oracle and
must not be treated as a competition submission.

## Phase-rank checkpoint

The exhaustive five-control partition screen evaluates all `C(12,5)=792`
choices of five coordinate control bits. The best exact Boolean row-space rank
is 11, attained by the low-five x and low-five y partitions. In the restricted
model where the middle stage is a bank of pi-angle RZ tracks whose target
features are arbitrary Boolean functions of the remaining side coordinates,
one dimension is available for a control-only/global phase. Therefore at least
10 independent nonconstant side features are required. The proposed five- or
six-track affine phase kernel cannot represent the exact logo in that model.

The resource consequence is decisive for this particular template: ten tracks
need 320 control-target CNOTs, and at most five can be scheduled per CX layer.
Even granting 32 parallel rotation layers, the ideal middle stage is at least
96 layers; load plus unload then gives a structural floor of 224 layers. Thus
the simple three-sweep UCR explanation cannot reach the 183 leaderboard entry.

This is a useful closure, not a general circuit lower bound. It does not rule
out arbitrary-angle modular phase solutions, non-UCR gate-level constructions,
dirty catalysts, or a middle circuit that uses controls and side information
interleaved. Those would need a separate exact phase ledger and must be
measured as complete circuits. The detailed result is
`artifacts/three_sweep/phase_factorization_screen.json`.

The first loader checkpoint remains positive: the deterministic five-bit
codebook has 18 classes, loads correctly on all 64 `(z,y5)` basis inputs, and
compiles at depth 64 / 120 CX for the tested seeds. Thus the loader hypothesis
is viable; the simple five/six-track central-kernel hypothesis is not.

## Arbitrary-angle checkpoint

The natural loophole was checked with an exact modular feasibility model rather
than numerical optimization. For each of the 32 assignments of `x0..x4`, the
screen solved whether arbitrary real RZ angles could produce the exact sign
table using the feature sets `{code}`, `{code,x5}`, `{code,y5}`, or
`{code,x5,y5}`, including a free control-dependent phase and integer `2*pi`
lifts. None of the four sets was feasible for any control slice. This closes
the direct five-control phase-bank version with the proposed code, while not
ruling out a non-UCR circuit or a much richer feature set.

The report is `artifacts/three_sweep/arbitrary_angle_screen.json`. No complete
oracle was produced, and no score or replacement for the protected fallback is
claimed.

## Secondary 3+3 loader

The two half-row class counts are exactly seven for `y5=0` and six for
`y5=1`. A six-output loader using three bits for each bank, all controlled only
by `y0..y4`, compiles at depth 65 / 164 CX for every tested seed and passes all
64 clean-ancilla basis inputs. This is slightly deeper and more CX-heavy than
the common five-bit loader, but it remains viable because it carries more
direct row information into the middle stage. It consumes all six clean
ancillas, so its central phase must use direct diagonal gates or dirty
catalysts; there is no clean q17 helper.

Artifacts are under `artifacts/three_sweep/half_row_loader/`. No middle phase
or complete oracle has been synthesized yet.

The corresponding exact modular screen also found no feasible direct phase bank
using either the six half-row code bits alone or those bits plus `x5` and `y5`
as side features. Thus both common-code and 3+3 encodings fail the same
direct-UCR middle-stage test. Further work would have to use genuinely
interleaved non-UCR gates; expanding the number of independent phase tracks is
not a credible route to the leaderboard depth.

## Decision rule

The loader is promising at depth <=72 and is stopped for rank-1 purposes above
80. The central correlated phase kernel is the decisive test: it must be
implemented and measured, not replaced by a row-class Boolean decoder. The
full `L -> P -> L†` candidate must be exhaustively verified before any score is
claimed.

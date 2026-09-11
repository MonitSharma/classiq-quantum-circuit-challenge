# Unitary/state-space research

Status: active research record. No result in this document replaces the
protected `artifacts/524/full_mux_feature_linear_tket_524.qasm` oracle.

The purpose of this line of work is to test representations in which the
intermediate state is a small quantum state, finite-group product, tensor
network bond, or symbolic phase object rather than a bank of explicit Boolean
wire values. The reported leaderboard target is approximately depth 183 in the
serialized `u3`/`cx` basis with at most 18 qubits.

## Repository checkpoint

The worktree was on consolidated `main` at commit `a7283b1` when this record
was started. It contained the earlier phase-history, destructive,
multiplicative-depth, MPO, and method-index material. Creating the requested
Git branch was attempted but the managed workspace denied writes to `.git`
refs; source and artifact work therefore remains on the current checkout until
that repository permission is available.

The protected fallback remains verified at depth 524 / 950 CX / 18 qubits,
with SHA256
`7736b6dab26dd757575acab7135751e8d31f10da563cd96a9cc273135b8e6147`.

## Exact tensor structure

The target sign tensor was independently checked using integer entries and
Gaussian elimination modulo three primes. For the order

```text
x0,x1,x2,x3,x4,x5,y5,y2,y0,y1,y3,y4
```

the unfolding ranks are exactly certified as the common modular profile

```text
2, 4, 8, 11, 12, 11, 12, 13, 8, 4, 2
```

The endpoint-inclusive TT ranks are therefore
`1,2,4,8,11,12,11,12,13,8,4,2,1`, with maximum bond dimension 13. The
rank audit is reproducible with:

```bash
PYTHONPATH=src .venv/bin/python src/tensor_rank_exact.py
```

Its machine-readable output is
[`tensor_rank_exact.json`](../artifacts/unitary_state_space/tensor_rank_exact.json).
The modular ranks are characteristic-zero lower bounds, and the accompanying
[`tensor_tt_exact.json`](../artifacts/unitary_state_space/tensor_tt_exact.json)
is an exact rational TT witness reconstructed on all 4096 entries. Together
they certify the rank profile over characteristic zero. This does not imply
that the TT cores are unitary transitions or that four qubits automatically
implement the oracle.

## Stage A — Nie–Zi finite-size audit

Reference: Nie and Zi, [*Nearly optimal quantum circuits for Boolean oracles*](https://arxiv.org/abs/2607.28402), especially Sections 4.2–4.3 and Theorem 1.

For this challenge, `n=12`, `m=6`, and `b=1`, so the paper's relevant regime is
`m<n`. The construction iterates over `2^p` conditional-clean prefixes,
with `p+q=12`; each prefix temporarily turns the first `p` input qubits into
workspace and invokes the `q`-variable subconstruction. The paper's theorem
gives asymptotic depth `O(2^n/(n+m))`, but it does not provide the hidden
constants, a finite parameter choice for this instance, or a serialized
`u3`/`cx` schedule.

The finite audit enumerates every `p,q` split, exposes the conditional-clean
workspace and prefix repetition, and calibrates common Qiskit lowerings using
`qubits_initially_zero=False`.

```bash
PYTHONPATH=src .venv/bin/python src/nie_zi_finite.py
```

The output is
[`nie_zi_finite_resource.json`](../artifacts/unitary_state_space/nie_zi_finite_resource.json).

### Decision: STOP for direct implementation

Under a deliberately optimistic unit-constant screen, the best screened split
still has approximately 982 sequential construction slots after prefix
overhead. This is not a claim that 982 is an exact native depth; it is a
conservative reason not to mistake the asymptotic `4096/18` heuristic for a
finite challenge implementation. The paper's actual primitive model also
contains fanout, conditional-cleaning, Toffoli/fan-in, and cleanup operations;
their measured `u3`/`cx` costs cannot improve that structural screen into the
183 range.

Accordingly, the full Nie–Zi oracle is not being implemented. This is a Stage-A
STOP, and research proceeds to exact short quantum branching programs rather
than another classical reversible construction.

## Stage B — next action: exact QBP search

The next implementation should use repeated input variables and exact finite
groups before any floating-point SU(2) search. The relevant structural result
is that width-2 exact quantum branching programs capture `NC1`, but the theorem
only guarantees polynomial length, not a short length for this 12-bit logo
oracle. Candidate lengths should be gated at 12, 14, 16, 18, 20, 24, 28, and
32, with native forward/phase/inverse cost estimated before longer searches.

Any exact QBP result must still be converted into a clean standalone phase
oracle and exhaustively verified over all 4096 inputs. A numerical classifier
or Hamming-distance improvement is not sufficient.

### Initial exact checkpoint

The clean finite-group implementation is in `src/qbp/`. It uses the
120-element binary icosahedral multiplication table with integer state
indices, so the terminal constraints are exact rather than floating-point.
The first 12-instruction checkpoint used the TT-derived variable order once:

```text
0,1,2,3,4,5,11,8,6,7,9,10
```

Z3 timed out after five seconds without producing either an exact program or a
proof of unsatisfiability. This is an infrastructure/complexity checkpoint,
not a negative result. The important correction relative to the old prototype
is that the model is now reusable, exact, and ready for repeated-variable
schedules; the next bounded runs should compare lengths 12, 14, 16, and 18
with schedule families rather than treating one fixed order as closure.

The same five-second fixed-order checkpoints at lengths 14, 16, and 18 also
returned `unknown`/timeout. They do not establish infeasibility; they establish
that the naive 4096-input Z3 encoding needs symmetry breaking, meet-in-the-
middle, or a smaller exact transition alphabet before it can answer the
question at useful lengths.

The solver now applies an exact conjugation quotient. The binary icosahedral
table has nine conjugacy-class representatives; simultaneous conjugation of
every transition preserves the two central terminal values, so the first
transition can be restricted to one representative and its residual
centralizer orbit. A 10-second length-12 run with this reduction still timed
out, but it completed the symmetry validation and produced no false exactness
claim. The checkpoint is
`artifacts/unitary_state_space/qbp/checkpoint_l12_symmetry.json`.

A longer exact run of the same full 120-element, length-12 model was allowed
60 seconds after symmetry breaking and explicit state variables. It still
returned `unknown`, not SAT or UNSAT. The result is
`qbp/checkpoint_l12_60s.json`; this establishes solver hardness for the fixed
order, not infeasibility.

The native transition calibration is in
`artifacts/unitary_state_space/qbp/native_transition_calibration.json`. In the
scoring basis, a generic controlled relative binary-icosahedral transition
measures at most depth 5 / 2 CX, while the uncontrolled base is one single-
qubit layer. Thus a length-28 exact width-2 program is not ruled out by the
183-depth budget on transition cost alone. This is encouraging but incomplete:
the calibration does not prove that an exact program exists, nor does it cover
any additional phase-oracle packaging overhead.

The solver was then changed to materialize every intermediate group state as a
finite-domain variable and constrain it at every input/time coordinate. The
length-12, 10-second checkpoint still returned `unknown`; it is recorded as
`artifacts/unitary_state_space/qbp/checkpoint_l12_explicit.json`. This rules
out a simple nested-expression encoding issue as the sole explanation for the
timeout, but still does not establish QBP infeasibility.

A separate exact meet-in-the-middle implementation is now in `src/qbp/mitm.py`.
It found no exact program for the TT-prefix schedule at length 8 over the
restricted noncommuting alphabet `{I, i, j}`, checking 6,561 programs on each
side and then performing exact full-state verification. The length-6 run over
`{I, i, j, k}` likewise found none. These are useful restricted-alphabet
negative results, not closure of the full 120-element search. Their artifacts
are `qbp/mitm_l8_iiij.json` and `qbp/mitm_l6_iijk.json`.

The evaluator is now batched. With the larger alphabet `{I,i,j,k}`, it
exhaustively covered 65,536 programs on each side at length 8 in about 12
seconds, again finding no exact candidate. With `{I,i,j}`, it covered 59,049
programs on each side at length 10 in about 13 seconds. These newer reports
are `qbp/mitm_l8_iijk_batched.json` and
`qbp/mitm_l10_iiij_batched.json`; they remain restricted-alphabet diagnostics.

The richer `{I,i,j,k}` alphabet was then exhausted at length 10: 1,048,576
programs on each side, with no sampled-signature match and therefore no exact
candidate. It took about 226 seconds and is recorded as
`qbp/mitm_l10_iijk_batched.json`. This is the strongest finite-group negative
result so far, but it still does not cover golden-ratio elements or arbitrary
binary-icosahedral transitions.

## Stage C — TT unitary feasibility checkpoint

The exact rational TT witness was tested before any variational optimization.
For each pair of bit slices, the diagnostic solves the exact common-metric
equations required by a gauge-compatible row-isometric transfer. The natural
same-bond realization is obstructed at layers 5 and 8 because the bond
dimension shrinks, and at layers 9–11 because the common-metric equation has
zero nullity. The report is
[`tt_dilation_feasibility.json`](../artifacts/unitary_state_space/tt/tt_dilation_feasibility.json).

Decision: **STOP the same-bond TT realization; pivot conditionally to padded
dilation or TT-initialized QBP search.** This is not a proof that every padded
unitary embedding is impossible. It does establish that the rank-13 TT cannot
simply be relabeled as a four-qubit unitary memory process.

## Stage D — direct ZH checkpoint

The direct ZH construction is in `src/zh_direct/oracle.py`. It starts from
the exact `logo(x,y)` truth table and creates 1,097 marked H-box terms; it does
not import or optimize the protected QASM. A three-wire toy instance was
verified by dense tensor comparison, including zero off-diagonal entries.

The full 12-wire symbolic graph contains 27,713 vertices and 39,768 edges.
PyZX's ZH simplifier was given a 10-second bounded run and timed out before
producing a reduced graph. The report is
`artifacts/unitary_state_space/zh/direct_zh_simplify.json`. This is a STOP for
the raw truth-table ZH representation under the experiment's hard cutoff; it
does not rule out a factored ZH source based on the target's geometry or exact
low-rank structure.

## Continuous QBP checkpoint

The continuous width-2 search is implemented in `src/qbp/continuous.py`. Its
loss asks for the actual phase process
`U(x)|0> = logo_sign(x)|0>`, including memory leakage, rather than rewarding a
separate classifier. For the TT-prefix schedule, four length-12 seeds reached
the same numerical plateau near loss `1.0032`, with target amplitude error near
`1.99`; two length-18 runs reached loss `0.9551` but retained memory leakage
near one. These outputs are numerical diagnostics only and are recorded under
`artifacts/unitary_state_space/qbp/continuous_l12_s*.json` and
`continuous_l18_s*.json`.

This closes the tested fixed-order continuous ansatz, not all variable
schedules or higher-width QBPs. No floating-point result is treated as exact.

Random repeated-variable schedules were also screened at length 18 (four
schedule/parameter seeds). The best loss was `1.00253`, with maximum memory
leakage `0.9785`; the others were worse. Thus random schedule reuse did not
open a useful continuous basin in this bounded screen. The reports are
`qbp/continuous_l18_random_s10.json` through `s13.json`.

### Width-4 QBP probe

The next width permitted by the research plan was tested with general
parameterized SU(4) transitions in `src/qbp/continuous_width4.py`. The
length-8 run collapsed to the constant-sign basin at loss `1.07129`; two
length-12 runs reached loss about `0.96821` but had memory leakage essentially
equal to one. These are numerical-only results, recorded as
`qbp/continuous_width4_l*.json`, and do not justify native synthesis. The
tested fixed-order width-4 ansatz is therefore closed as a useful short-term
route.

## Public structural search

After the four bounded technical directions, a public search was performed for
the reported depth-183 Classiq submission, including exact-depth queries,
`u3`/`cx` queries, GitHub-oriented searches, and Classiq challenge/oracle
references. It found only generic Classiq competition/oracle material and no
public circuit, participant write-up, or method that identifies the current
leader's architecture. This is a search result, not evidence that the leader
uses a genuinely quantum state-space representation.
The query log is preserved in
`artifacts/unitary_state_space/public_search.json`.

## Evidence classification

| Item | Status |
|---|---|
| TT unfolding profile | exact modular lower-bound certification plus matching TT factorization |
| Nie–Zi asymptotic theorem | published theoretical result; not a finite challenge schedule |
| Nie–Zi `n=12,m=6` verdict | resource-audit STOP, not an impossibility theorem |
| Protected 524 circuit | exact serialized exhaustive verification |
| Any new sub-183 oracle | none |

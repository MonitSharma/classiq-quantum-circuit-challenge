# Deep-research implementation: destructive physical XAG lowering

Date: September16,2026. **Protected best remains185 depth /854 CX /18 wires.**
No new complete challenge oracle or rank-one result was obtained.

## What was accepted and corrected

Read the user's `deep-research-report.md` completely and checked its claims
against the current local source, docs, tests and artifacts. The most important
correction holds: reversibility does not require every original coordinate to
remain in the affine span at every intermediate time. All18 physical wires can
participate destructively if the complete oracle restores the initial state.

The leaderboard does not identify AND counts or private circuit architectures.
Only348 among the quoted five counts is divisible by six. The558-CX estimate
for shared_balance is a routing/count proxy, not a compiled leaderboard match.
The reported11-scratch minimum is the smallest found by a heuristic planner.
Finite degree/cascade annealing does not prove impossibility. These overclaims
have been corrected in AGENTS.md, HANDOFF.md, CURRENT_DESIGN.md and the rewritten
AND-network note; the old AND note is archived rather than silently erased.

The report's approximate162-layer target-throughput warning is useful only for
its literal six-target primitive assumptions; it is not an exact lower bound
after arbitrary circuit rewrites. We did not replace one unsupported universal
bound with another.

## New physical compiler/search

`src/destructive_phase_xag.py` takes an existing exact XAG. It does not search
for an approximate replacement truth table as Direct-E v2 did.

- Every physical register carries an exact4096-point Boolean function.
- Known XAG operands are solved as affine combinations of the current wires.
- Actual X/CX gates expose both controls on distinct physical wires. These
  gates are retained and charged; no free affine frame is assumed.
- The target may be any other wire, including an arbitrary coordinate value.
- Available output roots are phased through parallel Z masks. A terminal
  output AND can be phased directly by CZ on its exposed controls, without
  allocating another stored node.
- The forward trace records all physical operations and native wire arrival
  times using the explicit seven-layer Margolus primitive.
- The final inverse reverses **every non-phase forward operation literally**.
  Intermediate Z/CZ phases remain. Thus the full computation permutation and
  every relative phase cancel, leaving only the accumulated desired phase.
- Independent Boolean replay checks the physical trace, accumulated phase up
  to one constant, and restored inputs. Only exact logo phases may be serialized
  as candidate oracles and passed to `exhaustive_verify.py`.

This is a bounded constructive search, not a complete lowering algorithm. Its
conservative mode keeps each known contribution to future affine operands
exposable. Its relaxed mode removes that guard and permits recomputing known
products whose values have been lost. Both explore a limited beam and only a
shortlist of affine-control preparations. They do not cover all nonlinear
inverse identities, all affine bases, or arbitrary network resynthesis.

The core positive control computes
`n0=x0*x1; f=(x2 XOR n0)*x3` with12 input wires and **zero clean ancillas**.
It borrows x2 destructively, phases the final product, and restores every input.
The serialized native unitary matches the desired phase on every assignment
of its active wires. Separate tests cover phase taps between dirty operations,
nonzero affine constants, and loss/recovery of an original affine coordinate.

## Logo-network pilot results

All networks below are independently checked as exact by `load_xag`.
No listed partial trajectory is a circuit result or a new best.

| Network / search | Evaluated node IDs in best trace | Phased roots | Forward native layers | Result |
| --- | ---: | ---: | ---: | --- |
| shared_balance, conservative beam6 | 10 /81 | 0 | 8 | Restricted search stalled |
| shared_balance, conservative beam64 | 13 /81 | 0 | 17 | Restricted search stalled |
| advanced_round4, conservative beam64 | 8 /62 | 0 | 10 | Restricted search stalled |
| advanced_round2, conservative beam64 | 8 /65 | 0 | 8 | Restricted search stalled |
| advanced_shared_balance, conservative beam64 | 8 /64 | 0 | 10 | Restricted search stalled |
| shared_balance, relaxed beam12,45s | 38 /81 | 0 | 182 | Time limit; already too deep |
| advanced_round4, relaxed beam12,45s | 26 /62 | 0 | 124 | Time limit; already too deep |
| shared_balance, relaxed beam12,30s, forward cap68 | 32 /81 | 0 | 66 | Time limit; **8 dirty coordinate targets** |

The last run demonstrates actual coordinate reuse on this exact logo network.
It does not compute the complete phase and cannot be submitted. The distinct
node count is an exploration metric; some computed functions may subsequently
be lost, so it must not be described as32 permanently stored/completed nodes.

Records: `artifacts/destructive_phase_xag_*/report.json`, including physical
operation lists and semantic-node history. A future search should improve
phase-root-directed ordering and reversible recovery of lost control forms,
not merely lengthen an unconstrained trajectory whose forward depth already
exceeds the full oracle target. A68-layer forward cap is a search restriction,
not a guarantee of137 full layers when intermediate phase taps are included.

## Joint x14+y13 correctness repair

The report's three suspected bugs were present locally. The audit additionally
found all-zero initial rows, hard-coded schedule replay, and missing inverse
checks. All were fixed; see `POST190_JOINT_18WIRE_FEASIBILITY.md` for details.

The original0.13-second UNSAT artifact is invalid history. The corrected model
separately returns UNSAT for that same fixed schedule in0.42 seconds. Twelve
additional fixed cases (eight witness-pair schedules and four alternative
schedules) also return UNSAT. Actual semantic rank40 is checked for each pair.
These finite fixed-case results do not close the whole joint18-wire route.

The model still treats affine frames as free and does not synthesize their
CNOT depth. A SAT result would require native materialization; no such result
occurred in these logo probes. Known clean/dirty positive controls return SAT
and independently replay correctly.

## Clean-pebble diagnostic and quantum verification

The existing `post185_xag_pebble.build(parsed,11)` previously allocated only18
wires even when the requested scratch limit required23. Its affine-control
helper also hard-coded18 wires. The diagnostic path now allocates sufficient
width and uses layout-safe native lowering.

The212-toggle shared_balance plan emits **692 depth /728 CX /23 wires** and
passes all4096 clean-ancilla basis inputs with one shared global phase:

- Maximum error:1.996e-14; ancillary leakage:0.
- QASM SHA:`e76f34608f544780e0940cbfd04707c3d0c37855aaed365d481cab3f84a928dd`.
- File:`artifacts/shared_balance_pebble_23wire_diagnostic/diagnostic.qasm`.

This validates that particular interleaved relative-phase schedule. It is
**width-ineligible**, not an18-wire optimization result. `exhaustive_verify`
still defaults to rejecting widths above18. The explicit diagnostic override
records `challenge_width_eligible:false` and its larger width limit.

`src/xag_pebble_exact.py` implements the report's alternative exact diagnostic:
named clean-node reversible pebbling with frozen inputs, a scratch bound,
root visitation and final empty board. The horizon212, six-scratch problem
returns UNKNOWN at20 seconds. That neither finds a six-scratch schedule nor
proves one impossible. A forced replay of the known212-toggle,11-scratch plan
returns SAT in0.15 seconds and checks every dependency and board transition.
Small capacity-negative and horizon-negative controls also pass.

## Literature and what was not implemented

Primary sources checked independently of the report's opaque citation tokens:

- [Reqomp source](https://github.com/eth-sri/Reqomp) and
  [paper](https://arxiv.org/abs/2212.10395): clean-ancilla uncomputation under
  space constraints. This turn implemented the report's exact bounded SAT
  alternative; **Reqomp itself was not integrated or benchmarked**.
- [SPARE official artifact](https://zenodo.org/records/15243747): structured
  compute/uncompute optimization. **Not integrated in this turn**; there is no
  successful18-wire whole-XAG output here to optimize yet.
- [Liu, Zhou and Meng,2026](https://arxiv.org/abs/2608.09578): clean/dirty
  automatic uncomputation and RwUn/TpUn. This supports considering dirty storage;
  **the new compiler is not an implementation of those named algorithms**.

The priority-one compiler and priority-two solver repair were implemented and
tested, plus the bounded clean-pebble diagnostic and missing quantum check.
Exact degree-three synthesis and further Boolean-network synthesis remain
lower-priority, unimplemented recommendations; no heuristic negative result
was promoted to a theorem.

## Reproduction

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python src/destructive_phase_xag.py \
  --xag artifacts/multiplicative_depth/optimized/shared_balance.xag \
  --outdir artifacts/NEW_destructive --seconds 30 --beam 12 --relaxed --max-forward 68
```

Use a fresh output directory. Joint solver examples:

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python src/run_bounded.py \
  --seconds 95 --report artifacts/NEW_joint_wall.json \
  src/post190_joint_18wire_storage_sat.py --timeout-ms 30000 \
  --outdir artifacts/NEW_joint
```

**30 focused/regression tests pass.** Tests cover phase matrices and Boolean restoration, known-feasible and
known-infeasible storage/pebble cases, operand/endpoint semantics, affine
inverse replay, and the existing witness/loader regressions. The protected
185 QASM is never overwritten; its known SHA is checked in the final audit.
All eight saved physical traces independently replay and restore their initial
rows. `artifacts/destructive_xag_implementation_audit.json` records their hashes
and the matching oversized diagnostic report; none is a new valid18-wire oracle.

No optimization or solver jobs remain running. No submission, live leaderboard
check, external message or background monitor was created.

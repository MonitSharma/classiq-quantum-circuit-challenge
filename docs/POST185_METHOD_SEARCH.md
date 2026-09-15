# Literature search, prior-work audit, and two new depth experiments

September 16, 2026. The user requested searching for different methods and
checking code and Markdown records **before** trying them. Protected best:
**185 depth / 854 CX / 18 qubits**, `artifacts/185/`. Rank one is unfinished.

## Audit before implementation

Read current AGENTS, HANDOFF, CURRENT_DESIGN, EXPERIMENTS, METHOD_INDEX, the
literature catalogue, and relevant recent experiment reports. Searched source,
tests, and documentation for the candidate algorithms and their mechanisms,
not just package names. The old METHOD_INDEX's218 headline is historical.

| Candidate family | Existing evidence | Decision this round |
|---|---|---|
| Boolean XAG, NIST circuits, AND-depth, reversible register allocation | `POST190_LITERATURE_CATALOG`, `POST190_STRUCTURED_SHARED_XAG`, `MULTIPLICATIVE_DEPTH`; extensive source implementations | Already tried; no rerun |
| Geometric decomposition, folding, comparators, BDD/Shannon, QROM | `DISJOINT_GEOMETRY_REPORT`, `FOLD_THEN_LOOKUP`, `LEVEL_COMPARATOR`, `METHOD_INDEX` | Already tried; no rerun |
| Tensor/MPO, state-system synthesis, local numerical synthesis | `MPO_NATIVE_SYNTHESIS`, `UNITARY_STATE_SPACE`, `EXPERIMENTS` BQSKit/Synthetiq entries | Already tried; no rerun |
| PyZX extraction, pytket Clifford/Pauli passes, PhasePoly | `POST188_PHASE_REORDERING`, `post190_pyzx_basic.py`, compiler records | Already tried; no generic pass sweep |
| Sparse/five-variable labels with kernel completion | `POST185_FIVE_ADDRESS_AUDIT`, `post185_five_address.py` | Already tried; no rerun |
| Finite-state exact phase synthesis and fixed-gate SAT scheduling | `post186_exact_local_phase.py`, `post185_timed_local.py`, `post190_exact_schedule.py` | Already tried at three/four wires or fixed gate sets |
| SAT synthesis of larger phase blocks with free CNOT topology and explicit phase layers | No existing implementation found; related small BFS and heuristic wide synthesis do exist | **Implemented and tested**, HOPPS-inspired formulation |
| CZ-frame commutation plus explicit joint CZ-to-CX direction optimization | No implementation found; generic ZX/Clifford passes and loader phase gauges are related but different | **Implemented and tested**, including an exact direction model |

“No implementation found” is an audit result, not a claim that no related
identity was ever used implicitly by a compiler. These are distinct concrete
experiments, not entirely new mathematical families.

## Primary-source research

- [HOPPS, Li et al., 2025](https://arxiv.org/abs/2511.18770) synthesizes phase
  polynomials using SAT and iterated blocks, targeting CNOT count/depth. Our
  adaptation explicitly counts phase gates as layers too. Published percentage
  improvements on other circuits do not predict this oracle's result.
- [Maslov and Zindorf, 2022](https://arxiv.org/abs/2201.05215) studies depth of
  CZ, CNOT and Clifford circuits. This motivates examining the representation
  and depth metric; we do not claim to implement its asymptotic construction.
- [Heuristic and Optimal Synthesis of CNOT and Clifford Circuits, 2025](https://arxiv.org/abs/2503.14660)
  and the authors' [CliffordOpt repository](https://github.com/m-webster/CliffordOpt)
  offer depth-oriented linear/Clifford synthesis. Not invoked here: the proposed
  local blocks contain arbitrary phase angles, requiring a phase-aware method.
- [Syndrome-decoding CNOT synthesis](https://arxiv.org/abs/2201.06457) is another
  linear-network option. It was not substituted for whole-oracle depth scoring.
- [CNOT-ladder depth via measurements](https://arxiv.org/abs/2511.13256) uses
  mid-circuit measurements/classical control. Those resources do not match this
  standalone U3/CX unitary task, so its constant-depth result was not used.

## Experiment 1: SAT phase blocks

New code: `src/post185_sat_phase_blocks.py`. A solver tracks an n-bit parity
on every wire at every time step. It chooses arbitrary directed CNOTs and
phase placements, enforces disjoint wire use per native layer, emits each
required phase once, and restores the exact final linear map. Optional
per-wire arrival/deadline constraints include surrounding circuit timing.
There is no clean-ancilla assumption inside a replacement.

The model differs from old fixed-gate scheduling: it can invent a new network.
It differs from the old three/four-wire BFS: it supports larger blocks via
symbolic solving. It still fixes the phase polynomial and is not a general
unitary synthesis or unrestricted global optimum.

Results:

- First screen:60 blocks (56 seven-wire,4 six-wire), about48.6 seconds.
  41 UNSAT for the requested shorter local bound,18 solver timeouts,1 SAT.
- The SAT replacement reduces its isolated block from5 to4 layers. Complete
  oracle stays185/854; the critical-gate count changes1104→1103 only.
  `post185_sat_blocks_v1/candidate38_d185.qasm` passes all4,096 inputs.
- Exact global scheduling of that candidate remains185, optimal only for its
  fixed commutation graph (`post185_sat_blocks_exact_v1`).
- Context-aware screen:45 blocks (40 seven-wire,5 six-wire), about45.4 seconds.
  38 SAT replacements yield verified185-layer circuits;7 timeout. No strict
  improvement. Block selection favored six/seven wires despite allowing five.

All SAT models are positive-control tested against complete small operators,
including arbitrary dirty spectator wires, simultaneous phases/CNOTs, an
impossible one-layer parity rotation, and release/deadline restrictions.
Timeout is recorded as UNKNOWN, not UNSAT.

## Experiment 2: change entangling-gate representation and directions

New code: `src/post185_cz_orientation.py`. Rewrite CX as H–CZ–H, fuse exact
one-qubit matrices, and build a CZ commutation graph. For each CZ, either
physical endpoint may be the target of its CX realization, with the required
Hadamards included. Search directions against **total native depth**, then
serialize back to U3/CX and verify. No CZ-basis score is used as a submission
metric, and arbitrary one-qubit phases are retained.

Eight orders ×1,200 direction proposals =9,600 proposals. All eight final
oracles pass4,096-input verification. Native depths:
**185,194,194,197,199,212,193,198**, all854 CX. The185 result merely ties.

The three selected rescheduled candidates reached189,187,189 in15-second
exact scheduling runs. A deeper solve of the187 candidate reached185 and
proved185 optimal for that fixed graph after10.6 seconds. Two other runs
remained FEASIBLE at their limit; neither is an impossibility result.

### Joint direction solver

The random direction search was followed by an exact CP-SAT formulation.
For every wire segment between CZ events, its one-qubit matrix is
`H(next_target) * M * H(previous_target)`. All four orientation combinations
have a known zero-or-one native gate cost. Timing constraints optimize all
854 directions together, avoiding the single-flip local-minimum limitation.

For four fixed CZ orders, the direction-optimal depths are185,192,193,198.
All four complete circuits pass4,096-input verification. Optimality concerns
directions and one-qubit fusion for each fixed wire order only. The model is
independently checked against brute-force orientation enumeration on a small
full-operator test. See `post185_cz_exact_directions_v1` and the additional
global scheduling follow-up `post185_cz_joint_schedule_v1`.
That follow-up also reaches185 and proves the bound only for its fixed graph.

## Preservation, validation, and reproduction

The protected185 QASM and original notebook are unchanged. New circuits are
under fresh artifact directories. Eight focused tests pass:

```sh
OPENBLAS_NUM_THREADS=1 \
PYTHONPATH=/tmp/classiq-scheduling-deps-20260915:src .venv/bin/python -m pytest -q \
  tests/test_post185_sat_phase_blocks.py tests/test_post185_cz_orientation.py \
  tests/test_native_wire_identity.py
```

Bounded primary experiments:

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python src/post185_sat_phase_blocks.py \
  --outdir artifacts/NEW_SAT_DIRECTORY --trials 60 --seconds 150 --per-window 2

OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python src/post185_cz_orientation.py \
  --outdir artifacts/NEW_CZ_DIRECTORY --orderings 8 --moves 1200 --seconds 120
```

The saved reports contain gate selections, exact phase-layer witnesses, CZ
orders, and direction choices. `exact_orientations` reconstructs the joint
direction experiment from a saved CZ order without resampling the search.
Every reusable transpilation uses `native`, which sets
`qubits_initially_zero=False` and materializes output layouts.

The measured result remains185 layers. Local savings and solver bounds must
not be described as a new best, a global floor, or rank one.
All jobs from this campaign finished. No submission, background optimization,
or leaderboard monitor was created.

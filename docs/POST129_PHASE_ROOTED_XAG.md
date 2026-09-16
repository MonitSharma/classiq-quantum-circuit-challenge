# Phase-rooted whole-function XAG campaign — September 16

## Outcome

**Protected best remains 185 depth / 854 CX / 18 wires.** No circuit from this
campaign improves it. No leaderboard submission or rank-one claim was made.

The user's latest pasted analysis correctly identifies an important freedom:
coordinates need restoration only at the end, and phase products need not be
stored as output bits. Implemented a backward-demand destructive compiler in
`src/post129_phase_rooted_xag.py`, reusing the existing exact physical-wire,
paid-control-exposure, primitive timing, and literal-inverse machinery.

The best compact partial trajectory deposits **three of 11 roots in 40 forward
native layers**. Allowing a complete computation rollback reaches four roots
in 109 forward layers. Neither is a complete logo oracle, and these are not
submission depths. A separate, complete affine-preserving control reaches
**1440 / 1396 / 18** and passes exhaustive verification. Its large depth is
evidence against this particular independent-cone schedule, not the general
whole-function or destructive XAG route.

## Assessment of the supplied analysis

Reproduced directly from `advanced_round4.xag`: 62 AND nodes, 11 nonlinear
output roots, nine terminal roots. Omitting those terminal products leaves
53 possible materialization nodes; this is neither a gate count nor a promise
that all remaining nodes can be computed once. Nodes 47 and 54 are output roots
with nonlinear consumers, so they may require both a CZ contribution and later
materialization. The implementation supports that distinction.

The report's high-level phase-oracle specification matches the notebook.
One detail needs correction: the notebook tests three randomized full-support
states; the repository's exhaustive verifier separately checks all 4096
clean-ancilla basis inputs with one shared global phase. We used the stronger
repository verification for complete circuits.

The reported 129-depth leaderboard, optimal BDD width, and all-balanced-split
rank claims were not independently reproduced in this campaign. None is used
as a correctness assumption, and CX counts do not identify competitors' methods.

## Implementation

`PhaseRooted` maintains the actual 18 wire truth tables over all 4096 inputs.
It recursively walks backward from missing phase operands, recognizing an
available affine combination before recursing into its individual signals.
The nearest two unmet roots guide proposals, permitting shared dependencies.
Nine terminal products are excluded from materialization proposals.

* Every coordinate and ancilla can be a nonlinear target.
* CZ deposits an exposed output product immediately, including nonterminal
  outputs. Exposed affine residuals can also be deposited using Z gates.
* Affine materialization costs actual X/CX operations; frames are retained.
* RCCX costs its actual seven U3/CX primitives on per-wire arrival clocks.
* Repeated AND computations are allowed. Paid recovery candidates include old
  physical blocks, recent non-diagonal suffixes, and an optional full rollback.
* Saved partial trajectories can be resumed after independent truth-table
  replay; phase mask, physical operations, and recovery history are preserved.
* Complete destructive candidates use the literal inverse of all non-phase
  operations to restore coordinates and cancel relative phases. Partial traces
  are never emitted as valid logo QASMs.

The heuristic prioritizes deposited roots, then inaccessible primary inputs,
then missing cone nodes, then forward native depth. It is not an optimal
allocator or a native-depth lower bound. It currently examines only a small
set of affine exposures and recovery moves. Beam pruning and time/step limits
can discard useful paths. No failed run proves infeasibility.

## Bounded experiments

All output directories are under `artifacts/`; original packages are preserved.

| Directory suffix after `post129_phase_rooted` | Trials | Budget | Result |
| --- | ---: | --- | --- |
| `_pilot` | 5 | 1 s, beam 4, forward cap 120 | One root; shortest partial 16 layers |
| `_campaign` | 100 | 1 s, beam 4, forward cap 120 | All reached one root; no complete oracle |
| `_longer` | 10 | 10 s, beam 4, forward cap 160 | 6 reached one root, 3 reached two, 1 reached three |
| `_suffix` | 20 | 5 s, beam 3, forward cap 180 | 13 reached one root, 7 reached two |
| `_resumed` | 20 | 5 s from three-root checkpoint, cap 150 | No fourth root; extra recovery costs depth |
| `_reset` | 10 | 10 s from checkpoint, cap 300, full rollback | Four-root partial; best recorded forward depth 109 |

Time budgets are checked between state expansions, so an expansion can slightly
overshoot. Tie-breaking is seeded; the number of completed expansions within
wall-clock budgets can vary. Best operation traces are saved, so their
semantics and timings remain exactly replayable. The final audit summarizes
completed counts and validates these saved traces.

The compact checkpoint is `_longer/best.json`: roots 54, 55, and 68, 40 forward
layers, two dirty coordinate targets, three recovery moves. Remaining root
demands lack affine access to input signals 2 and/or 9. Recent suffix recovery
does not solve that; full rollback restores access but loses the low-depth
advantage. The four-root checkpoint in `_reset/best.json` uses 123 forward
layers and has a smaller remaining cone than the 109-layer trial. `best.json`
selects by the documented progress heuristic; it is not always the lowest-depth
partial trace with a given number of phased roots.

## Complete controls and physical correctness

To test complete emission independently of heuristic search success, reused
short existing per-root operand-exposure pebbling witnesses. This is a control,
not a new minimum-AND or six-pebble search campaign. A first attempt to share
clean live nodes across successive roots exceeded a 150,000-state search cap;
the control then used each root's known witness and its reverse.

`--reference` restores every affine control frame and yields **1525 / 1335 / 18**.
`src/phase_rooted_frames.py` retains frames between paid operations and across
roots. It normalizes a zero target for computation, exposes a pure product
for release, clears that product from other registers, and physically restores
the final coordinate frame. It still preserves affine access to the inputs;
coordinate targets here do not imply general destructive storage freedom.

One hundred retained-frame schedules all pass full-domain Boolean restoration
and phase replay. The lowest raw-depth schedule has 370 nonlinear toggles,
raw depth 1585, and compiled **1440 / 1396 / 18**. Only the selected QASM received
the full quantum exhaustive check; do not call all 100 quantum-verified.
The two-trial pilot's selected QASM is separately verified at 1445 / 1394 / 18.

The paired control's relative-phase argument is narrower than the destructive
emitter's: each AND creation starts at zero and each release starts at that
same logical product with identical logical operands. The real Margolus
primitive is self-adjoint. Their phases cancel even if paid affine frames
change the physical register mapping. The final QASM checks independently
confirm phase and restoration, rather than relying only on this argument.

All three saved complete QASMs use standalone `u3/cx`, 18 wires, and pass all
4096 basis inputs. SHA-linked reports are adjacent to each QASM. Compilation
uses `distributed_frame_search.native`, including
`qubits_initially_zero=False` and output-layout materialization.

## Tests and continuation

Eleven focused tests pass across `test_phase_rooted_xag.py`,
`test_destructive_phase_xag.py`, and `test_exhaustive_diagnostic_width.py`.
New tests cover backward slicing, nonterminal-root phase deposition without
materialization, affine constants, resumed trajectories, native timing, and
full quantum correctness of small destructive and paired constructions.

Continue with **dependency-aware recovery of lost input/control forms** from
the compact three-root checkpoint. The current one-step pressure score cannot
reliably recognize multi-step recovery that temporarily worsens availability.
A useful next change must demonstrate additional roots without paying the
whole-trajectory reset cost. Do not resume generic side encoders, Direct-E
truth-table searches, six-pebble campaigns, or the independent-cone control's
100-seed sweep by default. Those are not the current requested direction.

Example new-directory run:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python \
  src/post129_phase_rooted_xag.py --outdir artifacts/NEW_NAME \
  --resume artifacts/post129_phase_rooted_longer/best.json \
  --trials 20 --seconds 5 --beam 4 --cap 150 --suffix-recovery
```

This command is an example for a changed recovery strategy; the existing
bounded probes are completed, not pending or scheduled work.

## Phase-completion audit

The follow-up audit in `src/post185_phase_completion_search.py` replays the
three saved phase-rooted checkpoints and tests the exact residual phase over
the 4,096 reachable states against the GF(2) span of current-wire monomials.
All three checkpoints require minimum degree **9**; none has an exact degree
1–4 completion. The persistent report is
`artifacts/post185_phase_completion_v1/report.json`. This supersedes root count
as the primary progress metric for this route: the three-root 40-layer state
is not a competitive low-degree phase-completion seed.

# Selective control recovery and affine destinations

September 16, 2026. **Protected best remains 185 / 854 / 18.** No complete
logo oracle was found or promoted. These are new compiler operations and
bounded experiments, not another pass over the old independent-cone controls.

## Measured result

The saved three-root checkpoint loses affine access to original inputs 2 and
9 (one-based logical signal numbering). Input 9 can be restored by exactly:

```text
RCCX(q6, q7, q17)
RCCX(q9, q17, q8)
```

Its forward depth increases from 40 to **44**, with all primitive arrival times
charged. There is no need to reverse the entire computation to recover this
input. This statement concerns the Boolean action of the relative-phase gates;
the final literal inverse cancels their incidental phases.

With recovery and storage release, the best recorded **four-root** checkpoint
has forward depth **65**, versus 109 in the previous full-rollback experiment.
Its emitted phase operator including restoration compiles to **112 depth /
154 CX / 18 wires**, but implements only four of the eleven output terms.
It is **not** a complete oracle or a submission-depth improvement.

A five-root checkpoint uses 141 forward layers and compiles to 233 / 273 / 18
including restoration. Its cost is already too high. Resuming the 65-layer
four-root checkpoint did not reach a fifth root within the tested 125-layer
forward cap. These are bounded heuristic results, not infeasibility proofs.

## Implementation

New module: `src/post185_selective_recovery.py`, extending `PhaseRooted`.

1. **Inverse dependency slicing.** Starting from the requested recovered
   output wire, scan the inverse computation backwards. Include a gate only
   when its target is needed; then include its controls as dependencies.
   This reproduces the selected output of the full inverse while permitting
   unrelated work to remain. Historical-prefix variants can restore earlier
   operand combinations, not just original coordinates.
2. **Semantic release of a stored AND.** Re-expose its logical controls in
   the current frame, expose the product on a third wire, and toggle that wire
   to zero. The physical wires need not match those used at creation. This
   avoids relying on stale physical control identities.
3. **One-AND algebraic recovery.** Search for a missing input as the current
   destination XOR an affine combination XOR one product of two other wires.
   The destination is excluded from every control, so this is a reversible
   update, not destructive assignment. It provides a cheaper option for
   input 2 at the original checkpoint; it cannot directly recover input 9,
   which needs degree three in those unchanged wire functions.
4. **Prepare the destination for its next consumer.** For a needed expression
   `P XOR (A AND B)`, physically form `P` on the target before the RCCX.
   Both control and target preparation cost real X/CX gates. This extends the
   earlier proposal set, which considered existing target values but did not
   deliberately prepare useful affine destinations.
5. **Native orientation choices.** Optionally choose the two control orders
   of RCCX, or the two CZ lowering directions, using primitive wire arrivals.
   Boolean rows and requested phase taps are unchanged. The literal-inverse
   construction still cancels the differing RCCX relative phases.

When phase-demand progress ties, the heuristic now rewards a reusable affine
storage direction. Otherwise a cheap dirty toggle can repeatedly displace
another value without exposing anything useful. This remains an incomplete
heuristic. It does not prove that a discarded state is worse globally.

The compiler also records the lowest-forward-depth candidate for each root
count across generated states within the cap. This fixes a measurement gap:
the old `best.json` followed its progress heuristic and could overwrite an
earlier, substantially shallower partial checkpoint. `best.json` still records
the heuristic winner; `roots_N.json` records the depth milestone.

## Completed experiments

All directories below have prefix `artifacts/post185_selective_`.

| Suffix | Trials | Main distinction | Outcome |
| --- | ---: | --- | --- |
| `recovery_pilot` | 3 | Input recovery cones | Three roots; recovered input at depth 44 |
| `release_pilot` | 4 | Add semantic release | Four roots; saved depth 88 |
| `algebraic_pilot` | 4 | Add one-AND recovery and milestone recording | Four-root milestone 75 |
| `recovery_wide` | 6 | Beam 8, cap 160 | Four-root milestone 65; one five-root run at 145 |
| `recovery_historical` | 3 | Include historical operand recovery | Four roots; no lower milestone |
| `oriented` | 4 | Native orientation choices | Five-root milestone 141 |
| `target_forms` | 6 | Affine destination preparation | Five roots at 141; cap issue below |
| `resume_four` | 6 | Resume 65-layer state; corrected cap 125 | Four roots; no exact completion |

Total: **36 bounded trials**, roughly six minutes of recorded search time.
Time limits are checked between expansions and can slightly overshoot.
The early target-form run checked the native cap before depositing newly
available phases: all six results were 141 despite a nominal 140 cap. This is
now fixed by filtering after phase deposition and asserting the returned cap.
Those historical runs are explicitly flagged in the audit; they are not
evidence of a result at or below 140. No correctness or protected result depended
on this budget-check bug.

## Residual completion and verification

`artifacts/post185_selective_completion_audit.json` repeats the exact
current-wire monomial-span audit on the four- and five-root milestones.
Both residuals first enter the span at degree **8**, compared with degree 9
for the previous checkpoints. Neither permits degree 1–4 completion. This
degree is specific to those current wire functions and does not bound general
oracle depth or the cost of changing the wire functions again.

`artifacts/post185_selective_recovery_audit.json` records every saved trace's
SHA and full 4096-bit phase/restoration replay, all trial outcomes, native
partial metrics, and the unchanged protected QASM hash. The native partial
metrics are diagnostic: these were not passed off as logo-verifier successes,
and no new submission QASM or companion QMOD was generated.

**19 focused tests pass** across the selective-recovery, phase-rooted,
destructive-phase, and diagnostic-width test files. New tests include exact
unitary checks on small circuits with dirty inputs and deposited phases,
causal slicing that preserves unrelated work, altered-frame release,
one-AND recovery, affine destination preparation without clean scratch,
orientation timing, trace validation, and post-phase native cap enforcement.

The shared resume helper now honors a saved `semantic_phase_hex` and still
checks it against the actual operations. This supports future residual-phase
completions whose phase cannot be reconstructed from a root mask alone.
Old trace files remain supported.

## What remains open

Selective recovery is now a demonstrated operation rather than an untested
suggestion. It removes one concrete compiler bottleneck, but the remaining
phase computation is still expensive. The five-root milestone does not justify
scaling up the same beam search. A next campaign needs to optimize native cost
of the remaining phase and restoration jointly; root count alone remains a
misleading completion metric. SPARE was not integrated in this campaign.

All searches here have finished. No background optimization or monitoring
was scheduled, and no old broad sweep was restarted.

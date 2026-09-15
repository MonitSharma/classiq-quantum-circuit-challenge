# Information-space and register-repair campaign

The protected full oracle remains **190 depth / 857 CX / 18 qubits**.
No complete new coordinate encoder, sub-77 encoder, or winning submission was
found. Partial circuits below are **not substitutes for either loader**.
Protected QASM SHA remains
`f8f6aec7835f6fe4e28023e2736553eb029d3522b1ea724a1e0d74213b41f549`.

## Direct evidence against the old pruning rule

The optional callback in `post190_semantic_register.search` observes rejected
states without changing the old acceptance or ranking decisions.
`artifacts/post190_information_space/audit/report.json` records:

| Measurement | Count |
| --- | ---: |
| Rejected span collisions | 7,215 |
| Different ordered physical wire functions | 7,209 |
| Different timing vectors | 7,215 |
| Some earlier physical wire availability | 5,942 |
| Cheaper needed operand exposure | 973 |
| Cheaper individual goal materialization | 298 |
| Cheaper exposure or goal materialization (union) | 1,108 |

Exposure costs use the legacy minimum-popcount affine expression and its
exposure routine. These are reproducible future-cost surrogates, **not** an
exhaustive optimum over all affine expressions or a proof that any rejected
state would complete. Examples save both concrete bases, timing vectors and
per-operand/goal costs. Individual wire readiness is counted separately because
wire functions can differ. The union does not include that weaker metric.

## Implemented search model

`post190_information_space.py` stores nine full 512-bit truth tables. Initially
these are nine independent variables; only the low64 entries constrain goals.
It enumerates affine aliases, permits dirty coordinate targets, and saves the
actual X/CX/RCCX prefix, all full functions, clean projections, timing, goal and
product membership, ranks and stage counts. `restore` checks exact replay.

Physical dedup retains the ordered basis and exact availability times. Pareto
mode only applies componentwise timing dominance to **identical ordered full
wire functions**. Different bases are not declared dominated. Beam capacity
and diversity caps still discard states heuristically; this is not an exact
reachability solver. Absolute timing is kept to avoid unsafe normalization.

General affine frames are selected as invertible row matrices and synthesized
by reversible Gaussian elimination. The physical cost is paid. This is a
correct baseline frame synthesizer, not a depth-optimal linear synthesizer.
The stage generator can pack up to three already exposed disjoint RCCXs after
a common frame. It does not enumerate every jointly exposed three-gate frame.

`post190_information_quotient.py` separates the semantic question further:
for exposed controls it enumerates all hyperplanes retaining those controls,
then replaces a complementary direction with its XOR with the product.
It retains a physical replay representative for each clean semantic span.
The quotient is used only for unrestricted-affine reachability, **not physical
cost dominance**. Beam width, operand aliases, and one selected control exposure
remain limitations. Native routing is reconstructed if all goals are reached.

`post190_register_repair.py` spends a bounded suffix budget on saved prefixes,
using wider exposures, aliases and stage packing. It evaluates all64 inputs
exactly through truth tables. Timeouts are never UNSAT results.

## Controlled comparison

The cached comparison gives each run a15-second allowance and24-step cap,
beam24, seed0. Runs finishing the step cap use less time. A/B match the old
move widths and span dedup, but use the **common new rank-aware score**; they
are not literal replays of the old score. The separate audit is the literal
old-search instrumentation.

| Mode | Seconds | Updates | Unique spans | Accepted states | Goals | Deficit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A: span, no mix | 4.09 | 27,447 | 12,486 | 13,429 | 2 | 2 |
| B: span, mix | 15.01 | 183,505 | 44,166 | 48,420 | 2 | 2 |
| C: Pareto, broader exposure | 11.45 | 166,894 | 4,397 | 165,565 | 1 | 3 |
| D: affine frames, aliases, packing | 15.02 | 174,604 | 15,196 | 168,738 | 2 | 2 |

All incomplete. Counts of accepted physical states are cumulative, not the
number simultaneously retained in the beam. Goal/product extrema in reports
refer to the saved bounded archive, not every rejected or transient candidate.
B's best relaxed suffix estimate is5; D's is6. These are sums of relaxed
individual goal arrival levels, not predicted native depths or stage bounds.

Profiling found repeated closure and GF(2) elimination dominated runtime.
Caching semantic metrics by canonical clean span improved D from76,810 updates
in15 seconds to174,604 in the follow-up. Timing comparisons are approximate:
these are wall-clock budgets, some ancillary runs overlapped, not controlled
CPU benchmark measurements.

## Repair and off-manifold experiments

Repair from the stronger B two-goal prefixes tried1–4 additional packed stages.
The one-stage pass finished its generated beam; longer passes hit their
10-second budgets. Update counts were10,127;136,923;143,846;142,121.
None reduced the best goal-rank deficit below2 or completed a state.
A semantic hyperplane suffix pass explored127,514 updates /86,434 unique spans
in24.05 seconds across an8-step cap, also without completion.

The Y semantic quotient with up to8 aliases examined70,725 updates in30 seconds,
reaching2 goals, deficit2. A one-alias run examined156,381 updates in30 seconds,
also2 goals, deficit2 (relaxed suffix estimate5 versus6). There is **no measured
reachability improvement from multiple off-manifold extensions in these runs**.
This is not evidence they can never help routing. Given identical ordered clean
wire functions, the same gate sequence has identical clean behavior; differing
full extensions do not by themselves create extra clean information. The useful
freedom is access to different physical affine masks and retained directions.

A deeper Y single-alias run finished24 search steps in42.50 seconds,
examining214,067 updates /162,194 distinct spans. It still had2 goals and
rank deficit2. Its relaxed suffix estimate improved to4 only with a21-RCCX
prefix (estimated wire availability165), so this is not a native-depth gain.
Stage-cap tests5/6/7 examined90,583 /100,291 /103,928 updates and reached
1/2/2 goals respectively. They finished their bounded beams without completion.

A final regression fixed recognition of a goal reached on the last permitted
stage: new candidates are now checked immediately, before another beam step
or timeout. No existing saved frontier has rank deficit0. Earlier bounded
searches should not be interpreted as exhaustive regardless of this fix.

## Measured partial circuits

The following are serialized and reloaded native QASM, checked on all64 legal
inputs for the **reported subset** of goals and compute/Z/actual-inverse phase.
They do not satisfy all four goals.

| Side | Present | Missing | Rank deficit | RCCXs | Search stages | Nonlinear dependency depth | Native depth | CX | Placements |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Y13 B prefix | code0, raw | code1, code2 | 2 | 9 | 9 | 8 | 61 | 66 | 3,4 |
| X14 quotient prefix | code0, raw | code1, code2 | 2 | 6 | 6 | 5 | 44 | 49 | 8,6 |

Artifacts: `partial_y/partial_0.qasm`, `partial_x/partial_0.qasm` under
`artifacts/post190_information_space/`. Their reports contain exact SHAs.
Inverse-phase errors are1.55e-15 and9.70e-16. These prefixes are selected by
search score, not asserted globally optimal among all partial encoders.

The next step has not been proved to fail. The beam exhausts its candidate
or time budget while retaining only two independent goal directions. No
register-capacity or witness-topology impossibility follows from this.

## Reproduction and files

All commands use fresh output directories; run from the repository root.

```sh
.venv/bin/python src/post190_dedup_audit.py --outdir /tmp/classiq_audit_new --seconds 10
.venv/bin/python src/post190_information_campaign.py --outdir /tmp/classiq_comparison_new --seconds 15
.venv/bin/python src/post190_register_repair.py --config artifacts/post190_information_space/comparison_cached/B/config.json --frontier artifacts/post190_information_space/comparison_cached/B/frontier.json --outdir /tmp/classiq_repair_new --seconds 40 --max-stages 4
.venv/bin/python src/post190_information_quotient.py --witness artifacts/post190_nist_variants_wide/y_candidate_0.json --side y --outdir /tmp/classiq_quotient_new --seconds 30 --aliases 1
.venv/bin/python -m pytest -q tests/test_post190_information_space.py tests/test_post190_semantic_register.py
```

Every run has `config.json`, `report.json`, and saved frontiers. The campaign
runner records A–E. Additional exact commands can be reconstructed from each
config. `post190_partial_report.py` exports and verifies incomplete prefixes.
Only the legacy module's optional audit hook was changed; other compiler files
are new. No old QASM, notebook, witness, or protected package was changed.

Tests:16 passed, including full512-input affine-frame quantum checks, clean
alias projection, dirty-target semantics, incomparable timing retention,
rank-deficit behavior, packed gates, snapshot replay, hyperplane transitions,
exact witness targets, and a complete synthetic encoder. The synthetic encoder
is not a logo result.

## Next experiment supported by these results

Use the saved two-goal prefixes for **joint multi-product hyperplane transitions**:
choose two or three control pairs together and retain their common information
before replacing multiple directions. Current semantic search updates one
product at a time; current physical packing mostly finds products already
exposed by a frame chosen for one gate. Broader single-gate aliases cost time
without improving completion. A jointly chosen frame directly addresses that
remaining restriction. This is a proposed experiment, not a promised solution.

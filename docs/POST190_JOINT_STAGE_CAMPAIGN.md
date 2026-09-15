# True joint affine-stage campaign

Protected submission remains **190 depth /857 CX /18 qubits**, unchanged.
No new complete Y13 or X14 encoder has been found. A synthetic positive control
is complete; it is not the challenge predicate and is not a submission.

## What changed

`src/post190_joint_stage.py` selects two or three seed products together,
backtracks over their full affine control aliases, and requires rank2k on the
nine-bit **linear coefficient masks**. Overlapping coefficient supports are
allowed. It chooses the entire retained space H and ordered target quotient
basis before applying any nonlinear update. The full512-bit successor is
formed simultaneously. This is not the old one-product-first packer.

For every visited independent control tuple:

- width2 enumerates all155 retained seven-dimensional H containing C, and all6
  ordered bases of V/H:930 transitions;
- width3 uses H=C and enumerates all168 ordered quotient bases exactly;
- optional width1 enumerates127 retained hyperplanes.

Target lifts differing by an element of H, and target affine constants, give
the same successor affine span, so canonical quotient representatives suffice.
Controls' affine constants are preserved in the physical frame. All full
preimages are available; no cheapest-alias-only shortcut is used. A wall-clock
limit can interrupt enumeration, and reports distinguish that from exhaustion.
Products selected within one stage are distinct seed-bank entries; this scope
is explicit in every finite conclusion below.

Semantic dedup uses the full affine span, with the shallowest visited suffix
depth retained. It does not assert physical timing dominance. BFS was tried
first; best-first search and resumable expansion address large branching.
Queue-cap drops are recorded as heuristic losses, not dominance proofs.

A successful semantic path is saved with its initial snapshot, product sets,
control aliases, H, quotient bases, full products, frames and successor spans.
Reconstruction emits a single common X/CX frame followed by disjoint RCCXs.
The actual serialized native QASM is reloaded and checked on all64 legal inputs,
including expected phase and inverse cleanup. No real encoder completed, so
expensive linear-frame depth optimization was not started.

## Exact one-stage results

The starting Y prefix is index0 of
`artifacts/post190_information_space/comparison_cached/B/frontier.json`.
It has code0+raw in its affine span, missing code1+code2, deficit2.

| Quantity | Y prefix | X prefix |
| --- | ---: | ---: |
| Product pairs considered | 6 | 36 |
| Independent pair alias sets | 5 | 33 |
| Product triples considered | 4 | 84 |
| Independent six-control alias sets | 2 | 45 |
| H enumerated (width2+3) | 777 | 5,160 |
| Width3 distinct successor spans | 336 | 7,560 |
| Width2 distinct successor spans | 4,650 | 30,690 |
| Total distinct successor spans | 4,986 | 38,250 |
| Best deficit after including starting state | 2 | 2 |
| Deficit-improving width3 sets | 0 | 0 |

These runs exhausted their specified one-stage generators. The X prefix is
index0 of `artifacts/post190_information_space/quotient_x/frontier.json`.
The counts are not global statements about every prefix or every Boolean
construction. Independent controls exist; their absence is not the sole
obstacle. Jointly choosing targets did not improve goal rank from these prefixes.

## Replayable necessary stage bound for this Y prefix

`src/post190_joint_certificate.py` evaluates a synchronous relaxation: keep
unlimited storage and add **every** seed product whose operands belong to the
current span at the start of a stage. A legal joint stage can add only a subset
of those products. By induction, its actual clean span is contained in the
relaxed span after every stage. This yields a necessary suffix-stage bound,
independent of native gate scheduling.

From the starting prefix, the relaxed goal availability is:

| Additional stages | Available goals | Rank deficit |
| --- | --- | ---: |
| 0 | code0, raw | 2 |
| 1 | code0, raw | 2 |
| 2 | code0, code2, raw | 1 |
| 3 | all four | 0 |

More strongly, enumerate **all5,494 first successors**, including width1:

- 5,008 still need at least4 additional relaxed stages;
- 486 still need at least3 additional relaxed stages.

Therefore this saved prefix requires **at least4 additional stages** in the
specified distinct-seed-product model, even with arbitrary affine frames and
dirty targets. A three-stage repair is ruled out within that model. This does
not rule out another prefix, new nonlinear products, relabeling, or a different
oracle. It is not a native-depth lower bound.

The certificate contains witness and frontier hashes:
`artifacts/post190_joint_stage/y_prefix_certificate.json`.
The three-stage all-width search exhausts all5,494 successors and rejects each
with this admissible bound; no timeout or queue truncation occurs in that run.

## Deeper searches and the actual bottleneck

The initial two-stage BFS reached35,100 full spans in30 seconds before timing
out, with4,800 first-stage successors still unexpanded. Some transitions reduce
their parent's deficit by1 by recovering information previously lost, but none
improves below the original deficit2. This is not partial progress to deficit1.

Three- and four-stage best-first runs reached120,793 and131,502 full spans,
respectively, within30 seconds each, without completion. A later four-stage
all-width run with admissible pruning reached126,114 spans in40 seconds;
464 states remained queued. An alternate Y prefix (code1+raw) reached86,747
spans in30 seconds, also deficit2.

The extended four-stage all-width run reached **456,886 full spans** and
1,650,185 generated transitions in180 seconds. It considered2,358 product-pair
instances and1,832 product-triple instances, found3,158 independent alias sets
(406 width3), and enumerated367,359 H instances. Width3 generated68,208
transitions and11,032 novel successor spans. There were248 six-control sets
with parent-relative rank improvement (7,392 transitions), but no improvement
below the original deficit2. The run timed out with246 queued expansions;
it had no queue-cap drops. This remains unresolved, not an exhausted four-stage
proof. Counts refer to visited state/product instances and are not globally
unique product sets.

Identity-start5/6/7-stage allowances were tested. Naively expanding the root
exhausts the budget on hundreds of thousands of aliases before a second stage.
Resumable expansion lets later stages run: streamed5/6/7 tests reached239,264,
237,373 and381,675 full spans, but only raw was in the best saved goal span
(deficit3). The largest observed prefix depth was4; these are **not exhaustive
5/6/7-stage tests**. Queue losses occurred in some runs and are reported.

Profiling: generating stages was roughly0.66 of5 seconds in the profile;
semantic metrics, relaxed witness distance and canonicalization dominated.
Caching complete state metrics reduced repeated work. Python combinatorial
mask enumeration was not the dominant measured cost, so no C++ port was made.
The primary observed deeper-search limitation is branching and state selection,
not demonstrated physical routing failure or a witness impossibility theorem.

## Synthetic proof of new functionality

Controls `(3,6,12,24,48,32)` as nine-bit masks are independent despite overlapping
supports. The tested old greedy first-product exposure plus opportunistic packer
cannot fit the three requested products in that frame, for any legal first
target. The joint frame exposes all six controls and all three targets at once.
This is a counterexample to that old packing choice, not to all possible
sequential reversible implementations.

`artifacts/post190_joint_stage/synthetic_case/` contains the complete synthetic
encoder:15 native depth,24 CX,9 wires,3 RCCXs in one joint stage, outputs6/7/8/5.
All64 legal inputs pass; inverse-phase error6.94e-16. Its SHA is
`82a7661524ba4899d934e9ac44b6296e7bcbec20e15502ad90a17104d89f3956`.
This validates semantic completion through physical reconstruction. **It is not
an X14/Y13 encoder.** The three disjoint RCCXs alone compile to depth7.

## Real encoder status

No complete outputs, native depth or CX can be reported for a new real encoder.
The previous verified partials remain the useful reference:

| Prefix | Goals | RCCXs | Prefix nonlinear dependency depth | Native depth | CX |
| --- | --- | ---: | ---: | ---: | ---: |
| Y13 | code0+raw; missing code1+code2 | 9 | 8 | 61 | 66 |
| X14 | code0+raw; missing code1+code2 | 6 | 5 | 44 | 49 |

Those prefixes predate this campaign and are not loaders. No full-oracle
composition was attempted. Protected QASM SHA remains
`f8f6aec7835f6fe4e28023e2736553eb029d3522b1ea724a1e0d74213b41f549`.

## Tests and preservation

New tests cover width2/3 full truth semantics, all155 H spaces, all6/168 quotient
bases, independent overlapping controls, disjoint physical support, exact
replay, synthetic advantage over the old packer, immediate completion/export,
and the admissible bound's containment property.

The full existing suite run reported174 passes and one failure in unchanged
`tests/test_three_sweep_phase.py`, which expects `central_ucr_depth_floor` while
`analyze()` now returns `idealized_central_ucr_schedule`. No failure was hidden
or relabeled as a pass. After adding the completion and bound regressions, the
focused joint/information/semantic suite passed23 tests.
The full suite rewrote two unrelated timing/temp-path report fields; those
incidental changes were restored. No protected artifact or notebook changed.

## Reproduction

Use fresh output directories, from the repository root:

```sh
.venv/bin/python src/post190_joint_stage.py --frontier artifacts/post190_information_space/comparison_cached/B/frontier.json --outdir /tmp/joint_y_one --stages 1 --seconds 30
.venv/bin/python src/post190_joint_certificate.py --frontier artifacts/post190_information_space/comparison_cached/B/frontier.json --witness artifacts/post190_nist_variants_wide/y_candidate_0.json --out /tmp/joint_y_certificate.json
.venv/bin/python src/post190_joint_stage.py --frontier artifacts/post190_information_space/comparison_cached/B/frontier.json --outdir /tmp/joint_y_three --stages 3 --seconds 30 --policy best --burst 256 --relaxed-prune --widths 3,2,1
.venv/bin/python src/post190_joint_stage.py --frontier artifacts/post190_information_space/comparison_cached/B/frontier.json --outdir /tmp/joint_y_four --stages 4 --seconds 180 --policy best --max-states 20000 --burst 256 --relaxed-prune --widths 3,2,1
.venv/bin/python -m pytest -q tests/test_post190_joint_stage.py tests/test_post190_information_space.py tests/test_post190_semantic_register.py
```

Every search directory contains its exact CLI config, counters, best saved path,
and (in later runs) example width2/3 stage frames. Any complete semantic path
also produces completion JSON, QASM and verification with matching SHA.
`summary.json` collects the individual reports. Counts across searches overlap;
summing them does not count globally unique states.

## Next step

Perform a bounded local NIST replacement of the missing code1/code2 computation,
allowing one or two extra ANDs, and rank candidates by the certified relaxed
stage bound **and** true joint-stage feasibility. This directly tests whether
the current prefix's four-stage minimum can be avoided. It is an experiment,
not a claim that a larger witness will win. Current results do not establish
that Y13 is globally unschedulable or that physical frame optimization alone
will solve retention. No phase-weaving implementation was attempted.

All campaign processes finished; nothing is scheduled or running in background.

# Verified improvement: 188 depth / 855 CX / 18 qubits

September 15, 2026. The new protected package is `artifacts/188/`. Its exact
standalone QASM SHA-256 is
`f8f7e73ad2d48daa31a29a354e2287347b90e59d460f9e7d271495850635e46e`.
The original notebook and all older protected packages are preserved.

The user's attached leaderboard screenshot shows 137/561/18 at rank one and
190/857/18 at rank ten. This run did not query the live leaderboard or submit a
circuit. The new result is a local improvement; rank one remains unfinished.
Against that screenshot, 188/855 would still lose the CX tie-breaker to the
188/451 entry, so this improvement alone would not move the user above it.

## What changed

The saved gate list imposes more ordering than the unitary requires. In
particular, CNOTs with a common control or common target commute; diagonal
single-qubit gates commute through CNOT controls; X-axis rotations commute
through CNOT targets. Compatible single-qubit gates can commute as well.

`src/post190_commuting_schedule.py` builds a dependency graph retaining the
order of every original pair that does not satisfy these conservative rules.
It removes transitive edges and searches parallel layers with at most one
operation per wire. No angle, wire identity, or gate is altered by scheduling.
The matrix checks use a 1e-12 tolerance; the actual serialized full oracles
receive independent numerical verification before promotion.

`src/post190_exact_schedule.py` models each gate's integer layer in CP-SAT.
Dependencies constrain order, and all-different constraints prevent gates
sharing a wire from occupying the same layer. A saved solution stores the
complete gate permutation, so replay does not need OR-Tools or another solve.

The first stochastic run tried 2,000 schedules and improved the 190/857
package to 189/857. Native fusion then removed nine U3 gates without reducing
depth further. A portfolio screen checked 13 distinct saved full circuits,
with 96 schedules per circuit. The previous 191/855 package became 189/855.
An exact schedule of that fused circuit reached **188/855**. Another native
fusion reduced its U3 count to 773, followed by a final exact schedule.

This is why it helped to revisit a previous runner-up: the 191-depth source
benefited more from the new ordering model than the old 190-depth winner.

| Source or stage | Initial depth / CX | Best measured depth / CX |
|---|---:|---:|
| Protected 190, fixed native gates | 190 / 857 | 189 / 857 |
| Protected 190 after exposed U3 fusion | 189 / 857 | 189 / 857 |
| Protected 191, stochastic schedule and fusion | 191 / 855 | 189 / 855 |
| That 189 circuit, exact scheduling | 189 / 855 | 188 / 855 |
| That 188 circuit after further U3 fusion | 188 / 855 | 188 / 855 |
| Protected 193 CX refinement | 193 / 853 | 190 / 853 |
| Alternate 190 from joint search v5 | 190 / 859 | 189 / 859 |

CP-SAT returned OPTIMAL for the six exact-scheduling runs, within about
7–15 seconds each. These are optima **for their particular fixed native
gates and conservative commutation dependencies**, not global circuit-depth
lower bounds. Algebraic rewrites, different parity networks, and different
encoders remain outside these models.

The exact 190 QASM has maximum per-wire gate occupancy **176**, not the 181
quoted in the older handoff. Its dependency-only longest path is also 176.
Neither is a tight scheduling bound: the solver obtains 189 once wire
contention and the ordering constraints are enforced together.

## Verification and packaging

- Exact packaged QASM: depth 188, CX 855, U3 773, width 18.
- All 4,096 clean-ancilla basis inputs pass with one common global phase.
- Maximum exhaustive error: 7.12e-15; ancilla error: zero; accumulated
  discarded-amplitude bound: 2.12e-14.
- Five independent dense random states pass, maximum error 2.90e-16;
  maximum ancilla amplitude is 5.94e-17.
- QMOD parsing matches all 1,628 QASM gates. Its `main` has the usual twelve
  preparation Hadamards, which are absent from the scored oracle QASM.
- Recorded source, gate permutations, and two native-fusion stages replay
  to the exact package SHA; the replayed file also passed all 4,096 inputs.
- Focused commutation and native wire-identity tests pass. No broad historical
  optimization campaign or cloud synthesis was rerun.

The source is the protected 191 package. Its phase kernel has a physical
ancilla permutation. `source_encoder_recipe.json` preserves that provenance;
it is not a recipe for reproducing the final gate order. Use the new replay:

```sh
.venv/bin/python src/build_rescheduled_oracle.py --package artifacts/188 --outdir /tmp/classiq-188-replay --verify
```

The destination must not already exist. `build_permuted_oracle_package.py`
continues to replay the older packages but does not reproduce this new schedule.

## What remains for first place

The dominant architectural issue is unchanged: the old loaders take 77 layers
each. A conservative staged target of two 50-layer encoders plus a 36-layer
kernel would be depth 136. No such 50-layer logo encoder exists in the checked
artifacts. The direct Boolean 139-layer template is also unsolved. These are
resource targets for structural research, not new candidate circuits.

The practical new tool from this run is exact scheduling of commuting native
gates. Use it on genuinely new candidates and previously close alternatives;
do not spend more seeds trying to beat a solver-proved optimum of the same
fixed graph. Ranking remains a separate submission and leaderboard outcome.

## Files and environment

- `artifacts/post190_commuting_schedule_v1/`: initial heuristic search.
- `artifacts/post190_schedule_portfolio_v1/`: 13-source screen and first replay stage.
- `artifacts/post190_exact_schedule*/`: exact models' solution records and outcomes.
- `artifacts/188/`: authoritative QASM, literal QMOD, reports, and replay data.
- `artifacts/post188_replay_v1/`: independently rebuilt and verified package.

OR-Tools 9.15.6755 and its helper packages were placed in the temporary
directory `/tmp/classiq-scheduling-deps-20260915`; the workspace virtual
environment was not changed. To use that installed solver during this session,
set `PYTHONPATH=/tmp/classiq-scheduling-deps-20260915:src`. Deterministic package
replay only needs the existing workspace dependencies. All jobs finished;
no automation, monitoring, or submission was created.

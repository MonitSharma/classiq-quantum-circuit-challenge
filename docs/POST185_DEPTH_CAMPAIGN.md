# Depth-focused follow-up: best remains 185 / 854 / 18

September 15, 2026. The user explicitly prioritized **depth over CNOT count**.
This campaign allowed larger CNOT networks and temporary depth regressions;
it did not optimize the CX tie-breaker. No verified circuit below 185 layers
was found. Protected `artifacts/185/` remains unchanged, SHA
`ef933bc786bc25feb1fbd618fc8c45a0bdc8dce43879aacfcc6042daaca5bfc8`.
Rank one remains unfinished. The user's screenshot shows a 137-layer leader;
no live-rank check or submission was performed.

## Completed experiments

| Method | Work completed | Depth outcome |
|---|---|---|
| Stochastic multi-rewrite walk | 1,764 attempts, 107 accepted steps, 12 restarts | 185 |
| Solver-guided rewrite branches | 50 one-to-three-rewrite proposals | 185 |
| Dirty-wire CNOT mediation | 600 sampled rewrites; eight retained circuits exactly scheduled and verified | 185–186 |
| Temporary compiler wire relabeling | 400 restored-label compilations, alternating circuit/inverse | 185 |
| Strict 184-layer tests from two parents | 148 + 142 rewritten networks | No 184 witness |
| Deadline-aware three-wire phase networks | 120 strict windows, then 240 neutral windows | 185 |
| Deadline-aware four-wire phase networks | 60 windows | 185 |
| Joint phase placement and scheduling | 739 phase gates, 867 legal occurrences | 185 |

The separate exact scheduling of both stochastic-walk survivors also returns
185. These are bounded searches and restricted-model solver results, not a
proof that the logo cannot have lower depth.

### More CNOTs, different dependencies

`src/post185_depth_walk.py` ranks depth first and critical-path gate count
second. It allows up to 100 extra CNOTs and temporary depth up to three layers
above the best. It retained two equal-depth variants for exact scheduling.

`src/post185_solver_walk.py` applies one to three CNOT identities before
solving the full gate schedule. It has no CX cap or penalty. Some solves ask
strictly for 184; others permit 185 to retain alternative parents. Of 50
proposals, 48 are infeasible under their stated scheduling ceilings, one is
unresolved after five seconds, and one yields an equal-depth parent. That
parent is a measured search state, not a promoted package. Positive controls
check the scheduling model against feasible and infeasible small circuits;
the protected 185 circuit itself solves correctly at 185.

`src/post185_mediated_cx.py` substitutes four CNOTs for one:

```text
CX(a,k), CX(k,b), CX(a,k), CX(k,b) = CX(a,b)
```

The mediator k may contain arbitrary quantum information and is restored.
Both execution directions and all local wire assignments pass full-operator
tests. The sweep sampled 600 of 18,830 nearby critical-gate/mediator choices.
Exact scheduling of the eight retained circuits finds depths 185–186; all
eight pass the 4,096-input verifier. The 185-depth mediated variants use 857
CX and were kept despite the larger CX count, but do not improve depth.

`src/post185_depth_sweep.py` asks for a strict 184-layer schedule after each
rewrite, without a CX cap or objective. It tested 148 networks from the
protected circuit and 142 from a differently scheduled equal-depth parent.
288 are infeasible **for their exact rewritten gates, commutation rules, and
184-layer ceiling**. Two solves timed out unresolved. Both runs stopped at
their 200-second campaign budgets; they did not cover every possible move.

### Phase networks that fit the surrounding schedule

`src/post185_timed_local.py` searches finite three/four-wire parity networks
with explicit per-wire release times and deadlines derived from the full
oracle. This differs from minimizing isolated subcircuit depth. It allows
waiting and extra CNOTs, preserves the local output linear map, and applies
each required phase on a wire carrying the matching parity. Four-wire layers
can contain two disjoint CNOTs.

The strict three-wire run finds no local network meeting its requested
one-layer-earlier deadlines in 120 selected windows. A second run permits
equal-depth replacements to reduce the number of critical gates. It completes
240 windows and accepts seven independently verified changes, reducing that
proxy from 1,104 to 1,096 while keeping actual depth **185**. This proxy change
is not a leaderboard improvement. Exact global rescheduling of the final
variant also stays at 185. The four-wire follow-up completes 59 windows and
hits the state limit on one; no full-circuit gain occurs.

### Joint phase placement and global scheduling

`src/post185_phase_placement.py` extracts each diagonal/CNOT block, accumulates
its phase polynomial, and records every interval in which a wire contains a
requested input parity. CP-SAT chooses the occurrence and gate layer together.
Non-diagonal gates delimit the blocks; the entire serialized oracle is scored.

The initial model preserves per-wire CNOT order. A stronger version allows
commuting skeleton gates to reorder. In the stronger model, every target-side
CNOT before/after a chosen phase occurrence is constrained to stay on its
respective side. This prevents a change in the parity when mutually commuting
CNOTs sharing a target swap order. Control-side CNOTs may commute through the
phase. All gates still obey per-wire resource limits.

Both models find and prove an optimum of **185 in their respective models**,
using 878 fixed gates plus 739 phase gates with 867 occurrence choices. Both
serialized outputs pass the full oracle verifier. These results do not cover
new CNOT networks, crossing non-diagonal block boundaries, or changing the
encoder architecture.

### Compiler diversity and phase-merging composition

`src/post185_relabel_compile.py` temporarily renames wires, safely transpiles
with `qubits_initially_zero=False`, materializes output permutations, and
restores all original labels before scoring. Four hundred permutations,
alternating the original oracle and its inverse, do not improve depth. Their
saved outputs are diagnostic measurements; the method's full-unitary and
inverse behavior is independently tested on an entangled small circuit.

PhasePoly rotation merging was reapplied to the newer CNOT network to check
whether the two methods combine. It produces a fully verified 196/854 native
intermediate, then exact scheduling gives verified **186/854**, a regression
against the protected185. Its fixed-graph optimum is recorded in
`artifacts/post185_phasepoly_followup_exact_v1/report.json`.

## Verification and reproducibility

**31 focused tests pass**, covering dirty mediation, critical paths, restored
wire labels, release/deadline constraints, simultaneous CNOT layers, solver
ceilings, phase occurrence correctness, and the previous local-rewrite/native
wire-identity/phase-synthesis tests. No global 18-qubit Operator is allocated.
The only original shared helper change in this continuation is allowing
`phase_signature` to use its input circuit's width; existing three-wire tests
continue to pass. New searches use new output directories.

The protected package audit matches the actual QASM hash against exhaustive
and dense reports, verifies literal QMOD gate equality, and checks identical
replay (`artifacts/185/package_audit.json`). The package has 763 U3 gates and
854 CX gates, total 1,617. All 4,096 inputs and five dense states remain valid.
Replay still uses:

```sh
.venv/bin/python src/build_bridge_oracle.py --package artifacts/185 --outdir /tmp/classiq-185-replay --verify
```

No protected QASM or notebook was overwritten. All runs are bounded; no
background monitoring, scheduled optimization, or submission was created.
All jobs from this continuation have finished.

## Implication for the next search

The current single-rewrite, local phase retiming, and fixed parity-network
families have not produced another layer reduction. The next substantial
experiment should change larger portions of the network or the encoder/kernel
interface and continue scoring **depth**, even when that requires more CX.
The existing 139-layer direct Boolean template remains unsolved and is not a
submission circuit. The 185 result is not a global optimality claim.

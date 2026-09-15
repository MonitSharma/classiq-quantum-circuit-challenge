# New local rewrites: verified 185 depth / 854 CX / 18 qubits

September 15, 2026. The protected package is `artifacts/185/`, SHA
`ef933bc786bc25feb1fbd618fc8c45a0bdc8dce43879aacfcc6042daaca5bfc8`.
It improves the previous 186/855 circuit in both scored metrics. It contains
763 U3 gates, seven fewer than the previous package. Earlier protected files
and the original notebook are preserved. No circuit was submitted and no live
leaderboard was checked. The user's screenshot has a 137/561 leader; rank one
remains unfinished.

## Successful method: change the CNOT network

The previous exact scheduler could only reorder existing commuting gates. The
new `src/post186_cnot_bridge.py` changes the interactions using exact CNOT
identities. For example, in execution order:

```text
CX(a,b), CX(b,c)  ->  CX(b,c), CX(a,c), CX(a,b)
```

The two sides implement the same reversible map on all eight local inputs.
The reversed-chain form is also implemented. A gate is moved across intervening
operations only when each commutes with it. Both movement directions and all
wire assignments are checked as full operators in the tests.

The added endpoint CNOT can remove a scheduling bottleneck or expose other
cancellations. This is related to the general technique of circuit templates
described in [Maslov et al., Quantum Circuit Simplification and Level
Compaction](https://arxiv.org/abs/quant-ph/0604001). The implementation here is
a small explicit CNOT identity search, with independent numerical verification.

Each rewrite is safely lowered to U3/CX, tried with three commuting schedules,
then lowered again. Promising and structurally different candidates receive
exact CP-SAT scheduling. The useful sequence was:

| Stage | Depth | CX | U3 |
|---|---:|---:|---:|
| Protected input | 186 | 855 | 770 |
| First CNOT rewrite and exact schedule | 185 | 856 | 763 |
| Second rewrite and exact schedule | 185 | 855 | 763 |
| Third rewrite and exact schedule | **185** | **854** | **763** |

The first successful rewrite crosses CX(17,5) with CX(5,4), adding CX(17,4).
It changes the gate dependencies enough to reach 185, while exposing seven
one-qubit fusions. The next two rewrites each save one CX without losing depth.

Three sweeps evaluated 282, 305, and 294 moves: **881 rewrites** in total.
Twenty-seven retained or independently reconstructed candidates were exactly
scheduled and exhaustively verified. Their optima are for their own fixed gate
lists and conservative commutation graphs, not global lower bounds on the logo.

A useful search lesson: ranking only by emitted depth misses candidates. The
third successful candidate initially measures 186/854, then exact scheduling
recovers 185/854. Inspect lower-CX and lower-gate-count entries in the full
`rows` report as well as the default `retained` shortlist. `optimized_move`
reconstructs an individual recorded move without rerunning a whole sweep.

Artifacts: `post186_bridge_v1/`, `post186_bridge_exact_98/`,
`post185_bridge_fusion_v1/`, `post185_bridge_v2/`, `post185_bridge_exact_37/`,
`post185_bridge_v3/`, and `post185_v3_exact_166/`. Other exact runs are recorded
in the `post185_bridge_exact_*`, `post185_diverse_exact_*`, and
`post185_v3_exact_*` directories.

## Two other new methods tested

1. **Exact three-wire phase-network synthesis.**
   `src/post186_exact_local_phase.py` collects convex regions across the entire
   oracle, stopping at incompatible external interactions and non-diagonal
   gates. Its finite search tracks an invertible three-bit linear map and the
   phase parities still to emit. It minimizes synchronous layers in that
   restricted local gate model, retaining the complete output map. Among
   12,000 region attempts, 21 locally improved replacements were scored in the
   full circuit; none improved 186/855. This is not a global optimality result.
2. **Four/five-wire phase networks with boundary timing.**
   `src/post186_context_windows.py` scores phase synthesis using actual arrival
   times and remaining work on each selected wire. Every local replacement is
   compared as a full operator before composition. The corrected four-wire run
   completed 150 windows and the five-wire run 160; neither improved its input
   circuit. Two four-wire searches hit their step limits without a conclusion.

The first four-wire probe hit the older beam routine's 4,000-step nonconvergence
assertion after more than 100 scored windows and did not write a final report.
The corrected caller uses an explicit 128-step limit, records unresolved cases,
and saves checkpoints. `psynth` now accepts optional `max_steps`; its existing
default of 4,000 and earlier callers' behavior are unchanged. This failure does
not affect any accepted circuit.

## Verification and replay

The exact packaged QASM passes all 4,096 clean-ancilla basis inputs with one
shared global phase: max error 6.27e-15, ancilla error zero, and accumulated
discarded-amplitude bound 2.04e-14. The literal QMOD matches all 1,617 gates;
only its `main` adds the twelve preparation Hadamards.

`src/build_bridge_oracle.py` replays three recorded identities, their native
rewrites, and saved gate permutations from the preserved 186 QASM. It checks
every intermediate SHA. It needs no SAT solver, external optimizer, network,
Classiq login, or cloud synthesis:

```sh
.venv/bin/python src/build_bridge_oracle.py --package artifacts/185 --outdir /tmp/classiq-185-replay --verify
```

Use a new destination directory. The package includes the input QASM and
`bridge_recipe.json`; replay does not depend on the search directories. Use
this builder for 185; the older rescheduling-only builder cannot apply the
new CNOT identities.

The package's five-state dense report and fresh replay report are stored next
to the QASM and in `artifacts/post185_bridge_replay_v1/`, respectively. Focused
tests cover identities, convex extraction, local unitary equivalence, beam
completion and step limits, native wire identity, and existing phase synthesis.
All **21 focused tests pass**. Fresh replay matches the protected SHA and
passes all 4,096 inputs. Five dense-state checks pass with max error 2.68e-16,
ancilla amplitude 5.70e-17, and normalization error 9.33e-15.

## Remaining gap

This is a real but small reduction. The screenshot's leader is still 48 layers
below the new circuit. The unsolved 139-layer Boolean template remains a
hypothesis, not a submission. Further work can combine different CNOT templates
or broader phase regions, but additional gains are not guaranteed by this run.

# Instructions for agents continuing this workspace

Current protected best is now **185 / 854 / 18**, `artifacts/185/`, as confirmed in `docs/HANDOFF.md`. Use `src/build_bridge_oracle.py --package artifacts/185 --outdir <new-directory>` for replay. Read `docs/POST186_CNOT_REWRITES.md` for the new identities, phase-network probes, and fixed-gate solver limits. The previous 186, 188 and 190 packages remain preserved. Read `docs/POST190_NEW_ARCHITECTURES.md` for structural research; its 139-layer direct Boolean template is unsolved and is not a submission circuit. Rank one is unfinished; the user's September 15 screenshot shows a 137-depth leader.

Read `docs/HANDOFF.md`, `docs/EXPERIMENTS.md`, and `docs/CURRENT_DESIGN.md` before continuing. The user's objective is rank 1 in the Classiq challenge. Do not report that objective achieved based only on a local circuit improvement.

Latest user steering: read `docs/POST129_PHASE_ROOTED_XAG.md`. Prioritize
backward phase-rooted destructive lowering of exact `advanced_round4`, with
paid native timing and recovery of overwritten controls. Three-root/40 and
four-root/109 checkpoints are partial forward traces, not oracle depths.
Complete independent-cone controls verified at 1440–1525 depth are not a
competitive route or a bound on destructive XAGs. Do not restart the completed
side-encoder, generic Direct-E, six-pebble, or independent-cone sweeps by default.

Selective recovery is now implemented: read `docs/POST185_SELECTIVE_RECOVERY.md`.
Its four-root/65 checkpoint is partial (112 native layers with restoration),
and five roots already cost 233. No new complete oracle exists. Do not repeat
the 36 completed probes or describe recovery as unimplemented. Current-wire
residual degree 8 is diagnostic, not a universal bound. The cap-after-phase
fix and the six historical 141-versus-140 overshoots are documented.

Read `docs/POST185_AND_NETWORK_ROUTE.md` and
`docs/POST185_DESTRUCTIVE_XAG_IMPLEMENTATION.md` first. Leaderboard CX counts
suggest possible architectures but do not identify them; shared_balance's558
proxy is not a compiled rank-one circuit. Six clean AND targets is a restriction
of the input-preserving compiler, not a universal18-wire bound. The current
pebbler found11 scratch for shared_balance; it did not prove optimality. Width
does not follow from multiplicative depth alone. Degree/cascade annealing
failures are heuristic, not impossibility proofs. Prioritize destructive physical
lowering of exact XAGs and corrected joint18-wire storage feasibility, with
native depth and exact phase verification. Do not cite5,131 layers against the
whole XAG route or restart minimum-AND side-loader sweeps; their built witnesses
lose through affine-routing cost. See the new report for bounded search results.

Also read `docs/POST185_ARCHITECTURE_FLOOR.md` before proposing another code or
emitter change. Its `r + 2c <= n` result is a representation-specific floor for
the measured parity-walk/UCR realization, not a universal two-stage bound. It
records useful closures for loader-aware relabelling, raw-kernel-wire trades,
and ANF loaders, but does not close the joint 18-wire x14+y13 route. That route
has 27 exact AND nodes, 32/32 five-batch-capable witness pairs, and an active
storage-aware/free-frame feasibility line; read
`docs/POST190_JOINT_18WIRE_FEASIBILITY.md` before abandoning it. Liveness was
already measured in prior MD/XAG work; the open XAG question is joint topology,
storage, toggle count, control exposure, and affine materialization.

The user's latest steering is to prioritize depth reductions over CNOT savings.
Allow more CX when it helps depth; do not spend follow-up rounds primarily on
CX tie-breakers. The 188/853 and 195/859 alternatives are historical experiments.
Read `docs/POST185_DEPTH_CAMPAIGN.md` for the latest depth-only searches.
They did not beat 185; neutral critical-gate proxy changes are not depth gains.
Do not rerun their completed sweeps automatically. Joint phase-placement
optimality is restricted to its recorded parity network and block boundaries.

## Correctness and preservation

- Preserve the original notebook and the current verified best QASM. Generate new candidates under new names until verified.
- Use `qubits_initially_zero=False` in **every Qiskit transpilation of an oracle or reusable subcircuit**, including MCX synthesis helpers. The default caused invalid low-depth results earlier.
- Materialize nonidentity transpiler output layouts before QASM serialization or subcircuit composition; `distributed_frame_search.native` now does this. Layout metadata is not a gate.
- Input is arbitrary on q[0:12]; only q[12:18] starts clean. Coordinates must be preserved and ancillas restored. A single shared global phase is allowed.
- Score the exact serialized, standalone QASM in the `u3`/`cx` basis, with at most 18 qubits. State-preparation Hadamards are not part of the oracle.
- Run `src/exhaustive_verify.py` on each proposed new best. Match the verification report SHA to the actual file. Do not mistake an old report for validation of an overwritten file.
- Relative-phase gates require a justified compute/phase/uncompute construction; lower depth alone does not establish correctness.
- `artifacts/185/two_stage_185.qmod` is the literal gate-matching companion to the latest verified QASM; its main adds preparation Hadamards. The preserved 186, 188, 190, 193/853, 193/857 and 196 packages retain their own companions. Older experimental QMODs must not be assumed to match newer QASMs.
- The 193 kernel includes a physical ancilla permutation. Use its saved uncompute mapping and `src/build_two_stage_193.py`; inserting it into the old symmetric builder is incorrect.
- Keep this documentation current when a new best or material failure is established. Distinguish verified results, historical measurements, hypotheses, and pending work.

## Workflow

Run Python through `.venv/bin/python` from the workspace root. No new login should be required unless the SDK reports expiration: the user already completed Classiq SDK authentication. Never print tokens or copy authentication material into documentation. The user requested Safari for challenge browsing.

Do not automatically rerun all old searches: some take substantial time and overwrite artifacts. `src/full_mux.py` as a script runs 200 seeds and overwrites the best QASM during its search. Prefer importing `build` and writing a new candidate filename.

The user requests active optimization to sub-140 first, then further reduction and rank one, without asking the community. Read `docs/SUB140_SEARCH.md` for the latest experiments.
The historical CX-refinement checkpoint is depth 193 / CX 853 / width 18, packaged
with a matching gate-level QMOD in `artifacts/193_cx853/`. This is a CX tie-breaker gain;
depth is unchanged. Read `docs/POST193_CX_REFINEMENT.md` and use
`src/build_permuted_oracle_package.py --package artifacts/193_cx853` for compiler replay.
For the previous depth improvement, read
`docs/POST193_RESEARCH.md` and `artifacts/193/README.md` for the phase kernel and
permuted uncomputation, exact replay, and
remaining limitations, and `docs/POST218_RESEARCH.md` for the loader floor
argument and the variants that failed. The sub-100 and rank-one objectives remain unfinished. Read `docs/POST196_RESEARCH.md` for the latest audit and searches.
No background optimization or leaderboard monitoring is scheduled.

Use `src/run_bounded.py` for native SAT runs requiring a wall-clock limit; an in-process Python timer failed to interrupt CaDiCaL. The original `src/post221_kernel_cofactor_cadical.py` adapter is invalid; use its corrected v2, which expands cardinality constraints and has positive-control validation. See `docs/POST221_RESEARCH.md`.

# Instructions for agents continuing this workspace

Current protected best is now **185 / 854 / 18**, `artifacts/185/`, as confirmed in `docs/HANDOFF.md`. Use `src/build_bridge_oracle.py --package artifacts/185 --outdir <new-directory>` for replay. Read `docs/POST186_CNOT_REWRITES.md` for the new identities, phase-network probes, and fixed-gate solver limits. The previous 186, 188 and 190 packages remain preserved. Read `docs/POST190_NEW_ARCHITECTURES.md` for structural research; its 139-layer direct Boolean template is unsolved and is not a submission circuit. Rank one is unfinished; the user's September 15 screenshot shows a 137-depth leader.

Read `docs/HANDOFF.md`, `docs/EXPERIMENTS.md`, and `docs/CURRENT_DESIGN.md` before continuing. The user's objective is rank 1 in the Classiq challenge. Do not report that objective achieved based only on a local circuit improvement.

Read `docs/POST185_ARCHITECTURE_FLOOR.md` before proposing another code or
emitter change. It shows the packaged 185 is 6% above the `r + 2c <= n` layer
bound for its own spectra, so local rewrites cannot reach rank one, and it closes
loader-aware relabelling, raw-kernel-wire trades, and ANF loaders with built,
verified counterexamples. The two directions it leaves open are a Boolean network
with peak liveness at most six values above the twelve coordinates, and a
parity-network emitter that holds its rotation rate at low spectral density.

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

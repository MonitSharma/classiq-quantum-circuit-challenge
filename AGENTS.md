# Instructions for agents continuing this workspace

Read `docs/HANDOFF.md`, `docs/EXPERIMENTS.md`, and `docs/CURRENT_DESIGN.md` before continuing. The user's objective is rank 1 in the Classiq challenge. Do not report that objective achieved based only on a local circuit improvement.

## Correctness and preservation

- Preserve the original notebook and the current verified best QASM. Generate new candidates under new names until verified.
- Use `qubits_initially_zero=False` in **every Qiskit transpilation of an oracle or reusable subcircuit**, including MCX synthesis helpers. The default caused invalid low-depth results earlier.
- Materialize nonidentity transpiler output layouts before QASM serialization or subcircuit composition; `distributed_frame_search.native` now does this. Layout metadata is not a gate.
- Input is arbitrary on q[0:12]; only q[12:18] starts clean. Coordinates must be preserved and ancillas restored. A single shared global phase is allowed.
- Score the exact serialized, standalone QASM in the `u3`/`cx` basis, with at most 18 qubits. State-preparation Hadamards are not part of the oracle.
- Run `src/exhaustive_verify.py` on each proposed new best. Match the verification report SHA to the actual file. Do not mistake an old report for validation of an overwritten file.
- Relative-phase gates require a justified compute/phase/uncompute construction; lower depth alone does not establish correctness.
- `artifacts/196/two_stage_196.qmod` is a literal gate-matching companion to the verified 196 QASM; its main adds preparation Hadamards. Older experimental QMODs must not be assumed to match newer QASMs.
- Keep this documentation current when a new best or material failure is established. Distinguish verified results, historical measurements, hypotheses, and pending work.

## Workflow

Run Python through `.venv/bin/python` from the workspace root. No new login should be required unless the SDK reports expiration: the user already completed Classiq SDK authentication. Never print tokens or copy authentication material into documentation. The user requested Safari for challenge browsing.

Do not automatically rerun all old searches: some take substantial time and overwrite artifacts. `src/full_mux.py` as a script runs 200 seeds and overwrites the best QASM during its search. Prefer importing `build` and writing a new candidate filename.

The user requests active optimization to sub-140 first, then further reduction and rank one, without asking the community. Read `docs/SUB140_SEARCH.md` for the latest experiments.
The newest verified local result is depth 196 / CX 858 / width 18, packaged
with a matching gate-level QMOD in `artifacts/196/`. Read
`artifacts/196/README.md` for the beam-scheduled phase kernel, exact replay, and
remaining limitations, and `docs/POST218_RESEARCH.md` for the loader floor
argument and the variants that failed. The sub-100 and rank-one objectives remain unfinished. Read `docs/POST196_RESEARCH.md` for the latest audit and searches.
No background optimization or leaderboard monitoring is scheduled.

Use `src/run_bounded.py` for native SAT runs requiring a wall-clock limit; an in-process Python timer failed to interrupt CaDiCaL. The original `src/post221_kernel_cofactor_cadical.py` adapter is invalid; use its corrected v2, which expands cardinality constraints and has positive-control validation. See `docs/POST221_RESEARCH.md`.

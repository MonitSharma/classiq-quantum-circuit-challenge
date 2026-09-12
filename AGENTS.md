# Instructions for agents continuing this workspace

Read `docs/HANDOFF.md`, `docs/EXPERIMENTS.md`, and `docs/CURRENT_DESIGN.md` before continuing. The user's objective is rank 1 in the Classiq challenge. Do not report that objective achieved based only on a local circuit improvement.

## Correctness and preservation

- Preserve the original notebook and the current verified best QASM. Generate new candidates under new names until verified.
- Use `qubits_initially_zero=False` in **every Qiskit transpilation of an oracle or reusable subcircuit**, including MCX synthesis helpers. The default caused invalid low-depth results earlier.
- Input is arbitrary on q[0:12]; only q[12:18] starts clean. Coordinates must be preserved and ancillas restored. A single shared global phase is allowed.
- Score the exact serialized, standalone QASM in the `u3`/`cx` basis, with at most 18 qubits. State-preparation Hadamards are not part of the oracle.
- Run `src/exhaustive_verify.py` on each proposed new best. Match the verification report SHA to the actual file. Do not mistake an old report for validation of an overwritten file.
- Relative-phase gates require a justified compute/phase/uncompute construction; lower depth alone does not establish correctness.
- Existing QMOD artifacts are experiments, not companions to the current best circuit. A matching QMOD remains to be produced.
- Keep this documentation current when a new best or material failure is established. Distinguish verified results, historical measurements, hypotheses, and pending work.

## Workflow

Run Python through `.venv/bin/python` from the workspace root. No new login should be required unless the SDK reports expiration: the user already completed Classiq SDK authentication. Never print tokens or copy authentication material into documentation. The user requested Safari for challenge browsing.

Do not automatically rerun all old searches: some take substantial time and overwrite artifacts. `src/full_mux.py` as a script runs 200 seeds and overwrites the best QASM during its search. Prefer importing `build` and writing a new candidate filename.

The user requests active optimization to sub-180 without asking the community.
The newest verified local result is depth 224 / CX 957 / width 18, packaged
with a matching gate-level QMOD in `artifacts/224/`. Read
`docs/POST258_RESEARCH.md` for parity-assisted class codes, exact replay, and
remaining limitations. The sub-180 and rank-one objectives remain unfinished.
No background optimization or leaderboard monitoring is scheduled.

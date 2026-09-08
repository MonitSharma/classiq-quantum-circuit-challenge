# Continuation handoff

## State at handoff

Updated September 8, 2026. The user wants the top rank, and most recently requested Markdown files containing everything tried, including failures, so a different chat/agent can continue. This is a research/optimization workspace, not a finished submission.

Best: `artifacts/full_mux.qasm`, depth **536**, CX **1020**, width **18**, generator seed **94**. The exhaustive verifier completed successfully on all 4096 clean-ancilla input basis states: maximum numerical error 1.4816382783292104e-14, ancilla error 0, accumulated discarded-amplitude bound 2.7656819215066786e-14, peak sparse support 64. Its report is `artifacts/full_mux.exhaustive.json`. SHA-256:

`93857f2dac80456feaf9c97ac464ee382eb532d8efe87e3622689103223683f0`

This is exhaustive numerical checking, not a symbolic proof. Since all basis columns are checked with one shared global phase, it also checks the action on superpositions by linearity, subject to numerical tolerance.

No challenge entry has been submitted. No current official score/rank exists for our artifact. No matching best-circuit QMOD has been packaged. Do not claim rank 1.

## Challenge and scoring

Source: https://www.classiq.io/challenge, visited in the user's Safari. Last observed leaderboard (historical snapshot, refresh before making current claims):

| Rank | Name | Depth | CX |
|---|---|---:|---:|
| 1 | Mateusz P. | 291 | 655 |
| 2 | Dean B. | 293 | 527 |
| 3 | Amit S. | 295 | 816 |
| 4 | Pablo C. | 303 | 645 |
| 5 | Tushar P. | 327 | 536 |

Rank 10 was depth 395; rank 14 was depth 538. Rank 1 used width 18. Do not infer a guaranteed placement from this snapshot. Observed deadline September 30, 2026; five top winners receive $2,000 each. Recheck official rules and leaderboard before submission.

The oracle must phase-mark the union of these integer-grid shapes, for x,y in 0..63:

- Square: 2 <= x <= 26 and 29 <= y <= 53.
- Bar: 26 <= x <= 49 and 39 <= y <= 43.
- Disk D1: (x-55)^2 + (y-41)^2 <= 42.
- Disk D2: (x-40)^2 + (y-19)^2 <= 72.

There are 1097 marked points out of 4096. The authoritative local predicate is `logo` in `src/search.py`. x is little-endian q[0:6], y is little-endian q[6:12]. At most six clean ancillas q[12:18] may be used. Preserve inputs and restore all ancillas. A shared global phase is acceptable. Deliverables are QMOD plus standalone QASM; depth of the exact U3/CX QASM is the main optimization target.

Original notebook: `classiq-challenge-baseline (1).ipynb`. Its saved baseline was depth 5329, CX 3502, width 18 and was verified in the notebook. It decomposes the shape into 18 disjoint rectangles. Classiq models include input Hadamards for synthesis context, but the standalone oracle removes exactly the two top-level `hadamard_transform` calls on x/y. Do not remove internal Hadamards indiscriminately.

## Critical failure and fix

Qiskit's default `qubits_initially_zero=True` let high-level synthesis treat input/dirty helper qubits as clean. An apparently excellent depth-688 pair circuit was **invalid**, with phase error 2. The same issue affected other historical low-depth MCX variants, including an apparent depth-746 candidate. The error was isolated by testing individual phase terms in `src/debug_phase.py`.

All known source transpile calls were changed to `qubits_initially_zero=False`. A rebuilt pair circuit is valid at depth 779. Old QASM files were not all rebuilt; a corrected source file does not validate its old artifact. Revalidate anything without a current matching report.

## Verified progression

| Artifact | Depth | CX | Evidence |
|---|---:|---:|---|
| `artifacts/xag_rank_True.qasm` | 1046 | 903 | Exhaustive and random-state reports |
| `artifacts/pair.qasm` | 779 | 736 | Exhaustive report; overwritten invalid 688 version |
| `artifacts/radius_mux.qasm` | 682 | 740 | Exhaustive report |
| `artifacts/full_mux.qasm` | 536 | 1020 | Exhaustive report, current best |

Verify report hashes before relying on any row. The best circuit reduces baseline depth by about 90%, but still needs a substantial reduction to beat the observed leader.

## Environment and authentication

- Workspace: `/Users/monitsharma/Downloads/classiq`.
- `.venv` Python 3.13. Use its Python, not the system interpreter.
- Installed: Qiskit 2.5.2, Qiskit Aer 0.17.2, Classiq 1.29, NumPy, SciPy, SymPy, PyEDA 0.29.
- Also installed: PySAT `python-sat` 1.9.dev15 for the native incremental SAT decomposition search.
- Newly installed and **not yet tried**: PyZX 0.10.6 and pytket 2.18.1. Installation completed successfully immediately before documentation.
- `experiments/abc/abc` is a built Berkeley ABC binary, cloned from its official repository. Build used `make -j4 ABC_USE_NO_READLINE=1`.
- PyEDA installation needed `CFLAGS=-Wno-incompatible-function-pointer-types`.
- Classiq SDK authentication was completed by the user. `CLASSIQ_TEXT_ONLY=true` was used for login. Native synthesis worked afterward. Do not expose credentials; only reauthenticate if required.
- Network package installation and Classiq synthesis previously needed approved sandbox escalation. Local optimization and verification work offline.
- No optimization process or monitor is intentionally left running at this handoff. The last verification and package-install processes both exited successfully.

## Next useful work

1. Preserve the current QASM and confirm its report hash. The independent dense verifier has now also passed on `full_mux` (5 random dense states; report `artifacts/full_mux.verification.json`).
2. The active mixed-variable LUT branch is implemented in `src/lut_decomposition.py`, `src/lut_mux_oracle.py`, and `src/search_lut_supports.py`. It exhaustively rejected all 715 four-LUT and 1,287 five-LUT combinations formed from the 13 six-input supports extracted from `experiments/logo.bench`. A separate 100-tuple random five-LUT screen found 75 UNSAT, 24 unknown, and one round-limit result; 100 additional repeated-support multisets were all UNSAT. `solve_joint_z3`, `solve_joint_z3_array`, `solve_joint_z3_bool`, and native `solve_joint_pysat` now choose arbitrary supports and LUT tables jointly with symmetry breaking; the strongest canonicalized native-SAT k=5 run completed 2,000 one-collision rounds and 2,010 pairs without a model, while a conflict-budgeted larger-batch run reached unknown at round 46. The direct all-4096-input k=4 SAT CNF (1.2M variables, 5.2M clauses) was unresolved under a 1M-conflict budget; k=5 is 1.55M variables and 6.95M clauses. The synthetic parity regression passed. This still does not cover arbitrary support tuples conclusively, so do not generalize it to all decompositions.
3. Try global PyZX and pytket rewrites of the best circuit, since local Qiskit optimization may miss cancellations across lookup/phase/uncompute. Packages are installed; no optimization script for them exists yet. Preserve qubit ordering and compile outputs to U3/CX before scoring. Check correctness after extraction/rebasing.
4. Seek architectural reductions: three separate approximately 128-depth multiplexor stages dominate the current design. Simple seed search has diminishing returns. See `CURRENT_DESIGN.md` for the construction and alternatives.
5. For every improvement, write a new artifact, exhaustively verify the serialized file, and update these docs with hash, depth, CX, and generator settings.
6. Build a matching QMOD and a clear final notebook/source explanation. Existing QMODs do not correspond to the 536-depth circuit.
7. Recheck official rules and leaderboard in Safari. Arrange submission only once deliverables are concrete and user-facing required fields/actions are known. No submission has happened.

## Safe reproduction

The saved seed is 94. Generate under a new name rather than overwriting the verified artifact:

```sh
OPENBLAS_NUM_THREADS=1 .venv/bin/python - <<'PYCODE'
import sys
from pathlib import Path
sys.path.insert(0, 'src')
from full_mux import build
from qiskit import qasm2
q = build(94)
Path('artifacts/full_mux_rebuilt.qasm').write_text(qasm2.dumps(q))
print(q.depth(), q.count_ops())
PYCODE
OPENBLAS_NUM_THREADS=1 .venv/bin/python src/exhaustive_verify.py artifacts/full_mux_rebuilt.qasm
```

Transpiler heuristics/version changes can alter the result; the saved verified QASM is the reference, not an expectation of byte-identical rebuilding. Running `src/full_mux.py` directly searches 200 seeds and overwrites its output as improvements are found.

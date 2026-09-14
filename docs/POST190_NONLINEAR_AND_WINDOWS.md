# Further experiments from the verified 190 circuit

The protected best remains **190 depth / 857 CX / 18 qubits**. Its QASM SHA is
`f8f6aec7835f6fe4e28023e2736553eb029d3522b1ea724a1e0d74213b41f549`.
No depth reduction, sub-140 construction, or leaderboard improvement was achieved.
All runs below finished; no background jobs remain.

## Nonlinear kernel with free unreachable-state phases

`src/post190_nonlinear_care.py` screens the identity and all 672 single
relative-phase Toffoli conjugations on the eight kernel wires, including open
controls. For each conjugation C, solve a weighted phase LP on C applied to the
182 actually reachable code words. The construction is C, diagonal phase D,
then the actual C inverse. Relative input phases cancel in this construction.
Two LP iterations were used per case, followed by six refinement iterations
for the 32 smallest-support cases. This is a bounded heuristic, not a proof.

The smallest phase support was **51 nonconstant terms**, versus the protected
recipe's 63. Eight promising candidates were compiled at two beam seeds each.
Each compiled kernel passed a full complex operator comparison on every
reachable word, including off-diagonal leakage. But nonlinear overhead erased
the phase-term gain: full depths ranged from 200 to 210.

The best measured alternative was **200 / 859 / 18**, using controls 1,5 and
target 3, a 52-term phase polynomial, and scheduling seed 123. It is saved as
`artifacts/post190_nonlinear_care_v1/diagnostic_200.qasm` solely as a verified
experiment, not a replacement submission. All 4096 basis inputs pass with one
shared global phase, max error 7.78e-15, zero ancilla error. SHA:
`769da656be444302c7da97a94859d7c78a7cac09522afad0ff9ea8963425453b`.
Its hash-matched `.exhaustive.json` report is alongside it.

## Fixed-boundary local resynthesis

`src/post190_window_phase.py` reconstructs the exact phase polynomial and
linear output matrix of a small window in the protected kernel. It then beam
synthesizes that window with the same output matrix and scores its composition
inside the complete oracle, retaining the saved uncompute permutation.

240 trials, 238 with nonempty phase targets, covered serialized windows of
12–64 gates. None improved on 190/857. A focused test checks the replacement
contract as a complete eight-qubit operator, including global phase.
Results: `artifacts/post190_window_phase_v1/report.json`.

## Corrections to earlier unsuccessful experiments

The old RCCX conjugation script compared a diagonal candidate against the
protected kernel, which also includes a physical output permutation. This
incorrectly rejected candidates. It also used the normalized Walsh transform
as its inverse without multiplying by 256. Both are now corrected: comparison
uses the full diagonal reconstructed from the phase recipe. The fully corrected
run is `artifacts/post190_rccx_phase_v5_corrected/`, with 672 screened moves and
20 compiled candidates meeting its support filter. Best full measurement was
214/871; none beat 190. The intermediate v4 run corrected only the permutation
comparison and still had wrong phase scaling; it is not a logo-oracle result.
Future new best candidates in this script now undergo exhaustive verification.

`src/post190_reachable_lift_beam.py` had two additional contract errors: its
reachable-word builder used x4 instead of x4 XOR x5, and its recipe path mixed
radians with phase-in-pi units while missing inverse-Walsh normalization. These
are corrected, and the current 63-term recipe is now retained as an explicit
baseline even when a restart perturbs unreachable values.

The corrected run used eight starts and 3000 moves per start. It retained 63
terms, with no support improvement. Six identity-ending kernel schedules
measured 45–48 depth. They should not be compared directly with the protected
permutation-ending kernel as if their output contracts were identical.
Results: `artifacts/post190_reachable_lift_v6_corrected/`.
Earlier phase-lift runs that used these erroneous domain/scaling helpers do
not establish an architectural limit and should not be used as such.

## Validation and interpretation

Four focused tests in `tests/test_post190_nonlinear_care.py` pass. They check
all 4096 coordinate-to-code truth mappings, open-control RCCX phase cleanup,
phase normalization against the protected physical kernel, and fixed-boundary
window synthesis. The protected 190 QASM hash was checked unchanged.

Native recompilation of the inverse of the full protected oracle also retained
190/857. No original notebook or protected package was modified.

The useful new observation is that nonlinear preprocessing can reduce the
kernel's phase support. In the tested single-gate family, it costs more depth
than it saves. This does not close multiple nonlinear layers, different
encoders, direct Boolean synthesis, or other oracle architectures. The previous
unsolved 139-depth Boolean template remains a conditional construction, not a
synthesized logo circuit.

# Search from 196 toward sub-100

September 13, 2026. The user's updated objective is **sub-100 depth and rank one**.
Safari showed the official leader at **142 depth / 557 CX / 18 qubits** and
Monit S. at 218 / 897. No submission was made in this continuation. A verified
142-depth entry establishes feasibility of 142 under the rules; it does not
establish feasibility of 99.

## Baseline independently reproduced

The protected `artifacts/196/two_stage_196.qasm` passed a fresh all-4096-input
check, copied to `artifacts/post196_audit_v1/baseline.qasm` so its original
reports remain intact. SHA-256:
`63333fade2e7e38c9a4edf333888c26bdac234c04e955fd6a624c0ea6e714c30`.
Maximum error 9.03e-15, zero ancilla error. Rebuilding with the corrected native
compiler into `artifacts/post196_audit_v1/rebuild/` produces the identical SHA
and passes exhaustive verification again.

## A second serialization correctness issue found and fixed

`qubits_initially_zero=False` is necessary but insufficient to preserve reusable
oracle semantics. Qiskit can elide a permutation and retain it in
`QuantumCircuit.layout`. Neither a literal QASM2 file nor ordinary circuit
composition applies that metadata. An x-loader constructed by the guarded
beam was correct before compilation but put input 4 on coordinate 6 afterward:
its final layout exchanged wires 1 and 8. This was caught before integration.

`distributed_frame_search.native()` now materializes nonidentity final layouts
as actual three-CX swaps, asserting that the initial placement is identity.
The new cycle-permutation regression test checks the exact serialized operator.
Nine focused tests pass, including all existing beam-scheduler tests. This fix
does not change the 196 artifact or its deterministic replay. The distinction is
also documented by IBM's [ElidePermutations reference](https://quantum.cloud.ibm.com/docs/api/qiskit/qiskit.transpiler.passes.ElidePermutations).

The offline report's statement that guarded loaders of depth 70 and 74 were
"worse than 77" is internally inconsistent. No saved validated artifacts or
complete recipe for those numbers were found in the inspected source. A fresh
bounded audit (three seeds, beam 12, branch 6) gives **126–134 for y and 127–132
for x**, with all 64 promised input mappings checked. This does not disprove
that another configuration could reach 70; it does mean those numbers cannot
currently justify integration. See `post196_guard_audit.py` and
`artifacts/post196_audit_v1/guard_report.json`.

## Completed new experiments

| Experiment | What was actually tested | Result |
|---|---|---|
| Recompile old modular kernel lifts | 13 distinct saved full-turn/promised-domain phase vectors, 12 new beam schedules each | None beat the current 43/89 kernel under the selected configuration; 196 unchanged |
| Linear recoding of the loaded bits | All 168 invertible three-bit frames, binary and signed-lift lookup tables, 12 structured schedules each; 18 selected frames also get 12 bank schedules | 4,248 raw options per side. Best compiled shortlisted alternative loaders 83 y / 80 x; baseline 77 is better. All retained loaders checked on 64 inputs. No full-oracle improvement |
| Kernel restoration with incoming wire times | 10,000 randomized Gaussian eliminations; compile 40 distinct leading depth/count choices and check their complete eight-qubit operators | Best complete score 197 / 857, versus protected 196 / 858. Lower CX does not win when depth increases |

Artifacts: `post196_nulls_v1`, `post196_linear_frames_v1`, and
`post196_restore_v2`. The initial restoration prototype (`v1`) failed its
internal identity assertion because it could choose an already-eliminated
pivot row. The corrected search excludes those rows; no invalid candidate was
exported from that prototype.

## Architecture implications and open work

The 77-layer observation is a property of the current construction, not a
proved optimum over reversible encoders. In particular, the earlier 77-layer
argument assumes a fixed division between source wires and phase hosts and
adds an empirical frame overhead. The 56-layer wire-slot estimate also fixes a
particular phase spectrum. Neither is a universal quantum lower bound.

Holding both current loader circuits fixed makes sub-100 unavailable through
kernel-only optimization. The next substantial route being tested is an
in-place reversible encoder: two layers of disjoint nonlinear gates separated
by affine transformations, four class-separating outputs, and five garbage
wires. The inverse restores all coordinates. This changes the encoder's job
and permits temporary coordinate modification. It remains an experiment, not
a demonstrated sub-100 construction.

`post196_layered_cadical.py` translates the earlier bounded encoder model to
fully expanded CNF for CaDiCaL. Its first positive-control run exposed incomplete
model reconstruction through the tactic converter. The corrected adapter lifts
the Boolean assignment against the original formula, checks every original
constraint, and then performs the original all-64-input collision check.
Only a fully separating witness qualifies for circuit construction. External
wall-clock guards are required. SAT on a subset is not an encoder solution;
a timed-out run is not UNSAT.


### Bounded nonlinear-encoder outcomes

Both two-layer CaDiCaL searches were stopped by their external 120-second
limits. The y run reached a 27-sample witness but still had 72 class collisions
on the complete domain; x reached a 35-sample witness but still had 96. These
are rejected partial witnesses, not candidate oracles or impossibility proofs.
The corrected positive control (a known separable 16-class map on all 64 inputs)
passes; see `artifacts/post196_layered_positive_v2/`.

A distinct preconditioning screen (`post196_nonlinear_two_frame.py`) applies
one physical two-control NOT, including all control polarities, to a six-bit
coordinate before looking for a two-frame code. This conjugates the period
conditions by a nonlinear permutation and is not covered by the earlier
linear-period exclusions. The completed y screen tested **4,560** combinations
of gate, feasible raw parity and independent physical-axis direction triple;
none admitted a separating code. This closes this particular y-side
preconditioner family, not arbitrary nonlinear preconditioning or arbitrary
period directions. The x search has a separate bounded report.

A final 32-seed Qiskit recompilation of the exact 196 QASM also leaves the best at 196 / 858 (`artifacts/post196_final_compile_v1/report.json`). All calls explicitly disable initially-zero assumptions and materialize output layouts.

The x preconditioning run completed at least 4,520 cases without a witness before its 150-second limit. Its family was not exhausted. No background optimizer or monitoring task remains running. Best verified result remains 196 / 858 / 18; sub-100 and rank one remain unresolved.

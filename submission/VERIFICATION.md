# Submission

This folder contains the circuit submitted to the Classiq Quantum Circuit Challenge.

| file | contents |
|---|---|
| `submission.qasm` | OpenQASM 2 circuit (depth 111, 557 CX, 423 U3, 18 qubits), SHA-256 `339c99e90a56a2aff4e7ce3f465879cd4a25acc8a1f82acb78a4534cd8108b1a` |
| `submission.qmod` | gate-for-gate Qmod transcription of the same circuit |
| `oracle_spec.qmod` | high-level specification of the oracle |
| `synthesis_options.json` | synthesis settings (depth optimisation, width 18) |
| `submission.exhaustive.json`, `verification_report.json` | exhaustive verification on all 4,096 clean-ancilla inputs |
| `submission.verification.json` | dense random-state check |

The circuit is identical to [`artifacts/111/conditional_loader_111_cx557.qasm`](../artifacts/111/conditional_loader_111_cx557.qasm), the official challenge submission (depth 111, 557 CX, 423 U3, 18 qubits). Earlier milestones at depths 112, 113, 114, and 115 are preserved in [`artifacts/`](../artifacts/).

## Checking it

```sh
python scripts/verify_circuit.py submission/submission.qasm     # numpy only
python src/exhaustive_verify.py submission/submission.qasm      # Qiskit-based
python src/verify.py submission/submission.qasm 5                # five dense random states (Qiskit Aer)
```

The exhaustive check propagates each of the 4,096 inputs $|x, y, 0^6\rangle$ through the circuit and requires the output $e^{i\phi}(-1)^{f(x,y)}|x, y, 0^6\rangle$, with a single global phase $\phi$ shared by all inputs. The largest deviation is $5.57 \times 10^{-14}$, and no amplitude leaks into nonzero ancilla states.

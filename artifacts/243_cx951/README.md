# Verified 243-depth, 951-CX package

This improves the CX tie-breaker from the earlier `artifacts/243/` package;
the depth is unchanged. It does **not** meet the user's sub-180 objective.

- `two_stage_243.qasm`: standalone 18-qubit U3/CX oracle, no preparation H gates.
- `two_stage_243.qmod`: literal matching gate-level oracle. Its `main` harness
  adds twelve preparation H gates; those are not part of the oracle score.
- `two_stage_243.exhaustive.json`: all 4096 clean-ancilla basis inputs checked.
- `two_stage_243.verification.json`: three independent dense-state checks.
- `manifest.json`: exact QASM SHA and gate-for-gate QMOD matching result.

QASM SHA-256:
`38f5948a44d21c923ae740e64b968336898448ee01a30e85d81c583fe3dff696`.
Exhaustive maximum error `6.88e-15`; dense maximum error `1.67e-16`.
Coordinates and ancillas are restored. The forward encoders use alternative
integer rotation angles with the same output-bit parity; their exact inverses
cancel the input-dependent phases. The eight-wire kernel and class codes are
the same as the protected 243/971 circuit.

Reproduce in a **new** directory from the workspace root:

```sh
.venv/bin/python src/post258_encoder_lifts.py \
  --outdir /tmp/classiq_encoder_lifts_fresh --seeds 8
```

The lift choices and encoder settings are in
`artifacts/post258_encoder_lifts_v1/report.json`. All transpilation explicitly
uses `qubits_initially_zero=False`. No cloud resynthesis or submission was made.

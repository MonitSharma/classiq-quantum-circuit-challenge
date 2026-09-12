# Verified 224-depth oracle

**224 depth / 957 CX / 18 qubits**, standalone U3/CX basis. This improves on
258 by 34 layers; sub-180 and rank one remain unfinished.

- `two_stage_224.qasm`: oracle only, no input-preparation Hadamards.
- `two_stage_224.qmod`: literal matching 1761-gate oracle. Its `main` harness
  adds twelve preparation Hadamards; they are absent from the oracle QASM.
- `two_stage_224.exhaustive.json`: all 4096 arbitrary-coordinate basis inputs
  checked with clean ancillas, preserving coordinates and restoring ancillas.
- `two_stage_224.verification.json`: independent dense-state checks.
- `manifest.json`: exact SHA and gate-for-gate QMOD match.

QASM SHA-256:
`14b9272a21fc9a8d47ce036daa2c45fe792e092f06078f3e7ad4dd14bb79371f`.
Exhaustive maximum error is `7.56e-15`, with one shared global phase.
Three dense-state checks have maximum error `2.11e-16` and ancilla leakage
`6.45e-17`.
A fresh replay produces the identical QASM SHA. No cloud resynthesis or
challenge submission was made; the package is locally numerically verified.

The construction loads three bits on each side, assisted by y5 and the
temporarily exposed coordinate parity x4 XOR x5. New class codes and phase
scheduling reduce the kernel to 69 layers. Joint encoder scheduling chooses
the full compute/kernel/uncompute circuit rather than isolated loader scores.
Every reused component is transpiled with `qubits_initially_zero=False`.

Reproduce from the workspace root into a new output directory:

```sh
.venv/bin/python src/post258_joint_encoder_schedule.py \
  --record artifacts/224/class_codes.json \
  --kernel artifacts/224/kernel.qasm \
  --outdir /tmp/classiq_224_fresh --seeds 120
```

The selected encoder settings and alternatives are recorded in
`artifacts/post258_joint_encoders_v1/report.json`.

# Verified 221-depth oracle

Standalone `two_stage_221.qasm`: **221 depth, 944 CX, 18 qubits**, U3/CX only.
SHA-256: `4f9fa6232930777426ac4f8118155780471f111c31435e7578175170035e313f`.

The 222 package remains preserved. This uses its same class codes, relative-phase
lookup construction, and 69-layer kernel. Choosing y encoder seed 99 and x seed
151 jointly exposes a more favorable complete-circuit simplification than choosing
isolated minimum-depth encoders. Both encoders have depth 77. The assembled raw
circuit is depth 223; native optimization produces 221. This is an incremental
boundary optimization, not a new architectural breakthrough.

`two_stage_221.exhaustive.json` checks all 4096 clean-ancilla basis inputs against
one shared global phase (maximum error 7.11e-15, ancilla error zero). Independent
three-state dense verification is in `two_stage_221.verification.json`.
The QMOD oracle matches all 1749 QASM gates and parameters; its main adds twelve
preparation Hadamards absent from the standalone oracle. Cloud resynthesis and
challenge submission have not been performed. Sub-180 and rank one are unfinished.

## Reproduction

Run from the workspace root with a fresh output directory:

```sh
.venv/bin/python src/post222_joint_relative.py --record artifacts/221/class_codes.json --kernel artifacts/221/kernel.qasm --outdir /tmp/classiq_joint_relative_fresh --seeds 160
```

The selected `joint_d221_cx944.qasm` must have the SHA above. A separate direct
reconstruction using seeds 99 and 151 reproduced that SHA. The search retains
17 y and 13 x nondominated wire-timing profiles and compiles all 221 combinations.
Timing dominance is only a search heuristic: native cancellation depends on gate
structure, so omitted dominated circuits are not proven inferior.
The earlier top-32 screening and full-221 screening agreed on the best file.
Raw reports are `artifacts/post222_joint_relative_v1/report.json` and
`artifacts/post222_joint_relative_v2/report.json`.

Every native transpilation uses `qubits_initially_zero=False`. The construction
uses the encoder's actual inverse so its input-dependent relative phase cancels
through the diagonal kernel. All proposed best files were serialized and verified.

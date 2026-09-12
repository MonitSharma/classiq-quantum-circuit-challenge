# Verified 226-depth oracle

18 qubits, 959 CX gates, 804 U3 gates. This is an improvement from 258 but does
not meet sub-180. All original and earlier verified QASMs remain preserved.

`two_stage_226.qasm` is the standalone oracle without input Hadamards.
`two_stage_226.qmod` contains its literal matching gate sequence and a `main`
harness with twelve preparation Hadamards. It has not been cloud-resynthesized
or submitted. The exact-file exhaustive report and three dense-state checks
are alongside the circuit.

QASM SHA-256:
`5d048fc43047ec9566ca713602156681dec0eb5b81515fd839f9a72c2a818765`.
All 4096 inputs pass with a common global phase, maximum error `7.57e-15`;
three dense states pass with maximum error `2.10e-16`. Ancillas are restored.

The encoder uses y5 and the temporarily exposed parity x4 XOR x5 as its fourth
code bits. A new class-code assignment reduces the kernel to 71 layers. Both
encoders, including the x parity update, have depth 78. The inverse restores
the original coordinate wires exactly.

Reproduce from the workspace root into a new directory:

```sh
.venv/bin/python src/post258_raw_parity_codes.py \
  --record artifacts/226/class_codes.json \
  --kernel-file artifacts/226/kernel.qasm \
  --outdir /tmp/classiq_226_fresh --seeds 48
```

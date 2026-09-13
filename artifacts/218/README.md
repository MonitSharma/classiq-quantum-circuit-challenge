# Verified 218-depth oracle

`two_stage_218.qasm`: **218 depth / 897 CX / 18 qubits**, standalone U3/CX oracle.
SHA-256: `3a685c32ea0d78637be1a575c91e6c7d13db0efdbf37a8f794fb44e7fb024a88`.

The kernel is now 66 depth / 123 CX. Adding integer multiples of 2π times Boolean
monomials changes no basis-state phase. Searching these equivalent phase
representations and resynthesizing reduced the prior 69-layer kernel. The
encoders use the existing class codes, with y seed 11 and x seed 151. All 221
nondominated encoder timing combinations in the 160-seed pools were compiled.

The exact serialized oracle passes all 4096 coordinate basis inputs with one
shared global phase, zero ancilla error, and maximum error 8.83e-15. Three
independent dense-state checks pass. Both kernel and oracle replay identically.
The QMOD oracle matches all 1683 serialized gates and parameters. Its `main`
adds twelve preparation Hadamards, which are absent from the standalone QASM.
Neither cloud resynthesis nor challenge submission has been performed.
The 221, 222, 224 and earlier verified packages remain preserved.

## Replay

From the workspace root, using a fresh output directory:

```sh
.venv/bin/python src/replay_two_stage_218.py --outdir /tmp/classiq_218_fresh
```

`kernel_recipe.json` contains the actual phase coefficients and synthesis seed.
`class_codes.json` retains the earlier Boolean ANF specification: it specifies
the same phase operation, but does not encode this new choice of integer lift.
The replay verifies both hashes in `manifest.json` and all 4096 inputs.

Source search: `src/post221_kernel_cube_nulls.py`, 6000 iterations over 1051
modular moves, followed by bounded native compilation. The selected phase
vector was found at iteration 2126; the selected kernel synthesis seed is 4.
Search evidence: `artifacts/post221_cube_nulls_v1/report.json` and
`artifacts/post221_cube_integrated_v1/report.json`.

Sub-180 and rank one remain unresolved. This package is an intermediate result.

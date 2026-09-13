# Verified 222-depth oracle

**222 depth / 945 CX / 18 qubits**, standalone U3/CX basis. Sub-180 and rank
one remain unfinished. Earlier verified circuits are preserved.

- `two_stage_222.qasm`: oracle only, without input-preparation Hadamards.
- `two_stage_222.qmod`: literal matching 1749-gate oracle. Its `main` harness
  adds twelve preparation Hadamards, absent from the scored oracle QASM.
- `two_stage_222.exhaustive.json`: all 4096 coordinate basis inputs checked
  with clean ancillas, one common global phase, and ancillas restored.
- `two_stage_222.verification.json`: independent dense-state checks.
- `manifest.json`: exact SHA and gate-for-gate QMOD match.

QASM SHA-256:
`6c8ff19470da3d6550d1741d502065e1ace10c72cb4c9d62aa4683703a344031`.
Exhaustive maximum error is `7.85e-15`; discarded-amplitude bound is `1.07e-14`.
A fresh replay reproduces the exact QASM hash. The QMOD has not been
cloud-resynthesized or submitted.

The class codes and 69-layer kernel are retained from the 224 package. The
lookup uses H-conjugated rotations and removes terminal data-to-target CXs
that contribute only canceling relative phases. Both selected encoders have
depth 77, including the x4 XOR x5 update. The exact inverse restores all data.

Reproduce from the workspace root into a new directory:

```sh
.venv/bin/python src/post224_relative_lookup.py \
  --outdir /tmp/classiq_222_fresh --seeds 32
```

The code reads the preserved 224 class codes and kernel. The same files are
copied into this package. The derivation and competing experiments are in
`docs/POST224_REVIEW_AND_EXPERIMENTS.md`.

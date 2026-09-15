# Verified local oracle: 185 depth / 854 CX / 18 qubits

This improves the previous 186/855 package through three exact CNOT rewrites,
native gate fusion, and scheduling. Rank one remains unfinished; nothing has
been submitted from this package.

- `two_stage_185.qasm`: standalone U3/CX oracle without preparation gates.
- `two_stage_185.qmod`: literal matching 1,617-gate companion; its `main`
  adds twelve preparation Hadamards.
- `two_stage_185.exhaustive.json`: all 4,096 promised basis inputs pass,
  with restored coordinates and ancillas and one shared global phase.
- `two_stage_185.verification.json`: five dense-superposition checks.
- `bridge_source.qasm`, `bridge_recipe.json`: source circuit, three exact
  rewrites, and saved gate permutations for reproducible construction.
- `kernel.qasm`, `class_codes.json`: earlier architecture provenance;
  these alone do not reproduce the new full-oracle rewrites.

SHA-256: `ef933bc786bc25feb1fbd618fc8c45a0bdc8dce43879aacfcc6042daaca5bfc8`.

```sh
.venv/bin/python src/build_bridge_oracle.py --package artifacts/185 --outdir /tmp/classiq-185-replay --verify
```

Run from the workspace root with a new output directory. No solver, network,
external optimizer, authentication, or submission is involved in replay.
See `docs/POST186_CNOT_REWRITES.md` for methods, validation, and limitations.

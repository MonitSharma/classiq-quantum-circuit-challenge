# Verified local oracle: 186 depth / 855 CX / 18 qubits

This improves the previous local 188/855 and submitted 190/857 circuits.
Rank one remains unfinished. This package has not been submitted.

- `two_stage_186.qasm`: scored standalone U3/CX oracle, without preparation.
- `two_stage_186.qmod`: literal matching 1,625-gate companion. Its `main`
  adds the twelve-Hadamard synthesis harness.
- `two_stage_186.exhaustive.json`: all 4,096 promised basis inputs pass,
  with coordinates and ancillas restored and one shared global phase.
- `two_stage_186.verification.json`: five dense-superposition checks pass.
- `reschedule_source.qasm`, `schedule_recipe.json`: self-contained replay
  through two saved permutations and one native-fusion stage.
- `phasepoly_provenance.json`: provenance of the phase-reordered source,
  including the external optimizer commit and original 188 circuit hash.
- `kernel.qasm`, `class_codes.json`: original architecture provenance;
  these alone do not reproduce the final gate order.

SHA-256: `5e7f8f165928e965cc47d5b697def0681a79aa6432b8d94302374fd071f25ac6`.

```sh
.venv/bin/python src/build_rescheduled_oracle.py --package artifacts/186 --outdir /tmp/classiq-186-replay --verify
```

Run from the workspace root with a new output directory. Replay requires no
solver, external PhasePoly checkout, network access, or authentication. A fresh
replay in `artifacts/post186_replay_v1/` matched the hash and passed all inputs.
See `docs/POST188_PHASE_REORDERING.md` for results and limitations.

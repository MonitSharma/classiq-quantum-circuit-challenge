# Verified 188 / 855 / 18 oracle

This is the new local best, improving the submitted 190 / 857 / 18 circuit.
Rank one has not been achieved or claimed. Nothing was submitted in this run.

- `two_stage_188.qasm`: standalone oracle; no preparation Hadamards.
- `two_stage_188.qmod`: literal gate-matching companion; `main` adds the
  twelve-Hadamard synthesis harness.
- `two_stage_188.exhaustive.json`: all 4,096 basis inputs, restored coordinates
  and ancillas, one shared global phase.
- `two_stage_188.verification.json`: five dense-superposition checks.
- `schedule_recipe.json` and `reschedule_source.qasm`: deterministic replay
  of gate permutations and native fusions from the protected 191 source.
- `kernel.qasm`, `class_codes.json`, `source_encoder_recipe.json`: provenance
  of the original construction, including its physical ancilla permutation.

QASM SHA-256:
`f8f7e73ad2d48daa31a29a354e2287347b90e59d460f9e7d271495850635e46e`.

```sh
.venv/bin/python src/build_rescheduled_oracle.py --package artifacts/188 --outdir /tmp/classiq-188-replay --verify
```

Run from the workspace root with a new output directory. This replay needs
no optimization solver, authentication, or network access.

See `docs/POST190_COMMUTING_SCHEDULE.md` for the search, correctness checks,
fixed-gate optimality limits, and remaining structural depth gap.

# Verified 193-depth / 853-CX oracle

**Depth remains 193.** CX count improves from 857 to **853**; width remains 18.
This is a tie-breaker improvement, not a new depth milestone or rank-one result.

Standalone QASM SHA-256:
`4dbd4993f7d1e807b5ae2908f9580d70070f247a4496140b858f08c95ce82709`.

- `two_stage_193.qasm`: complete `u3`/`cx` oracle, 1,636 gates.
- `two_stage_193.qmod`: exact gate-matching companion; main adds twelve
  preparation Hadamards, which are absent from the oracle QASM.
- `kernel.qasm`: 40-depth / 85-CX phase-plus-permutation kernel. It is not
  diagonal by itself; use the mapping in `replay_recipe.json`.
- `replay_recipe.json`: loader seeds 298/506 in both directions and physical
  uncompute mapping. `phase_search_recipe.json` records the phase search.

All 4,096 inputs pass with one common global phase: maximum error 7.56e-15,
zero ancilla error, discarded-amplitude bound 1.41e-14. Five dense random
superpositions pass with maximum error 2.21e-16. Fourteen targeted tests pass.
The original 193/857 and 196 packages remain unchanged. No submission was made.

Replay the compiler assembly from the saved kernel into a new directory:

```sh
.venv/bin/python src/build_permuted_oracle_package.py \
  --package artifacts/193_cx853 --outdir artifacts/new_193_cx853_replay --verify
```

See `docs/POST193_CX_REFINEMENT.md` for the experiments and their limits.

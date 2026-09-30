# 111 / 557 CX recipe

Result: `../../conditional_loader_111_cx557.qasm` (SHA-256 `339c99e90a56a2aff4e7ce3f465879cd4a25acc8a1f82acb78a4534cd8108b1a`),
depth 111, 557 CX, 423 U3. Same construction as `../cx561/README.md`, with a lower-CX x loader:

- x loader `x_loader.pkl` / `x_loader_beam.txt`: frame `../cx561/x_frame.lb`, `lbeam4c` PREFIX restart from a 111/112
  loader (parameters in `x_loader_campaign_row.json`: prefix beam, K, seed, W, randomized beam weights), ready 39 / 40 / 41 / 43, 120 CX.
- y loader `y_loader_T2xL0.pkl` = the 111/561 y loader (ym_s9 with target 2 relabeled to plain L2).
- FEM kernel beam at T = 111, W = 12000, seed 2 (`tail115/paireval.py`, STRICT ZOCC FUSE) → assembled 111, `canc`, exact MILP 111
  → 111 / 559 (`stage_559_m111.qasm`, `kernel_schedule.txt`, `kernel_model.in`).
- `numresyn/dsloop.py` (k = 3, `SHARD=0/2`): 559 → 558 → 557 (`dsloop_559_to_557.log`).

Replay:
```
export CLASS_CODES=$PWD/artifacts/185/class_codes.json CLASSIQ_ROOT=$PWD
STRICT=1 ZOCC=1 FUSE=1 .venv/bin/python src/post151_sa/tail115/paireval.py \
  artifacts/111/recipes/cx557/x_loader.pkl artifacts/111/recipes/cx557/y_loader_T2xL0.pkl 111 12000 2 r111b
SHARD=0/2 .venv/bin/python src/post151_sa/tail115/numresyn/dsloop.py artifacts/111/recipes/cx557/stage_559_m111.qasm ds 3 10
```

Checks: `scripts/verify_circuit.py` PASS (6.66e-14), `src/exhaustive_verify.py` all 4096 inputs (5.57e-14, ancillas restored),
`tail115/everify.py` PASS, dense check vs the 116 champion (`../../dense_cx557_vs_116.txt`).

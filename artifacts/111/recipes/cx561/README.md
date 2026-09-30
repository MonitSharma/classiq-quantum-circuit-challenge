# 111 / 561 CX recipe (and 111 / 558)

Result: `../../conditional_loader_111_cx561.qasm` (SHA-256 `7fb5dcb9227dfe71d7b87f0cd29bdd7bda1fb10537c09b227ff953bdde2d4314`),
depth 111, 561 CX, 423 U3, 18 wires.

Same method as the 113 and 112 recipes (relabeled target functions with sparse supports, re-searched loaders, a start-basis
relabel chosen by the exact-model kernel screen and realised by re-angling).

## Loaders
- **x**: frame `x_frame.lb` / `x_support.pkl` (target 1 loads `L1 ⊕ L0`, target 2 loads `L1 ⊕ L2 ⊕ px`; 45 / 22 / 24 rotations).
  `lbeam4c` with `PREFIX` = the 42-layer loader `x_prefix_beam_x6k_s10.txt`, `PREFIXK=20`, W = 12000, seed 1, maxd 45
  (`suffix_sat/loadcamp.py`): `x_loader.pkl` / `x_loader_beam.txt`, code wires ready at 39 / 40 / 41 / 43, 122 CX.
- **y**: frame `y_frame.lb` / `y_support.pkl` (target 1 = L1 with the lightest support, 30 / 11; target 2 = `L2 ⊕ Ly0`, 15 / 2),
  `lbeam4c` from scratch, W = 6000, seed 9: `y_loader_before_relabel.pkl` / `y_loader_beam.txt`, ready 33 / 37 / 39 / 45, 120 CX.
  Target 2 is then relabeled back to plain `L2` (⊕ Ly0) by re-angling (`suffix_sat/relabel2.py '{"2":64}'`, exact, same
  schedule, `req` recomputed): `y_loader_T2xL0.pkl`.

## How the pair and relabel were found
`suffix_sat/screen.py` over 6 x loaders × 8 y loaders × 32 realisable relabel combinations (y target 1 ⊕ {0, Ly0}, y target 2
⊕ {0, py, Ly0, both}, x target 2 ⊕ {0, px, L0, both}) at T = 111: feasible only for this x loader with three of the y loaders,
each with the y target-2 wire relabeled as above.

## Kernel
FEM kernel beam at T = 111 (`tail115/paireval.py`, STRICT ZOCC FUSE, W = 12000, seed 2) → assembled 111, `canc`, exact MILP
111 → 111 / 561 (`kernel_schedule.txt`, `kernel_model.in`; seed 1 gives 562).

Replay:
```
export CLASS_CODES=$PWD/artifacts/185/class_codes.json CLASSIQ_ROOT=$PWD
STRICT=1 ZOCC=1 FUSE=1 .venv/bin/python src/post151_sa/tail115/paireval.py \
  artifacts/111/recipes/cx561/x_loader.pkl artifacts/111/recipes/cx561/y_loader_T2xL0.pkl 111 12000 2 r111
# -> scratch/work_k/pe/r111_s2_m111.qasm, byte-identical to the artifact (checked 2026-09-27)
.venv/bin/python src/post151_sa/tail115/numresyn/dsloop.py artifacts/111/conditional_loader_111_cx561.qasm ds111 3 10   # SHARD=1/2 -> 558
```

## Checks
`scripts/verify_circuit.py` PASS (6.66e-14), `src/exhaustive_verify.py` all 4096 inputs (max error 5.57e-14, ancilla error
5.57e-14), `tail115/everify.py` PASS, five dense random superpositions equal to the 116 champion (`../../dense_cx561_vs_116.txt`).

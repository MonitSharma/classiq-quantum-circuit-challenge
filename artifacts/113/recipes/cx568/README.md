# 113 / 568 CX recipe (and 113 / 564)

Results: `../../conditional_loader_113_cx568.qasm` (SHA-256 `73fbd06c16b609764eb51c8e5aede8c262b612d2764558da5479477eef20e668`)
and, after numerical resynthesis, `../../conditional_loader_113_cx564.qasm`
(SHA-256 `6cf736a40af57d503641887dc73c04a9a8278811ec11ad55e87d2a9c51d32ccb`).

## Idea: choose which label combinations the loaders compute, then re-search the loader

Depth 114 came from letting a conditional target load `L ⊕ b` (a CZ absorbed at its closing Hadamard) with the old
loader schedule. For 113 the same freedom is used one level earlier: **a relabeled target function has a different, sometimes
much sparser, rotation support**, and the x loader is re-searched with the new supports.

- x target 2 loads `L1 ⊕ L2 ⊕ px` instead of `L1 ⊕ L2`: best support 24 rotations, only **4** depending on L0 (was 23 / 10),
  found by `suffix_sat/suppvar.py` (reweighted L1 with random mod-2π lifts, `CRIT=L`).
- x target 1 loads `L1 ⊕ L0`: support = the relabeled 114 x loader's target 1 (21 rotations + 1 = 22, 10 depending on L0).
- `suffix_sat/mkframe.py` builds the frame: supports 45 / 22 / 24, label code, and the code rows in the new basis
  (`req = [48, 64, 192, 496]` = px, L0, L1, L2 over inputs and target wires). Only 14 rotations need L0 after it closes (was 20).
- `lbeam4c` from scratch (W = 6000, seed 4, ready-time goals px 42 / Lx0 36 / both late wires 43) gives a **43-layer x loader**
  with code wires ready at 37 (Lx0), 41 (px), 41 (target-2 wire), 43 (target-1 wire); exact (`check_loader2` 4e-16), 122 CX.
  File `x_loader_cs4_T1L1xL0_T2L1xL2xpx.pkl`, beam `x_loader_beam.txt`, frame `x_frame.lb`, support dict `x_support.pkl`.
- y loader: `v34_1_yw005_3` with target 2 relabeled to `L2 ⊕ Ly0` by re-angling only (`suffix_sat/relabel2.py`, 12 angles),
  `req = [32, 64, 128, 320]`. File `y_loader_v34_1_T2xL0.pkl`.
- FEM kernel beam at T = 113 (`tail115/paireval.py`, STRICT ZOCC FUSE, W = 12000, seed 3) → assembled 113, `canc`, exact MILP
  113 → **113 / 568**. Seeds 1 and 2 give 569. `kernel_schedule.txt`, `kernel_model.in`.
- `numresyn/dsloop.py` (k = 3) on the 568: four accepted rounds → **113 / 564** (`../cx564/dsloop_568_to_564.log`).

Replay:
```
export CLASS_CODES=$PWD/artifacts/185/class_codes.json CLASSIQ_ROOT=$PWD
STRICT=1 ZOCC=1 FUSE=1 .venv/bin/python src/post151_sa/tail115/paireval.py \
  artifacts/113/recipes/cx568/x_loader_cs4_T1L1xL0_T2L1xL2xpx.pkl artifacts/113/recipes/cx568/y_loader_v34_1_T2xL0.pkl 113 12000 3 r113
.venv/bin/python src/post151_sa/tail115/numresyn/dsloop.py artifacts/113/conditional_loader_113_cx568.qasm ds113 3 8
```

## Checks
Both circuits: `scripts/verify_circuit.py` PASS, `src/exhaustive_verify.py` all 4096 inputs (max error 3.89e-14, ancilla error
3.89e-14), `tail115/everify.py` PASS, five dense random superpositions equal to the 116 champion.

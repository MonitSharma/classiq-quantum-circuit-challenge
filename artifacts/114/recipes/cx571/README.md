# 114 / 571 CX recipe

Result: `../../conditional_loader_114_cx571.qasm` (SHA-256 `7510ebd22c237d7948ed52e3af57369a4378100a6e81048e20459051b1bb3aa9`).

## Idea: relabel a late label by a CZ absorbed at its closing Hadamard

A CX that targets a label wire A right after its closing Hadamard is equal to a CZ applied before that Hadamard
(`CX(B->A) · H_A = H_A · CZ(B,A)`). In the phase-kickback frame a CZ with a wire holding `b` just flips the loaded label
by `b`: target A then loads `L ⊕ b` instead of `L`. So the kernel may start (and, mirrored, end) with the late x label
wire holding `L1 ⊕ L0` instead of `L1`. That is a different kernel start basis on the critical wire, and in the fused
exact model it makes the kernel schedulable at T = 114 with the unchanged loader timing (`suffix_sat/kbasis.py`
what-if: `Lx1 ^ L0` feasible, `Lx1 ^ px` mind 17).

The x loader has to load `L1 ⊕ L0` with its old schedule. Its target-1 relative phase must change by `π·L0(x)` (mod 2π).
`relabel.py` finds this by re-angling rotations only (MILP over the existing target-1 atoms, target-1 parities that a
wire holds at an idle layer, and mod-2π lifts): two existing rotations change angle and one rotation is added at an
idle slot (layer 33, wire 4, parity T1+x5+x3+x0). Same CX/H layering, same per-wire profile, 121 CX, 90 rotations.
The unloader is the exact inverse of the new loader, so every loader-only phase still cancels.

## Files

| file | content |
|---|---|
| `x_loader_xg_r36_32_1_L1xL0.pkl` | relabeled x loader (target 1 loads L1⊕L0; `newcode` updated) |
| `relabel_x1_L0.pkl` | the relabel solution (angle changes, free-slot atom) |
| `y_loader_v34_1_yw005_3.pkl` | y loader (unchanged, as in 115 / 566) |
| `kernel_co.npy` | phase array (co_24, unchanged) |
| `kernel_model.in`, `kernel_schedule.txt` | FEM kernel-beam input and output (T = 114, W = 12000, seed 1; Lx1 start row 96 = L1⊕L0) |

## Replay (byte-identical output, verified 2026-09-27)

```
export CLASS_CODES=$PWD/artifacts/185/class_codes.json CLASSIQ_ROOT=$PWD
S=src/post151_sa/tail115/suffix_sat
.venv/bin/python $S/relabel.py   $PWD/artifacts/115/recipes/cx569/x_loader_xg_r36_32_1.pkl 1 64
.venv/bin/python $S/mkrelabel.py $PWD/artifacts/115/recipes/cx569/x_loader_xg_r36_32_1.pkl scratch/work_k/relabel_x1_64.pkl x.pkl
.venv/bin/python $S/run_relab.py x.pkl artifacts/115/recipes/cx569/y_loader_v34_1_yw005_3.pkl 114 12000 1 rep114 '{"7":32}'
# -> scratch/work_k/pe/rep114_s1_m114.qasm (FEM kernel beam, assemble, canc, exact MILP at 114)
```
Seeds 1, 2 and 3 give the same circuit. Paths come from `tail115/localpaths.py` (WORK_K defaults to `scratch/work_k`).

## Checks
- `scripts/verify_circuit.py`: PASS depth 114, 571 CX, 419 U3, width 18, max error 3.88e-14.
- `src/exhaustive_verify.py`: all 4096 clean-ancilla inputs, max error 3.86e-14, ancilla error 3.86e-14
  (`../../conditional_loader_114_cx571.exhaustive.json`).
- `tail115/everify.py`: same numbers.
- Dense: five random input superpositions agree with the 116 champion (`../../dense_cx571_vs_116.txt`).

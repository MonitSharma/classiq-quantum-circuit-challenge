# 114 / 564 CX recipe

Result: `../../conditional_loader_114_cx564.qasm` (SHA-256 `1bf3025720ef60e2a74e18ae3c77d91c8339dd82e2058805b2b458d7fcc73eab`),
depth 114, 564 CX, 421 U3, 18 wires. See `../cx571/README.md` for the relabeling idea (CZ absorbed at a closing Hadamard).

## Steps

1. **Two relabels of the x loader `xg_r36_32_1`** (same CX/H schedule, angles only, `suffix_sat/relabel.py` + `mkrelabel.py`):
   - target 1 loads `L1 ⊕ L0` (2 rotations re-angled, 1 rotation added at an idle slot: layer 33, wire 4);
   - target 2 loads `(L1 ⊕ L2) ⊕ L0 ⊕ px` (`b = 112` in loader rows; 18 rotations re-angled, no new rotation).
   Result: `x_loader_xg_r36_32_1_T1xL0_T2xL0px.pkl` (121 CX, exact against the modified label code). The y loader is unchanged.
2. **FEM kernel beam at T = 114** with the kernel start/home rows changed accordingly (`STXOR {"7":32,"6":48}`:
   Lx1 wire = L1⊕L0, x12 wire = L1⊕L2⊕L0⊕px), W = 12000, seed 2, `CXPEN=0.02` → assembled 114, `canc`, exact MILP 114:
   `stage_567_x2b_cp_s2_m114.qasm` (114 / 567). Kernel: `kernel_schedule.txt` (81 CX).
3. **Depth-aware numerical 3-qubit resynthesis** (`numresyn/dsloop.py <stage_567> tag 3 5` with `SHARD=1/2`): three accepted
   rounds 567 → 566 → 565 → 564, each confirmed by the exact MILP at 114 and exhaustive verification (`dsloop_567_to_564.log`).

Replay commands:
```
export CLASS_CODES=$PWD/artifacts/185/class_codes.json CLASSIQ_ROOT=$PWD
CXPEN=0.02 src/post151_sa/tail115/suffix_sat/relab_variant.sh x2b_cp "1:64 2:112" "" '{"7":32,"6":48}' 2 12000
#  -> scratch/work_k/pe/v_x2b_cp_s2_m114.qasm, byte-identical to stage_567_x2b_cp_s2_m114.qasm
SHARD=1/2 .venv/bin/python src/post151_sa/tail115/numresyn/dsloop.py artifacts/114/recipes/cx564/stage_567_x2b_cp_s2_m114.qasm rep564 3 5
```
(`relab_variant.sh` = relabel.py + mkrelabel.py for each listed target, then `suffix_sat/run_relab.py`.)
The dsloop step replays byte-identically from `stage_567_x2b_cp_s2_m114.qasm` (checked 2026-09-27: 566 → 565 → 564, same SHA).

## Checks
- `scripts/verify_circuit.py`: PASS 114 / 564 / 421, max error 3.88e-14.
- `src/exhaustive_verify.py`: all 4096 inputs, max error 3.86e-14, ancilla error 3.86e-14 (`../../conditional_loader_114_cx564.exhaustive.json`).
- `tail115/everify.py`: same.
- Dense: five random superpositions equal to the 116 champion up to global phase (`../../dense_cx564_vs_116.txt`).

## Also tried (no further CX)
- dsloop (k = 3; 3 DAG shards, 2 wire-order shards) on this 564: no improvement. The other 8 distinct 567 circuits
  (seeds / CXPEN 0.02–0.15) end at 564–565.
- Kernel-suffix SAT at T = 114 (`kcxiter.py`, one CX fewer): a = 34…40 UNSAT, a = 28…32 timeout (900 s).

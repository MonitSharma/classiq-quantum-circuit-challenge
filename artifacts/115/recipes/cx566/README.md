# 115 / 566 CX recipe

Loaders: the same as `../cx569/` (x `xg_r36_32_1`, y `v34_1_yw005_3`), phase array `../kernel_co.npy` (co_24).

1. `k568.txt` is the 568 kernel (`../cx568/kernel_cx568_layers.json`) in kernel-schedule format (82 CX, tau0 30).
2. Kernel-suffix SAT (`src/post151_sa/tail115/suffix_sat/kcxiter.py ... k568.txt 115 38 900 i568`): layers 39–43 of
   the kernel re-solved exactly under the FEM windows at T = 115, all remaining terms placed freely, rows home at the
   end, one CX fewer. Result `i568_best.pkl` (keys CXL, ROT, TAIL, tau0; 81 CX). Assembled + `canc` + exact MILP:
   `i568_it0_a38_m115.qasm` = 115 / 567.
3. Depth-aware numerical resynthesis of the second [q9, q11, q13] 4-CX block of that circuit
   (`suffix_sat/dstarget.py <qasm> tag "9,11,13"`, i.e. `numresyn/dsloop.try_block`): CX order (q9→q11), (q13→q11),
   (q9→q11), slots `nunnznznz`, MILP 115 feasible → `artifacts/115/conditional_loader_115_cx566.qasm`.

See `docs/CX566_KERNEL_SUFFIX_SAT_2026-09-26.md`.

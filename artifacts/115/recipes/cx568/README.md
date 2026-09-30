# 115 / 568 CX recipe
Loaders and phase array: the same as `../cx569/` (x `xg_r36_32_1`, y `v34_1_yw005_3`, co_24 = `../kernel_co.npy`).
Kernel: `../cx569/kernel_schedule.txt` with kernel window 33 (6 layers) re-synthesized by
`src/post151_sa/tail115/kpeep.py` (17 → 16 CX). The resulting kernel CX layers are in `kernel_cx568_layers.json`
(`layers[k]` = CX pairs by plan index at kernel layer k+1, tau0 = 30). Rotations follow each term's first appearance,
except inside the re-synthesized window, where the SAT placed them.

# Depth-115 circuits

All circuits in this folder have depth 115 and width 18. Each passes the exhaustive check on all 4,096 clean-ancilla basis inputs (reports in `*.exhaustive.json`). Each is also compared with the depth-116 circuit on five dense random superpositions (`dense_*_vs_116.txt`).

| circuit | CX | U3 | SHA-256 | how it was obtained |
|---|---:|---:|---|---|
| `conditional_loader_115_cx566.qasm` | **566** | 418 | `3573dfc6…11ccc2e` | kernel-suffix SAT on the 568 kernel (a new 567), then one numerical three-qubit block (recipe `recipes/cx566/`) |
| `conditional_loader_115_cx567.qasm` | 567 | 418 | `8101000e…ecba69` | the 568 circuit with one three-qubit block re-synthesised numerically |
| `conditional_loader_115_cx568.qasm` | 568 | 418 | `ec51775f…eabfa3` | the 569 circuit with one kernel window re-synthesised by SAT |
| `conditional_loader_115_cx569.qasm` | 569 | 418 | `0664dc07…adaeca2` | lower-CX loaders with the same ready-time profile |
| `conditional_loader_115_cx571.qasm` | 571 | 418 | `49a699d8…c423e` | lower-CX loader variants |
| `conditional_loader_115.qasm` | 575 | 418 | `d61f2344…dbe3ce` | first depth-115 circuit (the challenge submission) |

Each `.qmod` file is a gate-for-gate Qmod transcription of the matching QASM file. Its `main` adds the twelve Hadamard gates used by the challenge's synthesis harness.

## How the circuits were built

**Loaders.** The x loader has code wires ready at layers 35, 42, 43 and 44 and depth 44. The y loader has code wires ready at layers 39, 39, 41 and 45 and depth 45. Neither loader beats earlier loaders on its own. Depth 115 comes from the pairing:

- the x loader finishes two of its code bits (at layers 42 and 43) earlier than previous x loaders, at the cost of a last bit at layer 44;
- the y loader accepts a last bit at layer 45 in exchange for earlier ones on its other wires.

**Kernel.** The 63-term phase array is [`recipes/kernel_co.npy`](recipes/kernel_co.npy). The kernel was scheduled by the windowed beam search at T = 115 under the fused rotation model (see the [technical report](../../docs/technical-report.md#33-the-loaderkernel-interface)).

**Post-processing.** After assembly, commutation-aware CX cancellation and the exact MILP rescheduler confirm depth 115. Three further steps then lower the CX count.

- **568 CX.** A SAT re-synthesis of 6-layer kernel windows, with fixed boundary parities and rotations, removed one CX in window 33 (17 → 16). No other 6-layer window could lose a CX.
- **567 CX.** A depth-aware numerical resynthesis of convex three-qubit blocks rewrote the block on q9, q11 and q13 at layers 73–82. It held four CX around a non-diagonal U3 on q11 and now holds three: (q9→q11), (q13→q11), (q9→q11), with Rz gates between them. The fit is exact to 10⁻¹⁵, and the MILP still schedules the result in 115 layers.
- **566 CX.** Exact SAT re-synthesis of the kernel *suffix* (last 17 layers of the 568 kernel, free rotation placement, rows home at the end, one CX fewer) gives kernel 82 → 81 CX and a new 115 / 567. Depth-aware numerical resynthesis of a [q9, q11, q13] block of that circuit then gives 566 (MILP 115 feasible). Recipe in `recipes/cx566/`, write-up in `docs/CX566_KERNEL_SUFFIX_SAT_2026-09-26.md`.

## Recipes

| folder | contents |
|---|---|
| `recipes/` | the first 115 circuit: x loader `x_loader_r36_1_q2.pkl`, y loader `y_loader_yw005_3.pkl`, kernel schedule, phase array |
| `recipes/cx571/` | loaders `x_loader_r32_3_r36.pkl`, `y_loader_v34_1_yw005_3.pkl` and kernel schedule |
| `recipes/cx569/` | loaders `x_loader_xg_r36_32_1.pkl`, `y_loader_v34_1_yw005_3.pkl` and kernel schedule (also used by 568 and 567) |
| `recipes/cx568/` | kernel CX layers after the SAT peephole |

The tools are in [`src/post151_sa/`](../../src/post151_sa/):

- the loader beam search (`lbeam4c`) and kernel beam search (`kbeam_t3`);
- the assembly and exact MILP (`kdrv.py`, `smilp.py`);
- the SAT peephole (`tail115/kpeep.py`);
- the numerical block resynthesis (`tail115/numresyn/`).

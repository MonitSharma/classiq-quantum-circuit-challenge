# Depth-114 circuits

All circuits in this folder have depth 114 and width 18. Each passes the exhaustive check on all 4,096 clean-ancilla basis inputs (reports in `*.exhaustive.json`). Each is also compared with the depth-116 champion on five dense random superpositions (`dense_*_vs_116.txt`).

| circuit | CX | U3 | SHA-256 | how it was obtained |
|---|---:|---:|---|---|
| `conditional_loader_114_cx564.qasm` | **564** | 421 | `1bf30257…fcc73eab` | **New All-Time Champion.** Both x conditional targets relabeled ($L_1 \oplus L_0$ and $L_1 \oplus L_2 \oplus L_0 \oplus p_x$), CXPEN=0.02 kernel beam (567 CX), then three numerical 3-qubit resynthesis rounds (recipe `recipes/cx564/`) |
| `conditional_loader_114_cx571.qasm` | 571 | 419 | `7510ebd2…1bb3aa9` | First depth-114 circuit: x target 1 relabeled to $L_1 \oplus L_0$, kernel beam under the exact fused rotation model (recipe `recipes/cx571/`) |

Each `.qmod` file is a gate-for-gate Qmod transcription of the matching QASM file. Its `main` adds the twelve Hadamard gates used by the challenge's synthesis harness.

## Gate Breakdown by Stage

| stage | 114 / 564 CX | 114 / 571 CX |
|---|---:|---:|
| x loader + unloader | 121 + 119 CX (90 + 89 U3) | 121 + 122 CX (90 + 90 U3) |
| y loader + unloader | 122 + 121 CX (89 + 87 U3) | 122 + 121 CX (89 + 88 U3) |
| phase kernel | 81 CX (66 U3) | 85 CX (62 U3) |
| **total** | **564 CX (421 U3, 985 gates)** | **571 CX (419 U3, 990 gates)** |

## How the circuits were built

### 1. Relabeling at the Closing Hadamard
At the closing Hadamard of a conditional loader target, applying a CX from an existing bit $B$ to target $A$ is algebraically equivalent to a CZ before the Hadamard:
$$
CX(B \to A) \cdot H_A = H_A \cdot CZ(B, A).
$$
In the phase-kickback frame, the CZ modifies the relative phase deposited on target $A$ by $(-1)^b$, which transforms the loaded label bit into $L \oplus b$.
By re-solving the rotation angles using the Howell normal form over $\mathbb{Z}/64$ (`suffix_sat/relabel.py` + `mkrelabel.py`) and utilizing an idle wire slot at layer 33, target 1 of the x loader loads $L_1 \oplus L_0$ with **zero change to the CX schedule or layer timing**. Target 2 can similarly load $(L_1 \oplus L_2) \oplus L_0 \oplus p_x$.

### 2. Kernel Synthesis in the Relabeled Basis
Presenting this transformed basis to the phase kernel decouples the wire congestion that previously forced a depth floor of 115. A beam search at $T = 114$ under the Fused Exact Model (`kbeam_t3`, width 12,000, seed 2, with CX penalty `CXPEN=0.02`) synthesizes the 63-term phase kernel in 81 CX.

### 3. Exact Scheduling and Numerical Resynthesis
- **Assembly & Rescheduling:** Commutation-aware CX cancellation and the exact MILP rescheduler (`smilp.py` with HiGHS) assemble the circuit at 114 layers and 567 CX (`stage_567_x2b_cp_s2_m114.qasm`).
- **Depth-Aware Numerical Resynthesis:** A convex 3-qubit block optimizer (`numresyn/dsloop.py`) optimizes blocks across non-diagonal gates, finding 3 successive 1-CX reductions (567 → 566 → 565 → 564 CX), each strictly verified for equivalence and MILP 114 makespan.

## Recipes

| folder | contents |
|---|---|
| `recipes/cx564/` | loader `x_loader_xg_r36_32_1_T1xL0_T2xL0px.pkl`, y loader `y_loader_v34_1_yw005_3.pkl`, kernel schedule, phase array, and dsloop log |
| `recipes/cx571/` | loader `x_loader_xg_r36_32_1_T1xL0.pkl`, y loader `y_loader_v34_1_yw005_3.pkl`, kernel schedule, and recipe README |

Replay commands and full details are documented in [`recipes/cx564/README.md`](recipes/cx564/README.md) and [`docs/DEPTH_114_RELABEL_2026-09-27.md`](../../docs/DEPTH_114_RELABEL_2026-09-27.md).

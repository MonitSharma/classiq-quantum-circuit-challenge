# Depth-116 circuits

All circuits in this folder have depth 116 and width 18. Each passes the exhaustive check on all 4,096 clean-ancilla basis inputs (reports in `*.exhaustive.json`).

| circuit | CX | U3 | SHA-256 | how it was obtained |
|---|---:|---:|---|---|
| `conditional_loader_116_cx565.qasm` | **565** | 419 | `7f73d2c1…d157156` | new y loader (parity bit ready at layer 40); kernel beam under the exact rotation model, seed 3 |
| `conditional_loader_116_cx567.qasm` | 567 | 419 | `97ef2122…b2530` | same loaders, seed 1 |
| `conditional_loader_116_cx570.qasm` | 570 | 421 | `4710d2b9…57c65` | an alternative phase array and a calibrated kernel model |
| `conditional_loader_116_cx571.qasm` | 571 | 420 | `8e50e43b…029a1` | wire-basis normalisation and a corrected restoration bound in the kernel search |
| `conditional_loader_116.qasm` | 573 | 420 | `5f4e4162…2a570` | first depth-116 circuit |

**What made 116 possible.** Only 182 of the 256 pairs of 4-bit class codes occur for valid inputs:

- x codes 12 and 15 never occur;
- y codes 6, 7 and 13 never occur.

Any phase supported only on unreachable code pairs leaves the oracle unchanged. Adding such phases changes the parity coefficients the kernel has to implement, and one of these completions (`recipes/kernel_co.npy`) schedules one layer shallower than the previous kernel.

The recipes (loaders, phase array and kernel schedules) are in `recipes/`. `src/post151_sa/replay116.py` and `src/post151_sa/replay571.py` rebuild the 573- and 571-CX circuits.

# Depth-117 circuits

All circuits in this folder have depth 117 and width 18. Each passes the exhaustive check on all 4,096 clean-ancilla basis inputs.

| circuit | CX | U3 | SHA-256 | how it was obtained |
|---|---:|---:|---|---|
| `conditional_loader_117_cx576.qasm` | **576** | 419 | `8ce115b1…35d2bd4` | CX cancellation and exact MILP rescheduling of the 590 circuit's kernel family |
| `conditional_loader_117_cx577.qasm` | 577 | 419 | `d26fa5c6…be01c11e` | same method, different kernel schedule |
| `conditional_loader_117.qasm` | 590 | 421 | `40cafa77…f07a2da` | first depth-117 circuit: rotation pull-in |

**Rotation pull-in.** A kernel rotation only needs its wire to hold the right parity. It does not need the loader to be finished with the wire. Allowing rotations from the layer where a code wire's value is fixed, instead of the layer of the loader's last gate on it, gave the kernel up to eight more layers on some wires. That removed the last layer between 118 and 117.

**Exact rescheduling.** `src/post151_sa/smilp.py` solves a time-indexed integer program over the commutation DAG (HiGHS through `scipy.optimize.milp`). It decides whether a gate list fits in *T* layers. Combined with commutation-aware CX cancellation (`src/post151_sa/canc.py`), it reduced 590 CX to 576 at the same depth.

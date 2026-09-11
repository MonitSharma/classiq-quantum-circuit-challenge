# LUT single-target synthesis screen

Updated September 11, 2026. This campaign tested whether keeping small
Boolean functions intact as reversible single-target gates could avoid the
live-intermediate cost seen in AND/XAG lowering.

The operation is `t ^= h(c1, ..., ck)` with arbitrary dirty contents allowed
in `t`. The eventual architecture would be `C† P C`, so coordinate wires could
be overwritten during `C`. No complete oracle is generated unless the forward
native estimate is at most 105 depth.

## Exact ABC mappings

`src/lut_single_target.py` runs Berkeley ABC on `experiments/logo.bench` using
`if -K k`. The emitted BLIF files are preserved under
`artifacts/lut_single_target/`; the complete inventory is
[`artifacts/lut_single_target_inventory.json`](../artifacts/lut_single_target_inventory.json).
Every mapping reproduces the exact logo truth table on all 4,096 inputs.

| LUT limit | LUT count | LUT levels | Arity histogram | Peak live signals | Optimistic native critical depth | CX |
|---:|---:|---:|---|---:|---:|---:|
| 3 | 142 | 10 | 2:38, 3:104 | 35 | **145** | 86 |
| 4 | 102 | 7 | 2:6, 3:26, 4:70 | 27 | **738** | 417 |
| 5 | 72 | 6 | 2:4, 3:6, 4:20, 5:42 | 24 | **2151** | 1225 |

The live-signal counts exceed the 18-wire budget before reversible target
assignment. They are not impossibility proofs for all pebbling schedules, but
they rule out treating these ABC DAGs as direct reversible schedules.

## Quantum-aware local cost database

Each distinct observed LUT was retained as a truth table and compiled directly
as a small single-target reversible operation. Canonicalization under input
permutation/input negation/output negation found:

| LUT limit | Canonical classes | Maximum local depth | Maximum local CX |
|---:|---:|---:|---:|
| 3 | 7 | 40 | 21 |
| 4 | 16 | 165 | 94 |
| 5 | 37 | 718 | 415 |

The optimistic native path adds exact local depth along the ABC dependency
path while ignoring target conflicts, garbage, rematerialization, and inverse
cost. Even the best 3-LUT mapping is 145 forward depth, above the 120-depth
closure threshold; the 4- and 5-LUT mappings are much worse.

## Disposition

This closes the tested ABC/LHRS-style mapping as a competition path. It tests a
representation absent from the earlier global XAG campaigns, but its best
exact conventional map does not leave a credible native-depth window. No
destructive LUT scheduler, local-window QASM synthesis, or complete `C† P C`
oracle was attempted.

The research context is LUT-based hierarchical reversible logic synthesis:
classical k-LUT mapping followed by reversible single-target gates, with
explicit workspace and garbage-management tradeoffs. This result reinforces
why quantum-aware mapping is necessary: minimum LUT count and LUT depth do not
control native U3/CX depth or live-wire pressure.

# Circuits

Each numbered folder holds the verified circuits of one depth milestone. A folder contains:

- the OpenQASM 2 circuit;
- in most cases, a gate-for-gate Qmod transcription;
- the exhaustive verification report (`*.exhaustive.json`, all 4,096 clean-ancilla inputs);
- where available, the recipe used to build it.

[`../results/verified_circuits.csv`](../results/verified_circuits.csv) lists every verified circuit with its depth, CX and U3 counts, SHA-256 and the date it was first committed.

| folders | depth | CX | architecture |
|---|---|---|---|
| [`115/`](115/) | 115 | 567–575 | conditional loaders, 63-term kernel, exact scheduling; SAT and numerical peepholes |
| [`116/`](116/) | 116 | 565–573 | phase freedom on unreachable class codes; exact rotation model |
| [`117/`](117/) | 117 | 576–590 | rotation pull-in; MILP rescheduling |
| `118b/`, `118/` … `124/` | 118–124 | 584–632 | ready-time loaders, freeze action, modulo-2π lift, blocked-term weighting |
| `125/` … `137/` | 125–137 | 624–651 | layer-synchronous beam-search loaders; windowed kernel beam |
| `148/` … `163/` | 148–163 | 629–643 | first conditional (cofactor) loaders; annealing; rescheduling |
| `185/` … `198/` | 185–198 | 853–862 | two-stage class-code oracle; kernel beam search; exact CNOT rewrites |
| `218/` … `243_cx951/` | 218–243 | 897–971 | parity-assisted class codes; integer-lifted kernels |
| `258/`, `456/` | 258, 456 | 1,140–1,188 | distributed lookup; comparator identity |
| `524/` … `531/` | 524–531 | 950–1,036 | affine six-feature multiplexer with peephole optimisation |
| `718/` … `756/` | 718–756 | 729–747 | early ancilla-assignment and pair-boundary designs |

Folders with a date suffix (`phase_network117_20260922/`, `rewrite117_20260922/`, `parity_preserved_20260923/`) hold candidate circuits from search campaigns. [`archive/`](archive/) keeps four early circuits (depths 536, 682, 779 and 1,046) that the main README lists.

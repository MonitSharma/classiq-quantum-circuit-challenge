# Code for earlier architectures

Scripts from the designs that preceded the current one. They are kept so that the circuits in `artifacts/` with depth above 150 can be traced back to the code that produced them.

| folder | designs | depth range |
|---|---|---|
| [`era1_direct_xag/`](era1_direct_xag/) | direct XAG synthesis, radius multiplexing, greedy ancilla allocation | 1,046 → 682 |
| [`era2_affine_mux/`](era2_affine_mux/) | affine six-feature lookup multiplexer, peephole passes | 682 → 524 |
| [`era3_distributed_lookup/`](era3_distributed_lookup/) | distributed parity lookups, level encoders, relative-phase boundaries | 524 → 258 |
| [`era4_parity_codes/`](era4_parity_codes/) | parity-assisted class codes, integer-lifted kernels | 258 → 218 |
| [`era5_bridge_rewrites/`](era5_bridge_rewrites/) | exact three-wire CNOT rewrites, ancilla permutations, commuting-gate scheduling, first kernel beam searches | 218 → 185 |
| [`era6_loader_annealing/`](era6_loader_annealing/) | overlapping conditional loaders, simulated annealing, windowed kernels | 185 → 148 |
| [`other_exploratory/`](other_exploratory/) | benchmarks, parameter sweeps, geometric probes | — |
| [`experimental_submodules/`](experimental_submodules/) | prototype packages for alternative designs | — |

The code that builds the current circuits is in [`src/post151_sa/`](../post151_sa/). The oracle definition and the verifiers are in [`src/classiq_synth/`](../classiq_synth/).

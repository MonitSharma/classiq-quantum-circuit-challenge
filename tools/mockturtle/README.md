# Mockturtle multiplicative-depth pilot

Source: `https://github.com/lsils/mockturtle`

Pinned checkout: `0886ebfdd101ce1110daf3d60b96d72edd3143ea`

The checkout is intentionally ignored under `external/mockturtle/`; it is
reproducible with a recursive clone at the pinned commit. The local build
directory is also ignored.

Environment used:

```text
cmake 4.2.2
Apple clang 21.0.0 (clang-2100.1.1)
```

Pilot build command:

```bash
mkdir -p tools/mockturtle/build
c++ -std=c++17 -O2 -Wno-deprecated-declarations \
  tools/md_synth/md_synth.cpp \
  -Iexternal/mockturtle/include \
  -Iexternal/mockturtle/lib/kitty \
  -Iexternal/mockturtle/lib/bill \
  -Iexternal/mockturtle/lib/lorina \
  -Iexternal/mockturtle/lib/parallel_hashmap \
  -o tools/mockturtle/build/md_synth
./tools/mockturtle/build/md_synth \
  artifacts/multiplicative_depth/logo_truth.hex \
  artifacts/multiplicative_depth/seeds/shared_rank.xag balance
```

The executable reads the authoritative 4096-point logo truth table and the
exported shared-rank seed. The seed is independently exact. The `xag_balance`
pipeline remains exact and reduces the seed from 97 to 81 ANDs, but leaves MD
at 6; its topological nonlinear live-width report is 13. The algebraic
depth-rewriting pipeline reports lower MD values but fails
the executable's exhaustive 4096-point check, so those outputs are rejected.
The full machine-readable result is
`artifacts/multiplicative_depth/mockturtle_logo_pilot.json`.

An optional fourth argument exports an exact optimized XAG seed. The exporter
uses 128-bit affine masks and the result must still pass `md_xag.XAG`'s
independent truth-table check before reuse.

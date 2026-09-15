# Five-variable loader audit and complete-circuit follow-up

September 16. Protected best remains **185 depth / 854 CX / 18 qubits**,
`artifacts/185/two_stage_185.qasm`, SHA
`ef933bc786bc25feb1fbd618fc8c45a0bdc8dce43879aacfcc6042daaca5bfc8`.
The five-variable experiments below have not improved the protected circuit.
Nothing was submitted or checked against a live leaderboard.

## What the side research establishes

The new `POST185_LOADER_ADDRESS_WIDTH.md` contains useful measured leads,
but some conclusions are stronger than the evidence:

- The saved kernel accompanying 185 is **38 depth / 87 CX / 63 U3**. The note's
  29-layer kernel is not identified by a saved QASM and verification report.
  The complete 185 circuit includes cross-boundary rewrites; its depth cannot
  be decomposed by simply adding isolated block depths.
- `2*78 = 156` is a budget for two particular loader implementations, not a
  lower bound for all labels, encoders, or whole-circuit rewrites. Existing
  `post188_sparse_revisit_v1` already contains 71–76-layer loaders whose
  complete circuits are worse (209–224). Neither observation proves a floor.
- Affine parities require physical CNOTs and are not free in a depth budget.
  The new experiment includes those gates and their exact inverse.
- ANF monomial counts and nonzero Walsh coefficients are distinct quantities;
  neither alone decides native depth. A particular dense completion does not
  exclude sparse completions on unreachable kernel inputs.
- Class sizes do give `sum(ceil(size/8)) = 14` on each axis. This establishes
  enough *capacity* for the proposed seven-wire encoding, not a shallow
  reversible encoder, clean scratch space, or a feasible serialized schedule.
- Boolean AND networks remain a possible route, but these experiments do not
  prove they are the only route to sub-140.

## Implemented follow-up

`src/post185_five_address.py` constructs a five-bit descriptor per axis from
two raw parities and three loaded bits. A label identifies the pair of row or
column classes encountered along a translation direction, and is constant
along that direction. An invertible six-wire CNOT frame exposes the unused
address bit. The frame is included in the encoder cost.

Reproduced y direction 16 / selector 16, and x direction 55 / selector 16.
Also tested x direction 4 / selector 12 and direction 59 / selector 16.
Each descriptor is checked for class separation on all 64 coordinate values.
The loader is checked on all 64 promised clean-output inputs, permitting only
input-dependent phases canceled by its actual inverse.

Tested both compressed axes (ten-wire kernel), compressed x only, and
compressed y only (nine-wire kernels). Three label searches per variant use
12-second bounds and optimize a weighted integer-ANF completion jointly with
the labels. The three y-only cases are different randomized label searches
of the same descriptor model; their unused x-direction metadata does not
represent a different physical frame.

The saved witnesses select a low-support candidate from each search's recorded
improvements. Each uses eight loader seeds with both sparse and open walks,
and two beam-synthesized native kernel candidates. This is a bounded heuristic
screen, not exhaustive label search or minimum-depth synthesis.

## Complete, serialized, verified results

| Compressed axes | x direction | y / x loader depths | Kernel depth | Oracle depth | CX |
|---|---:|---:|---:|---:|---:|
| Both | 4 | 65 / 67 | 430 | 559 | 1554 |
| Both | 55 | 65 / 60 | 411 | 539 | 1430 |
| Both | 59 | 70 / 69 | 399 | 536 | 1480 |
| x only | 4 | 77 / 67 | 193 | 346 | 1030 |
| x only | 55 | 77 / 73 | 154 | 307 | 1002 |
| x only | 59 | 77 / 71 | 155 | 308 | 986 |
| y only, run 1 | — | 71 / 77 | 237 | 390 | 1180 |
| y only, run 2 | — | 70 / 77 | 237 | 390 | 1180 |
| y only, run 3 | — | 69 / 77 | 241 | 393 | 1169 |

All nine pass `exhaustive_verify` on all 4,096 inputs, with restored coordinates
and ancillas and one common phase. Saved QASM hashes match their reports.
Results and witnesses: `artifacts/post185_five_address_v1/`; compact index:
`verified_summary.json`. These are negative full-oracle results despite the
real 60-layer loader measurement.

## Reachable-state phase completion

An additional LP search chooses real parity phases satisfying the target only
on reachable descriptor words. It alternates Boolean and integer-ANF phase
lifts and uses randomized reweighted L1 objectives. Phase coefficients, seeds,
iteration outcomes, residuals, and complete source descriptors are saved.

For the x-only direction-55 witness:

| Completion | Phase terms | Kernel depth | Oracle depth | CX |
|---|---:|---:|---:|---:|
| Initial integer ANF | 265 | 154 | 307 | 1002 |
| Six deterministic LP iterations | 189 | 120 | 273 | 935 |
| 25-second randomized LP search | 183 | 112 | **265** | 911 |

The 265-depth QASM passes all 4,096 inputs, maximum error 7.76e-14 and discarded
amplitude bound 9.54e-15. It is an improvement within this experimental family,
not a new best. File:
`artifacts/post185_five_address_care_v2_4/oracle_d265_cx911.qasm`, SHA
`d77de38e9cc442af232bc34acba7a4355d006e54fdc38c3bc2fd6b70f089680b`.

The randomized completion was also applied to a both-compressed witness:
669 phase terms, 344 kernel layers, and **473 oracle layers / 1306 CX**,
down from 539 layers for that witness's integer-ANF completion. The whole
oracle passes all 4,096 inputs with maximum error 2.56e-12 (below the 1e-10
acceptance threshold). Its metrics and exhaustive check are in
`artifacts/post185_five_address_care_v2_1/`.

In total, 16,592 label proposals and twelve complete verified circuits were
evaluated. All jobs in this campaign have finished.

## Reproduction and validation

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python src/post185_five_address.py \
  --outdir artifacts/NEW_DIRECTORY --seconds 12 --variants both x y --compile

OPENBLAS_NUM_THREADS=1 PYTHONPATH=src .venv/bin/python -m pytest -q \
  tests/test_post185_five_address.py tests/test_native_wire_identity.py \
  tests/test_post196_address_width.py
```

Nine focused tests pass. Wall-clock bounded searches can execute different
numbers of steps on replay; use the saved `source` and `co` fields with
`compile_one(source, new_output_directory, coefficients=co)` to reconstruct
a particular completion. Every transpilation uses the safe `native` helper,
and every reported oracle is scored after serialization to U3/CX at width 18.

## Interpretation

The five-variable idea works as an encoder simplification. It has not worked
as an oracle simplification in this campaign because the resulting phase
kernel more than consumes the saved layers. This supports deprioritizing this
specific lookup architecture; it does not prove a global lower bound.
For another attempt, require an explicit joint encoder/kernel depth estimate
including scratch cleanup before launching larger Boolean-network searches.
The 185 circuit and rank-one objective remain unchanged.

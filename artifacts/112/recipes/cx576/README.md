# 112 / 576 CX recipe (and 112 / 573)

Results: `../../conditional_loader_112_cx576.qasm` (SHA-256 `c770a17334ecd70df024e6377063b5d335f3e2a0811a2ebf320a461f50a95f64`)
and, after numerical resynthesis, `../../conditional_loader_112_cx573.qasm`
(SHA-256 `a24fc374370e6ea6f0242dd49f596ac82d6cdf41347dbffe57a3e4adb48d2326`).

Same method as `../../../113/recipes/cx568/README.md`: choose which label combination each loader target computes, use the
sparsest rotation supports for those functions, re-search the loaders, then relabel late label wires for free.

## Loaders

**x** (`x_frame.lb`, `x_support.pkl`; same frame as the 113 circuit): target 1 loads `L1 ⊕ L0` (22 rotations, 10 depending on
L0), target 2 loads `L1 ⊕ L2 ⊕ px` (24 / 4). `lbeam4c` from scratch, W = 6000, seed 12 (`suffix_sat/loadcamp.py`):
`x_loader.pkl` / `x_loader_beam.txt`, 43 layers, code wires ready at 39 / 41 / 41 / 43.

**y** (`y_frame.lb`, `y_support.pkl`, built by `suffix_sat/mkframe.py`): target 1 loads `L1` with the lightest support found
(30 rotations, 11 depending on Ly0, `suppvar.py CRIT=L`), target 2 loads `L2 ⊕ Ly0` (15 / 2). `lbeam4c`, W = 6000, seed 8:
`y_loader_before_relabel.pkl` / `y_loader_beam.txt`, code wires ready at 33 / 37 / 40 / 45, 127 CX.
Then target 2 is relabeled to `L2 ⊕ Ly0 ⊕ py` by re-angling 8 rotations (`suffix_sat/relabel2.py`, same schedule, exact;
`req` recomputed): `y_loader_T2xpy.pkl`.

The relabel was chosen by a start-basis screen at T = 112 (`suffix_sat/screen.py`, all single-wire changes on this pair):
the y target-2 wire ⊕ py and the x target-2 wire ⊕ L0 both make the kernel feasible; both are realisable and both
assemble to 112 (578/579 CX for the x variant).

## Kernel and post-processing
FEM kernel beam at T = 112 (`tail115/paireval.py`, STRICT ZOCC FUSE, W = 12000, seed 1) → assembled 112, `canc`, exact MILP
112 → 112 / 576 (`kernel_schedule.txt`, `kernel_model.in`; seeds 2 and 3 give 581). `numresyn/dsloop.py` (k = 3): 576 → 573
(`dsloop_576_to_573.log`).

Replay:
```
export CLASS_CODES=$PWD/artifacts/185/class_codes.json CLASSIQ_ROOT=$PWD
STRICT=1 ZOCC=1 FUSE=1 .venv/bin/python src/post151_sa/tail115/paireval.py \
  artifacts/112/recipes/cx576/x_loader.pkl artifacts/112/recipes/cx576/y_loader_T2xpy.pkl 112 12000 1 r112
.venv/bin/python src/post151_sa/tail115/numresyn/dsloop.py artifacts/112/conditional_loader_112_cx576.qasm ds112 3 10
```

## Checks
Both circuits: `scripts/verify_circuit.py` PASS, `src/exhaustive_verify.py` all 4096 inputs (max error 3.88e-14 / 3.87e-14,
ancillas restored), `tail115/everify.py` PASS, five dense random superpositions equal to the 116 champion.

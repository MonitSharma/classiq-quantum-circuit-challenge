# Direct 11-class relabeling audit

This bounded audit tests whether the protected raw-coordinate-plus-class
descriptor choice is the main synthesis bottleneck. It enumerates all 1,024
normalized Boolean cuts of each side’s 11 equivalence classes, with class 0
fixed to zero, and expands each cut to an exact 64-bit coordinate truth table.
Every candidate carries its 55-bit class-separation mask and exact ANF degree
and support count. Injective four-cut labelings were then sampled
deterministically and cross-scored on the 121 reachable class pairs.

All generated labelings reproduce the logo relation on all 4,096 `(x,y)`
pairs because they are injective on the actual 11 row/column classes. The
protected package was not modified.

## Results

- Row classes: 11; column classes: 11.
- Normalized cuts per side: 1,024 exactly.
- Valid four-cut labelings retained: 64 per side from the bounded portfolio.
- All 1,024 cuts were expanded and measured per side.
- Y cut degree distribution: degree 0: 1, degree 4: 15, degree 5: 496,
  degree 6: 512.
- X cut degree distribution: degree 0: 1, degree 4: 7, degree 5: 504,
  degree 6: 512.

The best measured direct-label pair used four cuts per side but produced a
255-term phase polynomial. Its emitted kernel measured **623 depth / 380 CX**
on eight wires. The protected kernel measures **38 depth / 90 CX**. The direct
label kernel was scored on the 121 care combinations embedded in a 256-entry
table, with unreachable entries filled by zero; no direct label showed a major
kernel advantage. Joint XAG merging and reversible scheduling were not
launched because this first gate—the kernel/label structural screen—failed.

The complete machine-readable audit is in
`artifacts/post190_class_relabel/report.json`, with all cut data in
`y_cuts.json` and `x_cuts.json`. The selected labels are stored in the report
and each is a verified injection of the 11 classes. The protected raw+3
control remains 13 reachable Y descriptor states and 14 reachable X states.

Conclusion: this bounded direct class-relabeling path does not currently show
that bad labels caused the synthesis difficulty. Close this path unless a
future search specifically improves the don't-care phase completion; do not
promote these labelings to the expensive reversible compiler.

Reproduce:

```sh
PYTHONPATH=src .venv/bin/python src/post190_class_relabel.py --outdir artifacts/post190_class_relabel
```

# Structured kernel care-set precheck

The 121 reachable structured descriptor words were synthesized directly as a
care set; the other 135 words were never assigned values. A plain deterministic
reweighted-L1 screen (64 seeds, 2 iterations) reached a best support of 50.
The complete one-RCCX conjugator screen (673 moves including `None`) reached a
best support of 33 at move `(2,6,1,1,1)`. The previously suggested
`(2,6,5,1,1)` was also screened and reached support 34 in this run.

Support is not the deciding metric. After actual conjugator inclusion, native
compilation and serialized care-set replay:

| construction | support | native depth | CX | U3 | care error |
|---|---:|---:|---:|---:|---:|
| best plain | 50 | 42 | 77 | 50 | 9.2e-14 |
| best plain compiled seed | 51 | **38** | 75 | 51 | 3.7e-14 |
| best conjugated | 33 | 42 | 67 | 48 | 1.0e-15 |
| suggested conjugator | 34 | 42 | 73 | 49 | 1.5e-14 |

The protected kernel is approximately 38 depth / 90 CX. Thus the structured
care-set kernel has a CX tie-breaker in this bounded screen, but no depth gain;
the 33-term conjugated representation is not better once its RCCX conjugator
is included. For a 136-depth full-oracle target, the best measured kernel
depth 38 leaves an encoder budget of `floor((136-38)/2) = 49` per side.

The exact finite screen and compiled records are in
`artifacts/post190_structured_kernel/`. All compiled kernels replay exactly on
the 121 reachable descriptor states up to one common phase. No structured
encoder or reversible scheduler was launched because no kernel-depth drop was
demonstrated and no jointly merged Boolean network has yet passed the 49-depth
promotion budget.

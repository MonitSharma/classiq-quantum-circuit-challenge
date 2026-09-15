# Campaign audit: what is verified and what to do next

September 15, 2026. Best full oracle remains **190/857/18**.

## Checked against current files

- Both `advanced_round4.xag` and `advanced_nist_sub45.xag` load as exact
  62-node Boolean networks using the existing loader's exhaustive truth check.
- Standalone QASM metrics reproduce: 5337/4076 and 5131/3859, width 18.
  Their saved exhaustive reports match the current file SHA256 values.
  This audit did not rerun those long compilation jobs.
- Protected 190 QASM and its verification SHA match and are unchanged.
- RCCX lowers to depth 7, with four U3 and three CX gates in this environment.
- Current merged NIST witnesses are x:15 ANDs, levels [9,3,3], and y:14 ANDs,
  levels [7,4,3]. The review's x14 pilot is linked to another session's
  `sandbox:/mnt/data` files; it was not found in the workspace or attachments.
  Its claimed [8,3,3] structure is not locally verified.

## Corrections that affect the decision

1. **131–135 is conditional, not achieved.** No verified 48–50-depth encoders
   were supplied. `post190_register_encoder.py` defines an unsolved template.
   Three clean registers do not hold fourteen or fifteen independent AND nodes
   simply because their Boolean depth is three. Affine movements, register
   reuse and any recomputation still have to be constructed and measured.
   The protected kernel also has an endpoint permutation; using arbitrary
   output placements requires consistent physical remapping, not a stage sum.

2. **The new compiler is input-preserving pebbling.**
   `xag_to_inplace_layers.py` fixes `wire={i:i for i in range(12)}` and allocates
   node targets only from 12..16, with root accumulation on 17. It restores
   every temporary affine control frame. This is a useful correct reference,
   but it does not implement arbitrary coordinate-overwriting register reuse.
   The 5131 depth does not measure that proposed compiler.

3. **Multiplying RCCX batch counts by seven is not a universal lower bound.**
   Seven RCCXs `(0,1,2), (0,3,4), ..., (0,13,14)` use 15 wires and compile to
   depth **13**, CX21. The asserted formula gives `7*ceil(7/6)=14` on up to18
   wires. Native gates from overlapping RCCXs interleave. Similarly, summing
   ceiling counts by logical AND level imposes barriers not forced by the DAG.
   Therefore these arguments do not exclude the 62- or 81-AND networks from
   every possible lowering. They do bound particular atomic-layer templates.

4. **The review's CX arithmetic divides by two twice.** Under its assumptions
   of A forward RCCXs and their inverse, the CX contribution is 6A. Thus
   561/6 is about93 forward occurrences before linear costs, not46; 348/6 is58,
   not29. Neither calculation identifies the private winning algorithm.

5. Relative-phase cancellation needs a basis-permutation encoder with the
   correct output predicate and the actual inverse around Z. `E.inverse()*E=I`
   alone is not a proof for arbitrary E with a Z inserted. The matching
   exhaustive reports support the supplied constructions numerically.

6. The observed sample-search failures and timeouts do not prove CEGIS cannot
   certify this function. They are a practical reason to stop the current
   blind formulation, not a theorem about all encodings or runtimes.

## Next experiment

Prioritize a **seeded nine-wire affine-register compiler with free placement of
all four required descriptor outputs**. Seed it with the existing verified
NIST graphs, then enumerate affine variants and select them by measured native
cost. Check the actual wire functions after every overwrite; losing an input
function cannot be excused by calling the target dirty. Keep the best measured
schedule, not just the smallest logical AND count.

First acceptance gate: one complete three-bit-plus-raw encoder, all64 inputs,
within nine wires and below77 depth. Then target both sides around50 and
measure the actual complete oracle; kernel cost and endpoint wiring cannot be
assumed to remain35. A 50-layer estimate is not a candidate.

Keep global62-node rewriting as a secondary branch with timing-aware scheduling.
Do not reject it using the invalid seven-times-batch-count bound. Do not launch
more full-domain-from-scratch CEGIS just because another shorter template can
be written down. No new long search was launched by this audit.

## Arithmetic work completed during the review

The radius-from-x integration was built and fully verified in this turn.
`artifacts/post190_radius_interval/oracle.qasm` is2524/2035/18; replacing its
interval with a literal carry implementation gives3303/2471/18 in
`artifacts/post190_radius_carry/oracle.qasm`. Both saved reports match their
serialized files. The lookup remains77 and fold+lookup85; the cube and
constant-adder lowerings are expensive. These are failed implementations,
not arithmetic lower bounds. Neither replaces190. All new jobs finished.

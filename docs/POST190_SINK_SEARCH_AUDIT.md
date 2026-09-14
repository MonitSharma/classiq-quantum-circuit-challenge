# Audit of the retirement and sinks-only searches

Inspected the supplied update and scratchpad `sinkrun.py` and `lower9b.py`.
No running processes or their sources were changed. This audit does not confirm
process liveness. Protected full oracle remains 190/857/18.

## Degree barrier: three internal nodes are insufficient

The protected output degrees, independently reconstructed from their truth
tables, are [5,6,6] for y and [5,6,6] for x.

Suppose an XAG has t internal AND nodes and all remaining AND nodes are sinks:
no AND gate reads a sink. Every sink is computed from primary inputs and
at most t internal nodes, so its entire ancestor circuit uses at most t+1
ANDs. By the scalar degree bound used in POST190_XAG_DEGREE_CERTIFICATE.md,
its degree is at most t+2. Internal nodes have degree at most t+1. Affine
output combinations cannot increase the maximum degree.

For t=3 every output therefore has degree <=5, no matter how many sinks are
added. This cannot realize the protected labels. The scratchpad queue has:

| search | internal nodes | consequence |
|---|---:|---|
| k=6, tail=3 | 3 | impossible for fixed protected labels |
| k=7, tail=4 | 3 | impossible for fixed protected labels |
| k=7, tail=3 | 4 | not excluded by this degree argument |

`lower9b.lower` hard-codes internal=list(range(3)) and treats every later node
as a sink. It therefore does not implement the last queued case. A synthetic
k=6 witness at depth73 verifies one lower-degree example only; it cannot imply
that the degree-six protected functions fit that scheme or share that depth.

## Other implementation gaps

The initial retirement condition is not sufficient for lowering: moving a new
signal g onto a dirty wire holding x produces x XOR g, not g. Pre-adding x to
final outputs does not make g available for later nonlinear gates. The supplied
later update correctly recognizes this problem.

Sink status alone still does not establish a valid accumulation assignment,
correct output reconstruction, or a physical register schedule.

`lower9b.py` checks matrix invertibility with NumPy real-valued matrix_rank.
CNOT synthesis requires rank over GF(2). The rows [3,5,6], representing
[[1,1,0],[1,0,1],[0,1,1]], have real rank3 but GF(2) rank2. The existing
`post190_xag_inplace_lower.rank` handles GF(2).

Its output-row builder also needs an explicit equality check: the requested
node set must equal the XOR of selected held-node sets. Merely selecting held
sets contained in the requested set can silently omit uncovered nodes.

Its checker evaluates the pre-transpilation Boolean gates, prints a correctness
flag, then reports native metrics even if the flag is false. Before claiming a
usable encoder, reject failures and verify the compiled encoder and its actual
phase/inverse construction, including preserved coordinates/raw tag, clean
ancillas on final exit, shared global phase and materialized output layout.

## Recommended next search

Retain unrestricted k=6 only as Boolean feasibility work. For sink-restricted
fixed-label search, at least four internal nodes are necessary; the earlier
rank-three high-degree proof also calls for at least three high-degree sinks,
so k=7 with four internal nodes is the first not excluded instance of that
shape. It still needs a genuine reversible schedule on the available wires.
Search actual nine-wire transformations or model register contents/scheduling;
do not replace that requirement by last-use or sink flags alone.

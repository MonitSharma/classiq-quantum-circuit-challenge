#!/bin/sh
# Exact kernel search for depth 116 (champion loader pair x_loader_d44 + po_yF1_s6).
# Needs a strong SAT solver on the Mac, e.g.  brew install kissat   (or cadical / cryptominisat).
# The bundled src/post151_sa/cdcl.c is too weak: it cannot even re-solve the known-SAT k117f65.cnf.
#   k117f65.cnf : sanity check, T=117, kernel layers <=65 fixed to the 117 champion -> must be SAT
#   k117.cnf    : T=117 free                                          -> must be SAT
#   k116f64/60/55.cnf : T=116, champion kernel prefix fixed up to layer 64/60/55
#   k116.cnf    : T=116, kernel fully free (the decisive instance)
# A SAT model is decoded, assembled, CX-cancelled and checked with the exact MILP by:
#   cd src/post151_sa && CLASS_CODES=../../artifacts/185/class_codes.json CLASSIQ_ROOT=../.. \
#     python3 ksat.py dec sat116/<name>.cnf.meta sat116/<name>.sol 116
# (needs scipy for the MILP; model semantics are the kbeamS "bogus pull-in" windows of try6.py.)
SOLVER=${SOLVER:-kissat}
cd "$(dirname "$0")"
for f in k117f65 k116f64 k116f60 k116f55 k116; do
  echo "== $f"; $SOLVER $f.cnf > $f.out; grep '^s ' $f.out
  grep '^v ' $f.out | sed 's/^v //' | tr '\n' ' ' > $f.sol
done

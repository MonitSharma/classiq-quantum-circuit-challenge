"""Exact bounded residual-synthesis entry point.

The current implementation uses the finite 64-bit enumerator as the exact
backend.  This has the same selector semantics as a BitVec/SAT encoding, but
keeps all affine masks and product truth tables concrete.  In particular,
``UNSAT`` is returned only after the requested finite state space is exhausted;
wall-clock interruption is reported as ``timeout``.
"""
from post190_relative_xag import load_prefix, residual_search


def solve(frontier, side, index=0, max_products=3, max_stages=3, seconds=60):
    prefix = load_prefix(frontier, index=index, side=side)
    return residual_search(prefix, max_products=max_products,
                           max_stages=max_stages, seconds=seconds)


__all__ = ['solve']

"""Symbolic exact two-stage residual XAG solver.

Every truth-table equality is a 64-bit BitVec equality.  Products in a stage
read only the prefix plus products from earlier stages, so same-stage
dependencies are impossible by construction.
"""
from __future__ import annotations
import argparse, json, time
from pathlib import Path
import z3

from post190_relative_xag import affine_library, load_prefix, _unique_forms


def affine_expr(selectors, basis):
    out = z3.BitVecVal(0, 64)
    for bit, value in zip(selectors, basis):
        term = value if isinstance(value, z3.BitVecRef) else z3.BitVecVal(value, 64)
        out = out ^ z3.If(bit, term, z3.BitVecVal(0, 64))
    return out


def _gate(solver, name, sources):
    aa = [z3.Bool(f'{name}_a_{i}') for i in range(len(sources))]
    bb = [z3.Bool(f'{name}_b_{i}') for i in range(len(sources))]
    a = affine_expr(aa, sources); b = affine_expr(bb, sources); p = a & b
    solver.add(a != z3.BitVecVal(0, 64), b != z3.BitVecVal(0, 64),
               a != z3.BitVecVal((1 << 64)-1, 64), b != z3.BitVecVal((1 << 64)-1, 64))
    return (aa, bb, a, b, p)


def _output(solver, name, sources, goal):
    bits = [z3.Bool(f'{name}_{i}') for i in range(len(sources))]
    solver.add(affine_expr(bits, sources) == z3.BitVecVal(goal, 64))
    return bits


def _mask(model, bits):
    return sum((1 << i) for i, b in enumerate(bits) if z3.is_true(model.eval(b, model_completion=True)))


def verify_model(model_data, prefix, pattern):
    basis = tuple(prefix['basis']); products = []
    stages = []
    for stage_index, width in enumerate(pattern):
        sources = basis + tuple(products)
        stage = []
        for gate in model_data['gates'][stage_index]:
            am, bm = gate['a_mask'], gate['b_mask']
            a = 0; b = 0
            for i, v in enumerate(sources):
                if am >> i & 1: a ^= v
                if bm >> i & 1: b ^= v
            p = a & b; products.append(p); stage.append({'a': a, 'b': b, 'product': p})
        stages.append(stage)
    final = basis + tuple(products)
    for goal, mask in zip(model_data['goals'], model_data['output_masks']):
        got = 0
        for i, v in enumerate(final):
            if mask >> i & 1: got ^= v
        if got != goal: return False
    return True


def solve_prefix(prefix, pattern=(2, 2), seconds=60, models=1):
    start = time.monotonic(); solver = z3.Solver(); solver.set(timeout=max(1, int(seconds*1000)))
    basis = tuple(prefix['basis']); goals = tuple(prefix['goals'][i] for i in prefix['missing'])
    stage_data = []; products = []
    for si, width in enumerate(pattern):
        sources = basis + tuple(products)
        gates = [_gate(solver, f'g{si}_{j}', sources) for j in range(width)]
        stage_data.append(gates); products.extend(g[-1:] and [g[4]] for g in gates)
        # The previous line stores symbolic products as singleton lists; flatten.
        products = [x[0] if isinstance(x, list) else x for x in products]
    final = basis + tuple(products)
    outs = [_output(solver, f'out_{i}', final, g) for i, g in enumerate(goals)]
    status = solver.check(); result = {'status': str(status).upper(), 'pattern': list(pattern),
        'timeout_seconds': seconds, 'solving_time': time.monotonic()-start, 'models': []}
    if status == z3.sat:
        model = solver.model(); gates_out=[]
        for stage in stage_data:
            gates_out.append([{'a_mask': _mask(model,g[0]), 'b_mask': _mask(model,g[1])} for g in stage])
        output_masks = [_mask(model, x) for x in outs]
        data = {'pattern': list(pattern), 'gates': gates_out, 'goals': list(goals), 'output_masks': output_masks}
        data['verified'] = verify_model(data, prefix, pattern)
        result['models'].append(data); result['verified'] = data['verified']
    return result


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--frontier',required=True); ap.add_argument('--side',choices=('x','y'),required=True)
    ap.add_argument('--index',type=int,default=0); ap.add_argument('--seconds',type=float,default=60); ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args(); p=load_prefix(a.frontier,a.index,a.side); out={'prefix_depth':p['prefix_depth'],'prefix_hash':p['prefix_hash'],'patterns':{}}
    for pat in ((1,3),(2,2),(3,1)):
        out['patterns']['+'.join(map(str,pat))]=solve_prefix(p,pat,a.seconds)
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))

if __name__=='__main__': main()

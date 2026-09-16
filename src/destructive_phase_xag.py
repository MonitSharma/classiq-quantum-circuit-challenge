"""Physical, truth-table-checked lowering of a KNOWN exact XAG.

All wires can be destructive targets. Affine controls are physically exposed,
retained, and charged. Output roots are phased when available. A literal inverse
of the entire non-diagonal trajectory restores all inputs and cancels all
relative phases, even when phases were applied at several intermediate times.

The greedy future-use guard is sufficient, not complete. A stalled run is NOT
an impossibility certificate. No approximate Boolean classifier is emitted.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
import hashlib
import json
import math
import random
import time
from pathlib import Path
from functools import reduce
from operator import xor

from qiskit import QuantumCircuit, qasm2
from qiskit.circuit.library import U3Gate
from destructive_xag import load_xag
from md_xag import FULL, input_truth_tables, mask_indices, xor_mask
from direct_e_v2 import margolus


def basis(rows):
    """Coefficients are physical wire bits, with constant at bit len(rows)."""
    piv = {}
    for value, coeff in [(FULL, 1 << len(rows)), *[(v, 1 << i) for i, v in enumerate(rows)]]:
        while value:
            bit = value.bit_length() - 1
            if bit in piv:
                v, c = piv[bit]; value ^= v; coeff ^= c
            else:
                piv[bit] = value, coeff
                break
    return piv


def represent(piv, value):
    coeff = 0
    while value:
        bit = value.bit_length() - 1
        if bit not in piv:
            return None
        v, c = piv[bit]; value ^= v; coeff ^= c
    return coeff


def apply(rows, ops):
    rows = list(rows)
    for kind, ws in ops:
        if kind == 'x': rows[ws[0]] ^= FULL
        elif kind == 'cx': rows[ws[1]] ^= rows[ws[0]]
        elif kind == 'ccx': rows[ws[2]] ^= rows[ws[0]] & rows[ws[1]]
        elif kind not in ('z','cz'): raise ValueError(kind)
    return tuple(rows)


def clock_ops(arrivals, ops):
    clocks = list(arrivals)
    for kind, ws in ops:
        if kind == 'cz':
            a,b=ws
            clocks=list(clock_ops(clocks,[('x',[b]),('cx',[a,b]),('x',[b])]))
        elif kind == 'ccx':
            a, b, t = ws
            primitive = [('x', [t]), ('cx', [b,t]), ('x', [t]),
                         ('cx', [a,t]), ('x', [t]), ('cx', [b,t]), ('x', [t])]
            clocks = list(clock_ops(clocks, primitive))
        else:
            end = max(clocks[w] for w in ws) + 1
            for w in ws: clocks[w] = end
    return tuple(clocks)


def exposures(rows, left, right, arrivals, limit=4):
    piv = basis(rows); n = len(rows); low = (1 << n) - 1
    a, b = represent(piv, left), represent(piv, right)
    if a is None or b is None: return []
    # Constant/dependent operands yield affine products: no AND is required.
    if not a & low or not b & low or (a & low) == (b & low): return []
    candidates = []
    for p in mask_indices(a & low):
        first = [('cx', [c,p]) for c in mask_indices(a & low) if c != p]
        second = b & low
        if second >> p & 1: second ^= (a & low) ^ (1 << p)
        for r in mask_indices(second & ~(1 << p)):
            ops = first + [('cx', [c,r]) for c in mask_indices(second) if c != r]
            if a >> n & 1: ops += [('x', [p])]
            if b >> n & 1: ops += [('x', [r])]
            clocks = clock_ops(arrivals, ops)
            framed = apply(rows, ops)
            assert framed[p] == left and framed[r] == right
            candidates.append((max(clocks), len(ops), ops, p, r, framed, clocks))
    candidates.sort(key=lambda v: v[:2])
    return candidates[:limit]


@dataclass
class State:
    rows: tuple
    done: int
    phase: int
    phased_roots: int
    ops: tuple
    clocks: tuple
    history: tuple


class Lowerer:
    def __init__(self, parsed, width=18, relaxed=False, max_forward=None):
        assert width >= 12
        self.parsed, self.width = parsed, width
        self.relaxed=relaxed
        self.max_forward=max_forward
        self.signals = parsed.graph._signals()
        self.target = parsed.graph.evaluate()
        self.forms = [(node.left_affine_mask, node.right_affine_mask) for node in parsed.nodes]
        self.operands = [(xor_mask(a, self.signals), xor_mask(b, self.signals)) for a,b in self.forms]
        self.roots = [s for s in mask_indices(parsed.output_affine_mask) if s >= 13]
        self.users = [{j for j,(a,b) in enumerate(self.forms) if ((a|b)>>(i+13))&1}
                      for i in range(len(self.forms))]
        self.initial = tuple(input_truth_tables()) + (0,) * (width - 12)
        self.requirement_cache = {}

    def phase_available(self, state):
        piv = basis(state.rows); ops = []; phase = state.phase; phased = state.phased_roots
        # First try the complete residual; otherwise visit individual output roots.
        remaining = self.target ^ phase
        coeff = represent(piv, remaining)
        if coeff is not None:
            ops = [('z', [w]) for w in range(self.width) if coeff >> w & 1]
            phase ^= remaining  # constant is a permitted global phase
        else:
            for i, root in enumerate(self.roots):
                if phased >> i & 1: continue
                coeff = represent(piv, self.signals[root])
                if coeff is not None:
                    ops += [('z', [w]) for w in range(self.width) if coeff >> w & 1]
                    phase ^= self.signals[root]; phased |= 1 << i
        return State(state.rows, state.done, phase, phased, state.ops + tuple(ops),
                     clock_ops(state.clocks, ops), state.history)

    def required(self, done, phased):
        key = done, phased
        if key in self.requirement_cache: return self.requirement_cache[key]
        # Future operands are partitioned into already-generated and not-yet
        # generated signal contributions. Keep the former affine-exposable.
        available = ((1 << 13) - 1) | (done << 13)
        values = set()
        for i, (a,b) in enumerate(self.forms):
            if done >> i & 1: continue
            values.add(xor_mask(a & available, self.signals))
            values.add(xor_mask(b & available, self.signals))
        for i, root in enumerate(self.roots):
            if not phased >> i & 1 and done >> (root - 13) & 1:
                values.add(self.signals[root])
        self.requirement_cache[key] = tuple(values)
        return tuple(values)

    def initial_state(self):
        # Phase the linear/constant output part before destroying coordinates.
        linear = self.parsed.output_affine_mask & ((1 << 13) - 1)
        ops = tuple(('z', [s-1]) for s in mask_indices(linear) if s)
        state = State(self.initial, 0, xor_mask(linear, self.signals), 0, ops,
                      clock_ops((0,) * self.width, ops), ())
        return self.phase_available(state)

    def transitions(self, state, rng, max_exposures=2):
        piv = basis(state.rows)
        candidates = []
        blocked = 0
        for i, (left,right) in enumerate(self.operands):
            if state.done >> i & 1 and not self.relaxed: continue
            if represent(piv,left) is None or represent(piv,right) is None: continue
            product = left & right
            if represent(piv,product) is not None:
                if state.done>>i&1:continue
                # Known algebraic alias, with no physical gate required.
                nxt = State(state.rows, state.done | (1 << i), state.phase,
                            state.phased_roots, state.ops, state.clocks,
                            state.history + ({'node':i+13,'alias':True},))
                candidates.append(self.phase_available(nxt)); continue
            for _,_,pre,a,b,framed,clocks in exposures(state.rows,left,right,state.clocks,max_exposures):
                # A terminal output AND can contribute its phase as CZ on its
                # two affine controls. No stored node or clean target is needed.
                if i+13 in self.roots and not self.users[i]:
                    ri=self.roots.index(i+13)
                    if not state.phased_roots>>ri&1:
                        ops=pre+[('cz',[a,b])]
                        nxt=State(framed,state.done|(1<<i),state.phase^product,
                                  state.phased_roots|(1<<ri),state.ops+tuple(ops),
                                  clock_ops(clocks,[('cz',[a,b])]),
                                  state.history+({'node':i+13,'phase_only':True,'pre':pre},))
                        candidates.append(self.phase_available(nxt))
                        continue
                for t in range(self.width):
                    if t in (a,b): continue
                    rows = list(framed); rows[t] ^= product
                    ops = pre + [('ccx',[a,b,t])]
                    nxt = State(tuple(rows), state.done | (1 << i), state.phase,
                                state.phased_roots, state.ops + tuple(ops),
                                clock_ops(clocks,[('ccx',[a,b,t])]),
                                state.history + ({'node':i+13,'target':t,'dirty':bool(framed[t]),'pre':pre},))
                    nxt = self.phase_available(nxt)
                    new_basis = basis(nxt.rows)
                    if not self.relaxed and any(represent(new_basis,v) is None for v in self.required(nxt.done,nxt.phased_roots)):
                        blocked += 1; continue
                    candidates.append(nxt)
        # Optimize paid physical depth, not logical multiplicative depth.
        if self.max_forward is not None:
            candidates=[s for s in candidates if max(s.clocks)<=self.max_forward]
        ranked = sorted(candidates, key=lambda s:(self.score(s),rng.random()))
        return ranked, blocked

    def score(self,state):
        if not self.relaxed:return (max(state.clocks),-state.phased_roots.bit_count())
        piv=basis(state.rows)
        exposed=sum(represent(piv,v) is not None for v in self.signals[13:])
        ready=sum(represent(piv,a) is not None and represent(piv,b) is not None for a,b in self.operands)
        # Feasibility heuristics guide incomplete states; only exact completed
        # circuits may be compared by native depth. Repeated products are paid.
        return (-state.phased_roots.bit_count(),-state.done.bit_count(),-ready,-exposed,max(state.clocks))

    def run(self, seconds=30, beam=6, seed=0):
        rng = random.Random(seed); start=time.monotonic()
        frontier=[self.initial_state()]; best=frontier[0]; blocked=0; expanded=0
        status='search_limit'
        seen={}
        for step in range((2 if self.relaxed else 1)*len(self.forms)+1):
            next_states=[]
            for state in frontier:
                if state.phase == self.target:
                    return state,dict(status='exact',seconds=time.monotonic()-start,expanded=expanded,guard_rejections=blocked)
                if time.monotonic()-start >= seconds: break
                candidates,rejected=self.transitions(state,rng)
                next_states.extend(candidates[:beam]); blocked+=rejected; expanded+=1
            if time.monotonic()-start >= seconds: break
            if not next_states:
                status='restricted_search_stalled';break
            unique={}
            for s in next_states:
                key=(s.rows,s.done,s.phased_roots)
                if seen.get(key,float('inf'))<=max(s.clocks):continue
                if key not in unique or max(s.clocks)<max(unique[key].clocks):unique[key]=s
            if not unique:status='restricted_search_stalled';break
            frontier=sorted(unique.values(),key=self.score)[:beam]
            for s in frontier:seen[(s.rows,s.done,s.phased_roots)]=max(s.clocks)
            best=max([best,*frontier],key=lambda s:(s.phased_roots.bit_count(),s.done.bit_count(),-max(s.clocks)))
        return best,dict(status=status,seconds=time.monotonic()-start,expanded=expanded,guard_rejections=blocked)


def emit(state, width):
    """Intermediate phase taps followed by exact inverse of non-phase gates."""
    q=QuantumCircuit(width); compute=QuantumCircuit(width); primitive=margolus()
    for kind,ws in state.ops:
        if kind=='z': q.append(U3Gate(0,0,math.pi),ws);continue
        if kind=='cz':
            q.append(U3Gate(math.pi/2,0,math.pi),[ws[1]]);q.cx(*ws)
            q.append(U3Gate(math.pi/2,0,math.pi),[ws[1]]);continue
        block=QuantumCircuit(width)
        if kind=='x': block.append(U3Gate(math.pi,0,math.pi),ws)
        elif kind=='cx':block.cx(*ws)
        else:block.compose(primitive,ws,inplace=True)
        q.compose(block,inplace=True);compute.compose(block,inplace=True)
    q.compose(compute.inverse(),inplace=True)
    return q


def replay(state, initial, target):
    rows=tuple(initial);phase=0
    for kind,ws in state.ops:
        if kind=='z':phase ^= rows[ws[0]]
        elif kind=='cz':phase ^= rows[ws[0]]&rows[ws[1]]
        else:rows=apply(rows,[(kind,ws)])
    assert rows==state.rows
    # Saved semantic phase may include the physically omitted global constant.
    assert phase ^ state.phase in (0,FULL)
    assert apply(rows,[(kind,ws) for kind,ws in reversed(state.ops) if kind not in ('z','cz')])==tuple(initial)
    return phase ^ target in (0,FULL)


def main():
    p=argparse.ArgumentParser();p.add_argument('--xag',type=Path,required=True)
    p.add_argument('--outdir',type=Path,required=True);p.add_argument('--seconds',type=float,default=30)
    p.add_argument('--beam',type=int,default=6);p.add_argument('--seed',type=int,default=0)
    p.add_argument('--relaxed',action='store_true')
    p.add_argument('--max-forward',type=int)
    a=p.parse_args();assert not a.outdir.exists();a.outdir.mkdir(parents=True)
    parsed=load_xag(a.xag);lowerer=Lowerer(parsed,relaxed=a.relaxed,max_forward=a.max_forward)
    state,report=lowerer.run(a.seconds,a.beam,a.seed)
    exact=replay(state,lowerer.initial,lowerer.target)
    report.update(xag=str(a.xag),xag_sha256=hashlib.sha256(a.xag.read_bytes()).hexdigest(),
                  and_nodes=len(parsed.nodes),completed_nodes=state.done.bit_count(),relaxed=a.relaxed,max_forward=a.max_forward,
                  phased_roots=state.phased_roots.bit_count(),exact_phase=exact,
                  forward_native_depth=max(state.clocks),dirty_coordinate_targets=sum(
                      h.get('dirty',False) and h.get('target',18)<12 for h in state.history),
                  warning='Restricted constructive search; a stall is not UNSAT',
                  ops=state.ops,history=state.history)
    if exact:
        from distributed_frame_search import native
        from exhaustive_verify import exhaustive
        explicit=emit(state,18);q=min([explicit,native(explicit)],key=lambda q:q.depth())
        path=a.outdir/'oracle.qasm';path.write_text(qasm2.dumps(q));exhaustive(path)
        report.update(qasm=str(path),depth=q.depth(),cx=q.count_ops().get('cx',0))
    (a.outdir/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items() if k not in ('ops','history')},flush=True)


if __name__=='__main__':main()

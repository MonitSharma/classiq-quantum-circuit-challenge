"""Stochastic search for shallow promised-subspace side encoders.

This is deliberately a semantic/native-screening experiment.  It searches
reversible 9-wire circuits on the 64 promised inputs (six dirty coordinates
and three clean wires), then asks whether four *affine combinations* of the
nine outputs separate all class-distinct pairs.  The final affine completion
is measured separately; no result from this file is a submission candidate
without the full oracle verifier.
"""
from __future__ import annotations

import argparse, itertools, json, math, random, time
from pathlib import Path

from qiskit import QuantumCircuit, qasm2
from distributed_frame_search import native
from two_stage_oracle import ROWCLS, COLCLS

N = 64
FULL = (1 << N) - 1


def initial():
    return tuple(sum(1 << z for z in range(N) if z >> b & 1) for b in range(6)) + (0, 0, 0)


def affine(values, mask):
    out = FULL if mask & (1 << 9) else 0
    for i in range(9):
        if mask >> i & 1: out ^= values[i]
    return out


def apply(values, move):
    out = list(values); kind, a, b, t = move
    if kind == 'cx': out[b] ^= out[a]
    else: out[t] ^= out[a] & out[b]
    return tuple(out)


def conflicts(values, classes, masks=None):
    # The complete affine dictionary has only 512 functions.  A greedy
    # set-cover pass gives a fast lower-cost ranking; exact completion is
    # performed on finalists by exhaustive 4-tuples from the useful pool.
    if masks is None: masks = range(512)
    funcs = [affine(values, m) for m in masks]
    pairs = [(a,b) for a in range(N) for b in range(a) if classes[a] != classes[b]]
    uncovered = {(a,b) for a,b in pairs if True}
    chosen=[]
    for _ in range(4):
        best = max(range(len(funcs)), key=lambda i: sum(((funcs[i]>>a)^(funcs[i]>>b))&1 for a,b in uncovered))
        gain = sum(((funcs[best]>>a)^(funcs[best]>>b))&1 for a,b in uncovered)
        if not gain: break
        chosen.append(masks[best])
        uncovered = {(a,b) for a,b in uncovered if not ((funcs[best]>>a)^(funcs[best]>>b))&1}
    return len(uncovered), tuple(chosen), len(pairs)


def exact_projection(values, classes, pool):
    # Only combinations from a pool that are useful against a remaining
    # conflict are needed.  Keep all 512 masks for small final searches.
    pairs = [(a,b) for a in range(N) for b in range(a) if classes[a] != classes[b]]
    fs = {m: affine(values,m) for m in pool}
    for k in range(1,5):
        for combo in itertools.combinations(pool,k):
            seen={}
            ok=True
            for z in range(N):
                sig=tuple((fs[m]>>z)&1 for m in combo)
                old=seen.get(sig)
                if old is not None and classes[old] != classes[z]: ok=False; break
                seen[sig]=z
            if ok: return combo
    return None


def gate_pool():
    moves=[]
    for a in range(9):
        for b in range(9):
            if a != b: moves.append(('cx',a,b,-1))
    for a,b in itertools.combinations(range(9),2):
        for t in range(9):
            if t not in (a,b): moves.append(('rccx',a,b,t))
    return moves

MOVES = gate_pool()


def build(gates):
    q=QuantumCircuit(9)
    for kind,a,b,t in gates:
        if kind=='cx': q.cx(a,b)
        else: q.rccx(a,b,t)
    return q


def run(outdir, side, seconds, restarts, max_gates, seed):
    outdir.mkdir(parents=True, exist_ok=True)
    classes = ROWCLS if side=='y' else COLCLS
    rng=random.Random(seed); start=time.monotonic(); best=None; records=[]
    for restart in range(restarts):
        # Fixed-length mutation is materially better than growing a circuit:
        # it explores arbitrary gate placement and does not privilege the
        # last few gates through a sliding-window artifact.
        length = rng.randint(max(2, max_gates//2), max_gates)
        gates=[rng.choice(MOVES) for _ in range(length)]
        values=initial()
        for g in gates: values=apply(values,g)
        score=conflicts(values,classes)[0]
        temperature=8.0
        for step in range(max_gates*120):
            if time.monotonic()-start >= seconds: break
            pos=rng.randrange(length); old=gates[pos]; move=rng.choice(MOVES)
            trial=list(gates); trial[pos]=move; nv=initial()
            for g in trial: nv=apply(nv,g)
            ns=conflicts(nv,classes)[0]
            cost=ns
            oldcost=score
            accept=cost<=oldcost or rng.random()<math.exp((oldcost-cost)/max(0.15,temperature))
            if accept:
                gates=trial
                values=initial()
                for g in gates: values=apply(values,g)
                score=conflicts(values,classes)[0]
            temperature*=0.998
            if best is None or (score,len(gates)) < (best['greedy_conflicts'],best['gate_count']):
                greedy,combo,total=conflicts(values,classes)
                # A useful pool is all masks that distinguish at least one
                # remaining pair; exact projection is deferred to close states.
                best={'greedy_conflicts':greedy,'gate_count':len(gates),'gates':[list(g) for g in gates], 'greedy_combo':list(combo)}
                print({'side':side,'restart':restart,'step':step,'conflicts':greedy,'gates':len(gates)},flush=True)
                if greedy==0:
                    proj=exact_projection(values,classes,range(512))
                    if proj:
                        q=native(build(gates));best.update(projection=list(proj),native_depth=q.depth(),cx=q.count_ops().get('cx',0))
                        path=outdir/f'{side}_semantic_d{q.depth()}_cx{q.count_ops().get("cx",0)}.qasm';path.write_text(qasm2.dumps(q));best['path']=str(path)
                        records.append(best.copy());(outdir/'report.json').write_text(json.dumps(records,indent=2)+'\n')
                        print('projection witness',best,flush=True);return best
        records.append(best.copy() if best else {})
        (outdir/'report.json').write_text(json.dumps(records,indent=2)+'\n')
    return best


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);p.add_argument('--side',choices=['x','y'],required=True);p.add_argument('--seconds',type=float,default=120);p.add_argument('--restarts',type=int,default=8);p.add_argument('--max-gates',type=int,default=12);p.add_argument('--seed',type=int,default=0);a=p.parse_args();run(a.outdir,a.side,a.seconds,a.restarts,a.max_gates,a.seed)

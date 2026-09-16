"""Bounded exact input-preserving pebbling diagnostic, NOT a depth optimizer.

UNSAT excludes only the given toggle horizon and scratch budget. UNKNOWN is
inconclusive. Relative-phase quantum validity must still be checked after emit.
"""
import argparse,json,time
from pathlib import Path
import z3
from destructive_xag import load_xag
from post185_xag_pebble import output_parts,predecessors
from xag_to_inplace_layers import XAGGraph


def solve(deps,roots,limit,horizon,seconds=10,forced=None):
    ids=sorted(deps);pos={v:i for i,v in enumerate(ids)};n=len(ids)
    assert limit>=0 and horizon>=0
    s=z3.Solver();s.set(timeout=int(seconds*1000))
    board=[[z3.Bool(f'p_{t}_{i}') for i in range(n)] for t in range(horizon+1)]
    moves=[z3.Int(f'm_{t}') for t in range(horizon)]
    s.add([z3.Not(v) for v in board[0]+board[-1]])
    for row in board:s.add(z3.PbLe([(v,1) for v in row],limit))
    for t,move in enumerate(moves):
        s.add(move>=-1,move<n)
        if forced is not None:s.add(move==pos[forced[t]])
        for i,node in enumerate(ids):
            s.add(board[t+1][i]==z3.Xor(board[t][i],move==i))
            for parent in deps[node]:s.add(z3.Implies(move==i,board[t][pos[parent]]))
    for root in roots:s.add(z3.Or([row[pos[root]] for row in board]))
    start=time.monotonic();status=s.check()
    report=dict(status=str(status),limit=limit,horizon=horizon,nodes=n,seconds=time.monotonic()-start,
                scope='Frozen inputs, named clean node pebbles, at most the stated toggle horizon')
    if status==z3.unknown:report['reason']=s.reason_unknown()
    if status==z3.sat:
        model=s.model();trace=[model.eval(m).as_long() for m in moves];board=set();seen=set();peak=0
        for i in trace:
            if i<0:continue
            node=ids[i];assert set(deps[node])<=board
            board.symmetric_difference_update({node});seen.update(board);peak=max(peak,len(board))
        assert not board and set(roots)<=seen and peak<=limit
        report.update(trace=[ids[i] for i in trace if i>=0],peak=peak,replay_verified=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--xag',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--horizon',type=int,default=212)
    p.add_argument('--limit',type=int,default=6);p.add_argument('--seconds',type=float,default=10)
    a=p.parse_args();assert not a.out.exists()
    parsed=load_xag(a.xag);roots,_,_=output_parts(parsed)
    result=solve(predecessors(XAGGraph(parsed.nodes)),roots,a.limit,a.horizon,a.seconds)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k!='trace'},flush=True)

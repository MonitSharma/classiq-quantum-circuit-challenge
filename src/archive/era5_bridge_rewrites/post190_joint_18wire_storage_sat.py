"""Storage-aware free-affine-frame SAT model for one joint x14+y13 schedule.

This models semantic row replacement exactly on the 40-dimensional Boolean
function basis (constant, 12 inputs, 27 fixed AND nodes). Affine frames are
arbitrary invertible 18x18 physical row maps; CNOT depth is intentionally not
modeled here.
"""
from __future__ import annotations
import argparse, json, time
from pathlib import Path
from z3 import Bool, BoolVal, Solver, Xor, And, Or, Not, sat, unknown, is_true
from functools import reduce
from operator import xor
from post190_joint_18wire_feasibility import remap
from post190_xag_inplace_lower import outputs
from post190_degree_rank_bound import targets

ROOT=Path(__file__).resolve().parents[1]
XPATH=ROOT/'artifacts/post190_nist_variants/x_candidate_0.json'
YPATH=ROOT/'artifacts/post190_nist_variants_wide/y_candidate_0.json'
SCHEDULE=[[0,1,5,14,16,19],[20,2,3,6,7,10],[8,11,15,21,22,24],[12,17,25,4,9,23],[13,18,26]]

def form_coord(form, side, node_offset):
    ids,const=form; mask=(1 if const else 0)
    off=0 if side=='x' else 6
    for i in ids:
        if i<6: mask ^= 1 << (1 + i + off)
        else: mask ^= 1 << (13 + node_offset + i - 6)
    return mask

def combined_data(xpath=XPATH,ypath=YPATH):
    x=json.loads(xpath.read_text());y=json.loads(ypath.read_text())
    assert x['k']==14 and y['k']==13
    gates=remap(x,0,6)+remap(y,6,20)
    operands=[]
    for i,g in enumerate(x['gates']+y['gates']):
        side='x' if i<14 else 'y'; no=0 if side=='x' else 14
        operands.append((form_coord(g['a'],side,no),form_coord(g['b'],side,no)))
    nodes=[1 << (1+12+i) for i in range(27)]
    endpoint=[form_coord(o,'x',0) for o in x['outs']]
    endpoint += [(1<<5)^(1<<6)]
    endpoint += [form_coord(o,'y',14) for o in y['outs']]
    endpoint += [1<<12]
    return operands,nodes,endpoint,gates

def parity(xs):
    if not xs:return BoolVal(False)
    out=xs[0]
    for x in xs[1:]:out=Xor(out,x)
    return out

def frame(s, rows, tag):
    width=len(rows);dimension=len(rows[0])
    m=[[Bool(f'{tag}_m_{i}_{j}') for j in range(width)] for i in range(width)]
    inv=[[Bool(f'{tag}_i_{i}_{j}') for j in range(width)] for i in range(width)]
    c=[Bool(f'{tag}_c_{i}') for i in range(width)]
    for i in range(width):
        for j in range(width):
            s.add(parity([And(m[i][k],inv[k][j]) for k in range(width)]) == (i==j))
    out=[]
    for i in range(width):
        rr=[]
        for bit in range(dimension):
            terms=[And(m[i][j],rows[j][bit]) for j in range(width)]
            if bit==0:terms.append(c[i])
            v=Bool(f'{tag}_r_{i}_{bit}');s.add(v==parity(terms));rr.append(v)
        out.append(rr)
    return out,m,inv,c

def initial_rows(width=18, inputs=12):
    assert inputs<=width
    return [1<<(i+1) for i in range(inputs)]+[0]*(width-inputs)

def fixed_frame_solver(schedule=SCHEDULE, timeout_ms=120000, data=None, width=18, inputs=12):
    if data is None:
        operands,nodes,endpoint,gates=combined_data()
    else:operands,nodes,endpoint=data
    assert len(operands)==len(nodes)
    assert sorted(i for b in schedule for i in b)==list(range(len(nodes)))
    assert all(3*len(b)<=width for b in schedule)
    assert len(endpoint)<=width
    dimension=max([inputs+1,*[v.bit_length() for v in nodes+endpoint],*[v.bit_length() for ab in operands for v in ab]])
    s=Solver();s.set(timeout=timeout_ms)
    initial=initial_rows(width,inputs)
    rows=[[BoolVal(bool(v>>bit&1)) for bit in range(dimension)] for v in initial]
    frames=[];states=[]
    for stage,batch in enumerate(schedule):
        f,m,inv,c=frame(s,rows,f'f{stage}');frames.append((m,inv,c));states.append(('pre',f))
        k=len(batch); used=[]; nextrows=list(f)
        for slot,node in enumerate(batch):
            a,b=operands[node]; ca=[BoolVal(bool((a>>q)&1)) for q in range(dimension)]; cb=[BoolVal(bool((b>>q)&1)) for q in range(dimension)]
            s.add(*[f[2*slot][q]==ca[q] for q in range(dimension)])
            s.add(*[f[2*slot+1][q]==cb[q] for q in range(dimension)])
            target=2*k+slot
            replacement=[]
            for q in range(dimension):
                v=Bool(f's{stage}_{target}_{q}');s.add(v==Xor(f[target][q],BoolVal(bool((nodes[node]>>q)&1))))
                replacement.append(v)
            nextrows[target]=replacement
            used.extend([2*slot,2*slot+1,target])
        # Controls and targets are disjoint by canonical placement; all other
        # rows retain their framed value.
        rows=nextrows
    f,m,inv,c=frame(s,rows,f'f{len(schedule)}');frames.append((m,inv,c));states.append(('endpoint',f))
    for wire,vec in enumerate(endpoint):
        s.add(*[f[wire][q]==BoolVal(bool((vec>>q)&1)) for q in range(dimension)])
    started=time.monotonic();status=s.check();elapsed=time.monotonic()-started
    result={'status':'SAT' if status==sat else 'UNKNOWN' if status==unknown else 'UNSAT', 'seconds':elapsed,'timeout_ms':timeout_ms,'schedule':schedule,'endpoint_mode':'literal','model':f'{dimension}-bit semantic rows; {len(frames)} explicit invertible affine frames', 'width':width,'inputs':inputs,'revision':'corrected-v2'}
    if status==unknown:result['reason']=s.reason_unknown()
    if status==sat:
        model=s.model(); result['frames']=[]
        for m,inv,c in frames:
            result['frames'].append({'matrix':[[int(is_true(model.eval(v,model_completion=True))) for v in row] for row in m], 'inverse':[[int(is_true(model.eval(v,model_completion=True))) for v in row] for row in inv], 'translation':[int(is_true(model.eval(v,model_completion=True))) for v in c]})
        result['replay_verified']=replay_model(result,operands,nodes,endpoint)
    return result

def replay_model(result,operands,nodes,endpoint):
    # Recheck the extracted frames on coefficient vectors, independently of Z3.
    width=result.get('width',18);rows=initial_rows(width,result.get('inputs',12))
    def apply(fr):
        for i in range(width):
            for j in range(width):
                assert sum(fr['matrix'][i][k]*fr['inverse'][k][j] for k in range(width))%2==int(i==j)
        return [reduce(xor,(rows[j] for j in range(width) if fr['matrix'][i][j]),0) ^ int(fr['translation'][i]) for i in range(width)]
    for stage,batch in enumerate(result['schedule']):
        rows=apply(result['frames'][stage]); k=len(batch); old=rows[:]
        for slot,node in enumerate(batch):
            assert rows[2*slot]==operands[node][0] and rows[2*slot+1]==operands[node][1]
            rows[2*k+slot]=old[2*k+slot]^nodes[node]
    rows=apply(result['frames'][len(result['schedule'])])
    assert all(rows[i]==endpoint[i] for i in range(len(endpoint)))
    return True

def main():
    p=argparse.ArgumentParser();p.add_argument('--timeout-ms',type=int,default=120000);p.add_argument('--outdir',type=Path,required=True);a=p.parse_args();assert not a.outdir.exists();a.outdir.mkdir(parents=True);r=fixed_frame_solver(timeout_ms=a.timeout_ms);(a.outdir/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='frames'},indent=2))
if __name__=='__main__':main()

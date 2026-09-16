"""Storage-aware free-affine-frame SAT model for one joint x14+y13 schedule.

This models semantic row replacement exactly on the 40-dimensional Boolean
function basis (constant, 12 inputs, 27 fixed AND nodes). Affine frames are
arbitrary invertible 18x18 physical row maps; CNOT depth is intentionally not
modeled here.
"""
from __future__ import annotations
import argparse, json, time
from pathlib import Path
from z3 import Bool, BoolVal, Solver, Xor, And, Or, Not, sat, unknown
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

def combined_data():
    x=json.loads(XPATH.read_text());y=json.loads(YPATH.read_text())
    gates=remap(x,0,6)+remap(y,6,20)
    operands=[]
    for i,g in enumerate(gates):
        side='x' if i<14 else 'y'; no=0 if side=='x' else 14
        operands.append((form_coord(g['a'],side,no),form_coord(g['b'],side,no)))
    nodes=[1 << (1+12+i) for i in range(27)]
    endpoint=[form_coord(o,'x',0) for o in x['outs']]
    endpoint += [1<<5]
    endpoint += [form_coord(o,'y',14) for o in y['outs']]
    endpoint += [1<<12]
    return operands,nodes,endpoint,gates

def parity(xs):
    if not xs:return BoolVal(False)
    out=xs[0]
    for x in xs[1:]:out=Xor(out,x)
    return out

def frame(s, rows, tag):
    m=[[Bool(f'{tag}_m_{i}_{j}') for j in range(18)] for i in range(18)]
    inv=[[Bool(f'{tag}_i_{i}_{j}') for j in range(18)] for i in range(18)]
    c=[Bool(f'{tag}_c_{i}') for i in range(18)]
    for i in range(18):
        for j in range(18):
            s.add(parity([And(m[i][k],inv[k][j]) for k in range(18)]) == (i==j))
    out=[]
    for i in range(18):
        rr=[]
        for bit in range(40):
            terms=[And(m[i][j],rows[j][bit]) for j in range(18)]
            if bit==0:terms.append(c[i])
            v=Bool(f'{tag}_r_{i}_{bit}');s.add(v==parity(terms));rr.append(v)
        out.append(rr)
    return out,m,inv,c

def fixed_frame_solver(schedule=SCHEDULE, timeout_ms=120000):
    operands,nodes,endpoint,gates=combined_data(); s=Solver();s.set(timeout=timeout_ms)
    rows=[[BoolVal(j==bit) if bit in range(1,13) and j==bit-1 else BoolVal(False) for bit in range(40)] for j in range(18)]
    frames=[];states=[]
    for stage,batch in enumerate(schedule):
        f,m,inv,c=frame(s,rows,f'f{stage}');frames.append((m,inv,c));states.append(('pre',f))
        k=len(batch); used=[]; nextrows=list(f)
        for slot,node in enumerate(batch):
            a,b=operands[node]; ca=[BoolVal((a>>q)&1) for q in range(40)]; cb=[BoolVal((b>>q)&1) for q in range(40)]
            s.add(*[f[2*slot][q]==ca[q] for q in range(40)])
            s.add(*[f[2*slot+1][q]==cb[q] for q in range(40)])
            target=2*k+slot
            replacement=[]
            for q in range(40):
                v=Bool(f's{stage}_{target}_{q}');s.add(v==Xor(f[target][q],BoolVal(bool((nodes[node]>>q)&1))))
                replacement.append(v)
            nextrows[target]=replacement
            used.extend([2*slot,2*slot+1,target])
        # Controls and targets are disjoint by canonical placement; all other
        # rows retain their framed value.
        rows=nextrows
    f,m,inv,c=frame(s,rows,'f5');frames.append((m,inv,c));states.append(('endpoint',f))
    for wire,vec in enumerate(endpoint):
        s.add(*[f[wire][q]==BoolVal(bool((vec>>q)&1)) for q in range(40)])
    started=time.monotonic();status=s.check();elapsed=time.monotonic()-started
    result={'status':'SAT' if status==sat else 'UNKNOWN' if status==unknown else 'UNSAT', 'seconds':elapsed,'timeout_ms':timeout_ms,'schedule':schedule,'endpoint_mode':'literal','model':'40-bit semantic rows; six explicit invertible affine frames'}
    if status==sat:
        model=s.model(); result['frames']=[]
        for m,inv,c in frames:
            result['frames'].append({'matrix':[[int(bool(model.eval(v,model_completion=True))) for v in row] for row in m], 'inverse':[[int(bool(model.eval(v,model_completion=True))) for v in row] for row in inv], 'translation':[int(bool(model.eval(v,model_completion=True))) for v in c]})
        result['replay_verified']=replay_model(result,operands,nodes,endpoint)
    return result

def replay_model(result,operands,nodes,endpoint):
    # Recheck the extracted frames on coefficient vectors, independently of Z3.
    rows=[1<<i for i in range(1,13)]+[0]*6
    def apply(fr):
        return [sum((rows[j] if fr['matrix'][i][j] else 0) for j in range(18)) ^ ((1 if fr['translation'][i] else 0)) for i in range(18)]
    for stage,batch in enumerate(SCHEDULE):
        rows=apply(result['frames'][stage]); k=len(batch); old=rows[:]
        for slot,node in enumerate(batch):
            assert rows[2*slot]==operands[node][0] and rows[2*slot+1]==operands[node][1]
            rows[2*k+slot]=old[2*k+slot]^nodes[node]
    rows=apply(result['frames'][5])
    assert all(rows[i]==endpoint[i] for i in range(8))
    return True

def main():
    p=argparse.ArgumentParser();p.add_argument('--timeout-ms',type=int,default=120000);p.add_argument('--outdir',type=Path,default=ROOT/'artifacts/post190_joint_18wire_storage');a=p.parse_args();a.outdir.mkdir(parents=True,exist_ok=True);r=fixed_frame_solver(timeout_ms=a.timeout_ms);(a.outdir/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='frames'},indent=2))
if __name__=='__main__':main()

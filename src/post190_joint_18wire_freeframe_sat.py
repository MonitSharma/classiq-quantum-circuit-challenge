"""Exact unbounded-affine-frame feasibility screen for x14+y13 witnesses.

The free-frame model deliberately abstracts each inter-batch affine operation
to an arbitrary affine map.  It is therefore an optimistic relaxation of a
CNOT-depth model, but it uses actual 4096-point Boolean functions rather than
formally independent node symbols.  A positive result is a seed for a later
physical-frame SAT model; it is not a native circuit.
"""
from __future__ import annotations
import argparse, itertools, json
from pathlib import Path
from post190_xag_inplace_lower import outputs
from post190_joint_18wire_feasibility import remap, dependencies, capacity_schedule
from post190_degree_rank_bound import targets

ROOT=Path(__file__).resolve().parents[1]
XPATH=ROOT/'artifacts/post190_nist_variants/x_candidate_0.json'
YPATH=ROOT/'artifacts/post190_nist_variants_wide/y_candidate_0.json'

def truth(mask_fn, domain=4096):
    return sum(1<<i for i in range(domain) if mask_fn(i))

def rank(vectors):
    basis={}
    for v in vectors:
        while v:
            p=v.bit_length()-1
            if p in basis:v^=basis[p]
            else:basis[p]=v;break
    return len(basis)

def affine_vector(form, side, node_tables):
    ids,const=form
    value=(1<<4096)-1 if const else 0
    offset=0 if side=='x' else 6
    for i in ids:
        if i<6:
            value ^= truth(lambda z,i=i: bool((z>> (i+offset))&1))
        else:value ^= node_tables[i-6]
    return value

def candidate_tables(witness, side):
    nodes=[]
    for g in witness['gates']:
        a=affine_vector(g['a'],side,nodes);b=affine_vector(g['b'],side,nodes)
        nodes.append(a&b)
    outs=[affine_vector(o,side,nodes) for o in witness['outs']]
    return nodes,outs

def semantic_screen(xpath=XPATH,ypath=YPATH):
    x=json.loads(xpath.read_text());y=json.loads(ypath.read_text())
    xt,xo=candidate_tables(x,'x');yt,yo=candidate_tables(y,'y')
    # Constant plus twelve coordinate functions are the initial affine space.
    one=(1<<4096)-1
    initial=[one]+[truth(lambda z,i=i:bool((z>>i)&1)) for i in range(12)]
    nodes=xt+yt
    all_functions=initial+nodes
    # A free affine frame can expose any member of the current semantic span.
    # Dirty RCCX updates add each node to that span; target choice does not
    # change the span, while the six-target cap is enforced by the batches.
    base_rank=rank(initial)
    final_rank=rank(all_functions)
    deps=dependencies(remap(x,0,6)+remap(y,6,20))
    batches=capacity_schedule(deps,6)
    prefix=[];stage_ranks=[]
    for batch in batches:
        prefix.extend(nodes[i] for i in batch)
        stage_ranks.append(rank(initial+prefix))
    # The protected two-stage layout uses x4 and y5 as the raw half tags.
    endpoint=xo+[truth(lambda z,i=i:bool((z>>(i+0))&1)) for i in [4]]
    endpoint += yo+[truth(lambda z,i=i:bool((z>>(i+6))&1)) for i in [5]]
    endpoint_rank=rank(endpoint)
    endpoint_in_span=rank(initial+nodes+endpoint)==final_rank
    # Eight literal endpoint rows are placeable in an 18-row affine frame when
    # their semantic rank is no larger than the available row rank (12+6).
    literal_placeable=endpoint_in_span and len(set(endpoint))==8
    return {'status':'RELAXED_ENDPOINT_PASS_STORAGE_UNMODELED' if literal_placeable else 'RELAXED_ENDPOINT_FAIL',
            'x_source':str(xpath.relative_to(ROOT)),'y_source':str(ypath.relative_to(ROOT)),
            'x_and_nodes':len(xt),'y_and_nodes':len(yt),'total_and_nodes':len(nodes),
            'batches':batches,'nonlinear_batches':len(batches),'batch_capacity':6,
            'base_affine_rank':base_rank,'stage_affine_ranks':stage_ranks,
            'final_function_rank':final_rank,'endpoint_function_rank':endpoint_rank,
            'literal_endpoint_distinct':len(set(endpoint))==8,
            'literal_endpoint_placeable':literal_placeable,
            'endpoint_order':['x0','x1','x2','x_raw','y0','y1','y2','y_raw'],
            'model':'actual 4096-point semantic functions; endpoint/span diagnostic only',
            'warning':'This diagnostic does not model 18-row storage, row replacement, or frame invertibility across batches; it is not a SAT certificate.',
            'native_cnot_depth':'not modeled','kernel_permutation':'endpoint literal mode; physical kernel map not compiled'}

def affine_dependency_control():
    f=0b0011;g=0b0101;h=f^g
    return {'semantic_rank':rank([f,g,h]),'formal_symbol_rank':3,
            'passes':rank([f,g,h])==2 and 3>rank([f,g,h])}

def main():
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,default=ROOT/'artifacts/post190_joint_18wire_freeframe');a=p.parse_args();a.outdir.mkdir(parents=True,exist_ok=True)
    r=semantic_screen();r['affine_dependency_control']=affine_dependency_control();(a.outdir/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':main()

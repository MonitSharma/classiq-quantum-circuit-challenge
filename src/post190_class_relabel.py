"""Bounded direct 4-bit relabeling audit for the 11 logo classes."""
from __future__ import annotations
import argparse, itertools, json, random
from pathlib import Path
import numpy as np
from qiskit import transpile

from two_stage_oracle import ROWCLS, COLCLS, logo, walsh8, emit_kernel
from distributed_frame_search import native


def anf_stats(table):
    a=[(table>>x)&1 for x in range(64)]
    for b in range(6):
        for m in range(64):
            if m>>b&1: a[m]^=a[m^(1<<b)]
    support=[m for m,v in enumerate(a) if v]
    return {'degree':max((m.bit_count() for m in support),default=0), 'anf_monomials':len(support), 'anf_support':support}


def cut_table(classes, cut):
    return sum(((cut>>classes[x])&1)<<x for x in range(64))


def separation(table_values):
    mask=0
    for i in range(11):
        for j in range(i):
            if table_values[i]!=table_values[j]: mask |= 1 << (i*(i-1)//2+j)
    return mask


def enumerate_cuts(classes):
    rows=[]
    for raw in range(1024):
        cut = raw << 1  # class 0 is fixed to zero
        table=cut_table(classes,cut)
        stats=anf_stats(table)
        vals=[(cut>>i)&1 for i in range(11)]
        rows.append({'cut':cut,'truth':hex(table),'class_values':vals,'separation_mask':separation(vals),**stats})
    return rows


def label_code(cuts, classes, n=64):
    labels=[0]*11
    for c, row in enumerate(cuts):
        for k in range(11): labels[k] |= ((row>>k)&1)<<c
    return [labels[classes[x]] for x in range(n)], labels


def valid_label(cuts):
    labels=[sum(((cuts[b]>>k)&1)<<b for b in range(4)) for k in range(11)]
    return len(set(labels))==11 and labels[0]==0


def find_labelings(rows, seed=190915, count=64):
    rng=random.Random(seed); found={}; attempts=0
    # Deterministic random sampling of 4-cuts, plus greedy repair attempts.
    while attempts < 300000 and len(found)<count:
        cuts=tuple(rng.sample([r['cut'] for r in rows if r['cut']],4)); attempts+=1
        if not valid_label(cuts): continue
        labels=[sum(((cuts[b]>>k)&1)<<b for b in range(4)) for k in range(11)]
        canon=tuple(sorted(labels))
        found.setdefault(canon, {'cuts':cuts,'labels':labels})
    return list(found.values()), attempts


def kernel_metrics(ylabels,xlabels):
    table=[0]*256
    for y in range(64):
        for x in range(64): table[ylabels[y] | (xlabels[x]<<4)] = int(logo(x,y))
    coeff=walsh8(table); support=[m for m in range(1,256) if abs(coeff[m])>1e-12]
    q,_=emit_kernel(table,list(range(8))); q=transpile(q,basis_gates=['u3','cx'],qubits_initially_zero=False,optimization_level=3)
    return {'support':len(support),'support_masks':support,'kernel_depth':q.depth(),'kernel_cx':q.count_ops().get('cx',0)}


def run(outdir):
    outdir.mkdir(parents=True,exist_ok=True)
    yrows=enumerate_cuts(ROWCLS); xrows=enumerate_cuts(COLCLS)
    (outdir/'y_cuts.json').write_text(json.dumps(yrows,indent=2)); (outdir/'x_cuts.json').write_text(json.dumps(xrows,indent=2))
    ylabels,ya=find_labelings(yrows); xlabels,xa=find_labelings(xrows,seed=190916)
    # Retain a compact representative portfolio, then evaluate cross-products.
    ys=ylabels[:16]; xs=xlabels[:16]; pairs=[]
    for yi,y in enumerate(ys):
        for xi,x in enumerate(xs):
            km=kernel_metrics([y['labels'][ROWCLS[t]] for t in range(64)],[x['labels'][COLCLS[t]] for t in range(64)])
            pairs.append({'y_index':yi,'x_index':xi,'y_cuts':y['cuts'],'x_cuts':x['cuts'],'y_labels':y['labels'],'x_labels':x['labels'],**km})
    pairs.sort(key=lambda p:(p['kernel_depth'],p['support']))
    report={'class_counts':{'rows':len(set(ROWCLS)),'cols':len(set(COLCLS))},'cuts_per_side':1024,
            'y_labelings_found':len(ylabels),'x_labelings_found':len(xlabels),'sampling_attempts':[ya,xa],
            'labeling_pairs_measured':len(pairs),'best_pairs':pairs[:32],
            'control':{'protected_y_raw_plus_code':13,'protected_x_raw_plus_code':14}}
    (outdir/'report.json').write_text(json.dumps(report,indent=2)); print(json.dumps({'y_labelings':len(ylabels),'x_labelings':len(xlabels),'best':pairs[0] if pairs else None},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,default=Path('artifacts/post190_class_relabel'));run(p.parse_args().outdir)

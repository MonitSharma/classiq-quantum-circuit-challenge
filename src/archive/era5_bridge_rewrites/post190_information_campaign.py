"""Comparable bounded controls; all modes share scoring and exact semantics.

A/B reproduce legacy move widths and span dedup, not the legacy scoring rule.
The separate dedup audit instruments the literal legacy search.
"""
import argparse,json
from pathlib import Path
from post190_information_space import run
from post190_register_repair import repair

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--outdir',required=True);p.add_argument('--seconds',type=float,default=15);a=p.parse_args();root=Path(a.outdir);root.mkdir(parents=True,exist_ok=False)
    base=dict(witness='artifacts/post190_nist_variants_wide/y_candidate_0.json',side='y',seconds=a.seconds,beam=24,steps=24,seed=0,dedup='span',mix=False,mode='physical',aliases=1,exposure_limit=2,stage_width=1)
    results={}
    for name,changes in [('A',{}),('B',dict(mix=True)),('C',dict(dedup='pareto',aliases=4,exposure_limit=8)),('D',dict(dedup='pareto',aliases=4,exposure_limit=8,mode='information',stage_width=3))]:
        print(name,flush=True);results[name]=run({**base,**changes},root/name)
    results['E']=repair(root/'D/config.json',root/'D/frontier.json',root/'E',seconds=a.seconds)
    (root/'summary.json').write_text(json.dumps(results,indent=2))

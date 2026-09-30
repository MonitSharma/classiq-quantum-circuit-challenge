"""Bounded broader suffix beam from exact saved prefixes, never sampled SAT."""
import argparse,json
from pathlib import Path
from post190_information_space import restore,run


def repair(config_path,frontier_path,outdir,seconds=20,max_stages=4,prefixes=4):
    config=json.loads(Path(config_path).read_text());data=json.loads(Path(frontier_path).read_text())
    states=[restore(d) for d in data[:prefixes]]
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=False);results=[]
    for stages in range(1,max_stages+1):
        cfg={**config,'seconds':seconds/max_stages,'steps':stages,'beam':64,'dedup':'pareto','mode':'information','aliases':8,'exposure_limit':16,'stage_width':3,'mix':True}
        r=run(cfg,outdir/f'stages_{stages}',initial=states);results.append(r)
        if r.get('best'):break
    (outdir/'summary.json').write_text(json.dumps(results,indent=2));return results

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--frontier',required=True);p.add_argument('--outdir',required=True);p.add_argument('--seconds',type=float,default=20);p.add_argument('--max-stages',type=int,default=4);p.add_argument('--prefixes',type=int,default=4);a=p.parse_args();repair(a.config,a.frontier,a.outdir,a.seconds,a.max_stages,a.prefixes)

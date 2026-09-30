"""Search a shared XAG for a saved raw-plus-global label assignment."""
import argparse,json
from pathlib import Path
from two_stage_oracle import ROWCLS,COLCLS
from multioutput_minmc import synthesize

def target_masks(side, path):
    labels=json.loads(Path(path).read_text())['labels']; classes=ROWCLS if side=='y' else COLCLS
    return [sum(((labels[c]>>b)&1)<<z for z,c in enumerate(classes)) for b in range(3)]

def main():
 p=argparse.ArgumentParser();p.add_argument('--side',choices=['x','y'],required=True);p.add_argument('--labels',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--max-and',type=int,default=8);p.add_argument('--timeout-ms',type=int,default=15000);a=p.parse_args()
 t=target_masks(a.side,a.labels);print('targets',t,flush=True);r=synthesize(t,a.max_and,a.timeout_ms);out={'side':a.side,'labels':str(a.labels),'targets':t,'result':r};a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()

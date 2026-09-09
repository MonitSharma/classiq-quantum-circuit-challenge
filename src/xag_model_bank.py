"""Time-limited semantic XAG model bank for cross-output sharing tests."""
import json, time
from collections import Counter, defaultdict
from pathlib import Path
import z3
from minmc_xag import FULL, INPUTS, eval_xag, verify_xag, xor_selected, model_mask

def enumerate_models(target, count, max_models=1, timeout_ms=200):
    solver=z3.Solver();solver.set(timeout=timeout_ms);exprs=[z3.BitVecVal(FULL,64),*[z3.BitVecVal(x,64) for x in INPUTS]]; specs=[]
    for node in range(count):
        la=[z3.Bool(f"a_{node}_{i}") for i in range(len(exprs))];rb=[z3.Bool(f"b_{node}_{i}") for i in range(len(exprs))]
        solver.add(z3.Or(la),z3.Or(rb));exprs.append(xor_selected(la,exprs)&xor_selected(rb,exprs));specs.append((la,rb))
    outc=[z3.Bool(f"o_{i}") for i in range(len(exprs))];solver.add(xor_selected(outc,exprs)==z3.BitVecVal(target,64));models=[]
    while len(models)<max_models:
        status=solver.check()
        if status==z3.unknown:return models,"unknown"
        if status==z3.unsat:return models,"unsat"
        model=solver.model();nodes=[]
        # model_mask avoids relying on truthiness of Z3 BoolRefs.
        for left,right in specs:
            lm=model_mask(model,left);rm=model_mask(model,right)
            nodes.append({"left":[i for i in range(len(exprs)-1) if lm>>i&1],"right":[i for i in range(len(exprs)-1) if rm>>i&1]})
        om=model_mask(model,outc);xag={"and_nodes":nodes,"output":[i for i in range(len(exprs)) if om>>i&1],"and_count":count}
        if not verify_xag(xag,target):raise AssertionError("invalid enumerated XAG")
        models.append(xag)
        literals=[]
        for group in [x for pair in specs for x in pair]+[outc]:
            literals.extend([v==z3.is_true(model.eval(v,model_completion=True)) for v in group])
        solver.add(z3.Not(z3.And(literals)))
    return models,"sat_limit"

def main():
    cache=json.loads(Path("artifacts/minmc_factor_cache.json").read_text())["functions"]
    endpoint=json.loads(Path("artifacts/global_endpoint_inventory.json").read_text())
    targets={}
    pair=json.loads(Path("artifacts/pair_terms.json").read_text())
    for x,y in pair:targets[str(x)]=x;targets[str(y)]=y
    for side in ("x","y"):
        for row in endpoint[side]:targets[str(row["truth_table"])]=row["truth_table"]
    output=Path("artifacts/xag_model_bank.json")
    previous=json.loads(output.read_text()).get("functions",{}) if output.exists() else {}
    result=dict(previous);started=time.time();batch=0
    for key,target in targets.items():
        if key in result:continue
        if batch>=12:break
        spec=cache.get(key);k=int(spec["and_count"]) if spec else 5;entry={"target":target,"known_and_count":k,"models":[]}
        for count in (k,k+1):
            models,status=enumerate_models(target,count,max_models=1,timeout_ms=200)
            entry["models"].append({"and_count":count,"status":status,"xags":models})
        result[key]=entry
        batch+=1
    predicate_users=defaultdict(set)
    for key,entry in result.items():
        for batch in entry["models"]:
            for model in batch["xags"]:
                signals=[FULL,*INPUTS]
                for node in model["and_nodes"]:
                    left=0;right=0
                    for i in node["left"]:left^=signals[i]
                    for i in node["right"]:right^=signals[i]
                    signals.append(left&right)
                for signal in signals[13:]:predicate_users[signal].add(key)
    shared={str(tt):sorted(users) for tt,users in predicate_users.items() if len(users)>1}
    Path("artifacts/xag_model_bank.json").write_text(json.dumps({"elapsed_seconds":time.time()-started,"functions":result,"processed_this_batch":batch,"total_targets":len(targets)},indent=2))
    Path("artifacts/xag_shared_predicates.json").write_text(json.dumps({"shared_predicates":shared,"count":len(shared)},indent=2))
    print(json.dumps({"functions":len(result),"shared_predicates":len(shared),"elapsed_seconds":time.time()-started},indent=2))
if __name__=="__main__":main()

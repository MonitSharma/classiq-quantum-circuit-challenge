"""Select model-bank representatives by semantic predicate union size."""
import json
from collections import defaultdict
from pathlib import Path
from minmc_xag import FULL, INPUTS

def predicates(model):
    signals=[FULL,*INPUTS];out=[]
    for node in model["and_nodes"]:
        left=0;right=0
        for i in node["left"]:left^=signals[i]
        for i in node["right"]:right^=signals[i]
        value=left&right;signals.append(value);out.append(value)
    return set(out)

def main():
    bank=json.loads(Path("artifacts/xag_model_bank.json").read_text())["functions"]
    pair=json.loads(Path("artifacts/pair_terms.json").read_text())
    endpoint=json.loads(Path("artifacts/global_endpoint_inventory.json").read_text())
    groups={"pair_x":{str(x) for x,y in pair},"pair_y":{str(y) for x,y in pair},
            "endpoint_x":{str(x["truth_table"]) for x in endpoint["x"]},"endpoint_y":{str(y["truth_table"]) for y in endpoint["y"]}}
    result={}
    for name,keys in groups.items():
        selected={};union=set();independent=0;missing=[]
        for key in keys:
            entry=bank.get(key)
            if not entry:missing.append(key);continue
            model=next((m for b in entry["models"] for m in b["xags"]),None)
            if model is None:missing.append(key);continue
            ps=predicates(model);selected[key]=sorted(ps);union.update(ps);independent+=len(ps)
        result[name]={"outputs":len(keys),"selected_models":len(selected),"missing_models":missing,"independent_and_nodes":independent,"union_and_nodes":len(union),"absolute_saving":independent-len(union),"percent_saving":(100*(independent-len(union))/independent if independent else 0)}
    Path("artifacts/multioutput_xag_selection.json").write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=="__main__":main()

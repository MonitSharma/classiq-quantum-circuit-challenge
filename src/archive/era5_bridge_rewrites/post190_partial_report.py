"""Measure saved prefixes. These are incomplete encoders, never submissions."""
import argparse,json,hashlib
from pathlib import Path
from qiskit import qasm2
import post190_information_space as i
import post190_semantic_register as s

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--frontier',required=True);p.add_argument('--witness',required=True);p.add_argument('--side',required=True);p.add_argument('--outdir',required=True);a=p.parse_args();out=Path(a.outdir);out.mkdir(parents=True,exist_ok=False)
    data=json.loads(Path(a.frontier).read_text());products,goals=s.bank(json.loads(Path(a.witness).read_text()),a.side)
    reports=[]
    for index,d in enumerate(data[:8]):
        st=i.restore(d);present=d['metrics']['present'];wanted=tuple(goals[j] for j in present)
        done=s.finish(st.clean,st.times,wanted)
        if done is None:continue
        tail,places,_=done;ops=st.ops+tuple(tail);q=s.compile_ops(ops);text=qasm2.dumps(q);q=qasm2.loads(text)
        # Verify every reported present goal and inverse phase on all64 inputs.
        r=s.verify(q,places,wanted);r.update(complete=False,present_goal_indices=present,missing_goal_indices=d['metrics']['missing'],rank_deficit=d['metrics']['rank_deficit'],nonlinear_operations=d['nonlinear_operations'],stages=d['stages'],nonlinear_dependency_depth=d['nonlinear_dependency_depth'],sha256=hashlib.sha256(text.encode()).hexdigest(),source_index=index)
        (out/f'partial_{index}.qasm').write_text(text);reports.append(r)
    (out/'report.json').write_text(json.dumps(reports,indent=2));print(reports[0])

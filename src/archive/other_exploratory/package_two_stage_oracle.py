"""Package an exhaustively verified two-stage QASM and literal matching QMOD."""
import argparse,hashlib,json,re,shutil
from pathlib import Path
from qiskit import qasm2
from classiq import qfunc,QArray,QBit,Output,allocate,H,U,CX,Constraints,OptimizationParameter,create_model,write_qmod


def package(source,kernel,record,outdir):
    assert not outdir.exists()
    sha=hashlib.sha256(source.read_bytes()).hexdigest()
    report=json.loads(source.with_suffix('.exhaustive.json').read_text())
    assert report['sha256']==sha and report['basis_inputs_checked']==4096
    q=qasm2.load(source);assert q.num_qubits==18 and set(q.count_ops())<={'u3','cx'}
    gates=[(i.operation.name,list(map(float,i.operation.params)),[q.find_bit(b).index for b in i.qubits]) for i in q.data]
    @qfunc
    def two_stage_logo_oracle(q:QArray[QBit,18]):
        for name,p,w in gates:
            if name=='cx':CX(q[w[0]],q[w[1]])
            else:U(p[0],p[1],p[2],0.0,q[w[0]])
    @qfunc
    def main(q:Output[QArray[QBit,18]]):
        allocate(18,q)
        for i in range(12):H(q[i])
        two_stage_logo_oracle(q)
    model=create_model(main,constraints=Constraints(max_width=18,optimization_parameter=OptimizationParameter.DEPTH))
    outdir.mkdir(parents=True);name=f'two_stage_{q.depth()}'
    target=outdir/f'{name}.qasm';shutil.copyfile(source,target)
    shutil.copyfile(kernel,outdir/'kernel.qasm');shutil.copyfile(record,outdir/'class_codes.json')
    write_qmod(model,name,directory=outdir,decimal_precision=17)
    qm=outdir/f'{name}.qmod'
    qm.write_text(f'// Verified standalone QASM SHA-256: {sha}\n// main adds twelve preparation Hadamards; they are absent from the oracle QASM.\n'+qm.read_text())
    body=qm.read_text().split('qfunc two_stage_logo_oracle',1)[1].split('}',1)[0]
    parsed=[]
    for name,args in re.findall(r'\b(U|CX)\(([^;]+)\);',body):
        w=list(map(int,re.findall(r'q\[(\d+)\]',args)))
        if name=='CX':parsed.append(('cx',[],w))
        else:
            p=list(map(float,args.split(',')[:4]));assert p[3]==0;parsed.append(('u3',p[:3],w))
    assert parsed==gates
    manifest=dict(depth=q.depth(),cx=q.count_ops().get('cx',0),width=18,qasm=target.name,qmod=qm.name,sha256=sha,kernel_sha256=hashlib.sha256(kernel.read_bytes()).hexdigest(),qmod_gate_match=True,qmod_gate_count=len(gates),qmod_note='Literal gate-level matching oracle; main includes a 12-Hadamard synthesis harness. Not cloud-resynthesized or submitted.')
    (outdir/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    from exhaustive_verify import exhaustive
    exhaustive(target)
    print(json.dumps(manifest,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--kernel',type=Path,required=True);p.add_argument('--record',type=Path,required=True);p.add_argument('--outdir',type=Path,required=True);a=p.parse_args();package(a.source,a.kernel,a.record,a.outdir)

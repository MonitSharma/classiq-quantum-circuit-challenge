"""Isolated adapter to the public SPARE rewrite engine.

Imports an explicitly supplied external source tree, never marks data inputs
clean, and exports every resulting operation through safe native lowering.
The binary experiment excludes temporary qutrits and extra wires. It is not
the authors' full qutrit/lowering pipeline or their unpublished front end.
"""
from __future__ import annotations
import argparse, contextlib, copy, hashlib, json, os, sys, time
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit, qasm2
from qiskit.quantum_info import Operator
from qiskit.circuit.library import UnitaryGate
from distributed_frame_search import native,materialize_output_layout


def initialize(source,deps):
    for path in [source/'Spare'/'rewriter',source,source/'Spare',deps]:
        sys.path.insert(0,str(path))
    import cirq
    from rewriter.src.compile import RewriteEngine
    from rewriter.src.nodeset import LabelledNode
    from rewriter.src.slice import GateSlice
    import rewriter.src.rewrites
    return cirq,RewriteEngine,LabelledNode,GateSlice


def import_circuit(q,clean,api,dimension=2):
    _,Engine,Node,Slice=api
    n=q.num_qubits;engine=Engine(qubits=n);engine.dimension=dimension
    clean=set(clean);assert clean<=set(range(n))
    for end in (False,True):
        boundary=Slice(qubits=n,dimension=dimension)
        for w in range(n):
            node=Node(data=dict(qubits=[w],matrix=None,ancilla=w in clean))
            node.set_sink() if end else node.set_root();boundary.set_node(node)
        if end:
            engine.add_slice(boundary,no_edges=True);break
        engine.add_slice(boundary)
        for inst in q.data:
            ws=[q.find_bit(w).index for w in inst.qubits]
            if len(ws)==1:matrix=Operator(inst.operation).data;controls=[]
            elif inst.operation.name in ('cx','ccx','mcx'):
                matrix=np.array([[0,1],[1,0]],complex);controls=[1]*(len(ws)-1)
            elif inst.operation.name=='cz':matrix=np.diag([1,-1]).astype(complex);controls=[1]
            else:raise ValueError(f'Unsupported import gate: {inst.operation.name}')
            if dimension==3:
                lifted=np.eye(3,dtype=complex);lifted[:2,:2]=matrix;matrix=lifted
            node=Node(data=dict(qubits=ws,controls=controls,
                               matrix=dict(real=matrix.real.tolist(),imaginary=matrix.imag.tolist())))
            engine.add_slice(Slice(qubits=n,dimension=dimension,gate=node))
    engine.slice_edge_collection.update_all_mappings()
    return engine


def export_circuit(engine,api,global_phase=0):
    if engine.dimension==3:
        import ancilla_convertor.gate_convertor as gc
        import ancilla_convertor.circuit_convertor
        from qiskit import transpile
        def safe_transpile(q,*args,**kwargs):
            kwargs['qubits_initially_zero']=False
            return materialize_output_layout(transpile(q,*args,**kwargs))
        gc.transpile=safe_transpile
        engine=copy.deepcopy(engine)
        engine.unroll_multicontrolled_gates();engine.convert_gateslices()
        if engine.num_qubits>18:raise ValueError(f'SPARE lowering exceeds width: {engine.num_qubits}')
    cirq=api[0];c,_=engine.build_circuit(breakdown='vvv')
    q=QuantumCircuit(engine.num_qubits,global_phase=global_phase)
    for op in c.all_operations():
        assert all(w.dimension==2 for w in op.qubits),'qutrit export is not an eligible circuit'
        ws=[w.x for w in op.qubits]
        matrix=cirq.unitary(op)
        # Preserve known controlled single-target gates rather than asking a
        # generic two-qubit decomposer to rediscover a CX (which can introduce
        # basis changes and unnecessarily large intermediate sparse support).
        if len(ws)>1:
            local=matrix[-2:,-2:];expected=np.eye(len(matrix),dtype=complex)
            expected[-2:,-2:]=local
            if np.allclose(matrix,expected,atol=1e-14,rtol=0):
                if np.allclose(local,[[0,1],[1,0]],atol=1e-14,rtol=0):q.mcx(ws[:-1],ws[-1])
                elif len(ws)==2 and np.allclose(local,np.diag([1,-1]),atol=1e-14,rtol=0):q.cz(*ws)
                else:q.append(UnitaryGate(local).control(len(ws)-1),ws)
                continue
        # Cirq matrices are big endian in op.qubits; Qiskit is little endian.
        q.append(UnitaryGate(matrix),list(reversed(ws)))
    return q


def stats(q):return dict(depth=q.depth(),cx=q.count_ops().get('cx',0),width=q.num_qubits,gates=len(q.data))


def clean_columns(q,clean):
    return [x for x in range(1<<q.num_qubits) if all(not(x>>w&1) for w in clean)]


def positive_control(api,dimension=2):
    from rewriter.src.compile_basic import gateslices_simplify, collapse_states
    q=QuantumCircuit(4);q.ccx(0,1,3);q.cz(3,2);q.ccx(0,1,3)
    engine=import_circuit(q,[3],api,dimension)
    original=Operator(q).data[:,clean_columns(q,[3])]
    roundtrip=export_circuit(engine,api)
    assert np.allclose(Operator(roundtrip).data[:,clean_columns(q,[3])],original,atol=1e-12)
    engine.merge_greedily();engine.control_rewrite()
    engine=collapse_states(engine,if_verify=False)
    engine=gateslices_simplify(engine);engine.optimizer_pass()
    out=export_circuit(engine,api)
    actual=Operator(out).data[:,clean_columns(q,[3])]
    overlap=np.vdot(original,actual);phase=overlap/abs(overlap)
    err=float(np.max(np.abs(actual-phase*original)));assert err<1e-10
    return dict(input=stats(native(q)),output=stats(native(out)),max_error=err,
                annotation='only q3 clean; q0,q1,q2 arbitrary')


def run(source,deps,path,out,dimension=2):
    assert not out.exists();out.mkdir(parents=True)
    api=initialize(source,deps)
    from rewriter.src.compile_basic import gateslices_simplify,collapse_states
    q=qasm2.load(path);report=dict(input=str(path.resolve()),input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        baseline=stats(q),mode=f'SPARE engine dimension {dimension}; native exported width <=18',stages=[])
    with (out/'engine.log').open('w') as log,contextlib.redirect_stdout(log):
        report['positive_control']=positive_control(api,dimension)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('positive control',report['positive_control'],flush=True)
    with (out/'engine.log').open('a') as log,contextlib.redirect_stdout(log):
        engine=import_circuit(q,range(12,18),api,dimension)
    print('imported full circuit',flush=True)
    stages=[('roundtrip',lambda e:e),
            ('merge',lambda e:(e.merge_greedily(),e)[1]),
            ('control',lambda e:(e.control_rewrite(),e)[1]),
            ('collapse',lambda e:collapse_states(e,if_verify=False)),
            ('simplify',gateslices_simplify),
            ('optimizer',lambda e:(e.optimizer_pass(),e)[1])]
    for name,fn in stages:
        started=time.monotonic()
        print('starting stage',name,flush=True)
        with (out/'engine.log').open('a') as log,contextlib.redirect_stdout(log):
            engine=fn(engine);engine.serialize(str(out/f'{name}.engine.json'))
            raw=export_circuit(engine,api,q.global_phase)
        candidate=native(raw);dest=out/f'{name}.qasm';dest.write_text(qasm2.dumps(candidate))
        record=dict(stage=name,seconds=time.monotonic()-started,**stats(candidate),
                    sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
        # Verification is independent of SPARE's dense-matrix routines.
        from exhaustive_verify import exhaustive
        if candidate.depth()<=q.depth():
            exhaustive(dest);record['exhaustive_verified']=True
        else:record['exhaustive_verified']=False;record['disposition']='depth regression; not promoted'
        report['stages'].append(record)
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(record,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--deps',type=Path,required=True);p.add_argument('--outdir',type=Path,required=True)
    p.add_argument('--qasm',type=Path,default=Path('artifacts/185/two_stage_185.qasm'))
    p.add_argument('--dimension',type=int,choices=(2,3),default=2)
    a=p.parse_args();run(a.source,a.deps,a.qasm,a.outdir,a.dimension)

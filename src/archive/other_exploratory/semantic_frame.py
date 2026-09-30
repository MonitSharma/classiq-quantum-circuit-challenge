"""Truth-table semantic frames for exact affine CNOT/X transitions."""
from qiskit import QuantumCircuit

FULL=(1<<4096)-1

def rank(vectors):
    basis={}; r=0
    for value in vectors:
        x=value
        while x:
            p=x.bit_length()-1
            if p in basis:x^=basis[p]
            else:basis[p]=x;r+=1;break
    return r

def coordinate_system(values):
    """Return an echelon map pivot -> (vector, coordinate mask)."""
    system={}
    for index,value in enumerate(values):
        x=value; coeff=1<<index
        while x:
            pivot=x.bit_length()-1
            if pivot in system:
                base,base_coeff=system[pivot]; x^=base; coeff^=base_coeff
            else:
                system[pivot]=(x,coeff); break
    return system

def coordinates(value,system):
    x=value; out=0
    while x:
        pivot=x.bit_length()-1
        if pivot not in system: raise ValueError("function is outside frame span")
        base,coeff=system[pivot];x^=base;out^=coeff
    return out

def _reduce(rows, width, q):
    """Reduce physical rows to a canonical basis, returning involutive ops."""
    rows=list(rows); ops=[]
    # Remove affine constant components with X operations.
    for i in range(len(rows)):
        if rows[i]&1:
            q.x(i); ops.append(("x",i)); rows[i]^=1
    pivot=0
    for col in range(1,width):
        found=next((i for i in range(pivot,len(rows)) if rows[i]>>col&1),None)
        if found is None: continue
        if found!=pivot:
            for a,b in ((pivot,found),(found,pivot),(pivot,found)):
                q.cx(a,b);ops.append(("cx",a,b))
            rows[pivot],rows[found]=rows[found],rows[pivot]
        for i in range(len(rows)):
            if i!=pivot and (rows[i]>>col&1):
                q.cx(pivot,i);ops.append(("cx",pivot,i));rows[i]^=rows[pivot]
        pivot+=1
    return rows,ops

def _inverse_ops(ops,q):
    for op in reversed(ops):
        if op[0]=="x":q.x(op[1])
        else:q.cx(op[1],op[2])

def synthesize_transition(source,target):
    """Return CX/X circuit mapping exact source truth rows to target rows."""
    if len(source)!=len(target):raise ValueError("frame size mismatch")
    all_values=[FULL,*source,*target]
    # Build a common independent function basis with constant first.
    basis_values=[]
    for value in all_values:
        if rank(basis_values+[value])>len(basis_values):basis_values.append(value)
    # Keep FULL as coordinate bit zero so X is an explicit affine operation.
    ordered=[FULL]+[v for v in basis_values if v!=FULL]
    echelon=coordinate_system(ordered)
    src=[coordinates(v,echelon) for v in source];dst=[coordinates(v,echelon) for v in target]
    q=QuantumCircuit(len(source)); reduced_src,ops_src=_reduce(src,len(echelon),q)
    temp=QuantumCircuit(len(source));reduced_dst,ops_dst=_reduce(dst,len(echelon),temp)
    if reduced_src!=reduced_dst:raise ValueError("frames have different spans")
    _inverse_ops(ops_dst,q)
    return q

def apply_circuit(rows,circuit):
    rows=list(rows)
    for inst in circuit.data:
        bits=[circuit.find_bit(q).index for q in inst.qubits]
        if inst.operation.name=="cx":rows[bits[1]]^=rows[bits[0]]
        elif inst.operation.name=="x":rows[bits[0]]^=FULL
        elif inst.operation.name=="barrier":continue
        else:raise ValueError(inst.operation.name)
    return rows

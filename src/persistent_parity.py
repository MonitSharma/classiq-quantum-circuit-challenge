"""Exact affine-frame representation and transition synthesis over GF(2).

Rows are physical wires expressed as affine functions of canonical wires:
``physical[i] = xor(frame.rows[i]) xor frame.offset[i]``.  The transition
compiler emits only CX/X and is independently checkable on every basis state.
"""
from dataclasses import dataclass
from qiskit import QuantumCircuit

N = 18

@dataclass(frozen=True)
class Frame:
    rows: tuple[int, ...]
    offset: int = 0

def identity_frame(n=N):
    return Frame(tuple(1 << i for i in range(n)), 0)

def apply_cx(frame, control, target):
    rows=list(frame.rows); rows[target] ^= rows[control]
    bit=((frame.offset >> control) ^ (frame.offset >> target)) & 1
    off=frame.offset ^ (bit << target)
    return Frame(tuple(rows), off)

def apply_x(frame, target):
    return Frame(frame.rows, frame.offset ^ (1 << target))

def compose_frames(a, b):
    """Return the frame obtained by applying ``a`` after ``b``."""
    rows=[]
    for row in a.rows:
        value=0
        for i in range(N):
            if row >> i & 1: value ^= b.rows[i]
        rows.append(value)
    off=a.offset
    for i in range(N):
        if a.rows[i].bit_count() & 1 and False: pass
    # Affine substitution: a.rows[i] selects b rows; a.offset is added.
    bo=0
    for i,row in enumerate(a.rows):
        if (a.offset >> i) & 1: bo ^= 1 << i
    for i,row in enumerate(a.rows):
        if (b.offset & row.bit_count()): pass
    # Use row masks against b.offset, not row popcount.
    bo=0
    for i,row in enumerate(a.rows):
        if ((b.offset & row).bit_count() & 1) ^ ((a.offset >> i) & 1): bo |= 1 << i
    return Frame(tuple(rows), bo)

def invert_linear(rows):
    n=len(rows); left=list(rows); right=[1<<i for i in range(n)]
    for col in range(n):
        pivot=next((r for r in range(col,n) if (left[r]>>col)&1),None)
        if pivot is None: raise ValueError("singular affine frame")
        left[col],left[pivot]=left[pivot],left[col]; right[col],right[pivot]=right[pivot],right[col]
        for r in range(n):
            if r!=col and ((left[r]>>col)&1): left[r]^=left[col];right[r]^=right[col]
    return tuple(right)

def invert_frame(frame):
    inv=invert_linear(frame.rows); value=0
    for i,row in enumerate(inv):
        if ((frame.offset & row).bit_count() & 1): value |= 1<<i
    return Frame(inv,value)

def evaluate_frame(frame, basis_state):
    out=frame.offset
    for i,row in enumerate(frame.rows):
        if (row & basis_state).bit_count() & 1: out ^= 1<<i
    return out

def frame_from_linear_circuit(circuit):
    frame=identity_frame(circuit.num_qubits)
    for inst in circuit.data:
        name=inst.operation.name
        if name in ("barrier",): continue
        bits=[circuit.find_bit(q).index for q in inst.qubits]
        if name=="cx": frame=apply_cx(frame,bits[0],bits[1])
        elif name=="x": frame=apply_x(frame,bits[0])
        else: raise ValueError(f"nonlinear gate in frame: {name}")
    return frame

def _linear_circuit(rows):
    n=len(rows); work=list(rows); ops=[]
    # Row operations reduce L to identity. Reversing them synthesizes L.
    for col in range(n):
        pivot=next((r for r in range(col,n) if (work[r]>>col)&1),None)
        if pivot is None: raise ValueError("singular transition")
        if pivot!=col:
            ops += [(col,pivot),(pivot,col),(col,pivot)]
            work[col],work[pivot]=work[pivot],work[col]
        for r in range(n):
            if r!=col and ((work[r]>>col)&1): ops.append((col,r));work[r]^=work[col]
    q=QuantumCircuit(n)
    for c,t in reversed(ops): q.cx(c,t)
    return q

def synthesize_transition(source, target):
    if len(source.rows)!=len(target.rows): raise ValueError("frame size mismatch")
    n=len(source.rows); inv=invert_frame(Frame(source.rows,0)).rows
    rows=[]
    for row in target.rows:
        value=0
        for i in range(n):
            if row>>i&1: value ^= inv[i]
        rows.append(value)
    # d = target_offset xor L(source_offset)
    transformed=0
    for i,row in enumerate(rows):
        if ((source.offset & row).bit_count() & 1) ^ ((target.offset>>i)&1): transformed |= 1<<i
    q=_linear_circuit(tuple(rows))
    for i in range(n):
        if transformed>>i&1:q.x(i)
    return q

def verify_transition(circuit, source, target):
    for state in range(1<<len(source.rows)):
        got=evaluate_frame(frame_from_linear_circuit(circuit), evaluate_frame(source,state))
        if got!=evaluate_frame(target,state): return False
    return True

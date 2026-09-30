"""Standalone QASM must retain logical wires despite elided permutations."""
import sys
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit,qasm2
from qiskit.quantum_info import Operator
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from distributed_frame_search import native

def test_elided_nontrivial_cycle_is_restored():
 q=QuantumCircuit(4);q.h(0);q.ry(.37,2);q.swap(0,1);q.swap(1,2);q.cx(2,3);q.rz(.19,1)
 serialized=qasm2.loads(qasm2.dumps(native(q)))
 assert Operator(q).equiv(Operator(serialized))
 assert set(serialized.count_ops()) <= {'u3','cx'}

def test_identity_layout_keeps_native_basis():
 q=QuantumCircuit(3);q.h(1);q.rccx(0,1,2);q.rz(.23,2)
 assert Operator(q).equiv(Operator(qasm2.loads(qasm2.dumps(native(q)))))

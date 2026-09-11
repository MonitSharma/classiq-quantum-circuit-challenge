"""Construct the logo phase oracle directly as a ZH graph.

The construction is a symbolic truth-table baseline: one 12-legged H-box per
marked input, with X conjugations on zero literals. It intentionally does not
start from an existing QASM circuit.
"""

from __future__ import annotations

import argparse
import json
import signal
import subprocess
import time
from pathlib import Path

import pyzx as zx

from search import logo


N = 12
V = zx.VertexType


def marked_values() -> list[int]:
    return [x | (y << 6) for y in range(64) for x in range(64) if logo(x, y)]


def build_graph(marked: list[int] | None = None, n: int = N) -> zx.Graph:
    marked = marked_values() if marked is None else list(marked)
    graph = zx.Graph("simple")
    current: list[int] = []
    inputs: list[int] = []
    for qubit in range(n):
        boundary = graph.add_vertex(V.BOUNDARY, qubit, 0)
        current.append(boundary)
        inputs.append(boundary)
    row = 1
    for value in marked:
        z_vertices: list[int] = []
        negative: list[bool] = []
        for qubit in range(n):
            is_negative = ((value >> qubit) & 1) == 0
            negative.append(is_negative)
            if is_negative:
                x_gate = graph.add_vertex(V.X, qubit, row, phase=1)
                graph.add_edge((current[qubit], x_gate))
                current[qubit] = x_gate
            z_gate = graph.add_vertex(V.Z, qubit, row + 1)
            graph.add_edge((current[qubit], z_gate))
            z_vertices.append(z_gate)
        hbox = graph.add_vertex(V.H_BOX, n / 2, row + 1, phase=1)
        for z_gate in z_vertices:
            graph.add_edge((z_gate, hbox))
        for qubit, is_negative in enumerate(negative):
            if is_negative:
                x_gate = graph.add_vertex(V.X, qubit, row + 2, phase=1)
                graph.add_edge((z_vertices[qubit], x_gate))
                current[qubit] = x_gate
            else:
                current[qubit] = z_vertices[qubit]
        row += 3
    outputs: list[int] = []
    for qubit in range(n):
        boundary = graph.add_vertex(V.BOUNDARY, qubit, row)
        graph.add_edge((current[qubit], boundary))
        outputs.append(boundary)
    # PyZX matrix tensor ordering is big-endian in the boundary tuples.  The
    # reverse tuple gives the repository's q0-as-least-significant convention.
    graph.set_inputs(tuple(reversed(inputs)))
    graph.set_outputs(tuple(reversed(outputs)))
    return graph


def graph_summary(graph: zx.Graph) -> dict:
    types = {}
    for vertex in graph.vertices():
        name = graph.type(vertex).name
        types[name] = types.get(name, 0) + 1
    return {"vertices": graph.num_vertices(), "edges": graph.num_edges(), "vertex_types": types}


def run(mode: str, output_dir: Path, max_seconds: int = 120) -> dict:
    marked = marked_values()
    started = time.time()
    graph = build_graph(marked)
    raw = graph_summary(graph)
    result = {
        "kind": "direct ZH truth-table phase oracle",
        "mode": mode,
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "input_qubits": N,
        "marked_terms": len(marked),
        "raw_graph": raw,
        "source": "logo(x,y) truth table; no input QASM",
    }
    if mode in {"simplify", "extract"}:
        # PyZX's ordinary ZX reducer rejects H-boxes.  Use its ZH rewrite
        # system first; extraction additionally converts the resulting
        # hypergraph back to ZX before invoking the circuit extractor.
        def timeout(_signum, _frame):
            raise TimeoutError(f"ZH simplification exceeded {max_seconds}s")
        previous = signal.signal(signal.SIGALRM, timeout)
        signal.alarm(max_seconds)
        try:
            zh_rewrites = zx.hsimplify.zh_simp(graph)
            result["zh_rewrites"] = zh_rewrites
            if mode == "extract":
                zx.hsimplify.from_hypergraph_form(graph)
                zx.simplify.full_reduce(graph, quiet=True)
            result["reduced_graph"] = graph_summary(graph)
            result["simplification_status"] = "completed"
        except TimeoutError as error:
            result["simplification_status"] = "timeout"
            result["timeout_seconds"] = max_seconds
            result["error"] = str(error)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, previous)
    if mode == "extract" and result.get("simplification_status") == "completed":
        circuit = zx.extract_circuit(graph, quiet=True)
        result["extracted"] = {
            "qubits": circuit.qubits,
            "gates": len(circuit.gates),
            "depth": circuit.depth(),
            "gate_counts": circuit.gatecount(),
        }
    result["elapsed_seconds"] = time.time() - started
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"direct_zh_{mode}.json").write_text(json.dumps(result, indent=2) + "\n")
    graph.to_json(str(output_dir / f"direct_zh_{mode}.jsongraph"))
    print(json.dumps(result, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("build", "simplify", "extract"), default="build")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/unitary_state_space/zh"))
    parser.add_argument("--max-seconds", type=int, default=120)
    args = parser.parse_args()
    run(args.mode, args.output_dir, args.max_seconds)


if __name__ == "__main__":
    main()

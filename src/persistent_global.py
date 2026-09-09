"""Joint persistent-frame compiler for the shared pair-term XAG graph."""
import json
from pathlib import Path

from qiskit import QuantumCircuit, qasm2, transpile
from xag import INPUT_TT, linear, make_graph, plan
from xag_phase import phase_many
from semantic_frame import FULL, apply_circuit, rank, synthesize_transition


def qvalue(value):
    return value ^ FULL if value & (1 << 4095) else value


def qrank(values):
    return rank([qvalue(value) for value in values])


def qcontains(rows, value):
    return qrank(list(rows) + [value]) == qrank(rows)


def same_span(left, right):
    return qrank(left) == qrank(right) and all(qcontains(right, value) for value in left) and all(qcontains(left, value) for value in right)


def form_tt(graph, form):
    value = 0
    for signal in form:
        value ^= FULL if signal == -1 else graph.tt[signal]
    return value


def target_rows(current, fixed_values, fixed_positions, storage_positions):
    source_rank = qrank(current)
    for index, value in enumerate(fixed_values):
        if qrank(list(current) + [value]) != source_rank:
            raise ValueError(f"fixed semantic value outside current frame span index={index}")
    rows = [None] * 18
    for position, value in zip(fixed_positions, fixed_values):
        rows[position] = value
    selected = [value for value in rows if value is not None]
    basis = []
    for value in current:
        if qrank(selected + [value]) > qrank(selected):
            selected.append(value)
            basis.append(value)
    for position in sorted(storage_positions):
        if rows[position] is None and basis:
            rows[position] = basis.pop(0)
    if basis:
        raise ValueError("target frame needs more clean storage wires")
    rows = [0 if value is None else value for value in rows]
    if qrank(rows) != source_rank or any(qrank(rows + [value]) != source_rank for value in current):
        raise ValueError("target frame changed semantic span")
    return rows


class Compiler:
    def __init__(self, graph):
        self.graph = graph
        self.q = QuantumCircuit(18)
        self.current = [*INPUT_TT, *([0] * 6)]
        self.wire = {value: value for value in range(12)}
        self.live = set()

    def transition(self, desired):
        transition = synthesize_transition(self.current, desired)
        self.q.compose(transition, inplace=True)
        self.current = apply_circuit(self.current, transition)
        if self.current != desired:
            raise AssertionError("semantic transition simulation mismatch")

    def toggle(self, node):
        left, right = self.graph.nodes[node]
        at, bt = form_tt(self.graph, left), form_tt(self.graph, right)
        protected = {self.wire[value] for value in self.live}
        if node in self.live:
            target = self.wire[node]
            target_value = self.graph.tt[node]
        else:
            free = [position for position, value in enumerate(self.current)
                    if value == 0 and position not in self.wire.values()]
            if not free:
                raise ValueError(f"six-ancilla pool exhausted at node {node}")
            target = free[0]
            target_value = 0
        best = None
        for pivot in range(12):
            if pivot == target or pivot in protected:
                continue
            for other in range(12):
                if other in (pivot, target) or other in protected:
                    continue
                fixed = {pivot: at, other: bt, target: target_value}
                for value in self.live:
                    fixed[self.wire[value]] = self.graph.tt[value]
                positions = list(fixed)
                storage = set(range(12)) | protected | {target}
                try:
                    desired = target_rows(self.current, list(fixed.values()), positions, storage)
                    post = desired[:]
                    product = at & bt
                    post[target] = target_value ^ product
                    next_live = (self.live - {node}) if node in self.live else (self.live | {node})
                    expected = [*INPUT_TT] + [self.graph.tt[value] for value in sorted(next_live)] + [0] * (6 - len(next_live))
                    if not same_span(post, expected):
                        continue
                    transition = synthesize_transition(self.current, desired)
                    score = (transition.depth(), transition.count_ops().get("cx", 0))
                    if best is None or score < best[0]:
                        best = (score, pivot, other, target, desired, transition)
                except ValueError:
                    continue
        if best is None:
            # Trusted fallback: restore the canonical input/live layout, use
            # the existing exact affine preparation, and return to canonical.
            # This sacrifices persistence for a hard transition but preserves
            # correctness and makes the joint schedule measurable.
            fixed_positions = list(range(12))
            fixed_values = list(INPUT_TT)
            for value, position in self.wire.items():
                if value >= 12:
                    fixed_positions.append(position)
                    fixed_values.append(self.graph.tt[value])
            try:
                canonical = target_rows(self.current, fixed_values, fixed_positions,
                                        set(range(12)) | set(fixed_positions))
            except ValueError as error:
                live_state = [(value, self.wire[value], self.current[self.wire[value]] == self.graph.tt[value], qcontains(self.current, self.graph.tt[value])) for value in self.live]
                raise ValueError(f"fallback live values unavailable for node {node}; live_state={live_state}: {error}")
            try:
                self.transition(canonical)
            except ValueError as error:
                raise ValueError(f"no clean semantic frame for node {node}; live={sorted(self.live)} rank={qrank(self.current)} zero={[i for i,v in enumerate(self.current) if v==0]}: {error}")
            pre, pivot, other = linear(self.q, left, right, self.wire)
            if node in self.live:
                target = self.wire.pop(node)
            else:
                free = sorted(set(range(12, 18)) - set(self.wire.values()))
                if not free:
                    raise ValueError(f"six-ancilla pool exhausted at node {node}")
                target = free[0]
                self.wire[node] = target
            self.q.compose(pre, inplace=True)
            self.q.rccx(pivot, other, target)
            self.q.compose(pre.inverse(), inplace=True)
            self.current[target] ^= at & bt
            if node in self.live:
                self.live.remove(node)
            else:
                self.live.add(node)
                if self.current[target] != self.graph.tt[node]:
                    raise AssertionError(f"fallback computed live node has wrong truth table {node}")
            self._check_live_semantics()
            return
        _, pivot, other, target, desired, transition = best
        self.q.compose(transition, inplace=True)
        self.current = apply_circuit(self.current, transition)
        if self.current != desired or self.current[pivot] != at or self.current[other] != bt or self.current[target] != target_value:
            raise AssertionError(f"exact frame invariant failed at node {node}")
        self.q.rccx(pivot, other, target)
        self.current[target] ^= at & bt
        if node in self.live:
            self.live.remove(node)
            self.wire.pop(node)
        else:
            self.live.add(node)
            self.wire[node] = target
            if self.current[target] != self.graph.tt[node]:
                raise AssertionError(f"computed live node has wrong truth table {node}")
        if any(self.current[position] != 0 for position in range(12, 18) if position not in self.wire.values()):
            raise AssertionError("unused ancilla became dirty")
        self._check_live_semantics()

    def _check_live_semantics(self):
        missing_inputs = [index for index, value in enumerate(INPUT_TT)
                          if not qcontains(self.current, value)]
        missing_live = [value for value in self.live
                        if not qcontains(self.current, self.graph.tt[value])]
        if missing_inputs or missing_live:
            raise AssertionError(f"semantic span lost inputs={missing_inputs} live={missing_live}")

    def phase(self, forms):
        free = [position for position in range(12, 18) if position not in self.wire.values()]
        phase_many(self.q, tuple(forms), wire=self.wire, free=free)


def build(terms, order):
    graph, roots = make_graph(terms)
    compiler = Compiler(graph)
    records = []
    live = compiler.live
    for index in order:
        path = plan(graph, frozenset(live), roots[index], max_states=300000)
        before = len(compiler.q.data)
        for node in path:
            compiler.toggle(node)
        compiler.phase(roots[index])
        records.append({"term": index, "path_length": len(path), "gates_after_phase": len(compiler.q.data), "live": sorted(compiler.live)})
    cleanup = plan(graph, frozenset(live), [], max_states=300000)
    for node in cleanup:
        compiler.toggle(node)
    if not compiler.live and compiler.current != [*INPUT_TT, *([0] * 6)]:
        try:
            compiler.transition([*INPUT_TT, *([0] * 6)])
        except ValueError as error:
            missing = [index for index, value in enumerate(INPUT_TT) if not qcontains(compiler.current, value)]
            raise ValueError(f"final frame transition failed; rank={qrank(compiler.current)} missing_inputs={missing} zero={[i for i,v in enumerate(compiler.current) if v==0]}: {error}")
    if compiler.live or compiler.current != [*INPUT_TT, *([0] * 6)]:
        raise AssertionError(f"joint compiler failed to clean its frame live={sorted(compiler.live)} rank={qrank(compiler.current)} zero={[i for i,v in enumerate(compiler.current) if v==0]}")
    output = transpile(compiler.q, basis_gates=["u3", "cx"], qubits_initially_zero=False, optimization_level=3)
    return output, records


def main():
    terms = json.loads(Path("artifacts/pair_terms.json").read_text())
    order = [9, 7, 1, 2, 5, 4, 8, 0, 6, 3]
    output, records = build(terms, order)
    print(json.dumps({"depth": output.depth(), "cx": output.count_ops().get("cx", 0), "width": output.num_qubits, "records": records}, indent=2))
    Path("artifacts/persistent_global.qasm").write_text(qasm2.dumps(output))
    Path("artifacts/persistent_global.json").write_text(json.dumps({"order": order, "depth": output.depth(), "cx": output.count_ops().get("cx", 0), "width": output.num_qubits, "records": records}, indent=2))


if __name__ == "__main__":
    main()

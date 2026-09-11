"""Bounded semantic search for an in-place six-wire y classifier.

The search state is the complete six-wire truth-signature permutation.  Only
four designated boundary wires are scored; the other two are unrestricted
garbage.  This is a bounded falsification probe, not an optimality proof.
"""

import json
import itertools
from pathlib import Path

from comparator_oracle_structure import Y_B, Y_M

ALL = (1 << 64) - 1
TARGET = [sum(((Y_B[y] >> 0) & 1) << y for y in range(64))]
TARGET += [sum(((Y_M[y] >> bit) & 1) << y for y in range(64))
           for bit in range(3)]


def gates():
    out = []
    for t in range(6): out.append(("x", (), t))
    for c in range(6):
        for t in range(6):
            if c != t: out.append(("cx", (c,), t))
    for a in range(6):
        for b in range(a + 1, 6):
            for t in range(6):
                if t not in (a, b): out.append(("rccx", (a, b), t))
    return out


GATES = gates()
OUTPUT_MAPS = list(itertools.permutations(range(6), 4))


def apply(state, gate):
    name, controls, target = gate
    values = list(state)
    if name == "x": values[target] ^= ALL
    elif name == "cx": values[target] ^= values[controls[0]]
    else: values[target] ^= values[controls[0]] & values[controls[1]]
    return tuple(values)


def score(state):
    # Fast admissible upper bound for beam ordering.  Exact distinct-wire
    # assignment is checked by best_mapping() for the reported state.
    return sum(max(64 - (state[wire] ^ TARGET[i]).bit_count()
                   for wire in range(6)) for i in range(4))


def best_mapping(state):
    return max(OUTPUT_MAPS,
               key=lambda mapping: sum(64 - (state[wire] ^ TARGET[i]).bit_count()
                                       for i, wire in enumerate(mapping)))


def exact_score(state):
    mapping = best_mapping(state)
    return sum(64 - (state[wire] ^ TARGET[i]).bit_count()
               for i, wire in enumerate(mapping))


def main(max_gates=8, beam_width=500):
    initial = tuple(sum(((y >> i) & 1) << y for y in range(64))
                   for i in range(6))
    beam = [(score(initial), initial, ())]
    seen = {initial}
    best = beam[0]
    best_exact = (exact_score(initial), initial, ())
    for depth in range(1, max_gates + 1):
        candidates = []
        for _, state, history in beam:
            for gate in GATES:
                nxt = apply(state, gate)
                h = history + (gate,)
                s = score(nxt)
                if s > best[0]: best = (s, nxt, h)
                es = exact_score(nxt)
                if es > best_exact[0]: best_exact = (es, nxt, h)
                candidates.append((s, nxt, h))
        candidates.sort(key=lambda item: (-item[0], len(item[2])))
        new = []
        for item in candidates:
            if item[1] in seen: continue
            seen.add(item[1]); new.append(item)
            if len(new) >= beam_width: break
        beam = new
        print(json.dumps({"gate_depth": depth, "best_score": best[0],
                          "max_score": 256, "beam": len(beam)}), flush=True)
        if best_exact[0] == 256:
            break
    report = {
        "max_gates": max_gates, "beam_width": beam_width,
        "best_score": best[0], "max_score": 256,
        "best_exact_score": best_exact[0],
        "best_gate_count": len(best_exact[2]),
        "best_output_wires": list(best_mapping(best_exact[1])),
        "best_history": [{"name": n, "controls": list(c), "target": t}
                         for n, c, t in best_exact[2]],
        "status": "exact boundary mapping found" if best_exact[0] == 256
                  else "bounded search did not reach exact boundary mapping",
    }
    out = Path("artifacts/comparator_oracle/y_loader/whole_register_search.json")
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

"""Mine reusable cofactors from the documented compact BDD order.

This is an analysis artifact, not a claimed circuit.  It records the exact
truth table of each reachable reduced-BDD node so later reversible compilers
can select shared cofactors without materializing the whole BDD.
"""

import itertools
import json
from pathlib import Path

from pyeda.inter import expr2bdd, exprvars, truthtable, truthtable2expr

from search import logo


ORDER = [0, 1, 5, 2, 3, 4, 11, 10, 9, 8, 6, 7]


def target_values():
    values = []
    for bits in itertools.product((0, 1), repeat=12):
        q = [0] * 12
        for i, bit in enumerate(bits):
            q[ORDER[i]] = bit
        x = sum(q[i] << i for i in range(6))
        y = sum(q[6 + i] << i for i in range(6))
        values.append(int(logo(x, y)))
    return values


def walk(node, out):
    if node is None or node.root < 0:
        return
    key = id(node)
    if key in out:
        return
    out[key] = node
    walk(node.lo, out)
    walk(node.hi, out)


def node_mask(node, assignments):
    mask = 0
    for i, bits in enumerate(assignments):
        cur = node
        while cur.root >= 0:
            cur = cur.hi if bits[cur.root - 1] else cur.lo
        if cur.root == -2:
            mask |= 1 << i
    return mask


def main():
    variables = exprvars("b", 12)
    values = target_values()
    bdd = expr2bdd(truthtable2expr(truthtable(variables, values)))
    nodes = {}
    walk(bdd.node, nodes)
    assignments = list(itertools.product((0, 1), repeat=12))
    records = []
    seen_masks = set()
    for node in nodes.values():
        mask = node_mask(node, assignments)
        if mask in (0, (1 << 4096) - 1) or mask in seen_masks:
            continue
        seen_masks.add(mask)
        support = []
        stack = [node]
        visited = set()
        while stack:
            cur = stack.pop()
            if cur is None or cur.root < 0 or id(cur) in visited:
                continue
            visited.add(id(cur))
            support.append(ORDER[cur.root - 1])
            stack.extend((cur.lo, cur.hi))
        records.append({
            "root_position": node.root,
            "root_qubit": ORDER[node.root - 1],
            "support": sorted(set(support)),
            "support_size": len(set(support)),
            "ones": mask.bit_count(),
            "truth_mask": hex(mask),
        })
    records.sort(key=lambda r: (r["support_size"], r["ones"], r["root_position"]))
    result = {
        "order": ORDER,
        "bdd_reachable_nonterminal_nodes": len(nodes),
        "unique_nonconstant_cofactors": len(records),
        "cofactors": records,
    }
    Path("artifacts/bdd_cofactor_inventory.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: result[k] for k in result if k != "cofactors"}, indent=2))
    for record in records[:20]:
        print(record["support"], record["support_size"], record["ones"])


if __name__ == "__main__":
    main()

"""Build an exact inventory of scalar factors used by rank decompositions."""

import json
from functools import lru_cache
from pathlib import Path

import numpy as np

from search import MASK, esop, truth
from pair_search import pair_circuit


PARETO_TERMS = [
    [134217724, 17997355542380544],
    [132199093370880, 134219776],
    [281479271677952, 4063232],
    [140746078289920, 251688960],
    [281466386776064, 268433408],
    [2025493932409880576, 123626338648064],
    [4611686018427387900, 17042430230528],
    [1154047404513689600, 70437463654400],
    [279223176896970752, 264398186741760],
    [105604655874048, 67112960],
]


def check_terms(terms):
    result = np.zeros((64, 64), dtype=np.uint8)
    for x, y in terms:
        result ^= np.outer(
            [(y >> i) & 1 for i in range(64)],
            [(x >> i) & 1 for i in range(64)],
        ).astype(np.uint8)
    if not np.array_equal(result, MASK):
        raise AssertionError("rank factorization does not reconstruct MASK")


def essential_support(tt):
    return [i for i in range(6) if any(
        ((tt >> n) & 1) != ((tt >> (n ^ (1 << i))) & 1)
        for n in range(64) if not (n & (1 << i))
    )]


def anf_profile(tt):
    values = [(tt >> i) & 1 for i in range(64)]
    for bit in range(6):
        for mask in range(64):
            if mask & (1 << bit):
                values[mask] ^= values[mask ^ (1 << bit)]
    monomials = [i for i, value in enumerate(values) if value]
    return {
        "degree": max((i.bit_count() for i in monomials), default=0),
        "anf_monomials": len(monomials),
    }


@lru_cache(None)
def scalar_metadata(tt):
    cubes = esop(tt, 6)
    return {
        "truth_table": tt,
        "support": essential_support(tt),
        "support_size": len(essential_support(tt)),
        "ones": tt.bit_count(),
        **anf_profile(tt),
        "esop_cubes": len(cubes),
        "esop_cost_proxy": sum(max(0, 2 * mask.bit_count() - 3)
                                for mask, _ in cubes),
    }


def main():
    pareto_path = Path("artifacts/rank_mc_pareto_terms.json")
    if not pareto_path.exists():
        check_terms(PARETO_TERMS)
        pareto_path.write_text(json.dumps(PARETO_TERMS, indent=2))
    pareto = json.loads(pareto_path.read_text())
    check_terms(pareto)

    bases = {
        "pair_terms": json.loads(Path("artifacts/pair_terms.json").read_text()),
        "rank_terms": json.loads(Path("artifacts/rank_terms.json").read_text()),
        "rank_mc_pareto_terms": pareto,
    }
    inventory = {}
    for basis_name, terms in bases.items():
        check_terms(terms)
        for term_index, (x, y) in enumerate(terms):
            for side, table in (("x", x), ("y", y)):
                key = f"{side}:{table}"
                record = inventory.setdefault(key, {"side": side, **scalar_metadata(table)})
                record.setdefault("uses", []).append({
                    "basis": basis_name,
                    "term_index": term_index,
                })
    for record in inventory.values():
        record["pair_costs"] = []
        for use in record["uses"]:
            terms = bases[use["basis"]]
            x, y = terms[use["term_index"]]
            try:
                compiled = pair_circuit(x, y)
                record["pair_costs"].append({
                    "basis": use["basis"],
                    "term_index": use["term_index"],
                    "depth": compiled.depth(),
                    "cx": compiled.count_ops().get("cx", 0),
                })
            except (ValueError, IndexError):
                pass
    output = {
        "bases": {name: {"terms": len(terms)} for name, terms in bases.items()},
        "unique_functions": len(inventory),
        "functions": sorted(inventory.values(), key=lambda r: (r["side"], r["truth_table"])),
    }
    Path("artifacts/rank_factor_inventory.json").write_text(json.dumps(output, indent=2))
    print(json.dumps({"unique_functions": output["unique_functions"], "bases": output["bases"]}, indent=2))


if __name__ == "__main__":
    main()


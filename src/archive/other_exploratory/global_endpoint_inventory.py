"""Compute compact complexity metadata for the extracted endpoint functions."""

import json
from pathlib import Path


def degree(table):
    a = [(table >> i) & 1 for i in range(64)]
    for bit in range(6):
        for i in range(64):
            if (i >> bit) & 1: a[i] ^= a[i ^ (1 << bit)]
    return max((i.bit_count() for i, v in enumerate(a) if v), default=0)


def anf_terms(table):
    a = [(table >> i) & 1 for i in range(64)]
    for bit in range(6):
        for i in range(64):
            if (i >> bit) & 1: a[i] ^= a[i ^ (1 << bit)]
    return sum(a)


def main():
    source = json.loads(Path("artifacts/global_12_edge_endpoints.json").read_text())
    cache = json.loads(Path("artifacts/minmc_factor_cache.json").read_text())["functions"]
    all_tables = {"x": sorted({e["x_truth_table"] for e in source["edges"]}),
                  "y": sorted({e["y_truth_table"] for e in source["edges"]})}
    result = {}
    for side, tables in all_tables.items():
        result[side] = []
        for table in tables:
            spec = cache.get(str(table))
            result[side].append({"truth_table": table, "weight": table.bit_count(),
                                 "degree": degree(table), "anf_terms": anf_terms(table),
                                 "in_minmc_cache": spec is not None,
                                 "minmc_and_nodes": len(spec["and_nodes"]) if spec else None})
    Path("artifacts/global_endpoint_inventory.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: {"count": len(v), "degrees": [x["degree"] for x in v],
                          "cache_hits": sum(x["in_minmc_cache"] for x in v)} for k, v in result.items()}, indent=2))


if __name__ == "__main__": main()

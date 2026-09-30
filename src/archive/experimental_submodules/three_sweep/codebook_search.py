"""Exact bounded search over 3-bit half-row label permutations."""

import itertools
import json
from pathlib import Path

from search import esop, truth
from .half_row_loader import half_codes


def shell_cost(masks, labels, levels, blank_cost=None):
    previous = 0
    total = 0
    details = []
    for level, class_index in enumerate(levels, start=1):
        shell = masks[class_index] ^ previous
        previous = masks[class_index]
        x_terms = len(esop(shell, 6))
        allowed = [labels[class_index2] for class_index2 in levels[level - 1:]]
        code_terms = len(esop(truth(allowed), 3))
        total += x_terms * code_terms
        details.append({"class_index": class_index, "x_terms": x_terms,
                        "code_terms": code_terms})
    return total, details


def search():
    base = half_codes()
    lower_results = []
    for permutation in itertools.permutations(range(1, 6)):
        labels = {0: 0, **{i: permutation[i - 1] for i in range(1, 6)}, 6: 6}
        cost, details = shell_cost(base["lower_masks"], labels, range(1, 6))
        lower_results.append({"cost": cost, "labels": labels, "details": details})
    upper_results = []
    for permutation in itertools.permutations(range(5)):
        labels = {i: permutation[i] for i in range(5)}
        labels[5] = 5
        previous = base["upper_masks"][0]
        total = len(esop(previous, 6)) * len(esop(truth([labels[i] for i in range(5)]), 3))
        details = [{"class_index": 0, "x_terms": len(esop(previous, 6)),
                    "code_terms": len(esop(truth([labels[i] for i in range(5)]), 3))}]
        for level in range(1, 5):
            shell = base["upper_masks"][level] ^ previous
            previous = base["upper_masks"][level]
            x_terms = len(esop(shell, 6))
            allowed = [labels[i] for i in range(level, 5)]
            code_terms = len(esop(truth(allowed), 3))
            total += x_terms * code_terms
            details.append({"class_index": level, "x_terms": x_terms,
                            "code_terms": code_terms})
        upper_results.append({"cost": total, "labels": labels, "details": details})
    lower = min(lower_results, key=lambda row: row["cost"])
    upper = min(upper_results, key=lambda row: row["cost"])
    return {
        "lower_baseline_cost": next(row["cost"] for row in lower_results
                                     if row["labels"] == {i: i for i in range(7)}),
        "upper_baseline_cost": next(row["cost"] for row in upper_results
                                     if row["labels"] == {i: i for i in range(6)}),
        "lower_best": lower,
        "upper_best": upper,
        "searched_lower_permutations": len(lower_results),
        "searched_upper_permutations": len(upper_results),
    }


def write(path="artifacts/three_sweep/codebook_search.json"):
    result = search()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    write()


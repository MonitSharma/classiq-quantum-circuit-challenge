import json
from pathlib import Path

import numpy as np
import pyzx as zx

from zh_direct.oracle import build_graph


def test_direct_zh_toy_marked_terms_are_exact():
    graph = build_graph([0, 3, 5], n=3)
    matrix = zx.tensor_to_matrix(zx.tensorfy(graph), 3, 3)
    expected = np.ones(1 << 3)
    expected[[0, 3, 5]] = -1
    assert np.allclose(np.diag(matrix), expected, atol=1e-10)
    assert np.max(np.abs(matrix - np.diag(np.diag(matrix)))) < 1e-10


def test_full_direct_zh_bounded_report_is_recorded():
    report = json.loads(Path("artifacts/unitary_state_space/zh/direct_zh_simplify.json").read_text())
    assert report["marked_terms"] == 1097
    assert report["simplification_status"] == "timeout"

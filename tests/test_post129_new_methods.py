from post129_new_methods import (
    _mvi_pass_terms,
    cluster_ancilla_cost,
    cofactor_values,
    dirty_selectcopy_stage,
    replication_redundancy,
    seedgrow,
    table_words,
    ClusterItem,
)
from level_encoder_search_fast import CODES, targets_for
from level_oracle import LEVEL, logo


def test_mvi_terms_exact():
    for yn, xn in [("u1", "v1"), ("u2", "v2")]:
        for orientation in ("y", "x"):
            terms = _mvi_pass_terms(yn, xn, orientation)
            for y in range(64):
                for x in range(64):
                    got = 0
                    for a, b in terms:
                        got ^= ((a >> y) & 1) & ((b >> x) & 1)
                    assert got == int(LEVEL[yn][y] + LEVEL[xn][x] >= 6)


def test_two_pass_level_identity():
    for y in range(64):
        for x in range(64):
            got = int(LEVEL["u1"][y] + LEVEL["v1"][x] >= 6) ^ int(
                LEVEL["u2"][y] + LEVEL["v2"][x] >= 6)
            assert got == int(logo(x, y))


def test_table_words_matches_target_bits():
    ytriple, _ = CODES[0]
    targets = targets_for("u1", ytriple)
    words = table_words(targets)
    for address in range(64):
        expect = sum(((targets[bit] >> address) & 1) << bit for bit in range(3))
        assert words[address] == expect


def test_dirty_selectcopy_stage_width_and_inverse_shape():
    ytriple, _ = CODES[0]
    targets = targets_for("u1", ytriple)
    q = dirty_selectcopy_stage(range(6, 12), range(6), [12, 13, 14], targets)
    assert q.num_qubits == 18
    inv = q.inverse()
    assert inv.num_qubits == 18
    assert inv.size() == q.size()


def test_cofactor_values_partition_domain():
    selectors = (0, 6, 11)
    seen = set()
    rest = [b for b in range(12) if b not in selectors]
    for assignment in range(8):
        vals = cofactor_values(selectors, assignment)
        assert len(vals) == 1 << len(rest)
        for residual, got in enumerate(vals):
            point = 0
            for j, bit in enumerate(rest):
                point |= ((residual >> j) & 1) << bit
            for j, bit in enumerate(selectors):
                point |= ((assignment >> j) & 1) << bit
            seen.add(point)
            assert got == int(logo(point & 63, (point >> 6) & 63))
    assert seen == set(range(4096))


def test_cst_replication_accounting_and_seedgrow():
    a = ClusterItem("a", frozenset({0, 1, 2}))
    b = ClusterItem("b", frozenset({1, 2, 3}))
    c = ClusterItem("c", frozenset({4}))
    assert replication_redundancy([a, b]) == 2
    assert cluster_ancilla_cost([a, b]) == 4
    clusters = seedgrow([a, b, c], ancillas=4)
    assert sorted(item.name for cluster in clusters for item in cluster) == ["a", "b", "c"]
    assert all(cluster_ancilla_cost(cluster) <= 4 for cluster in clusters)

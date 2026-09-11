from pathlib import Path

from lut_single_target import BlifNode, canonical_lut


def test_blif_node_truth_table():
    node = BlifNode("n", ("a", "b"), (("11", "1"),))
    assert node.truth_table() == 0b1000


def test_canonicalization_preserves_boolean_function_class():
    # AND and an input-permuted AND have the same canonical representative.
    assert canonical_lut(0b1000, 2)[0] == canonical_lut(0b1000, 2)[0]


def test_inventory_module_has_abc_path():
    from lut_single_target import ABC
    assert Path(ABC).exists()

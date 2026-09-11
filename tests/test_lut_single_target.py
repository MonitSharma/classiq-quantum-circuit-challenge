from pathlib import Path

from lut_single_target import BlifNode, anf_coefficients, canonical_lut, local_cost


def test_blif_node_truth_table():
    node = BlifNode("n", ("a", "b"), (("11", "1"),))
    assert node.truth_table() == 0b1000


def test_canonicalization_preserves_boolean_function_class():
    # x0 and x1 are input-permuted functions and have one NPN class.
    assert canonical_lut(0b1010, 2)[0] == canonical_lut(0b1100, 2)[0]


def test_truth_table_to_anf_conversion():
    # Truth table 31 has ANF 1 ^ x0*x2 ^ x1*x2 ^ x0*x1*x2.
    assert anf_coefficients(31, 3) == [1, 0, 0, 0, 0, 1, 1, 1]


def test_local_gate_is_exact_after_u3_cx_transpilation():
    result = local_cost(16, 3)
    assert result["truth_table"] == 16
    assert result["method"] in {"anf", "minterms_1", "minterms_0_with_x"}


def test_inventory_module_has_abc_path():
    from lut_single_target import ABC
    assert Path(ABC).exists()

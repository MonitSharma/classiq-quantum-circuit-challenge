import numpy as np

from quotient_permutation import matrix, quotient_data, search_free_layouts, transformed_table, contiguous_layout


def test_exactly_eleven_row_and_column_classes():
    rows, columns, quotient = quotient_data(matrix())
    assert len(rows) == 11
    assert len(columns) == 11
    assert sorted(map(len, rows)) == sorted([22, 2, 2, 4, 4, 5, 12, 2, 2, 4, 5])
    assert sorted(map(len, columns)) == sorted([4, 25, 7, 2, 2, 4, 4, 5, 2, 4, 5])
    assert quotient.shape == (11, 11)


def test_free_layout_preserves_exact_population():
    rows, columns, quotient = quotient_data(matrix())
    transformed = transformed_table(
        quotient,
        contiguous_layout(rows, tuple(reversed(range(11)))),
        contiguous_layout(columns, tuple(reversed(range(11)))),
    )
    assert int(transformed.sum()) == 1097


def test_screen_reports_exact_classes():
    report = search_free_layouts(samples=4, seed=42)
    assert report["class_count"] == {"rows": 11, "columns": 11}
    assert report["best_free_contiguous_layout"]["metrics"]["marked_points"] == 1097
    assert report["best_free_contiguous_layout"]["metrics"]["exact_table_sha256"]

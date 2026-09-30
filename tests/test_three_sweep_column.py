from three_sweep.column_pair_loader import column_codes, tables_from_codes


def test_column_pair_count_and_four_tables():
    codes = column_codes()
    assert codes["class_count"] == 15
    assert len(tables_from_codes(codes)) == 4


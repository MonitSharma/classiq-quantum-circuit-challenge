from three_sweep.half_row_loader import half_codes, tables_from_codes


def test_half_row_class_counts_and_tables():
    codes = half_codes()
    assert codes["lower_class_count"] == 7
    assert codes["upper_class_count"] == 6
    assert len(tables_from_codes(codes)) == 6


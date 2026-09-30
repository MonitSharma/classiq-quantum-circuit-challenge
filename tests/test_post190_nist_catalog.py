"""Regression guard against treating spectral matches as actual equivalence."""
import json
from pathlib import Path
from post190_degree_rank_bound import targets
from post190_xag_inplace_lower import outputs


def test_catalog_witnesses_match_every_protected_input():
    root = Path('artifacts/post190_nist_catalog')
    maps = json.loads((root / 'affine_maps.json').read_text())
    tables = targets()
    assert set(maps) == {'x0', 'x1', 'x2', 'y0', 'y1', 'y2'}
    for key, mapping in maps.items():
        assert sorted(mapping['input_map']) == list(range(64))
        witness = json.loads((root / (key + '_witness.json')).read_text())
        assert witness['k'] == 5
        assert [outputs(witness, x)[0] for x in range(64)] == tables[key[0]][int(key[1])]
    for side in ('x', 'y'):
        witness = json.loads((root / (side + '_merged_witness.json')).read_text())
        assert all(outputs(witness, x) == [t[x] for t in tables[side]] for x in range(64))

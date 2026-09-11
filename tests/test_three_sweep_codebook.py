from three_sweep.codebook_search import search


def test_codebook_search_finds_lower_shell_proxy_than_baseline():
    result = search()
    assert result["searched_lower_permutations"] == 120
    assert result["searched_upper_permutations"] == 120
    assert result["lower_best"]["cost"] < result["lower_baseline_cost"]


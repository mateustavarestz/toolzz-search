from src.utils.cost_tracker import calculate_cost


def test_calculate_cost_with_cache_is_lower():
    no_cache = calculate_cost(18_000, 2_000, cached_input_tokens=0)
    with_cache = calculate_cost(18_000, 2_000, cached_input_tokens=16_000)
    assert with_cache < no_cache
    assert with_cache > 0


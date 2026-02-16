"""Calculo simples de custos de token."""


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
) -> float:
    """Calcula custo estimado em USD para GPT-5 mini."""
    normal_input = max(input_tokens - cached_input_tokens, 0)
    input_cost = (normal_input / 1_000_000) * 0.25
    cached_cost = (cached_input_tokens / 1_000_000) * 0.025
    output_cost = (output_tokens / 1_000_000) * 2.00
    return input_cost + cached_cost + output_cost


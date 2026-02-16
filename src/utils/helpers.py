"""Funcoes auxiliares."""
import re


def clean_html(html: str, max_chars: int = 50_000) -> str:
    """Remove trechos pesados de HTML e limita tamanho."""
    clean = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<style[^>]*>.*?</style>", "", clean, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<!--.*?-->", "", clean, flags=re.DOTALL)
    return clean[:max_chars]


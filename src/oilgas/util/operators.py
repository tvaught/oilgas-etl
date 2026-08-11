import re

_CANONICAL_NAMES = {
    "HIGHMARK ENERGY OPERATING LLC": "HIGHMARK ENERGY OPERATING LLC",
}


def canonical_operator_name(value: str) -> str:
    """Normalize operator punctuation and return known canonical names."""
    normalized = re.sub(r"\s+", " ", value.replace(",", "")).strip()
    return _CANONICAL_NAMES.get(normalized.upper(), normalized)

from __future__ import annotations

from oilgas.extractors.models import PDFWord


def join_words(words: list[PDFWord]) -> str:

    return " ".join(w.text for w in words)


def tokenize(text: str) -> list[str]:

    return text.split()


def starts_with_any(
    text: str,
    prefixes: list[str],
) -> bool:

    return any(text.startswith(p) for p in prefixes)


def ends_with_number(text: str) -> bool:

    tokens = text.split()

    if not tokens:
        return False

    last = tokens[-1]

    return any(c.isdigit() for c in last)

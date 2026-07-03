import re

WHITESPACE_RE = re.compile(r"\s+")


def collapse_whitespace(text: str) -> str:

    return WHITESPACE_RE.sub(
        " ",
        text.strip(),
    )


def is_upper_heading(text: str) -> bool:

    return text == text.upper()


def strip_punctuation(text: str) -> str:

    return text.strip(" ,.;:")

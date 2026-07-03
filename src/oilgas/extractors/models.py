from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class PDFWord:
    text: str

    x0: float
    y0: float

    x1: float
    y1: float

    block: int
    line: int
    word: int

    @property
    def center_x(self) -> float:
        return (self.x0 + self.x1) / 2


@dataclass(slots=True)
class PDFPage:
    number: int

    width: float
    height: float
    rotation: int

    text: str

    words: list[PDFWord] = field(default_factory=list)


@dataclass(slots=True)
class PDFDocument:
    path: Path

    page_count: int

    pages: list[PDFPage]

from __future__ import annotations

from dataclasses import dataclass

from oilgas.extractors.models import PDFWord


@dataclass(slots=True)
class LayoutRow:
    index: int
    y: float
    words: list[PDFWord]

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)


class RowBuilder:
    ROW_TOLERANCE = 3.0

    def __init__(
        self,
        words: list[PDFWord],
    ):
        #
        # Expect words already sorted by (y, x)
        #
        self.words = sorted(
            words,
            key=lambda w: (w.y0, w.x0),
        )

    def build(self) -> list[LayoutRow]:

        rows: list[LayoutRow] = []

        current: list[PDFWord] = []

        current_y: float | None = None

        for word in self.words:
            if current_y is None:
                current = [word]
                current_y = word.y0
                continue

            if abs(word.y0 - current_y) <= self.ROW_TOLERANCE:
                current.append(word)

                continue

            rows.append(
                self._finish_row(
                    len(rows),
                    current_y,
                    current,
                )
            )

            current = [word]
            current_y = word.y0

        if current:
            rows.append(
                self._finish_row(
                    len(rows),
                    current_y,
                    current,
                )
            )

        return rows

    def _finish_row(
        self,
        index: int,
        y: float,
        words: list[PDFWord],
    ) -> LayoutRow:

        words.sort(key=lambda w: w.x0)

        return LayoutRow(
            index=index,
            y=y,
            words=words,
        )

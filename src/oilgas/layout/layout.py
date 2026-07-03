from __future__ import annotations

from dataclasses import dataclass

from oilgas.extractors.models import PDFPage
from oilgas.geometry.spatial import SpatialIndex

from .models import Direction, TextRegion
from .rows import LayoutRow, RowBuilder

# ----------------------------------------------------------------------
# Layout
# ----------------------------------------------------------------------


class Layout:
    ROW_TOLERANCE = 3.0

    def __init__(self, page: PDFPage):

        self.page = page

        self.spatial = SpatialIndex(page.words)

        self.words = self.spatial.words

        self.rows = RowBuilder(self.words).build()

    # --------------------------------------------------------------

    def find_phrase(self, phrase: str) -> TextRegion | None:

        target = phrase.upper().split()

        for i in range(len(self.words) - len(target) + 1):
            candidate = self.words[i : i + len(target)]

            if [w.text.upper() for w in candidate] == target:
                return TextRegion(candidate)

        return None

    # --------------------------------------------------------------
    def row_for_region(
        self,
        region: TextRegion,
    ) -> LayoutRow:

        if not region.words:
            raise ValueError("Region contains no words.")

        first_word = region.words[0]

        for row in self.rows:
            if first_word in row.words:
                return row

        raise ValueError("Could not locate containing row.")

    def row_for_phrase(
        self,
        phrase: str,
    ) -> LayoutRow:

        region = self.find_phrase(phrase)

        if region is None:
            raise ValueError(f"Phrase not found: {phrase}")

        return self.row_for_region(region)

    def right_of(
        self,
        region: TextRegion,
        tolerance: float = 3,
        max_distance: float = 250,
    ) -> TextRegion:

        words = [
            w
            for w in self.words
            if (abs(w.y0 - region.y0) <= tolerance and region.x1 < w.x0 <= region.x1 + max_distance)
        ]

        return TextRegion(words)

    # --------------------------------------------------------------

    def left_of(
        self,
        region: TextRegion,
        tolerance: float = 3,
        max_distance: float = 250,
    ) -> TextRegion:

        words = [
            w
            for w in self.words
            if (abs(w.y0 - region.y0) <= tolerance and region.x0 - max_distance <= w.x1 < region.x0)
        ]

        return TextRegion(words)

    # --------------------------------------------------------------

    def above(
        self,
        region: TextRegion,
        tolerance_x: float = 15,
        max_distance: float = 50,
    ) -> TextRegion:

        words = [
            w
            for w in self.words
            if (
                abs(w.center_x - (region.x0 + region.x1) / 2) <= tolerance_x
                and region.y0 - max_distance <= w.y1 < region.y0
            )
        ]

        return TextRegion(words)

    def below(
        self,
        region: TextRegion,
        tolerance_x: float = 15,
        max_distance: float = 50,
    ) -> TextRegion:

        words = [
            w
            for w in self.words
            if (
                abs(w.center_x - (region.x0 + region.x1) / 2) <= tolerance_x
                and region.y1 < w.y0 <= region.y1 + max_distance
            )
        ]

        return TextRegion(words)

    def find_value(
        self,
        label: str,
        direction: Direction,
    ) -> str | None:

        region = self.find_phrase(label)

        if region is None:
            return None

        lookup = {
            Direction.RIGHT: self.right_of,
            Direction.LEFT: self.left_of,
            Direction.UP: self.above,
            Direction.DOWN: self.below,
        }

        return lookup[direction](region).text

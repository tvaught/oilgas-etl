from __future__ import annotations

from oilgas.layout import Direction, Layout
from oilgas.layout.rows import LayoutRow
from oilgas.models.header import RevenueHeader
from oilgas.util.dates import require_check_date
from oilgas.util.numbers import require_decimal


class HeaderExtractor:
    """
    Extracts the statement-level metadata from the first page
    of a revenue statement.
    """

    def __init__(self, layout: Layout):
        self.layout = layout

    def extract(
        self,
    ) -> RevenueHeader:

        header_row = self._header_row()
        words = header_row.words

        check_index = next(i for i, word in enumerate(words) if word.text == "Check")
        owner_number = words[0].text

        operator = " ".join(word.text for word in words[1:check_index])

        check_number = self.layout.find_value(
            "Check Number",
            Direction.RIGHT,
        )

        if check_number is None:
            raise ValueError("Could not locate 'Check Number'.")

        check_amount = self.layout.find_value(
            "Check Amount",
            Direction.RIGHT,
        )

        check_date = self.layout.find_value(
            "Check Date",
            Direction.RIGHT,
        )

        return RevenueHeader(
            owner_number=owner_number,
            operator=operator,
            check_number=check_number,
            check_date=require_check_date(
                check_date,
            ),
            check_amount=require_decimal(check_amount, "check_amount"),
        )

    def _header_row(
        self,
    ) -> LayoutRow:

        header_row = self.layout.row_for_phrase("Check Number")

        if header_row is None:
            raise ValueError("Check Number not found.")

        return header_row

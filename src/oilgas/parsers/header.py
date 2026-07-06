from __future__ import annotations

from oilgas.layout import Direction, Layout
from oilgas.models.header import RevenueHeader
from oilgas.util.dates import (
    require_check_date,
    require_production_period,
)
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

    #
    # ----------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------
    #

    def _value_for_label(
        self,
        label: str,
        direction: Direction,
    ) -> str:

        value = self.layout.find_value(
            label,
            direction,
        )

        if value is None:
            raise ValueError(f"Could not locate '{label}'.")

        return value

    def _header_row(
        self,
    ) -> LayoutRow:

        header_row = self.layout.row_for_phrase("Check Number")

        if header_row is None:
            raise ValueError("Check Number not found.")

        return header_row

    def _find_owner_number(
        self,
        layout: Layout,
    ) -> str:

        return self._header_row(self.layout).words[0].text

    def _find_operator(
        self,
    ) -> str:

        row = self._header_row(self.layout)

        words = row.words

        check_index = next(i for i, word in enumerate(words) if word.text == "Check")

        return " ".join(word.text for word in words[1:check_index])

    def _find_production_month(
        self,
    ) -> str:

        #
        # Temporary implementation.
        #
        # Locate the first WORKING INTEREST row and
        # return the month immediately following it.
        #

        for row in self.layout.rows:
            if row.text.startswith("WORKING INTEREST"):
                words = row.words

                for i, word in enumerate(words):
                    if word.text in (
                        "Jan",
                        "Feb",
                        "Mar",
                        "Apr",
                        "May",
                        "Jun",
                        "Jul",
                        "Aug",
                        "Sep",
                        "Oct",
                        "Nov",
                        "Dec",
                    ):
                        return f"{word.text} {words[i + 1].text}"

        raise ValueError("Production month not found.")

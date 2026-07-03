from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from oilgas.document import DocumentBlock
from oilgas.layout import LayoutRow
from oilgas.parsers.columns import (
    DEFAULT_COLUMNS,
    Column,
)
from oilgas.parsers.parser_models import ParsedField, ParsedRow

#
# Logical column names
#
REVENUE_TYPE = "revenue_type"
PRODUCTION_PERIOD = "production_period"
VOLUME = "volume"
UNIT_PRICE = "unit_price"
GROSS_VALUE = "gross_value"
OWNER_INTEREST = "owner_interest"
DISTRIBUTION_INTEREST = "distribution_interest"
OWNER_VOLUME = "owner_volume"
OWNER_VALUE = "owner_value"

DETAIL_TYPES = {
    "WORKING INTEREST",
    "TRANSPORTATION",
    "TEXAS SEVERANCE TAX",
    "MARKETING",
    "COMPRESSION",
}


#
# Revenue line labels we recognize.
#
class RevenueType(StrEnum):
    WORKING_INTEREST = "WORKING INTEREST"
    TRANSPORTATION = "TRANSPORTATION"
    TEXAS_SEVERANCE_TAX = "TEXAS SEVERANCE TAX"
    MARKETING = "MARKETING"
    COMPRESSION = "COMPRESSION"


class RevenueLineExtractor:
    def __init__(
        self,
        debug: bool = False,
    ):

        self.debug = debug
        self.columns = DEFAULT_COLUMNS

    def _nearest_column(
        self,
        x: float,
    ) -> str:

        nearest = min(
            self.columns,
            key=lambda c: abs(c.center_x - x),
        )

        return nearest.name

    def _debug_tokens(
        self,
        tokens: list[ParsedField],
    ) -> None:

        print()
        print("TOKENS")
        print("-" * 72)

        print(f"{'#':>2} {'X':>8} {'Token'}")

        print("-" * 72)

        for i, token in enumerate(tokens):
            print(f"{i:2d} {token.x:8.1f} {token.value}")

        print("-" * 72)

    def extract(
        self,
        product_block: DocumentBlock,
    ) -> list[ParsedRow]:

        rows: list[ParsedRow] = []

        #
        # Skip the product heading and totals.
        #
        for layout_row in product_block.rows[1:]:
            text = layout_row.text.strip()

            if text.startswith("Total "):
                continue

            if not self._is_detail_row(text):
                continue

            rows.append(self._parse_row(layout_row))

        return rows

    def _is_detail_row(
        self,
        text: str,
    ) -> bool:

        return any(text.startswith(t) for t in DETAIL_TYPES)

    def _tokenize_row(
        self,
        row: LayoutRow,
    ) -> list[ParsedField]:
        """
        Convert PDF words into logical tokens.

        Examples

            WORKING INTEREST
            TEXAS SEVERANCE TAX
            Nov 25

        become single tokens.
        """

        words = row.words

        tokens: list[ParsedField] = []

        i = 0

        while i < len(words):
            word = words[i]

            #
            # Revenue types
            #

            if word.text == "WORKING":
                next_word = words[i + 1]

                tokens.append(
                    ParsedField(
                        value="WORKING INTEREST",
                        column="",
                        x=(word.center_x + next_word.center_x) / 2,
                    )
                )

                i += 2
                continue

            if word.text == "TEXAS":
                tokens.append(
                    ParsedField(
                        value="TEXAS SEVERANCE TAX",
                        column="",
                        x=(word.center_x + words[i + 2].center_x) / 2,
                    )
                )

                i += 3
                continue

            #
            # Month + year
            #

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
            ) and i + 1 < len(words):
                next_word = words[i + 1]

                tokens.append(
                    ParsedField(
                        value=f"{word.text} {next_word.text}",
                        column="",
                        x=(word.center_x + next_word.center_x) / 2,
                    )
                )

                i += 2
                continue

            #
            # Everything else
            #

            tokens.append(
                ParsedField(
                    value=word.text,
                    column="",
                    x=word.center_x,
                )
            )

            i += 1

        return tokens

    def _parse_row(
        self,
        row: LayoutRow,
    ) -> ParsedRow:

        parsed = ParsedRow()

        tokens = self._tokenize_row(row)

        if self.debug:
            self._debug_tokens(tokens)
        #
        # First token is always revenue type.
        #

        parsed.add(
            REVENUE_TYPE,
            tokens[0].value,
            tokens[0].x,
        )

        #
        # Second token is always production period.
        #

        parsed.add(
            PRODUCTION_PERIOD,
            tokens[1].value,
            tokens[1].x,
        )

        #
        # Remaining tokens map by x coordinate.
        #

        for token in tokens[2:]:
            column_name = self._nearest_column(
                token.x,
            )
            if self.debug:
                print(f"{token.value:15}x={token.x:7.1f}  -> {column_name}")

            parsed.add(
                column_name,
                token.value,
                token.x,
            )

        return parsed

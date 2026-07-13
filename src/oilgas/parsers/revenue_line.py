from __future__ import annotations

from dataclasses import dataclass

from oilgas.document import DocumentBlock
from oilgas.layout import LayoutRow
from oilgas.parsers.parser_models import ParsedField, ParsedRow
from oilgas.util.numbers import parse_decimal

MONTHS = {
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
}
#
# Logical column names
#
LINE_TYPE = "line_type"
REVENUE_TYPE = "revenue_type"
TAX_DEDUCT_CODE = "tax_deduct_code"
PRODUCTION_PERIOD = "production_period"
PROPERTY_VOLUME = "property_volume"
UNIT_PRICE = "unit_price"

PROPERTY_GROSS_VALUE = "property_gross_value"
PROPERTY_DEDUCTIONS = "property_deductions"
PROPERTY_NET_VALUE = "property_net_value"

OWNER_INTEREST = "owner_interest"
DISTRIBUTION_INTEREST = "distribution_interest"

OWNER_VOLUME = "owner_volume"

OWNER_GROSS_VALUE = "owner_gross_value"
OWNER_DEDUCTIONS = "owner_deductions"
OWNER_NET_VALUE = "owner_net_value"


class ColumnMap:
    """revenue_type
    production_period
    volume
    price
    gross
    owner_interest
    distribution_interest
    owner_volume
    owner_value"""

    pass


@dataclass(slots=True)
class Column:
    name: str
    center_x: float


DEFAULT_COLUMNS = [
    Column(REVENUE_TYPE, 60),
    Column(PRODUCTION_PERIOD, 160),
    Column(PROPERTY_VOLUME, 422),
    Column(UNIT_PRICE, 476),
    Column(PROPERTY_NET_VALUE, 531),
    Column(OWNER_INTEREST, 586),
    Column(DISTRIBUTION_INTEREST, 636),
    Column(OWNER_VOLUME, 701),
    Column(OWNER_NET_VALUE, 756),
]

NUMERIC_COLUMNS = [
    Column(PROPERTY_VOLUME, 422),
    Column(UNIT_PRICE, 476),
    Column(PROPERTY_NET_VALUE, 531),
    Column(OWNER_INTEREST, 586),
    Column(DISTRIBUTION_INTEREST, 636),
    Column(OWNER_VOLUME, 701),
    Column(OWNER_NET_VALUE, 756),
]


class RevenueLineExtractor:
    def __init__(
        self,
        product_block: DocumentBlock,
        debug: bool = False,
    ):
        self.product_block = product_block
        self.debug = debug
        self.columns = DEFAULT_COLUMNS
        self.numeric_columns = NUMERIC_COLUMNS

    def _nearest_column(
        self,
        x: float,
    ) -> str:

        nearest = min(
            self.numeric_columns,
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
            print(f"{i:2d} {token.x:8.1f} {token.text}")

        print("-" * 72)

    def extract(
        self,
    ) -> list[ParsedRow]:

        rows: list[ParsedRow] = []

        #
        # Skip the product heading and totals.
        #
        for layout_row in self.product_block.rows[1:]:
            text = layout_row.text.strip()

            #
            # Skip totals
            #
            if text.upper().startswith("TOTAL "):
                continue

            #
            # Skip blank rows
            #
            if not text:
                continue

            if not self._is_detail_row(layout_row):
                continue

            parsed = self._parse_row(layout_row)

            if self._is_continuation(parsed):
                if not rows:
                    raise ValueError("Continuation row encountered before any base transaction.")

                self._merge_into_previous(
                    rows[-1],
                    parsed,
                )
            else:
                rows.append(parsed)

        return rows

    def _is_detail_row(
        self,
        row: LayoutRow,
    ) -> bool:

        words = row.words

        for i in range(len(words) - 1):
            if words[i].text.upper() in MONTHS and words[i + 1].text.isdigit():
                return True

        return False

    def _tokenize_row(
        self,
        row: LayoutRow,
    ) -> list[ParsedField]:
        """
        Convert one revenue line into logical tokens.

        Supports both layouts:

            WORKING INTEREST Nov 25 ...
            ROYALTY INTEREST Feb 20 ...

        and

            Nov 21 RI TAX ...
        """

        words = row.words

        tokens: list[ParsedField] = []

        #
        # ------------------------------------------------------------------
        # Chevron layout
        #
        #     Nov 21 RI TAX ...
        #     Nov 21 OR TAX ...
        #     Nov 21 DEDUCT ...
        # ------------------------------------------------------------------
        #
        if len(words) >= 4 and words[0].text.upper() in MONTHS and words[1].text.isdigit():
            #
            # Revenue type begins after the month/year.
            #
            if words[2].text in {"RI", "OR", "WI"}:
                revenue_end = 4  # RI TAX, OR TAX, WI SEV, WI TRN
            else:
                revenue_end = 3  # DEDUCT, TRN, MIS

            revenue_words = words[2:revenue_end]

            tokens.append(
                ParsedField(
                    text=" ".join(w.text for w in revenue_words),
                    x=sum(w.center_x for w in revenue_words) / len(revenue_words),
                )
            )

            #
            # Production period
            #
            tokens.append(
                ParsedField(
                    text=f"{words[0].text} {words[1].text}",
                    x=(words[0].center_x + words[1].center_x) / 2,
                )
            )

            #
            # Remaining numeric values
            #
            for word in words[revenue_end:]:
                tokens.append(
                    ParsedField(
                        text=word.text,
                        x=word.center_x,
                    )
                )

            return tokens

        #
        # ------------------------------------------------------------------
        # Standard layout (Highmark / Apache)
        #
        #     WORKING INTEREST Nov 25 ...
        # ------------------------------------------------------------------
        #

        month_index = None

        for i in range(len(words) - 1):
            if words[i].text.upper() in MONTHS and words[i + 1].text.isdigit():
                month_index = i
                break

        if month_index is None:
            raise ValueError(f"Could not locate production period:\n{row.text}")

        revenue_words = words[:month_index]

        if not revenue_words:
            raise ValueError(f"No revenue type detected:\n{row.text}")

        tokens.append(
            ParsedField(
                text=" ".join(w.text for w in revenue_words),
                x=sum(w.center_x for w in revenue_words) / len(revenue_words),
            )
        )

        month = words[month_index]
        year = words[month_index + 1]

        tokens.append(
            ParsedField(
                text=f"{month.text} {year.text}",
                x=(month.center_x + year.center_x) / 2,
            )
        )

        for word in words[month_index + 2 :]:
            tokens.append(
                ParsedField(
                    text=word.text,
                    x=word.center_x,
                )
            )

        return tokens

    def _parse_row(
        self,
        row: LayoutRow,
    ) -> ParsedRow:

        parsed = ParsedRow()

        tokens = self._tokenize_row(row)

        if tokens[0].text == "DEDUCT" or tokens[0].text.startswith("DEDUCT "):
            return self._parse_chevron_deduct(tokens)

        if self.debug:
            self._debug_tokens(tokens)
        #
        # First token is always revenue type.
        # (for now make this also the line type)
        #
        parsed.add(
            LINE_TYPE,
            tokens[0].text,
            tokens[0].x,
        )

        parsed.add(
            REVENUE_TYPE,
            tokens[0].text,
            tokens[0].x,
        )

        #
        # Second token is always production period.
        #

        parsed.add(
            PRODUCTION_PERIOD,
            tokens[1].text,
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
                print(f"{token.text:15}x={token.x:7.1f}  -> {column_name}")

            parsed.add(
                column_name,
                token.text,
                token.x,
            )

        self._normalize_owner_net_value(parsed)

        if self.debug:
            self._debug_fields(parsed)

        return parsed

    def _debug_fields(
        self,
        parsed: ParsedRow,
    ) -> None:
        print()
        print("FIELDS")
        print("-" * 72)

        for name, field in parsed.fields.items():
            print(f"{name:24} : {field.text:15} (x={field.x:.1f})")

        print("-" * 72)

    def _normalize_owner_net_value(
        self,
        parsed: ParsedRow,
    ) -> None:
        """
        Some XTO/Chevron-style TRN, MIS, TRT, GAT, and DEDUCT rows contain only an
        owner-level amount. Its x-coordinate can fall closer to owner_volume
        than owner_net_value, so normalize it after all numeric tokens have
        been assigned.
        """

        revenue_type = parsed.get(REVENUE_TYPE)

        if revenue_type not in {"TRN", "MIS", "TRT", "GAT", "DEDUCT"}:
            return

        if parsed.get(OWNER_NET_VALUE) is not None:
            return

        owner_volume = parsed.field(OWNER_VOLUME)

        if owner_volume is None:
            return

        if parse_decimal(owner_volume.text) is None:
            return

        parsed.fields.pop(OWNER_VOLUME)
        parsed.add(
            OWNER_NET_VALUE,
            owner_volume.text,
            owner_volume.x,
        )

    def _is_continuation(
        self,
        record: ParsedRow,
    ) -> bool:
        line_type = record.get(LINE_TYPE)
        revenue_type = record.get(REVENUE_TYPE)
        interest_type = record.get("interest_type")

        transaction_type = line_type or revenue_type

        return (
            transaction_type in {"TRN", "MIS", "TRT", "GAT"}
            and interest_type is None
            and record.get(OWNER_NET_VALUE) is not None
        )

    def _merge_into_previous(
        self,
        previous: ParsedRow,
        continuation: ParsedRow,
    ) -> None:
        previous_type = previous.get(LINE_TYPE) or previous.get(REVENUE_TYPE)

        previous_code = (previous_type or "").split()[-1]

        if previous_code not in {"SEV", "MIS"}:
            raise ValueError(
                "Continuation row can only be merged into previous SEV or MIS row. "
                f"Previous row type was {previous_type!r}."
            )

        previous_value = parse_decimal(previous.get(OWNER_NET_VALUE))
        continuation_value = parse_decimal(continuation.get(OWNER_NET_VALUE))

        if previous_value is None:
            raise ValueError("Previous SEV row is missing owner_net_value.")

        if continuation_value is None:
            raise ValueError("Continuation row is missing owner_net_value.")

        field = previous.field(OWNER_NET_VALUE)
        x = field.x if field is not None else 0

        previous.add(
            OWNER_NET_VALUE,
            str(previous_value + continuation_value),
            x,
        )

    def find_period(tokens: list[str]) -> int:

        for i, token in enumerate(tokens[:-1]):
            if token.upper() in MONTHS:
                #
                # Next token should be 2-digit year
                #
                if tokens[i + 1].isdigit():
                    return i

        raise ValueError(f"Could not locate production month: {' '.join(tokens)}")

    def _parse_chevron_deduct(
        self,
        tokens: list[ParsedField],
    ) -> ParsedRow:

        parsed = ParsedRow()

        parsed.add(
            LINE_TYPE,
            "DEDUCT",
            tokens[0].x,
        )

        parsed.add(
            REVENUE_TYPE,
            "DEDUCT",
            tokens[0].x,
        )

        parsed.add(
            PRODUCTION_PERIOD,
            tokens[1].text,
            tokens[1].x,
        )

        #
        # owner interest
        #
        parsed.add(
            OWNER_INTEREST,
            tokens[2].text,
            tokens[2].x,
        )

        #
        # distribution interest
        #
        parsed.add(
            DISTRIBUTION_INTEREST,
            tokens[3].text,
            tokens[3].x,
        )

        #
        # property deduction
        #
        parsed.add(
            PROPERTY_NET_VALUE,
            tokens[4].text,
            tokens[4].x,
        )

        #
        # owner deduction
        #
        parsed.add(
            OWNER_NET_VALUE,
            tokens[5].text,
            tokens[5].x,
        )

        return parsed

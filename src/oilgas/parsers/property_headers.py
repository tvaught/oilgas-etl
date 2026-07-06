from __future__ import annotations

import re
from abc import ABC, abstractmethod

from oilgas.layout import LayoutRow

US_STATE_CODES = {
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
}


class PropertyHeaderParser(ABC):
    @abstractmethod
    def matches(
        self,
        row: LayoutRow,
    ) -> bool:
        """
        Return True if this row begins a property section.
        """

    @abstractmethod
    def parse(
        self,
        text: str,
    ) -> dict[str, str | None] | None:
        """
        Parse metadata from a property header.
        """


# ----------------------------------------------------------------------
# Property:
#     <code> <name>,
#     State: TX,
#     County: HENDERSON,
#     Operator API# - 1702722199
# ----------------------------------------------------------------------


class LabeledHeaderParser(
    PropertyHeaderParser,
):
    HEADER_RE = re.compile(
        r"""
        ^Property:\s+

        (?P<property_code>\S+)

        \s+

        (?P<property_name>.+?)

        ,\s*State:\s*

        (?P<state>[A-Z]{2})

        ,\s*County:\s*

        (?P<county>.+?)

        (?:,\s*Operator\s+API#\s*-\s*
            (?P<api_number>\d+)
        )?

        \s*$

        """,
        re.VERBOSE,
    )

    def matches(
        self,
        row: LayoutRow,
    ) -> bool:

        text = row.text.strip()

        return text.startswith("Property:") and "State:" in text and "County:" in text

    def parse(
        self,
        text: str,
    ) -> dict[str, str | None] | None:

        match = self.HEADER_RE.match(text)

        if match is None:
            return None

        return {
            "property_code": match.group("property_code"),
            "property_name": match.group("property_name"),
            "state": match.group("state"),
            "county": match.group("county").strip(),
            "api_number": match.group("api_number"),
        }


# ----------------------------------------------------------------------
#     0028829-00001 SPRINGER 10-23 E/2 UNIT TX WINKLER
# ----------------------------------------------------------------------


class CompactHeaderParser(
    PropertyHeaderParser,
):
    PROPERTY_RE = re.compile(r"^(?:\d{6}-\d{5}|[A-Z]\d{6}-\d{3,5})\b")

    def matches(
        self,
        row: LayoutRow,
    ) -> bool:

        text = row.text.strip()

        if text.startswith("Property:"):
            text = text[len("Property:") :].strip()

        return bool(self.PROPERTY_RE.match(text))

    def parse(
        self,
        text: str,
    ) -> dict[str, str | None] | None:

        text = text.strip()

        if text.startswith("Property:"):
            text = text[len("Property:") :].strip()

        if ", State:" in text:
            import re

            m = re.match(
                r"""
                (?P<property_code>\S+)\s+
                (?P<property_name>.+?),
                \s*State:\s*
                (?P<state>[A-Z]{2}),
                \s*County:\s*
                (?P<county>.+)
                """,
                text,
                re.VERBOSE,
            )

            if m is None:
                return None

            return {
                "property_code": m.group("property_code"),
                "property_name": m.group("property_name"),
                "state": m.group("state"),
                "county": m.group("county").strip(),
                "api_number": None,
            }
        #
        # Apache includes a "Property:" prefix.
        # Chevron starts directly with the property code.
        #
        if text.startswith("Property:"):
            text = text[len("Property:") :].strip()

        property_code, remainder = text.split(maxsplit=1)

        tokens = remainder.split()

        #
        # Find the last valid state abbreviation.
        #
        state_index = None

        for i in range(len(tokens) - 1, -1, -1):
            if tokens[i] in US_STATE_CODES:
                state_index = i
                break

        if state_index is None:
            return None

        return {
            "property_code": property_code,
            "property_name": " ".join(tokens[:state_index]),
            "state": tokens[state_index],
            "county": " ".join(tokens[state_index + 1 :]),
            "api_number": None,
        }


ALL_PROPERTY_HEADER_PARSERS = [
    LabeledHeaderParser(),
    CompactHeaderParser(),
]

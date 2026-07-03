from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ParsedField:
    """
    A single parsed table cell.

    Keeps both the extracted text and the spatial location
    that produced it.
    """

    value: str
    column: str
    x: float


@dataclass(slots=True)
class ParsedRow:
    """
    One parsed table row.

    Keys are logical column names.

    Example:

        {
            "owner_value": ParsedField(...),
            "gross_value": ParsedField(...),
        }
    """

    fields: dict[str, ParsedField] = field(default_factory=dict)

    def add(
        self,
        column: str,
        value: str,
        x: float,
    ) -> None:

        self.fields[column] = ParsedField(
            value=value,
            column=column,
            x=x,
        )

    def get(self, column: str) -> str | None:

        field = self.fields.get(column)

        return field.value if field else None

    def require(self, column: str) -> str:

        value = self.get(column)

        if value is None:
            raise ValueError(f"Missing required column '{column}'")

        return value

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ParsedField:
    text: str
    x: float


@dataclass(slots=True)
class ParsedRow:
    fields: dict[str, ParsedField] = field(default_factory=dict)

    def add(
        self,
        column: str,
        text: str,
        x: float,
    ) -> None:

        self.fields[column] = ParsedField(
            text=text,
            x=x,
        )

    def get(
        self,
        column: str,
    ) -> str | None:

        field = self.fields.get(column)

        return field.text if field else None

    def field(
        self,
        column: str,
    ) -> ParsedField | None:

        return self.fields.get(column)

    def require(
        self,
        column: str,
    ) -> str:

        value = self.get(column)

        if value is None:
            raise ValueError(f"Missing required column '{column}'")

        return value

    def __contains__(
        self,
        column: str,
    ) -> bool:

        return column in self.fields

    def items(self):

        return self.fields.items()

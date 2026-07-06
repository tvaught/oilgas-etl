from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, StrEnum
from typing import Any

from oilgas.parsers.property_headers import PropertyHeaderParser


class BlockType(StrEnum):
    HEADER = "header"
    PROPERTY = "property"
    PRODUCT = "product"
    TABLE = "table"
    FOOTER = "footer"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class DocumentBlock:
    type: BlockType
    start_row: int
    end_row: int
    rows: list[LayoutRow]
    parser: PropertyHeaderParser | None = None
    children: list["DocumentBlock"] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def header(self):

        return self.rows[0]

    @property
    def text(self):

        return "\n".join(r.text for r in self.rows)

    def meta(
        self,
        key: str,
    ) -> Any:

        try:
            return self.metadata[key]

        except KeyError:
            raise ValueError(f"Missing metadata '{key}' in {self.type} block.")

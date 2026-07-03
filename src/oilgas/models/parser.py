from dataclasses import dataclass, field


@dataclass(slots=True)
class ParsedRow:
    fields: dict[str, str] = field(default_factory=dict)

    def get(self, key: str, default: str | None = None) -> str | None:
        return self.fields.get(key, default)

from oilgas.models.parser import ParsedRow


def test_parsed_row_get_returns_existing_field() -> None:
    row = ParsedRow(fields={"owner_net_value": "123.45"})

    assert row.get("owner_net_value") == "123.45"


def test_parsed_row_get_returns_default_for_missing_field() -> None:
    row = ParsedRow()

    assert row.get("missing") is None
    assert row.get("missing", "fallback") == "fallback"


def test_parsed_row_fields_default_to_empty_dict() -> None:
    first = ParsedRow()
    second = ParsedRow()

    first.fields["line_type"] = "WORKING INTEREST"

    assert second.fields == {}

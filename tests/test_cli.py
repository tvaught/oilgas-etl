from pathlib import Path

from oilgas.cli import _pdf_files


def test_pdf_files_recursively_finds_pdf_files_case_insensitively(tmp_path) -> None:
    nested = tmp_path / "operator" / "revenue"
    nested.mkdir(parents=True)
    root_pdf = tmp_path / "root.pdf"
    nested_pdf = nested / "statement.PDF"
    ignored = nested / "notes.txt"
    root_pdf.write_bytes(b"root")
    nested_pdf.write_bytes(b"nested")
    ignored.write_text("not a PDF")

    assert _pdf_files(tmp_path) == [nested_pdf, root_pdf]


def test_pdf_files_returns_a_single_file_unchanged(tmp_path) -> None:
    pdf = Path(tmp_path) / "statement.pdf"
    pdf.write_bytes(b"statement")

    assert _pdf_files(pdf) == [pdf]

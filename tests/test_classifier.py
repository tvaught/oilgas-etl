from pathlib import Path

from oilgas.classifier import DocumentClassifier, DocumentType
from oilgas.extractors.models import PDFDocument, PDFPage


def document(*page_texts: str) -> PDFDocument:
    return PDFDocument(
        path=Path("fixture.pdf"),
        page_count=len(page_texts),
        pages=[
            PDFPage(
                number=i,
                width=800,
                height=600,
                rotation=0,
                text=text,
            )
            for i, text in enumerate(page_texts, start=1)
        ],
    )


def test_classifies_highmark_revenue() -> None:
    doc = document(
        "Highmark Energy Operating LLC\nRevenue Statement\nCheck Number\nCheck Date"
    )

    assert DocumentClassifier.classify(doc) == DocumentType.HIGHMARK_REVENUE


def test_classifies_highmark_jib_even_when_invoice_is_after_statement_page() -> None:
    doc = document(
        "Statement of Account\nOutstanding Invoice Details",
        "Highmark Energy Operating LLC\nOperator Invoice - JIB\n"
        "Invoice Number 10*05-AR-3084\nOp Accounting Month May 2026",
    )

    assert DocumentClassifier.classify(doc) == DocumentType.HIGHMARK_JIB


def test_classifies_highmark_statement() -> None:
    doc = document("Statement of Account\nOutstanding Invoice Details")

    assert DocumentClassifier.classify(doc) == DocumentType.HIGHMARK_STATEMENT


def test_classifies_xto_revenue() -> None:
    doc = document("XTO Energy\nRevenue detail")

    assert DocumentClassifier.classify(doc) == DocumentType.XTO_REVENUE


def test_classifies_unknown() -> None:
    doc = document("Some unrelated PDF text")

    assert DocumentClassifier.classify(doc) == DocumentType.UNKNOWN
